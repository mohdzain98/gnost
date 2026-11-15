"""Diagram model for the Mermaid reporters.

Turns file-level dependency edges into something that renders: it styles cycle
and deferred edges, and when the graph is too big for a readable diagram (GitHub
refuses Mermaid sources over ~50 000 characters or 500 edges) it groups files by
folder, choosing the deepest folder level that fits an edge budget.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

from gnost.core.cycles import IMPORT_TIME, Cycle, strongly_connected_components

NORMAL = "normal"
DEFERRED = "deferred"  # import that does not run at load time
CYCLE_SOFT = "cycle-soft"  # eager import, but its loop needs a deferred import
CYCLE_DEFERRED = "cycle-deferred"  # deferred import on a loop
CYCLE = "cycle"  # eager import on an import-time loop

_RANK = {NORMAL: 0, DEFERRED: 1, CYCLE_SOFT: 2, CYCLE_DEFERRED: 3, CYCLE: 4}

Edge = Tuple[str, str]

MIN_NODES = 6  # fewest boxes worth drawing when grouping by folder
HUB_SHARE = 0.4  # a folder imported by this share of the others is a "hub"
HUB_MIN_IMPORTERS = 6


@dataclass
class DiagramNode:
    key: str
    label: str
    files: int = 1
    folder: bool = False
    in_cycle: bool = False


@dataclass
class DiagramEdge:
    src: str
    dst: str
    style: str = NORMAL
    weight: int = 1


@dataclass
class Diagram:
    nodes: Dict[str, DiagramNode] = field(default_factory=dict)
    edges: List[DiagramEdge] = field(default_factory=list)
    level: Optional[int] = None  # folder level used, None for file-level
    omitted: int = 0  # edges dropped to respect the budget
    total_edges: int = 0  # edges before grouping or dropping
    hubs: Dict[str, int] = field(default_factory=dict)  # shared folders -> hidden edges

    @property
    def collapsed(self) -> bool:
        return self.level is not None

    def styles(self) -> Set[str]:
        return {e.style for e in self.edges}


# -------------------------
# Edge styles
# -------------------------


def edge_styles(
    edges: Iterable[Edge],
    deferred_edges: Set[Edge],
    cycles: List[Cycle],
) -> Dict[Edge, str]:
    """Style of every edge: on an import-time loop, on a loop that needs a
    deferred import (drawn dotted only if the edge itself is deferred), a plain
    deferred import, or normal."""
    edges = list(edges)
    group_of: Dict[str, int] = {}
    for index, cycle in enumerate(cycles):
        for f in cycle.files:
            group_of[f] = index

    successors: Dict[str, Set[str]] = {}
    for src, dst in edges:
        successors.setdefault(src, set()).add(dst)

    # Files that import each other as the modules load, per import-time group.
    eager_component: Dict[str, int] = {}
    next_component = 0
    for index, cycle in enumerate(cycles):
        if cycle.kind != IMPORT_TIME:
            continue
        members = set(cycle.files)

        def eager(node: str, members: Set[str] = members) -> Set[str]:
            return {
                d
                for d in successors.get(node, ())
                if d in members and (node, d) not in deferred_edges
            }

        for component in strongly_connected_components(cycle.files, eager):
            if len(component) > 1 or component[0] in eager(component[0]):
                next_component += 1
                for f in component:
                    eager_component[f] = next_component

    styles: Dict[Edge, str] = {}
    for src, dst in edges:
        deferred = (src, dst) in deferred_edges
        same_group = src in group_of and group_of.get(src) == group_of.get(dst)
        if same_group:
            on_eager_loop = (
                not deferred
                and src in eager_component
                and eager_component.get(src) == eager_component.get(dst)
            )
            if on_eager_loop:
                styles[(src, dst)] = CYCLE
            else:
                styles[(src, dst)] = CYCLE_DEFERRED if deferred else CYCLE_SOFT
        else:
            styles[(src, dst)] = DEFERRED if deferred else NORMAL
    return styles


# -------------------------
# Folder grouping
# -------------------------


def _dir_parts(path: str, root: str) -> List[str]:
    rel = os.path.relpath(os.path.dirname(path), root).replace(os.sep, "/")
    return [] if rel == "." else rel.split("/")


def common_prefix(paths: Iterable[str], root: str) -> List[str]:
    """Folders every file lives under (e.g. `src`), so grouping starts below it."""
    prefix: Optional[List[str]] = None
    for path in paths:
        parts = _dir_parts(path, root)
        if prefix is None:
            prefix = parts
        else:
            i = 0
            while i < len(prefix) and i < len(parts) and prefix[i] == parts[i]:
                i += 1
            prefix = prefix[:i]
    return prefix or []


def folder_key(path: str, root: str, base: List[str], level: int) -> str:
    """Folder a file belongs to at `level` folders below the common prefix."""
    parts = _dir_parts(path, root)
    return "/".join(parts[: len(base) + level]) or "."


def max_level(paths: Iterable[str], root: str, base: List[str]) -> int:
    return max((len(_dir_parts(p, root)) - len(base) for p in paths), default=0)


def _rel(path: str, root: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def _group(styled: Dict[Edge, str], root: str, base: List[str], level: int) -> Diagram:
    members: Dict[str, Set[str]] = {}
    for src, dst in styled:
        for f in (src, dst):
            members.setdefault(folder_key(f, root, base, level), set()).add(f)

    merged: Dict[Edge, DiagramEdge] = {}
    for (src, dst), style in styled.items():
        a = folder_key(src, root, base, level)
        b = folder_key(dst, root, base, level)
        if a == b:
            continue
        edge = merged.setdefault((a, b), DiagramEdge(a, b, NORMAL, 0))
        edge.weight += 1
        if _RANK[style] > _RANK[edge.style]:
            edge.style = style

    nodes = {
        key: DiagramNode(
            key=key,
            label="(root)" if key == "." else key,
            files=len(files),
            folder=True,
        )
        for key, files in members.items()
    }
    return Diagram(
        nodes=nodes,
        edges=sorted(merged.values(), key=lambda e: (e.src, e.dst)),
        level=level,
        total_edges=len(styled),
    )


def _hide_hubs(diagram: Diagram) -> Diagram:
    """Stop drawing arrows into shared folders (utilities, config, db).

    A folder that most others import adds one arrow from everywhere and turns
    the picture into a hairball; it is listed in a note instead. Cycle arrows
    are always kept.
    """
    if len(diagram.nodes) < MIN_NODES:
        return diagram
    importers: Dict[str, Set[str]] = {}
    for e in diagram.edges:
        importers.setdefault(e.dst, set()).add(e.src)
    limit = max(HUB_MIN_IMPORTERS, int(HUB_SHARE * len(diagram.nodes)))
    hubs = {k for k, v in importers.items() if len(v) >= limit}
    if not hubs:
        return diagram
    kept = [
        e
        for e in diagram.edges
        if e.dst not in hubs or e.style in (CYCLE, CYCLE_DEFERRED, CYCLE_SOFT)
    ]
    for hub in hubs:
        diagram.hubs[hub] = sum(1 for e in diagram.edges if e.dst == hub) - sum(
            1 for e in kept if e.dst == hub
        )
    diagram.edges = kept
    return diagram


def _prune(diagram: Diagram, max_edges: int) -> Diagram:
    if len(diagram.edges) <= max_edges:
        return diagram
    ranked = sorted(
        diagram.edges,
        key=lambda e: (-_RANK[e.style], -e.weight, e.src, e.dst),
    )
    kept = sorted(ranked[:max_edges], key=lambda e: (e.src, e.dst))
    used = {e.src for e in kept} | {e.dst for e in kept}
    diagram.omitted += len(diagram.edges) - len(kept)
    diagram.edges = kept
    diagram.nodes = {k: n for k, n in diagram.nodes.items() if k in used}
    return diagram


def _mark_cycle_nodes(diagram: Diagram) -> Diagram:
    for edge in diagram.edges:
        if edge.style == CYCLE:
            diagram.nodes[edge.src].in_cycle = True
            diagram.nodes[edge.dst].in_cycle = True
    return diagram


def build_diagram(
    styled: Dict[Edge, str],
    root: str,
    max_edges: int,
    level: Optional[int] = None,
) -> Diagram:
    """Diagram of `styled` edges that fits in `max_edges`.

    Files are shown individually when they fit. Otherwise they are grouped by
    folder, using the deepest level that fits (or `level` when given), and as a
    last resort the least important edges are dropped (cycles are kept first).
    """
    files = sorted({f for edge in styled for f in edge})
    base = common_prefix(files, root)

    def file_level() -> Diagram:
        nodes = {f: DiagramNode(key=f, label=_rel(f, root)) for f in files}
        edges = [DiagramEdge(s, d, st) for (s, d), st in sorted(styled.items())]
        return Diagram(nodes=nodes, edges=edges, total_edges=len(styled))

    if level is None and len(styled) <= max_edges:
        return _mark_cycle_nodes(file_level())

    deepest = max_level(files, root, base)
    if level is not None:
        chosen = max(1, min(level, max(deepest, 1)))
        return _mark_cycle_nodes(
            _prune(_hide_hubs(_group(styled, root, base, chosen)), max_edges)
        )

    for chosen in range(deepest, 0, -1):
        diagram = _hide_hubs(_group(styled, root, base, chosen))
        if len(diagram.edges) <= max_edges:
            # A diagram of two or three boxes says nothing: when the level that
            # fits is that coarse, keep the next, more detailed level and drop
            # the least important edges instead.
            if len(diagram.nodes) < MIN_NODES and chosen < deepest:
                finer = _hide_hubs(_group(styled, root, base, chosen + 1))
                return _mark_cycle_nodes(_prune(finer, max_edges))
            return _mark_cycle_nodes(diagram)

    return _mark_cycle_nodes(
        _prune(_hide_hubs(_group(styled, root, base, 1)), max_edges)
    )


def edges_within(
    styled: Dict[Edge, str], root: str, base: List[str], level: int, folder: str
) -> Dict[Edge, str]:
    """Edges whose two files both belong to `folder` (for drill-down views)."""
    return {
        (s, d): st
        for (s, d), st in styled.items()
        if folder_key(s, root, base, level) == folder
        and folder_key(d, root, base, level) == folder
    }
