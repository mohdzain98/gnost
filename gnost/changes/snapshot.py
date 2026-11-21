"""One scanned version of a project: its files, import graph, flow, routes and cycles.

`ProjectSnapshot.scan` runs the same steps as `gnost onboard` on a folder. `RefCheckout` exports
a git ref into a temporary folder so the base side of a change can be scanned the same way
without touching the working tree.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from types import TracebackType
from typing import List, Optional, Sequence, Set, Type

from gnost.core.cycles import Cycle
from gnost.core.flow import FlowBuilder, FlowResult
from gnost.core.graph import DependencyGraph
from gnost.languages.base import LanguageAdapter
from gnost.languages.java import JavaAdapter
from gnost.languages.javascript import JavaScriptAdapter
from gnost.languages.python import PythonAdapter
from gnost.languages.typescript import TypeScriptAdapter
from gnost.routes import Route, find_routes
from gnost.scanner.engine import ScannerEngine
from gnost.scanner.models import ScanResult
from gnost.utils.fs import remove_tree
from gnost.vcs.git import GitRepository


def default_adapters() -> List[LanguageAdapter]:
    """The language adapters every GNOST scan uses."""
    return [PythonAdapter(), JavaScriptAdapter(), TypeScriptAdapter(), JavaAdapter()]


@dataclass
class ProjectSnapshot:
    """A scanned folder with the structures built from it."""

    root: str
    scan: ScanResult
    graph: DependencyGraph
    flow: FlowResult

    @classmethod
    def scan_folder(
        cls, root: str, exclude: Optional[Sequence[str]] = None
    ) -> "ProjectSnapshot":
        """Scan root and build the dependency graph, flow and routes."""
        scan = ScannerEngine(
            adapters=default_adapters(), exclude=list(exclude or [])
        ).scan(root)
        scan.routes = find_routes(scan)
        graph = DependencyGraph.from_scan(scan)
        flow = FlowBuilder(graph=graph, scan=scan).build()
        return cls(root=root, scan=scan, graph=graph, flow=flow)

    def relative(self, path: str) -> str:
        """A scanned file's path relative to the root, with forward slashes."""
        return os.path.relpath(path, self.scan.root).replace(os.sep, "/")

    def files(self) -> Set[str]:
        """Relative paths of every scanned file."""
        return {self.relative(f.path) for f in self.scan.files}

    def cycle_keys(self) -> Set[frozenset]:
        """Each circular dependency as the set of its relative file paths."""
        return {self.cycle_key(c) for c in self.flow.cycles}

    def cycle_key(self, cycle: Cycle) -> frozenset:
        """The identity of one cycle: which files are in it."""
        return frozenset(self.relative(f) for f in cycle.files)

    def routes(self) -> List[Route]:
        """The routes found in this version."""
        return list(self.scan.routes)


class RefCheckout:
    """Exports a git ref into a temporary folder; removes it on exit, even after Ctrl+C.

    `with RefCheckout(repo, commit, subpath) as folder:` gives the folder to scan.
    """

    def __init__(self, repo: GitRepository, ref: str, subpath: str = ".") -> None:
        self.repo = repo
        self.ref = ref
        self.subpath = subpath
        self._temp: Optional[str] = None

    def __enter__(self) -> str:
        self._temp = tempfile.mkdtemp(prefix="gnost-base-")
        try:
            self.repo.checkout_to(self.ref, self._temp, self.subpath)
        except BaseException:
            self.__exit__(None, None, None)
            raise
        folder = os.path.join(self._temp, self.subpath)
        return os.path.realpath(folder if self.subpath not in ("", ".") else self._temp)

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        if self._temp:
            remove_tree(self._temp)
            self._temp = None
