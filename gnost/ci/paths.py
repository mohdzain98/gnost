"""Maps the file paths in findings back to real files, relative to the repository root.

Analyzers report paths in different forms: absolute, relative, or only the last two parts
(`core/file_utils.py`). SARIF and fingerprints need one stable form, so `PathResolver`
matches each reported path against the files that were analyzed.
"""

from __future__ import annotations

import os
from typing import Dict, Iterable, List


class PathResolver:
    """Resolves a reported path to a repository-relative path with forward slashes."""

    def __init__(self, files: Iterable[str], root: str) -> None:
        self.root = os.path.realpath(root)
        self._known = {self._relative(f) for f in files}
        self._by_suffix: Dict[str, List[str]] = {}
        for rel in sorted(self._known):
            parts = rel.split("/")
            for i in range(len(parts)):
                self._by_suffix.setdefault("/".join(parts[i:]), []).append(rel)

    def resolve(self, reported: str) -> str:
        """The repository-relative path for a reported one, or the reported text if unknown.

        Matches the longest tail of the path that is exactly one analyzed file.
        """
        text = reported.replace("\\", "/")
        if os.path.isabs(reported):
            return self._relative(
                reported
            )  # symlinks such as /var -> /private/var are resolved
        text = text[2:] if text.startswith("./") else text
        parts = text.split("/")
        for start in range(
            len(parts)
        ):  # longest tail first; an extra leading folder is dropped
            matches = self._by_suffix.get("/".join(parts[start:]), [])
            if matches:
                return matches[0] if len(matches) == 1 else text
        return text

    def exists(self, relative: str) -> bool:
        """True if the resolved path is a real file under the root."""
        return relative in self._known or os.path.isfile(
            os.path.join(self.root, relative)
        )

    def _relative(self, path: str) -> str:
        """A path made relative to the root, comparing real paths (unchanged if outside it)."""
        absolute = os.path.realpath(path)
        if absolute == self.root or absolute.startswith(self.root + os.sep):
            return os.path.relpath(absolute, self.root).replace(os.sep, "/")
        return absolute.replace(os.sep, "/")
