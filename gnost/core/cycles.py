"""Circular dependency detection on the file dependency graph."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Dict, List, Set

from gnost.core.graph import DependencyGraph

Neighbors = Callable[[str], Set[str]]

IMPORT_TIME = "import-time"
DEFERRED = "deferred"


@dataclass
class Cycle:
    """A group of files that depend on each other.

    `kind` is "import-time" when the files import each other as the modules
    load (this can break at startup), or "deferred" when every loop goes through
    an import inside a function, a type-only import or a dynamic `import()`
    (usually deliberate).
    """

    files: List[str]
    example: List[str]  # one concrete loop, e.g. [a, b, a]
    kind: str


def strongly_connected_components(
    nodes: List[str], neighbors: Neighbors
) -> List[List[str]]:
    """Tarjan's algorithm, iterative so deep import chains cannot hit the
    recursion limit. Components come back sorted, in a stable order."""
    index: Dict[str, int] = {}
    low: Dict[str, int] = {}
    on_stack: Set[str] = set()
    stack: List[str] = []
    components: List[List[str]] = []
    counter = 0

    for root in sorted(nodes):
        if root in index:
            continue

        work = [(root, iter(sorted(neighbors(root))))]
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)

        while work:
            node, children = work[-1]
            advanced = False
            for child in children:
                if child not in index:
                    index[child] = low[child] = counter
                    counter += 1
                    stack.append(child)
                    on_stack.add(child)
                    work.append((child, iter(sorted(neighbors(child)))))
                    advanced = True
                    break
                if child in on_stack:
                    low[node] = min(low[node], index[child])
            if advanced:
                continue

            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index[node]:
                component = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member == node:
                        break
                components.append(sorted(component))

    return sorted(components)


def _is_cyclic(component: List[str], neighbors: Neighbors) -> bool:
    return len(component) > 1 or component[0] in neighbors(component[0])


def example_cycle(files: List[str], neighbors: Neighbors) -> List[str]:
    """A shortest loop back to the first file, e.g. [a, b, c, a]."""
    members = set(files)
    start = files[0]
    parents: Dict[str, str] = {}
    queue = deque([start])

    while queue:
        node = queue.popleft()
        for dep in sorted(neighbors(node)):
            if dep not in members:
                continue
            if dep == start:
                chain = [node]
                while chain[-1] != start:
                    chain.append(parents[chain[-1]])
                return chain[::-1] + [start]
            if dep not in parents:
                parents[dep] = node
                queue.append(dep)
    return [start]


def find_cycles(graph: DependencyGraph) -> List[Cycle]:
    """Every cycle group in the graph, import-time ones first.

    A group is a strongly connected component of more than one file, or a file
    that imports itself. Groups are sorted by kind, then size (largest first),
    then name.
    """
    nodes = list(graph.all_nodes())
    cycles: List[Cycle] = []

    for component in strongly_connected_components(nodes, graph.dependencies_of):
        if not _is_cyclic(component, graph.dependencies_of):
            continue

        members = set(component)

        def eager(node: str, members: Set[str] = members) -> Set[str]:
            return graph.eager_dependencies_of(node) & members

        runtime = [
            c
            for c in strongly_connected_components(component, eager)
            if _is_cyclic(c, eager)
        ]
        if runtime:
            neighbors: Neighbors = eager
            kind = IMPORT_TIME
        else:
            neighbors = graph.dependencies_of
            kind = DEFERRED

        cycles.append(Cycle(component, example_cycle(component, neighbors), kind))

    return sorted(cycles, key=lambda c: (c.kind != IMPORT_TIME, -len(c.files), c.files))
