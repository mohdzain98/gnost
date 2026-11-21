"""Blast radius: the files that import a changed file, directly or through other files.

`BlastRadius` walks the import graph backwards from the changed files, breadth first, up to a
depth. Every affected file records its distance and the changed file it was reached from.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Dict, Iterable, List, Set, Tuple

from gnost.core.graph import DependencyGraph

DEFAULT_DEPTH = 3
Relative = Callable[[str], str]  # turns a graph node into a path relative to the folder


@dataclass(frozen=True)
class AffectedFile:
    """A file that depends on the change."""

    path: str  # relative to the scanned folder
    depth: int  # 1 = imports a changed file directly
    via: str  # the changed file it was reached from


class BlastRadius:
    """Finds dependents of a set of files in one dependency graph."""

    def __init__(self, graph: DependencyGraph, relative: Relative) -> None:
        self.graph = graph
        self.relative = relative

    def of(
        self, changed: Iterable[str], depth: int = DEFAULT_DEPTH
    ) -> List[AffectedFile]:
        """Files affected by `changed` (relative paths), nearest first, then by path."""
        by_rel = {self.relative(n): n for n in self.graph.all_nodes()}
        seeds = [by_rel[c] for c in sorted(set(changed)) if c in by_rel]
        seen: Set[str] = set(seeds)
        found: Dict[str, Tuple[int, str]] = {}
        queue: Deque[Tuple[str, int, str]] = deque(
            (s, 0, self.relative(s)) for s in seeds
        )
        while queue:
            node, distance, origin = queue.popleft()
            if distance >= depth:
                continue
            for parent in sorted(self.graph.dependents_of(node)):
                if parent in seen:
                    continue
                seen.add(parent)
                found[parent] = (distance + 1, origin)
                queue.append((parent, distance + 1, origin))
        items = [
            AffectedFile(self.relative(n), d, via) for n, (d, via) in found.items()
        ]
        return sorted(items, key=lambda a: (a.depth, a.path))
