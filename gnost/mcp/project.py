"""The project facts the MCP tools read, and the path rules that keep them inside it.

`ProjectData` loads `insights.json` from the output folder (never runs a scan), and
`resolve` turns a tool argument into a project-relative path or refuses it.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from gnost.utils.layout import OutputLayout


class ProjectError(Exception):
    """A problem the agent can read and act on (missing data, bad path)."""


class ProjectData:
    """One project root and its `insights.json`, loaded again when the file changes."""

    def __init__(self, root: str, output_dir: Optional[str] = None) -> None:
        self.root = os.path.realpath(root)
        self.layout = OutputLayout(self.root, output_dir)
        self._cache: Optional[Dict[str, Any]] = None
        self._stamp: float = -1.0

    @property
    def insights(self) -> Dict[str, Any]:
        """The parsed insights; raises ProjectError telling the user how to create them."""
        path = self.layout.insights_json
        try:
            stamp = os.path.getmtime(path)
        except OSError:
            raise ProjectError(
                f"No analysis found at {self.layout.relative_name}/insights.json. "
                f"Ask the user to run `gnost onboard {self.root}` first."
            ) from None
        if self._cache is None or stamp != self._stamp:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except (OSError, ValueError) as exc:
                raise ProjectError(f"Cannot read insights.json: {exc}") from None
            self._stamp = stamp
        return self._cache or {}

    def resolve(self, path: str) -> str:
        """A project-relative, forward-slash path; refuses anything outside the project."""
        if not isinstance(path, str) or not path.strip():
            raise ProjectError("`file` must be a non-empty path")
        full = os.path.realpath(os.path.join(self.root, path))
        if os.path.commonpath([self.root, full]) != self.root:
            raise ProjectError("Path is outside the project")
        return os.path.relpath(full, self.root).replace(os.sep, "/")

    def edges(self) -> List[Dict[str, Any]]:
        """The import edges of the dependency graph."""
        return list(self.insights.get("graph", {}).get("edges", []))
