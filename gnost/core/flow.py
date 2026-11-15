# gnost/core/flow.py

from collections import deque
from typing import Deque, List, Dict, Set, Tuple
from dataclasses import dataclass, field

from gnost.scanner.models import ScanResult
from gnost.languages.base import EntryPoint
from gnost.core.cycles import Cycle, find_cycles
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
    # Every dependency edge reachable from the entry points (sorted), and the
    # shortest distance of each reachable file from an entry point.
    edges: List[Tuple[str, str]] = field(default_factory=list)
    depths: Dict[str, int] = field(default_factory=dict)
    # Circular dependencies in the whole graph, and the edges that only come
    # from imports which do not run at load time (see DependencyGraph).
    cycles: List[Cycle] = field(default_factory=list)
    deferred_edges: Set[Tuple[str, str]] = field(default_factory=set)

    def ordered_layer(self, name: str, limit: int = 0) -> List[str]:
        """Files of a layer, closest to an entry point first (a reading order)."""
        files = sorted(
            self.layers.get(name, set()),
            key=lambda f: (self.depths.get(f, 0), f),
        )
        return files[:limit] if limit else files

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
        depths: Dict[str, int] = {}

        for entry in entry_files:
            self._walk(entry, paths, depths)

        edges = sorted(
            (src, dst)
            for src in depths
            for dst in self.graph.dependencies_of(src)
            if dst in depths
        )
        layers = self._classify_layers(paths)

        return FlowResult(
            entry_points=self.scan.entry_points,
            paths=paths,
            layers=layers,
            edges=edges,
            depths=depths,
            cycles=find_cycles(self.graph),
            deferred_edges=set(self.graph.deferred_edges),
        )

    def _walk(self, start: str, paths: List[FlowPath], depths: Dict[str, int]) -> None:
        """Breadth-first walk that expands each file once per entry point.

        A path is recorded where a branch ends: at a file with no dependencies,
        or at one whose dependencies were all reached already (including
        cycles). This keeps the path count bounded by the number of files
        instead of the number of distinct routes through the graph, and every
        path is a shortest route from the entry point.
        """
        visited: Set[str] = {start}
        queue: Deque[List[str]] = deque([[start]])

        while queue:
            path = queue.popleft()
            node = path[-1]
            depths[node] = min(depths.get(node, len(path) - 1), len(path) - 1)

            unvisited = [
                dep
                for dep in sorted(self.graph.dependencies_of(node))
                if dep not in visited
            ]

            if not unvisited:
                paths.append(FlowPath(start=start, path=path))
                continue

            visited.update(unvisited)
            for dep in unvisited:
                queue.append(path + [dep])

    def _resolve_entry_files(self) -> List[str]:
        """
        Convert EntryPoint objects into concrete files.
        """
        resolved = []

        # Helper scripts only seed the flow when nothing else starts the app.
        primary = [
            ep for ep in self.scan.entry_points if ep.priority == EntryPoint.PRIMARY
        ]
        for ep in primary or self.scan.entry_points:
            resolved.append(ep.file)

        # Fallback: graph roots if no explicit entry point
        if not resolved:
            resolved.extend(self.graph.roots())

        return self._drop_reachable_entries(sorted(set(resolved)))

    def _drop_reachable_entries(self, entries: List[str]) -> List[str]:
        """Keep only entries no other entry imports.

        `main.tsx` imports `App.tsx`: both look like entry points by name, but
        only `main.tsx` starts anything. Walking both would traverse the whole
        project twice.
        """
        if len(entries) < 2:
            return entries

        imported: Set[str] = set()
        for entry in entries:
            seen = {entry}
            stack = [entry]
            while stack:
                for dep in self.graph.dependencies_of(stack.pop()):
                    if dep not in seen:
                        seen.add(dep)
                        stack.append(dep)
            imported |= seen - {entry}

        roots = [e for e in entries if e not in imported]
        return roots or entries

    def _classify_layers(self, paths: List[FlowPath]) -> Dict[str, Set[str]]:
        entry = set()
        core = set()
        leaf = set()

        for flow in paths:
            if not flow.path:
                continue

            entry.add(flow.path[0])

            last = flow.path[-1]
            if self.graph.dependencies_of(last):
                core.add(last)  # branch ended on an already-visited file
            else:
                leaf.add(last)

            for mid in flow.path[1:-1]:
                core.add(mid)

        return {
            "entry": entry,
            "core": core,
            "leaf": leaf,
        }
