import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_progress_bar_does_not_start_the_resource_tracker() -> None:
    """With the spawn start method, a tqdm multiprocessing lock starts the tracker."""
    code = (
        "import multiprocessing as mp\n"
        "from multiprocessing import resource_tracker\n"
        "mp.set_start_method('spawn')\n"
        "from gnost.utils.progress import progress_bar\n"
        "with progress_bar(enabled=True, total=2, desc='x') as bar:\n"
        "    bar.update(1)\n"
        "print(resource_tracker._resource_tracker._pid)\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    )
    assert out.stdout.strip().splitlines()[-1] == "None"


def _entry() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "gnost_entry", ROOT / "packaging" / "entry.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_entry_runs_multiprocessing_helpers_instead_of_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    entry = _entry()
    code = "from multiprocessing.util import info; print('helper ran')"
    assert entry.run_python_helper(["gnost", "-c", code, "5"]) is True
    assert "helper ran" in capsys.readouterr().out


def test_entry_leaves_other_arguments_alone(capsys: pytest.CaptureFixture[str]) -> None:
    entry = _entry()
    assert entry.run_python_helper(["gnost", "onboard", "."]) is False
    assert entry.run_python_helper(["gnost", "-c", "print('no')"]) is False
    assert entry.run_python_helper(["gnost", "-c"]) is False
    assert capsys.readouterr().out == ""


def test_the_entry_point_returns_the_exit_code_of_the_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A frozen binary must exit non-zero on failure; main()'s return value is the code."""
    entry = _entry()
    monkeypatch.setattr(
        "sys.argv", ["gnost", "analyze", str(tmp_path / "missing"), "--quiet"]
    )
    assert entry.run(["gnost", "analyze", str(tmp_path / "missing"), "--quiet"]) == 2
    monkeypatch.setattr("sys.argv", ["gnost", "version"])
    assert entry.run(["gnost", "version"]) == 0
    assert entry.run(["gnost", "-c", "from multiprocessing.util import info"]) == 0


def test_the_binary_exits_non_zero_when_it_fails(tmp_path: Path) -> None:
    """Runs the entry file as the frozen binary would, and checks the process exit code."""
    done = subprocess.run(
        [
            sys.executable,
            str(ROOT / "packaging" / "entry.py"),
            "analyze",
            str(tmp_path / "nope"),
            "--quiet",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert done.returncode == 2
