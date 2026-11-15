"""Helpers for reading project manifests (package.json, pyproject.toml, pom.xml...)."""

from __future__ import annotations

import os
from typing import Callable, Iterator, Set

SKIP_DIRS: Set[str] = {
    "node_modules",
    "dist",
    "build",
    "target",
    "venv",
    "env",
    "site-packages",
    "__pycache__",
}


def find_manifests(
    root: str, matches: Callable[[str], bool], max_depth: int = 2
) -> Iterator[str]:
    """Yield paths of files under `root` whose name satisfies `matches`.

    Looks at the root and up to `max_depth` folders below it (monorepos keep
    manifests in sub-folders). Hidden, build and dependency folders are skipped.
    """
    base_depth = root.rstrip(os.sep).count(os.sep)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
        )
        if dirpath.count(os.sep) - base_depth >= max_depth:
            dirnames[:] = []
        for name in sorted(filenames):
            if matches(name):
                yield os.path.join(dirpath, name)


def read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""
