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


# --------------------------------------------------------------- when to show it


class FakeStream:
    """A stream that says whether it is a terminal."""

    def __init__(self, tty: bool) -> None:
        self.tty = tty

    def isatty(self) -> bool:
        return self.tty


def policy(tty: bool, **environ: str):
    from gnost.utils.progress import ProgressPolicy

    return ProgressPolicy(stream=FakeStream(tty), environ=environ)


def test_progress_shows_in_a_terminal_only() -> None:
    assert policy(True).enabled() is True
    assert policy(False).enabled() is False  # a pipe or a redirected log


def test_progress_is_off_in_ci_and_when_switched_off() -> None:
    assert policy(True, CI="true").enabled() is False
    assert policy(True, GNOST_NO_PROGRESS="1").enabled() is False
    assert policy(True).enabled(disabled=True) is False


def test_forcing_progress_wins_over_everything() -> None:
    assert policy(False, CI="true").enabled(force=True) is True
    assert policy(True).enabled(force=True, disabled=True) is True


def test_a_stream_without_isatty_counts_as_not_a_terminal() -> None:
    from gnost.utils.progress import ProgressPolicy

    class Bare:
        pass

    assert ProgressPolicy(stream=Bare(), environ={}).enabled() is False  # type: ignore[arg-type]


# ----------------------------------------------------------------- the step bar


def test_step_progress_names_each_step_and_announces_itself(
    capsys: pytest.CaptureFixture,
) -> None:
    from gnost.utils.progress import StepProgress

    with StepProgress(True, ["One", "Two"], announce="Starting ...") as bar:
        bar.advance()
        bar.advance()
        bar.advance()  # more than the steps: harmless
    err = capsys.readouterr().err
    assert "Starting ..." in err and "One" in err and "Two" in err


def test_step_progress_is_silent_when_disabled(capsys: pytest.CaptureFixture) -> None:
    from gnost.utils.progress import StepProgress

    with StepProgress(False, ["One"], announce="Starting ...") as bar:
        bar.advance()
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_onboard_writes_progress_to_stderr_and_keeps_stdout_clean(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    import shutil

    from gnost.cli.commands.onboard import run

    shutil.copytree(ROOT / "tests" / "fixtures" / "python_app", tmp_path / "app")
    run(path=str(tmp_path / "app"), progress=True)
    captured = capsys.readouterr()
    assert "Onboarding " in captured.err and "Scanning files" in captured.err
    assert "Scanning files" not in captured.out and "Onboarding /" not in captured.out
    run(path=str(tmp_path / "app"), progress=False)
    assert "Scanning files" not in capsys.readouterr().err
