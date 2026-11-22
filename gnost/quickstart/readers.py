"""Readers that turn one kind of project file into quickstart steps.

Each `SourceReader` knows one file type (package.json, Makefile, Dockerfile, ...) and reports only
what that file says, naming the file. Adding support for another file type means adding a class to
`default_readers`. Nothing is guessed: a missing file or an unknown shape gives no steps.
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Dict, Iterable, Optional, Sequence, Tuple

from gnost.languages.manifests import read_text
from gnost.quickstart.models import Quickstart, Step

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


class SourceReader(ABC):
    """Reads one kind of project file and returns the steps it contains.

    A `fallback` reader only fills groups that no other reader filled (CI files are evidence of
    last resort, not the first thing to show).
    """

    fallback: bool = False

    @abstractmethod
    def read(self, root: str) -> Quickstart:
        """Steps found under `root`; an empty Quickstart when the file is absent."""

    @staticmethod
    def path(root: str, name: str) -> Optional[str]:
        """Full path of `name` in the project root, or None when it does not exist."""
        full = os.path.join(root, name)
        return full if os.path.isfile(full) else None


# ------------------------------------------------------------------ JavaScript


class PackageJsonReader(SourceReader):
    """package.json: package manager, scripts and the required Node version."""

    SCRIPT_GROUPS: Dict[str, Tuple[str, ...]] = {
        "build": ("build",),
        "run": ("dev", "start", "serve"),
        "test": ("test",),
    }

    def read(self, root: str) -> Quickstart:
        found = Quickstart()
        full = self.path(root, "package.json")
        if full is None:
            return found
        try:
            data = json.loads(read_text(full))
        except ValueError:
            return found
        if not isinstance(data, dict):
            return found
        manager = self._manager(root, data)
        engines = data.get("engines")
        node = engines.get("node") if isinstance(engines, dict) else None
        if isinstance(node, str):
            found.add(
                "prerequisites",
                Step(f"Node.js {node}", "package.json", command=False),
            )
        found.add("install", Step(f"{manager} install", "package.json"))
        scripts = data.get("scripts")
        if isinstance(scripts, dict):
            for group, names in self.SCRIPT_GROUPS.items():
                for name in names:
                    if name in scripts:
                        found.add(group, Step(self._run(manager, name), "package.json"))
        return found

    @staticmethod
    def _manager(root: str, data: Dict[str, object]) -> str:
        """The package manager named by `packageManager` or by the lock file; npm otherwise."""
        declared = data.get("packageManager")
        if isinstance(declared, str) and declared.split("@")[0] in (
            "npm",
            "yarn",
            "pnpm",
            "bun",
        ):
            return declared.split("@")[0]
        for lock, name in (
            ("pnpm-lock.yaml", "pnpm"),
            ("yarn.lock", "yarn"),
            ("bun.lockb", "bun"),
        ):
            if os.path.isfile(os.path.join(root, lock)):
                return name
        return "npm"

    @staticmethod
    def _run(manager: str, script: str) -> str:
        """`npm start` and `npm test` have short forms; other scripts need `run`."""
        if manager == "npm" and script not in ("start", "test"):
            return f"npm run {script}"
        return f"{manager} {script}"


# ---------------------------------------------------------------------- Python


class PyProjectReader(SourceReader):
    """pyproject.toml: Python version, how to install, console scripts and the test tool."""

    TEST_EXTRAS = ("test", "tests", "dev")

    def read(self, root: str) -> Quickstart:
        found = Quickstart()
        full = self.path(root, "pyproject.toml")
        if full is None:
            return found
        try:
            data = tomllib.loads(read_text(full))
        except ValueError:
            return found
        project = data.get("project", {})
        tool = data.get("tool", {})
        requires = project.get("requires-python")
        if isinstance(requires, str):
            found.add(
                "prerequisites",
                Step(f"Python {requires}", "pyproject.toml", command=False),
            )
        if "poetry" in tool:
            found.add("install", Step("poetry install", "pyproject.toml"))
        elif os.path.isfile(os.path.join(root, "uv.lock")):
            found.add("install", Step("uv sync", "pyproject.toml"))
        elif project:
            found.add("install", Step("pip install -e .", "pyproject.toml"))
            extras = project.get("optional-dependencies", {})
            for name in self.TEST_EXTRAS:
                if name in extras:
                    found.add(
                        "install", Step(f'pip install -e ".[{name}]"', "pyproject.toml")
                    )
                    break
        scripts = project.get("scripts", {})
        for name in list(scripts)[:3]:
            found.add("run", Step(str(name), "pyproject.toml"))
        if "pytest" in tool or "pytest" in json.dumps(data).lower():
            found.add("test", Step("pytest", "pyproject.toml"))
        return found


class RequirementsReader(SourceReader):
    """requirements.txt or setup.py, for projects without a pyproject.toml."""

    def read(self, root: str) -> Quickstart:
        found = Quickstart()
        if self.path(root, "pyproject.toml"):
            return found  # that file is the better source
        if self.path(root, "requirements.txt"):
            found.add(
                "install", Step("pip install -r requirements.txt", "requirements.txt")
            )
        elif self.path(root, "setup.py"):
            found.add("install", Step("pip install -e .", "setup.py"))
        return found


# ------------------------------------------------------------------- Makefile


class MakefileReader(SourceReader):
    """Makefile: targets with the usual names for install, build, run and test."""

    TARGET = re.compile(r"^([A-Za-z0-9_-]+)\s*:(?!=)")
    TARGET_GROUPS: Dict[str, Tuple[str, ...]] = {
        "install": ("setup", "install", "deps", "bootstrap"),
        "build": ("build", "compile"),
        "run": ("run", "dev", "serve", "start"),
        "test": ("test", "tests", "check"),
    }

    def read(self, root: str) -> Quickstart:
        found = Quickstart()
        full = self.path(root, "Makefile") or self.path(root, "makefile")
        if full is None:
            return found
        targets = {
            m.group(1)
            for line in read_text(full).splitlines()
            if (m := self.TARGET.match(line))
        }
        for group, names in self.TARGET_GROUPS.items():
            for name in names:
                if name in targets:
                    found.add(group, Step(f"make {name}", os.path.basename(full)))
        return found


# --------------------------------------------------------------------- Docker


class DockerfileReader(SourceReader):
    """Dockerfile: build and run commands, with the port it declares."""

    EXPOSE = re.compile(r"^\s*EXPOSE\s+(\d+)", re.MULTILINE | re.IGNORECASE)

    def read(self, root: str) -> Quickstart:
        found = Quickstart()
        full = self.path(root, "Dockerfile")
        if full is None:
            return found
        folder = os.path.basename(os.path.abspath(root)).lower()
        image = re.sub(r"[^a-z0-9._-]+", "-", folder).strip("-") or "app"
        port = self.EXPOSE.search(read_text(full))
        found.add("prerequisites", Step("Docker", "Dockerfile", command=False))
        found.add("build", Step(f"docker build -t {image} .", "Dockerfile"))
        mapping = f" -p {port.group(1)}:{port.group(1)}" if port else ""
        found.add("run", Step(f"docker run{mapping} {image}", "Dockerfile"))
        return found


class ComposeReader(SourceReader):
    """docker-compose.yml or compose.yaml: one command to start every service."""

    NAMES = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")

    def read(self, root: str) -> Quickstart:
        found = Quickstart()
        for name in self.NAMES:
            if self.path(root, name):
                found.add("prerequisites", Step("Docker", name, command=False))
                found.add("run", Step("docker compose up", name))
                break
        return found


# ------------------------------------------------------------------------- CI


class CiReader(SourceReader):
    """GitHub Actions workflows: the install and test commands the project's CI runs."""

    fallback = True

    INSTALL = re.compile(
        r"^(npm (ci|install)|yarn( install)?|pnpm install|pip install .+|poetry install|uv sync)$"
    )
    TEST = re.compile(
        r"^(npm (run )?test|yarn test|pnpm test|(python -m )?pytest\b.*|"
        r"(\./)?mvnw? .*\b(test|verify)\b.*|\./gradlew test|go test .*|cargo test)$"
    )
    PER_GROUP = 2

    def read(self, root: str) -> Quickstart:
        found = Quickstart()
        folder = os.path.join(root, ".github", "workflows")
        if not os.path.isdir(folder):
            return found
        counts = {"install": 0, "test": 0}
        for name in sorted(os.listdir(folder)):
            if not name.endswith((".yml", ".yaml")):
                continue
            source = f".github/workflows/{name}"
            for command in self._commands(read_text(os.path.join(folder, name))):
                if any(c in command for c in "$|&;<>`"):
                    continue  # variables and pipelines are not something to copy
                for group, pattern in (("install", self.INSTALL), ("test", self.TEST)):
                    if counts[group] < self.PER_GROUP and pattern.match(command):
                        before = len(getattr(found, group))
                        found.add(group, Step(command, source))
                        counts[group] += len(getattr(found, group)) - before
        return found

    @staticmethod
    def _commands(text: str) -> Iterable[str]:
        """The shell lines of every `run:` step, one command per line."""
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            match = re.match(r"^(\s*)(?:-\s+)?run:\s*(.*)$", lines[i])
            i += 1
            if not match:
                continue
            indent, rest = len(match.group(1)), match.group(2).strip()
            if rest and rest not in ("|", ">", "|-", ">-"):
                yield rest
                continue
            while i < len(lines):
                line = lines[i]
                if line.strip() and len(line) - len(line.lstrip()) <= indent:
                    break
                if line.strip():
                    yield line.strip()
                i += 1


# ----------------------------------------------------------------- environment


class EnvExampleReader(SourceReader):
    """.env.example and friends: the NAMES of the variables, never their values."""

    NAMES = (".env.example", ".env.sample", ".env.template", "example.env")
    VARIABLE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")

    def read(self, root: str) -> Quickstart:
        found = Quickstart()
        for name in self.NAMES:
            full = self.path(root, name)
            if full is None:
                continue
            for line in read_text(full).splitlines():
                match = self.VARIABLE.match(line)
                if match and not line.lstrip().startswith("#"):
                    found.add("environment", Step(match.group(1), name, command=False))
        return found


# ------------------------------------------------------------------------ Java


class MavenReader(SourceReader):
    """pom.xml: Java version, the Maven commands, and Spring Boot's run goal."""

    JAVA = re.compile(
        r"<(?:maven\.compiler\.release|maven\.compiler\.source|java\.version)>\s*([0-9.]+)\s*<"
    )

    def read(self, root: str) -> Quickstart:
        found = Quickstart()
        full = self.path(root, "pom.xml")
        if full is None:
            return found
        text = read_text(full)
        mvn = "./mvnw" if self.path(root, "mvnw") else "mvn"
        java = self.JAVA.search(text)
        if java:
            found.add(
                "prerequisites", Step(f"Java {java.group(1)}", "pom.xml", command=False)
            )
        found.add("build", Step(f"{mvn} package", "pom.xml"))
        found.add("test", Step(f"{mvn} test", "pom.xml"))
        if "spring-boot-maven-plugin" in text:
            found.add("run", Step(f"{mvn} spring-boot:run", "pom.xml"))
        return found


class GradleReader(SourceReader):
    """build.gradle(.kts): the Gradle commands, and Spring Boot's or the application plugin's run task."""

    def read(self, root: str) -> Quickstart:
        found = Quickstart()
        name = self.path(root, "build.gradle.kts") and "build.gradle.kts"
        name = name or (self.path(root, "build.gradle") and "build.gradle")
        if not name:
            return found
        text = read_text(os.path.join(root, name))
        gradle = "./gradlew" if self.path(root, "gradlew") else "gradle"
        found.add("build", Step(f"{gradle} build", name))
        found.add("test", Step(f"{gradle} test", name))
        if "org.springframework.boot" in text:
            found.add("run", Step(f"{gradle} bootRun", name))
        elif re.search(r"\bapplication\b", text):
            found.add("run", Step(f"{gradle} run", name))
        return found


def default_readers() -> Sequence[SourceReader]:
    """Every reader, in the order their steps are listed. Add a class here to support a file type."""
    return (
        PackageJsonReader(),
        PyProjectReader(),
        RequirementsReader(),
        MavenReader(),
        GradleReader(),
        MakefileReader(),
        DockerfileReader(),
        ComposeReader(),
        CiReader(),
        EnvExampleReader(),
    )
