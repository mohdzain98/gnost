"""Ways `gnost init` wires GNOST into a project: pom.xml, package.json, a GitHub workflow.

Each is an `Integration` subclass in the `INTEGRATIONS` registry; the command and its flags are
built from that list, so a new one (say Gradle) is one new class. Edits are small text insertions
that keep the user's comments and formatting, and are skipped when already set up.
"""

from __future__ import annotations

import difflib
import json
import os
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from gnost.utils.layout import DEFAULT_OUTPUT_DIR

# Version of the Maven plugin that exists on Central; the release updates it when Maven is published.
MAVEN_PLUGIN_VERSION = "0.6.0"
MAVEN_GROUP = "io.github.mohdzain98"
MAVEN_ARTIFACT = "gnost-maven-plugin"
NPM_SCRIPT_NAME = "gnost"
NPM_SCRIPT = "npx --yes gnost-cli onboard ."
WORKFLOW_PATH = ".github/workflows/gnost.yml"


class IntegrationError(Exception):
    """The file cannot be edited safely; the message says why and what to do."""


@dataclass
class IntegrationResult:
    """What one integration did (or would do in a dry run)."""

    label: str
    status: str  # "changed", "would change", "unchanged", "exists", "created", "would create"
    path: str
    diff: List[str] = field(default_factory=list)


# ------------------------------------------------------------------ pom.xml


class PomDocument:
    """A pom.xml as text, with enough structure to insert a plugin without reformatting it."""

    _TAG = re.compile(
        r"<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|<!DOCTYPE[^>]*>"
        r"|<(/?)([A-Za-z_][\w.\-:]*)([^>]*?)(/?)>",
        re.DOTALL,
    )

    def __init__(self, text: str) -> None:
        self.text = text
        self.eol = "\r\n" if "\r\n" in text else "\n"
        self.unit = self._indent_unit()
        self._tags = self._scan()

    def with_plugin(self, group: str, artifact: str, version: str) -> Optional[str]:
        """The text with the plugin added under build/plugins, or None if it is already there."""
        if artifact in self.text:
            return None
        if self._find("open", ("project",)) is None:
            raise IntegrationError("pom.xml has no <project> element")
        plugins = self._find("close", ("project", "build", "plugins"))
        build = self._find("close", ("project", "build"))
        project = self._find("close", ("project",))
        plugin = lambda indent: self._plugin(group, artifact, version, indent)  # noqa: E731
        if plugins is not None:
            base = self._indent_of(plugins) + self.unit
            insertion, at = plugin(base) + self.eol, self._line_start(plugins)
        elif build is not None:
            inner = self._indent_of(build) + self.unit
            insertion = self._wrap("plugins", inner, plugin(inner + self.unit))
            at = self._line_start(build)
        elif project is not None:
            inner = self.unit
            build_body = self._wrap(
                "plugins", inner + self.unit, plugin(inner + self.unit * 2)
            )
            insertion = self._wrap("build", inner, build_body.rstrip("\r\n"))
            at = self._line_start(project)
        else:
            raise IntegrationError("pom.xml is not complete (no closing </project>)")
        edited = self.text[:at] + insertion + self.text[at:]
        try:
            ET.fromstring(edited.encode("utf-8"))
        except ET.ParseError as exc:  # never write a file we broke
            raise IntegrationError(
                f"the edited pom.xml would not be valid XML ({exc})"
            ) from exc
        return edited

    def _plugin(self, group: str, artifact: str, version: str, indent: str) -> str:
        """The <plugin> block, each line starting with indent."""
        lines = [
            "<plugin>",
            f"{self.unit}<groupId>{group}</groupId>",
            f"{self.unit}<artifactId>{artifact}</artifactId>",
            f"{self.unit}<version>{version}</version>",
            "</plugin>",
        ]
        return self.eol.join(indent + line for line in lines)

    def _wrap(self, tag: str, indent: str, body: str) -> str:
        """body inside <tag>...</tag> at the given indentation, ending with a line break."""
        return f"{indent}<{tag}>{self.eol}{body}{self.eol}{indent}</{tag}>{self.eol}"

    def _scan(self) -> List[Tuple[str, Tuple[str, ...], int]]:
        """(kind, element path, start) for each tag; comments and CDATA are skipped."""
        stack: List[str] = []
        found: List[Tuple[str, Tuple[str, ...], int]] = []
        for m in self._TAG.finditer(self.text):
            if m.group(2) is None:
                continue
            name = m.group(2).split(":")[-1]
            if m.group(4):
                found.append(("empty", tuple(stack) + (name,), m.start()))
            elif m.group(1):
                if stack and stack[-1] == name:
                    found.append(("close", tuple(stack), m.start()))
                    stack.pop()
            else:
                stack.append(name)
                found.append(("open", tuple(stack), m.start()))
        return found

    def _find(self, kind: str, path: Tuple[str, ...]) -> Optional[int]:
        """Start of the first tag of this kind at this element path, or None."""
        return next(
            (start for k, p, start in self._tags if k == kind and p == path), None
        )

    def _line_start(self, pos: int) -> int:
        """Index of the start of the line containing pos."""
        return self.text.rfind("\n", 0, pos) + 1

    def _indent_of(self, pos: int) -> str:
        """Leading whitespace of the line containing pos."""
        line = self.text[self._line_start(pos) :]
        return re.match(r"[ \t]*", line).group(0)  # type: ignore[union-attr]

    def _indent_unit(self) -> str:
        """The indentation step the file uses (its first indented element)."""
        m = re.search(r"\n([ \t]+)<(?!/|!)", self.text)
        return m.group(1) if m else "    "


# ------------------------------------------------------------- integrations


class Integration(ABC):
    """One thing `gnost init` can set up. Subclasses name the file and say how to change it."""

    flag: str  # command-line flag, without the dashes
    help: str
    label: str
    relative_path: str

    def apply(self, root: str, dry_run: bool, force: bool) -> IntegrationResult:
        """Set this up under root (or only describe it in a dry run)."""
        path = os.path.join(root, self.relative_path)
        return self._apply_to(path, dry_run, force)

    @abstractmethod
    def _apply_to(self, path: str, dry_run: bool, force: bool) -> IntegrationResult:
        """Do the work for the file at path."""

    @staticmethod
    def _diff(label: str, before: str, after: str) -> List[str]:
        """A unified diff of the change, one string per line."""
        return list(
            difflib.unified_diff(
                before.splitlines(),
                after.splitlines(),
                f"{label} (before)",
                f"{label} (after)",
                lineterm="",
            )
        )


class EditsExistingFile(Integration):
    """An integration that changes a file the project already has."""

    @abstractmethod
    def edit(self, text: str) -> Optional[str]:
        """The new file text, or None when nothing needs to change."""

    def _apply_to(self, path: str, dry_run: bool, force: bool) -> IntegrationResult:
        """Read the file, edit it, and write it back unless this is a dry run."""
        if not os.path.isfile(path):
            raise IntegrationError(f"no {self.relative_path} in the project folder")
        with open(path, encoding="utf-8", newline="") as f:
            before = f.read()
        after = self.edit(before)
        if after is None:
            return IntegrationResult(self.label, "unchanged", path)
        if not dry_run:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(after)
        status = "would change" if dry_run else "changed"
        return IntegrationResult(
            self.label, status, path, self._diff(self.label, before, after)
        )


class CreatesFile(Integration):
    """An integration that writes a new file and leaves an existing one alone unless forced."""

    @abstractmethod
    def content(self) -> str:
        """The text of the new file."""

    def _apply_to(self, path: str, dry_run: bool, force: bool) -> IntegrationResult:
        """Write the file if it does not exist (or force is set)."""
        if os.path.exists(path) and not force:
            return IntegrationResult(self.label, "exists", path)
        if dry_run:
            return IntegrationResult(self.label, "would create", path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.content())
        return IntegrationResult(self.label, "created", path)


class PomIntegration(EditsExistingFile):
    """Adds gnost-maven-plugin to pom.xml."""

    flag = "pom"
    help = "Add gnost-maven-plugin to pom.xml"
    label = "pom.xml"
    relative_path = "pom.xml"

    def edit(self, text: str) -> Optional[str]:
        return PomDocument(text).with_plugin(
            MAVEN_GROUP, MAVEN_ARTIFACT, MAVEN_PLUGIN_VERSION
        )


class PackageJsonIntegration(EditsExistingFile):
    """Adds a "gnost" script to package.json, keeping its key order and indentation."""

    flag = "npm"
    help = 'Add a "gnost" script to package.json'
    label = 'package.json ("gnost" script)'
    relative_path = "package.json"

    def edit(self, text: str) -> Optional[str]:
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise IntegrationError(f"package.json is not valid JSON ({exc})") from exc
        if not isinstance(data, dict):
            raise IntegrationError("package.json is not a JSON object")
        scripts = data.setdefault("scripts", {})
        if not isinstance(scripts, dict):
            raise IntegrationError('"scripts" in package.json is not an object')
        if NPM_SCRIPT_NAME in scripts:
            return None
        scripts[NPM_SCRIPT_NAME] = NPM_SCRIPT
        indent = (re.search(r"\n([ \t]+)\"", text) or [None, "  "])[1]
        return json.dumps(data, indent=indent, ensure_ascii=False) + (
            "\n" if text.endswith("\n") else ""
        )


class WorkflowIntegration(CreatesFile):
    """Writes a GitHub Actions workflow that runs the GNOST action on pull requests and pushes."""

    flag = "github-action"
    help = f"Write {WORKFLOW_PATH}"
    label = "workflow"
    relative_path = WORKFLOW_PATH

    def __init__(self, version: str) -> None:
        self.version = version

    def content(self) -> str:
        return f"""# Runs GNOST on every pull request and push: quality gate, onboarding guide and a pull
# request comment with what the change touches. Written by `gnost init --github-action`; edit freely.
name: GNOST

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read
  pull-requests: write      # for the pull request comment
  # security-events: write  # add this and set `sarif: "true"` to show findings in code scanning

jobs:
  gnost:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # full history: hotspots and `gnost changes` need it
      - uses: mohdzain98/gnost@v{self.version}
        with:
          comment: "true"   # one comment per pull request: blast radius, risk, new cycles
          onboard: "true"   # also attach the .gnost/ guide to the run
          sarif: "false"    # "true" uploads findings to code scanning
          # fail-under: "7.5"   # fail the job when the quality score is below this
"""


class AgentsIntegration(CreatesFile):
    """Writes AGENTS.md so coding agents find the GNOST files instead of re-reading everything."""

    flag = "agents"
    help = "Write AGENTS.md pointing coding agents to the .gnost/ folder"
    label = "AGENTS.md"
    relative_path = "AGENTS.md"

    def __init__(self, folder: str = DEFAULT_OUTPUT_DIR) -> None:
        self.folder = folder

    def content(self) -> str:
        return f"""# Notes for coding agents

This repository has a map of its own code, made by [GNOST](https://gnost.readthedocs.io).
Read it before you search the whole tree:

- `{self.folder}/ONBOARD.md`: entry points, how the code flows, routes, risky and often changed files.
- `{self.folder}/insights.json`: the same facts as data (files, imports, layers, cycles, routes, history).
- `{self.folder}/flow/`: Mermaid diagrams of how the files depend on each other.

Refresh it after large changes: `npx gnost-cli onboard .` (or `gnost onboard .`).
Before a change, `gnost changes origin/main` shows which files it reaches and how risky they are.
"""


def default_integrations(gnost_version: str) -> Tuple[Integration, ...]:
    """The integrations `gnost init` offers; add a new class here to offer a new one."""
    return (
        PomIntegration(),
        PackageJsonIntegration(),
        WorkflowIntegration(gnost_version),
        AgentsIntegration(),
    )
