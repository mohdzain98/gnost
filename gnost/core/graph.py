from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set, Tuple

from gnost.core.resolver import ImportResolver
from gnost.scanner.models import ScanResult


class DependencyGraph:
    """
    Directed dependency graph of files.

    Edge: A -> B means A imports / depends on B
    """

    def __init__(self):
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)
        # Edges created only by imports that do not run at load time.
        self.deferred_edges: Set[Tuple[str, str]] = set()

    # -------------------------
    # Build Graph
    # -------------------------

    @classmethod
    def from_scan(cls, scan: ScanResult) -> "DependencyGraph":
        graph = cls()
        resolver = ImportResolver(scan.root, scan.files)

        for file_info in sorted(scan.files, key=lambda f: f.path):
            source = file_info.path
            graph._ensure_node(source)

            eager: Set[str] = set()
            lazy: Set[str] = set()
            for imp in file_info.imports:
                for target in resolver.resolve(imp, file_info.language):
                    (lazy if imp.deferred else eager).add(target)

            for target in sorted(eager | lazy):
                graph.add_edge(source, target, deferred=target not in eager)

        return graph

    # -------------------------
    # Graph Operations
    # -------------------------

    def add_edge(self, source: str, target: str, deferred: bool = False):
        self.adjacency[source].add(target)
        self.reverse_adjacency[target].add(source)
        if deferred:
            self.deferred_edges.add((source, target))
        else:
            self.deferred_edges.discard((source, target))

    def eager_dependencies_of(self, file: str) -> Set[str]:
        """Dependencies that load when the file does (not deferred)."""
        return {
            dep
            for dep in self.adjacency.get(file, set())
            if (file, dep) not in self.deferred_edges
        }

    def _ensure_node(self, node: str):
        self.adjacency.setdefault(node, set())
        self.reverse_adjacency.setdefault(node, set())

    # -------------------------
    # Queries
    # -------------------------

    def dependencies_of(self, file: str) -> Set[str]:
        """Files this file depends on"""
        return self.adjacency.get(file, set())

    def dependents_of(self, file: str) -> Set[str]:
        """Files that depend on this file"""
        return self.reverse_adjacency.get(file, set())

    def roots(self) -> List[str]:
        """
        Files with no incoming edges.
        Often entry-level files.
        """
        return [node for node in self.adjacency if not self.reverse_adjacency[node]]

    def leaves(self) -> List[str]:
        """
        Files with no outgoing edges.
        Usually utilities / low-level modules.
        """
        return [node for node, deps in self.adjacency.items() if not deps]

    def all_nodes(self) -> Set[str]:
        return set(self.adjacency.keys())

    # -------------------------
    # Metrics (for later ranking)
    # -------------------------

    def fan_in(self, file: str) -> int:
        return len(self.reverse_adjacency.get(file, []))

    def fan_out(self, file: str) -> int:
        return len(self.adjacency.get(file, []))
