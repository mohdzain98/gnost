"""Build the command line for an analyzer tool, in pip installs and frozen binaries."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

RUN_TOOL_FLAG = "--run-tool"
PYTHON_TOOLS = ("radon", "bandit", "mypy")


def is_frozen() -> bool:
    """Return True when running inside a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def _bundled_ruff() -> Optional[str]:
    base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    name = "ruff.exe" if os.name == "nt" else "ruff"
    path = base / "bin" / name
    return str(path) if path.is_file() else None


def tool_command(name: str) -> List[str]:
    """Return the argv prefix that starts the named tool."""
    if not is_frozen():
        return [name]
    if name == "ruff":
        return [_bundled_ruff() or name]
    if name in PYTHON_TOOLS:
        return [sys.executable, RUN_TOOL_FLAG, name]
    return [name]


def bundled_tool_available(name: str) -> bool:
    """Return True if a frozen build carries the tool."""
    if name == "ruff":
        return _bundled_ruff() is not None
    return name in PYTHON_TOOLS


def run_tool_entry(argv: List[str]) -> int:
    """Run a bundled Python tool as if it were its own command (hidden CLI mode)."""
    name, args = argv[0], argv[1:]
    if name not in PYTHON_TOOLS:
        print(f"unknown tool: {name}", file=sys.stderr)
        return 2
    sys.argv = [name] + args
    if name == "mypy":
        from mypy.__main__ import console_entry

        console_entry()
    elif name == "bandit":
        from bandit.cli.main import main as bandit_main

        bandit_main()
    else:
        from radon.cli import main as radon_main

        radon_main()
    return 0
