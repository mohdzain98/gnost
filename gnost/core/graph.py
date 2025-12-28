import os
from collections import defaultdict
from typing import Dict, List, Set

from gnost.scanner.models import ScanResult, FileInfo


class DependencyGraph:
    """
    Directed dependency graph of files.

    Edge: A -> B means A imports / depends on B
    """

    def __init__(self):
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)

    # -------------------------
    # Build Graph
    # -------------------------

    @classmethod
    def from_scan(cls, scan: ScanResult) -> "DependencyGraph":
        graph = cls()

        for file_info in scan.files:
            source = file_info.path
            graph._ensure_node(source)

            for imp in file_info.imports:
                target = cls._resolve_import(
                    imp.target,
                    scan.files,
                    source,
                )

                if target:
                    graph.add_edge(source, target)

        return graph

    # -------------------------
    # Graph Operations
    # -------------------------

    def add_edge(self, source: str, target: str):
        self.adjacency[source].add(target)
        self.reverse_adjacency[target].add(source)

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

    # -------------------------
    # Helpers
    # -------------------------

    @staticmethod
    def _resolve_import(
        import_path: str, files: List[FileInfo], source: str
    ) -> str | None:
        """
        Resolve imports for Python, JS, TS.
        """

        # -------- Python style --------
        normalized = import_path.replace(".", "/")
        for f in files:
            if f.path.endswith(normalized + ".py"):
                return f.path

        # -------- JS / TS relative imports --------
        if import_path.startswith("."):
            base_dir = os.path.dirname(source)
            candidate = os.path.normpath(os.path.join(base_dir, import_path))

            for ext in (".js", ".ts"):
                for f in files:
                    if f.path == candidate + ext:
                        return f.path
                    if f.path == os.path.join(candidate, "index" + ext):
                        return f.path

        return None
