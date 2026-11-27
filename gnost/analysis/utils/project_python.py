"""Find the Python interpreter of the project being analyzed, so mypy sees its packages.

GNOST usually runs from its own isolated environment (uvx, pipx, a frozen binary), where the
project's dependencies are not installed. Pointing mypy at the project's virtual environment
lets it resolve `import pandas` and friends instead of reporting every third-party import.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterator, Optional

from gnost.analysis.utils.tool_command import untrusted_repo


class ProjectPython:
    """Locates a virtual environment for a project folder.

    Looks for `.venv/` or `venv/` in the folder and its parents (up to the repository root),
    then falls back to an activated `$VIRTUAL_ENV` that is not GNOST's own environment.
    """

    VENV_NAMES = (".venv", "venv")
    MAX_PARENTS = 5  # the analyzed folder can be a subfolder of the repository

    def __init__(self, target: str) -> None:
        self.target = Path(target).resolve()

    def find(self) -> Optional[str]:
        """The project's interpreter path, or None when there is none to use.

        Never used for remote repositories: mypy runs the interpreter to read its paths.
        """
        if untrusted_repo():
            return None
        for folder in self._folders():
            for name in self.VENV_NAMES:
                python = self.interpreter(folder / name)
                if python:
                    return python
        active = os.environ.get("VIRTUAL_ENV")
        if active and Path(active).resolve() != Path(sys.prefix).resolve():
            return self.interpreter(Path(active))
        return None

    @staticmethod
    def interpreter(venv: Path) -> Optional[str]:
        """The python inside a virtual environment folder, if it is one."""
        if not (venv / "pyvenv.cfg").is_file():
            return None
        for relative in ("bin/python", "bin/python3", "Scripts/python.exe"):
            candidate = venv / relative
            if candidate.is_file():
                return str(candidate)
        return None

    def _folders(self) -> Iterator[Path]:
        """The target folder and its parents, stopping at the repository root."""
        folder = self.target if self.target.is_dir() else self.target.parent
        for _ in range(self.MAX_PARENTS + 1):
            yield folder
            if (folder / ".git").exists() or folder.parent == folder:
                return
            folder = folder.parent
