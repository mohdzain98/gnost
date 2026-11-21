"""The exit codes of the gnost command line, documented for scripts and CI.

0 means success. 1 is an unexpected failure while running. 2 is a mistake in how the command or
the config was written (argparse uses 2 as well). 3 means the quality gate failed.
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Process exit codes; compare with `int(ExitCode.GATE_FAILED)` or use directly in returns."""

    OK = 0
    ERROR = 1
    USAGE = 2
    GATE_FAILED = 3
    INTERRUPTED = 130
