"""Path helpers shared by the reporters."""

from __future__ import annotations

import os


def shorten(path: str, root: str) -> str:
    """Strip the root prefix and use forward slashes, on every OS.

    Text that merely contains a path (for example ``file:12`` or ``file::name``)
    keeps its suffix; text outside the root is only normalised.
    """
    for sep in {os.sep, "/"}:
        prefix = root.rstrip("/\\") + sep
        if path.startswith(prefix):
            path = path[len(prefix) :]
            break
    return path.replace(os.sep, "/")
