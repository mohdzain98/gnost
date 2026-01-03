# gnost/core/flow.py

from typing import List, Dict, Set
from dataclasses import dataclass

from gnost.scanner.models import ScanResult
from gnost.languages.base import EntryPoint
from gnost.core.graph import DependencyGraph


@dataclass
class FlowPath:
    """
    Represents one execution path.
    """

    start: str
    path: List[str]


@dataclass
class FlowResult:
    """
    Complete flow analysis result.
    """

    entry_points: List[EntryPoint]
    paths: List[FlowPath]
    layers: Dict[str, Set[str]]  # entry, core, leaf

    def overview_nodes(self) -> Set[str]:
        """
        Nodes to include in overview diagram.
        Entry + Core layers only.
        """
        nodes = set()

        for ep in self.entry_points:
            nodes.add(ep.file)

        for f in self.layers.get("core", []):
            nodes.add(f)

        return nodes


class FlowBuilder:
    """
    Builds execution flow using:
    - Entry points
    - Dependency graph
    """

    def __init__(self, graph: DependencyGraph, scan: ScanResult):
        self.graph = graph
        self.scan = scan

    # -------------------------
    # Public API
    # -------------------------

    def build(self) -> FlowResult:
        entry_files = self._resolve_entry_files()
        paths: List[FlowPath] = []

        for entry in entry_files:
            self._walk(
                start=entry,
                current=entry,
                visited=set(),
                path=[],
                paths=paths,
            )

        layers = self._classify_layers(paths)

        return FlowResult(
            entry_points=self.scan.entry_points,
            paths=paths,
            layers=layers,
        )

    def _walk(
        self,
        start: str,
        current: str,
        visited: Set[str],
        path: List[str],
        paths: List[FlowPath],
    ):
        if current in visited:
            return

        visited.add(current)
        path.append(current)

        dependencies = self.graph.dependencies_of(current)

        if not dependencies:
            paths.append(FlowPath(start=start, path=list(path)))
        else:
            for dep in dependencies:
                self._walk(
                    start=start,
                    current=dep,
                    visited=set(visited),
                    path=list(path),
                    paths=paths,
                )

    def _resolve_entry_files(self) -> List[str]:
        """
        Convert EntryPoint objects into concrete files.
        """
        resolved = []

        for ep in self.scan.entry_points:
            resolved.append(ep.file)

        # Fallback: graph roots if no explicit entry point
        if not resolved:
            resolved.extend(self.graph.roots())

        return list(set(resolved))

    def _classify_layers(self, paths: List[FlowPath]) -> Dict[str, Set[str]]:
        entry = set()
        core = set()
        leaf = set()

        for flow in paths:
            if not flow.path:
                continue

            entry.add(flow.path[0])
            leaf.add(flow.path[-1])

            for mid in flow.path[1:-1]:
                core.add(mid)

        return {
            "entry": entry,
            "core": core,
            "leaf": leaf,
        }
