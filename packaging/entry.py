"""PyInstaller entry point for the standalone gnost binary.

Runs the gnost command line and exits with its exit code (the pip console script does this
for us; a frozen program must do it itself, or every failure would look like success).
Also runs the multiprocessing helper that Python relaunches as `sys.executable -c ...`.
"""

import multiprocessing
import sys
from typing import List


def run_python_helper(argv: List[str]) -> bool:
    """Run a relaunched multiprocessing helper (python -c "from multiprocessing...").

    In the binary sys.executable is gnost, so Python's resource tracker starts
    gnost with those arguments. Run the code instead of reading it as a command.
    """
    if "-c" not in argv[1:-1]:
        return False
    code = argv[argv.index("-c") + 1]
    if not code.startswith("from multiprocessing."):
        return False
    sys.argv = ["-c"] + argv[argv.index("-c") + 2 :]
    exec(code, {"__name__": "__main__"})
    return True


def run(argv: List[str]) -> int:
    """Run the helper or the gnost command line; returns the process exit code."""
    if run_python_helper(argv):
        return 0
    from gnost.cli import main

    result = main()
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(run(sys.argv))
