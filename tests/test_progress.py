import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_progress_bar_does_not_start_the_resource_tracker():
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


def _entry():
    spec = importlib.util.spec_from_file_location(
        "gnost_entry", ROOT / "packaging" / "entry.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_entry_runs_multiprocessing_helpers_instead_of_commands(capsys):
    entry = _entry()
    code = "from multiprocessing.util import info; print('helper ran')"
    assert entry.run_python_helper(["gnost", "-c", code, "5"]) is True
    assert "helper ran" in capsys.readouterr().out


def test_entry_leaves_other_arguments_alone(capsys):
    entry = _entry()
    assert entry.run_python_helper(["gnost", "onboard", "."]) is False
    assert entry.run_python_helper(["gnost", "-c", "print('no')"]) is False
    assert entry.run_python_helper(["gnost", "-c"]) is False
    assert capsys.readouterr().out == ""
