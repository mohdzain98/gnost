"""Helpers shared by the packaging scripts."""

from __future__ import annotations

import shutil
from pathlib import Path


def dereference(root: Path) -> None:
    """Replace symlinks under root with real copies.

    npm drops symlinks when it packs a package, and zips do not keep them, so a
    macOS bundle (where _internal/Python links into Python.framework) would lose
    its Python library.
    """
    for link in [p for p in root.rglob("*") if p.is_symlink()]:
        target = link.resolve()
        link.unlink()
        if target.is_dir():
            shutil.copytree(target, link, symlinks=False)
        else:
            shutil.copy2(target, link)
