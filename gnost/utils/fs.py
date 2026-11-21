"""File system helpers shared by the commands.

`remove_tree` deletes a folder even when it holds read-only files, which Windows refuses to
remove (git marks its object files read-only). Used to clean up temporary clones.
"""

from __future__ import annotations

import os
import shutil
import stat
from typing import Any, Callable


def _make_writable_and_retry(
    function: Callable[[str], Any], path: str, _excinfo: Any
) -> None:
    """rmtree error handler: clear the read-only flag and try the removal once more."""
    try:
        os.chmod(path, stat.S_IWRITE)
        function(path)
    except OSError:
        pass  # best effort; the folder is in the temp directory anyway


def remove_tree(path: str) -> None:
    """Delete path and everything in it; never raises."""
    shutil.rmtree(path, ignore_errors=False, onerror=_make_writable_and_retry)
