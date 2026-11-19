"""PyInstaller entry point for the standalone gnost binary."""

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


if __name__ == "__main__":
    multiprocessing.freeze_support()
    if not run_python_helper(sys.argv):
        from gnost.cli import main

        main()
