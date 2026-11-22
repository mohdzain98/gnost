"""Quickstart detection: each reader, the merge rules, secrets, and the guide and JSON output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import jsonschema
import pytest

from gnost.cli.commands.onboard import run
from gnost.quickstart import GROUPS, Quickstart, QuickstartDetector, Step
from gnost.quickstart.readers import SourceReader
from gnost.reporters.insights_json import SCHEMA_PATH


def project(root: Path, files: Dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root


def texts(quickstart: Quickstart, group: str) -> List[str]:
    return [s.text for s in getattr(quickstart, group)]


# ---------------------------------------------------------------- JavaScript


def test_package_json_gives_install_run_test_and_the_node_version(
    tmp_path: Path,
) -> None:
    root = project(
        tmp_path / "web",
        {
            "package.json": json.dumps(
                {
                    "engines": {"node": ">=18"},
                    "scripts": {"dev": "vite", "build": "vite build", "test": "vitest"},
                }
            )
        },
    )
    found = QuickstartDetector().detect(str(root))
    assert texts(found, "prerequisites") == ["Node.js >=18"]
    assert texts(found, "install") == ["npm install"]
    assert texts(found, "run") == ["npm run dev"]
    assert texts(found, "build") == ["npm run build"]
    assert texts(found, "test") == ["npm test"]
    assert found.install[0].source == "package.json"


@pytest.mark.parametrize(
    "lock, manager",
    [("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("package-lock.json", "npm")],
)
def test_the_package_manager_follows_the_lock_file(
    tmp_path: Path, lock: str, manager: str
) -> None:
    root = project(
        tmp_path / "p",
        {"package.json": '{"scripts": {"start": "node ."}}', lock: ""},
    )
    found = QuickstartDetector().detect(str(root))
    assert texts(found, "install") == [f"{manager} install"]
    assert texts(found, "run") == [f"{manager} start"]


def test_a_broken_package_json_is_skipped(tmp_path: Path) -> None:
    root = project(
        tmp_path / "p", {"package.json": "{ not json", "Makefile": "test:\n\ttrue\n"}
    )
    found = QuickstartDetector().detect(str(root))
    assert texts(found, "test") == ["make test"]  # the other readers still work


# -------------------------------------------------------------------- Python


def test_pyproject_gives_python_version_install_extras_scripts_and_pytest(
    tmp_path: Path,
) -> None:
    root = project(
        tmp_path / "lib",
        {
            "pyproject.toml": (
                '[project]\nname = "lib"\nrequires-python = ">=3.9"\n'
                '[project.scripts]\nlibcli = "lib.cli:main"\n'
                '[project.optional-dependencies]\ntest = ["pytest"]\n'
            )
        },
    )
    found = QuickstartDetector().detect(str(root))
    assert texts(found, "prerequisites") == ["Python >=3.9"]
    assert texts(found, "install") == ["pip install -e .", 'pip install -e ".[test]"']
    assert texts(found, "run") == ["libcli"]
    assert texts(found, "test") == ["pytest"]


def test_poetry_and_uv_are_recognised(tmp_path: Path) -> None:
    poetry = project(tmp_path / "a", {"pyproject.toml": '[tool.poetry]\nname = "a"\n'})
    assert texts(QuickstartDetector().detect(str(poetry)), "install") == [
        "poetry install"
    ]
    uv = project(
        tmp_path / "b", {"pyproject.toml": '[project]\nname = "b"\n', "uv.lock": ""}
    )
    assert texts(QuickstartDetector().detect(str(uv)), "install") == ["uv sync"]


def test_requirements_txt_is_used_only_without_a_pyproject(tmp_path: Path) -> None:
    alone = project(tmp_path / "a", {"requirements.txt": "rich\n"})
    assert texts(QuickstartDetector().detect(str(alone)), "install") == [
        "pip install -r requirements.txt"
    ]
    both = project(
        tmp_path / "b",
        {"requirements.txt": "rich\n", "pyproject.toml": '[project]\nname = "b"\n'},
    )
    assert "pip install -r requirements.txt" not in texts(
        QuickstartDetector().detect(str(both)), "install"
    )


# ------------------------------------------------------------ Makefile, Docker


def test_makefile_targets_with_the_usual_names(tmp_path: Path) -> None:
    root = project(
        tmp_path / "m",
        {
            "Makefile": "install:\n\tpip install .\nrun:\n\tpython app.py\nlint:\n\ttrue\ntest:\n\tpytest\n"
        },
    )
    found = QuickstartDetector().detect(str(root))
    assert texts(found, "install") == ["make install"]
    assert texts(found, "run") == ["make run"]
    assert texts(found, "test") == ["make test"]  # `lint` is not a known name


def test_dockerfile_and_compose(tmp_path: Path) -> None:
    root = project(
        tmp_path / "My App",
        {
            "Dockerfile": "FROM python:3.12\nEXPOSE 8080\nCMD python app.py\n",
            "compose.yaml": "services:\n  web:\n    build: .\n",
        },
    )
    found = QuickstartDetector().detect(str(root))
    assert texts(found, "prerequisites") == ["Docker"]
    assert texts(found, "build") == ["docker build -t my-app ."]
    assert texts(found, "run") == [
        "docker run -p 8080:8080 my-app",
        "docker compose up",
    ]


# ------------------------------------------------------------------------ CI


def test_ci_commands_are_a_last_resort_and_skip_shell_noise(tmp_path: Path) -> None:
    workflow = (
        "jobs:\n  t:\n    steps:\n"
        "      - run: pip install -e .\n"
        '      - run: |\n          pytest -q\n          echo "$HOME"\n'
        '      - run: pip install "$WHEEL"\n'
    )
    only_ci = project(tmp_path / "a", {".github/workflows/t.yml": workflow})
    found = QuickstartDetector().detect(str(only_ci))
    assert texts(found, "install") == ["pip install -e ."]
    assert texts(found, "test") == ["pytest -q"]
    assert found.test[0].source == ".github/workflows/t.yml"
    with_make = project(
        tmp_path / "b",
        {".github/workflows/t.yml": workflow, "Makefile": "test:\n\tpytest\n"},
    )
    assert texts(QuickstartDetector().detect(str(with_make)), "test") == ["make test"]


# -------------------------------------------------------------- environment


def test_env_example_lists_names_and_never_values(tmp_path: Path) -> None:
    root = project(
        tmp_path / "e",
        {
            ".env.example": (
                "# database\nDATABASE_URL=postgres://user:s3cret@host/db\n"
                "export API_KEY=sk-live-123456\nEMPTY=\n  # COMMENTED=1\n"
            )
        },
    )
    found = QuickstartDetector().detect(str(root))
    assert texts(found, "environment") == ["DATABASE_URL", "API_KEY", "EMPTY"]
    dumped = json.dumps(found.to_dict())
    assert (
        "s3cret" not in dumped
        and "sk-live" not in dumped
        and "postgres://" not in dumped
    )


# ------------------------------------------------------------------------ Java


def test_maven_and_gradle(tmp_path: Path) -> None:
    pom = project(
        tmp_path / "m",
        {
            "pom.xml": (
                "<project><properties><java.version>17</java.version></properties>"
                "<build><plugins><plugin><artifactId>spring-boot-maven-plugin</artifactId>"
                "</plugin></plugins></build></project>"
            ),
            "mvnw": "",
        },
    )
    found = QuickstartDetector().detect(str(pom))
    assert texts(found, "prerequisites") == ["Java 17"]
    assert texts(found, "build") == ["./mvnw package"]
    assert texts(found, "run") == ["./mvnw spring-boot:run"]
    gradle = project(
        tmp_path / "g",
        {"build.gradle": "plugins { id 'org.springframework.boot' }\n", "gradlew": ""},
    )
    found = QuickstartDetector().detect(str(gradle))
    assert texts(found, "run") == ["./gradlew bootRun"]
    assert texts(found, "test") == ["./gradlew test"]


# ------------------------------------------------------------ merge and safety


def test_a_project_with_no_known_files_has_an_empty_quickstart(tmp_path: Path) -> None:
    empty = project(tmp_path / "x", {"notes.txt": "hi"})
    assert QuickstartDetector().detect(str(empty)).is_empty


def test_duplicates_are_dropped_and_groups_are_limited() -> None:
    quickstart = Quickstart()
    for i in range(20):
        quickstart.add("run", Step(f"cmd {i}", "f"))
    quickstart.add("run", Step("cmd 0", "other"))
    assert len(quickstart.run) == 8 and quickstart.run[0].source == "f"


def test_a_reader_that_crashes_does_not_stop_the_others(tmp_path: Path) -> None:
    class Broken(SourceReader):
        def read(self, root: str) -> Quickstart:
            raise RuntimeError("boom")

    class Fixed(SourceReader):
        def read(self, root: str) -> Quickstart:
            found = Quickstart()
            found.add("run", Step("go", "f"))
            return found

    found = QuickstartDetector([Broken(), Fixed()]).detect(str(tmp_path))
    assert texts(found, "run") == ["go"]


def test_a_new_reader_needs_no_change_to_the_detector(tmp_path: Path) -> None:
    class Cargo(SourceReader):
        def read(self, root: str) -> Quickstart:
            found = Quickstart()
            if self.path(root, "Cargo.toml"):
                found.add("test", Step("cargo test", "Cargo.toml"))
            return found

    root = project(tmp_path / "r", {"Cargo.toml": "[package]\n"})
    assert texts(QuickstartDetector([Cargo()]).detect(str(root)), "test") == [
        "cargo test"
    ]


# ------------------------------------------------------------------- output


def test_onboard_writes_the_section_and_the_json_field(tmp_path: Path) -> None:
    root = project(
        tmp_path / "app",
        {
            "main.py": "if __name__ == '__main__':\n    pass\n",
            "package.json": '{"scripts": {"test": "jest"}}',
            ".env.example": "TOKEN=abc123\n",
        },
    )
    run(path=str(root))
    guide = (root / ".gnost" / "ONBOARD.md").read_text(encoding="utf-8")
    assert "## Get it running" in guide
    assert "- `npm install` _(package.json)_" in guide
    assert "- TOKEN _(.env.example)_" in guide and "abc123" not in guide
    assert guide.index("## Get it running") < guide.index("## Entry Points")
    payload = json.loads((root / ".gnost" / "insights.json").read_text())
    assert payload["quickstart"]["test"][0] == {
        "text": "npm test",
        "source": "package.json",
        "command": True,
    }
    schema = json.load(open(SCHEMA_PATH))
    jsonschema.validate(payload, schema)
    assert set(payload["quickstart"]) == set(GROUPS)


def test_a_project_without_files_has_no_section_but_still_has_the_json_field(
    tmp_path: Path,
) -> None:
    root = project(tmp_path / "bare", {"main.py": "print(1)\n"})
    run(path=str(root))
    assert "## Get it running" not in (root / ".gnost" / "ONBOARD.md").read_text()
    payload = json.loads((root / ".gnost" / "insights.json").read_text())
    assert all(payload["quickstart"][g] == [] for g in GROUPS)


def test_the_terminal_summary_shows_the_first_command(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    root = project(
        tmp_path / "app", {"package.json": '{"scripts": {"start": "node ."}}'}
    )
    run(path=str(root))
    out = capsys.readouterr().out
    assert "Get it running" in out and "npm install  (package.json)" in out
