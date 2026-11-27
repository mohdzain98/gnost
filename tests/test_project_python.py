"""mypy uses the analyzed project's virtual environment, and import findings are info only."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

from gnost.analysis.analyzers.robustness_analyzer import RobustnessAnalyzer
from gnost.analysis.core.models import SeverityLevel
from gnost.analysis.utils.project_python import ProjectPython
from gnost.analysis.utils.tool_command import UNTRUSTED_ENV


def make_venv(folder: Path, windows: bool = False) -> Path:
    """A minimal virtual environment layout: pyvenv.cfg and the interpreter file."""
    (folder).mkdir(parents=True, exist_ok=True)
    (folder / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
    python = folder / ("Scripts/python.exe" if windows else "bin/python")
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_text("", encoding="utf-8")
    return python


@pytest.fixture(autouse=True)
def no_outside_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv(UNTRUSTED_ENV, raising=False)


def test_finds_dot_venv_in_the_project(tmp_path: Path) -> None:
    python = make_venv(tmp_path / ".venv")
    assert ProjectPython(str(tmp_path)).find() == str(python)


def test_finds_a_windows_venv(tmp_path: Path) -> None:
    python = make_venv(tmp_path / "venv", windows=True)
    assert ProjectPython(str(tmp_path)).find() == str(python)


def test_looks_up_to_the_repository_root(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    python = make_venv(tmp_path / ".venv")
    sub = tmp_path / "src" / "app"
    sub.mkdir(parents=True)
    assert ProjectPython(str(sub)).find() == str(python)


def test_stops_at_the_repository_root(tmp_path: Path) -> None:
    make_venv(tmp_path / ".venv")  # outside the repository
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    assert ProjectPython(str(repo)).find() is None


def test_a_folder_named_venv_is_not_enough(tmp_path: Path) -> None:
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    assert ProjectPython(str(tmp_path)).find() is None


def test_an_activated_venv_is_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    python = make_venv(tmp_path / "elsewhere")
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path / "elsewhere"))
    assert ProjectPython(str(repo)).find() == str(python)


def test_gnost_own_env_is_not_the_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".git").mkdir()
    monkeypatch.setenv("VIRTUAL_ENV", sys.prefix)
    assert ProjectPython(str(tmp_path)).find() is None


def test_never_for_a_remote_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_venv(tmp_path / ".venv")
    monkeypatch.setenv(UNTRUSTED_ENV, "1")
    assert ProjectPython(str(tmp_path)).find() is None


def test_the_mypy_command_uses_the_venv(tmp_path: Path) -> None:
    python = make_venv(tmp_path / ".venv")
    cmd = RobustnessAnalyzer.mypy_command(["a.py"], str(tmp_path))
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert cmd[cmd.index("--python-executable") + 1] == str(python)
    assert cmd[cmd.index("--python-version") + 1] == version
    assert cmd[-1] == "a.py"


def test_the_mypy_command_without_a_venv(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    cmd = RobustnessAnalyzer.mypy_command(["a.py"], str(tmp_path))
    assert "--python-executable" not in cmd


@pytest.mark.parametrize("code", ["import-not-found", "import-untyped"])
def test_import_findings_are_info(code: str) -> None:
    assert RobustnessAnalyzer()._get_mypy_severity_mapping(code) is SeverityLevel.INFO


BLOCKED_OUTPUT = (
    'tests/raw_files.py: error: Source file found twice under different module names: "raw_files" and '
    '"tests.raw_files"\nFound 1 error in 1 file (errors prevented further checking)\n'
)


def run_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outputs: list[str]
) -> list[dict]:
    """Run _mypy_output with a fake mypy that answers `outputs` in turn; return the calls."""
    calls: list[dict] = []

    async def fake_exec(
        cmd: list[str], cwd: str | None = None, env: dict | None = None
    ) -> str:
        calls.append({"cmd": cmd, "cwd": cwd, "env": env})
        return outputs[len(calls) - 1]

    monkeypatch.setattr(RobustnessAnalyzer, "_exec", staticmethod(fake_exec))
    asyncio.run(
        RobustnessAnalyzer()._mypy_output(["tests/raw_files.py"], str(tmp_path))
    )
    return calls


def test_a_blocked_run_is_retried_from_the_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "src").mkdir()  # a src/ layout: no __init__.py
    calls = run_output(tmp_path, monkeypatch, [BLOCKED_OUTPUT, "Success\n"])
    assert len(calls) == 2
    retry = calls[1]
    assert "--explicit-package-bases" in retry["cmd"]
    assert retry["cwd"] == str(tmp_path.resolve()) or retry["cwd"] == str(tmp_path)
    assert all(Path(f).is_absolute() for f in retry["cmd"][-1:])
    bases = retry["env"]["MYPYPATH"].split(os.pathsep)
    assert bases == [str(tmp_path), str(tmp_path / "src")]


def test_a_normal_run_is_not_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = run_output(tmp_path, monkeypatch, ["Success: no issues found\n"])
    assert len(calls) == 1
    assert "--explicit-package-bases" not in calls[0]["cmd"]
