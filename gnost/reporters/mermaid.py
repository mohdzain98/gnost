# gnost/reporters/mermaid.py

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from gnost.utils.paths import shorten
from gnost.core.flow import FlowResult
from gnost.reporters.mermaid_graph import (
    CYCLE,
    CYCLE_DEFERRED,
    CYCLE_SOFT,
    DEFERRED,
    Diagram,
    DiagramEdge,
    DiagramNode,
    Edge,
    build_diagram,
    common_prefix,
    edge_styles,
    edges_within,
)

# GitHub refuses Mermaid sources over 50 000 characters or 500 edges, and large
# diagrams stop being readable long before that.
DEFAULT_MAX_EDGES = 80
OVERVIEW_MAX_EDGES = 60
COMBINED_MAX_EDGES = 60  # per-feature diagrams in folder-paths.md
MAX_CHARS = 45_000
DRILLDOWN_FOLDERS = 6

# Words Mermaid treats as keywords when they appear as node ids.
_RESERVED = {
    "end",
    "graph",
    "subgraph",
    "flowchart",
    "class",
    "classdef",
    "style",
    "click",
    "default",
    "linkstyle",
    "direction",
}

_ARROWS = {
    "normal": "-->",
    DEFERRED: "-.->",
    CYCLE: "==>",
    CYCLE_DEFERRED: "-.->",
    CYCLE_SOFT: "-->",
}
_LINK_STYLES = {
    CYCLE: "stroke:#d32f2f,stroke-width:3px",
    CYCLE_DEFERRED: "stroke:#f57c00,stroke-width:2px",
    CYCLE_SOFT: "stroke:#f57c00,stroke-width:2px",
}


class MermaidFlowReporter:
    """
    Generates Mermaid flowchart diagrams from FlowResult.

    Diagrams that would be too big are grouped by folder (and, as a last
    resort, trimmed) so they stay renderable; `notes` explains what was done
    after a render.
    """

    def __init__(
        self,
        flow: FlowResult,
        root: str,
        overview: bool = False,
        depth: Optional[int] = None,
        layered: bool = False,
        max_edges: int = DEFAULT_MAX_EDGES,
        collapse: Optional[int] = None,
    ):
        self.flow = flow
        self.root = root
        self.overview = overview
        self.depth = depth
        self.layered = layered
        self.max_edges = max_edges
        self.collapse = collapse
        self.notes: List[str] = []
        self._styles: Optional[Dict[Edge, str]] = None

    # =====================================================
    # Public API
    # =====================================================

    def render(self, markdown: bool = True) -> str:
        diagram = self._fit(self._styled_edges(), self._budget(), self.collapse)
        return self._draw(diagram, "TD", markdown)

    def render_path(self, path: list[str], markdown: bool = True) -> str:
        """
        Render a single execution path (used for entry + representative paths).
        """
        nodes = path[: self.depth + 1] if self.depth else path
        if len(nodes) < 2:
            return ""

        edges = {(nodes[i], nodes[i + 1]) for i in range(len(nodes) - 1)}
        diagram = build_diagram(self._style(edges), self.root, max_edges=len(edges))
        return self._draw(diagram, "LR", markdown)

    def render_combined_paths(
        self,
        paths: list[list[str]],
        markdown: bool = True,
    ) -> str:
        """
        Render merged execution paths (used for keyword + deduplicated groups).
        """
        edges = self._collect_edges_from_paths(paths)
        if not edges:
            return ""

        diagram = self._fit(
            self._style(edges), min(self.max_edges, COMBINED_MAX_EDGES), None
        )
        return self._draw(diagram, "LR", markdown)

    def render_complete(self) -> str:
        """Every file and every import edge, ungrouped and unpruned.

        Meant for tools and AI, not for reading: it can exceed what GitHub
        will render.
        """
        styled = self._styled_edges()
        diagram = build_diagram(styled, self.root, max_edges=max(len(styled), 1))
        return self._draw(diagram, "TD", False, record=False)

    def render_document(self) -> str:
        """The body of FLOW-full.md: the whole flow, plus one detailed diagram
        per big folder when the whole flow had to be grouped by folder."""
        styled = self._styled_edges()
        diagram = self._fit(styled, self.max_edges, self.collapse)
        parts = [self._draw(diagram, "TD", True)]
        notes = self.notes_markdown()
        if notes:
            parts.append(notes)

        if diagram.collapsed:
            parts.extend(self._drilldown(styled, diagram))
        return "\n\n".join(p for p in parts if p)

    def notes_markdown(self) -> str:
        return "\n".join(f"> {n}" for n in self.notes)

    # =====================================================
    # Drill-down
    # =====================================================

    def _drilldown(self, styled: Dict[Edge, str], overall: Diagram) -> List[str]:
        files = sorted({f for edge in styled for f in edge})
        base = common_prefix(files, self.root)
        level = overall.level or 1

        sizes = sorted(
            (
                (folder, node.files)
                for folder, node in overall.nodes.items()
                if node.files > 1
            ),
            key=lambda item: (-item[1], item[0]),
        )

        parts: List[str] = []
        for folder, count in sizes:
            inner = edges_within(styled, self.root, base, level, folder)
            if not inner:
                continue
            sub = MermaidFlowReporter(
                flow=self.flow,
                root=self.root,
                layered=False,
                max_edges=self.max_edges,
            )
            diagram = sub._fit(inner, self.max_edges, None)
            title = "(root)" if folder == "." else folder
            parts.append(f"## `{title}` ({count} files)")
            parts.append(sub._draw(diagram, "TD", True))
            if sub.notes:
                parts.append(sub.notes_markdown())
            if len(parts) >= DRILLDOWN_FOLDERS * 3:
                break

        if parts:
            parts.insert(
                0,
                "# Detail by folder\n\nThe diagram above groups files by "
                "folder. These show the files inside the biggest folders.",
            )
        return parts

    # =====================================================
    # Fitting and drawing
    # =====================================================

    def _budget(self) -> int:
        return (
            min(OVERVIEW_MAX_EDGES, self.max_edges) if self.overview else self.max_edges
        )

    def _fit(
        self, styled: Dict[Edge, str], budget: int, level: Optional[int]
    ) -> Diagram:
        """Build a diagram within the edge budget and the character limit."""
        diagram = build_diagram(styled, self.root, budget, level)
        for _ in range(8):
            if len(self._draw(diagram, "TD", False, record=False)) <= MAX_CHARS:
                break
            budget = max(5, int(budget * 0.6))
            diagram = build_diagram(styled, self.root, budget, level)
        self._record_notes(diagram)
        return diagram

    def _record_notes(self, diagram: Diagram) -> None:
        self.notes = []
        if diagram.collapsed:
            folders = len(diagram.nodes)
            self.notes.append(
                f"Grouped by folder to stay readable: {folders} folders; "
                "numbers on arrows count the file-level imports they stand for."
            )
        if diagram.hubs:
            names = ", ".join(f"`{k}`" for k in sorted(diagram.hubs))
            self.notes.append(
                f"Arrows into {names} are not drawn: most folders import "
                "them, and drawing every arrow would hide the structure."
            )
        if diagram.omitted:
            self.notes.append(
                f"{diagram.omitted} less important dependencies are not drawn "
                "(cycles are always kept first)."
            )
        styles = diagram.styles()
        if CYCLE in styles:
            self.notes.append(
                "Thick red arrows: circular imports that happen as modules load."
            )
        if CYCLE_DEFERRED in styles or CYCLE_SOFT in styles:
            self.notes.append(
                "Orange arrows (dotted when the import itself is deferred): circular "
                "dependencies that only close through an import inside a function, "
                "a type-only import or a dynamic import."
            )
        if DEFERRED in styles:
            self.notes.append(
                "Dotted arrows: imports that do not run when the module loads."
            )

    def _draw(
        self, diagram: Diagram, direction: str, markdown: bool, record: bool = True
    ) -> str:
        lines: List[str] = []
        if markdown:
            lines.append("```mermaid")
        lines.append(f"flowchart {direction}")

        if not diagram.edges:
            if markdown:
                lines.append("```")
            return "\n".join(lines) if record else ""

        ids = self._node_ids(diagram)
        layered = self.layered and not diagram.collapsed

        if layered:
            self._emit_layer_defs(lines)
            groups: Dict[str, List[str]] = {"Entry": [], "Core": [], "Leaf": []}
            for key in diagram.nodes:
                groups[self._node_layer(key)].append(key)
            for layer, keys in groups.items():
                if keys:
                    lines.append(f"  subgraph {layer}")
                    lines.extend(f"    {self._node_def(diagram, k, ids)}" for k in keys)
                    lines.append("  end")
            lines.append("")
        else:
            lines.extend(f"  {self._node_def(diagram, k, ids)}" for k in diagram.nodes)

        styled_links: Dict[str, List[int]] = {}
        for index, edge in enumerate(diagram.edges):
            arrow = _ARROWS[edge.style]
            label = f"|{edge.weight}|" if diagram.collapsed and edge.weight > 1 else ""
            lines.append(f"  {ids[edge.src]} {arrow}{label} {ids[edge.dst]}")
            if edge.style in _LINK_STYLES:
                styled_links.setdefault(edge.style, []).append(index)

        for style, indexes in styled_links.items():
            joined = ",".join(str(i) for i in indexes)
            lines.append(f"  linkStyle {joined} {_LINK_STYLES[style]}")

        cycle_nodes = [ids[k] for k, n in diagram.nodes.items() if n.in_cycle]
        if cycle_nodes:
            lines.append("  classDef cycle stroke:#d32f2f,stroke-width:3px")
            lines.append(f"  class {','.join(cycle_nodes)} cycle")

        if layered:
            for key in diagram.nodes:
                lines.append(f"  class {ids[key]} {self._layer_class(key)}")

        if markdown:
            lines.append("```")
        return "\n".join(lines)

    def _node_def(self, diagram: Diagram, key: str, ids: Dict[str, str]) -> str:
        node = diagram.nodes[key]
        label = self._escape(node.label)
        if node.folder:
            noun = "file" if node.files == 1 else "files"
            label += f"<br/>{node.files} {noun}"
        return f'{ids[key]}["{label}"]'

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace('"', "'")

    def _node_ids(self, diagram: Diagram) -> Dict[str, str]:
        ids: Dict[str, str] = {}
        taken: Set[str] = set()
        for key in sorted(diagram.nodes):
            node = diagram.nodes[key]
            base = re.sub(
                r"[^0-9A-Za-z_]", "_", self._shorten(node.label if node.folder else key)
            )
            ident = f"dir_{base}" if node.folder else base
            if ident.lower() in _RESERVED or not re.match(r"[A-Za-z_]", ident):
                ident = (
                    f"n_{ident}"  # `end`, `graph`... or a leading digit break Mermaid
                )
            candidate, n = ident, 1
            while candidate in taken:
                n += 1
                candidate = f"{ident}_{n}"
            taken.add(candidate)
            ids[key] = candidate
        return ids

    # =====================================================
    # Edges
    # =====================================================

    def _all_styles(self) -> Dict[Edge, str]:
        if self._styles is None:
            self._styles = edge_styles(
                self.flow.edges, self.flow.deferred_edges, self.flow.cycles
            )
        return self._styles

    def _style(self, edges: Set[Edge]) -> Dict[Edge, str]:
        known = self._all_styles()
        return {e: known.get(e, "normal") for e in edges}

    def _styled_edges(self) -> Dict[Edge, str]:
        return self._style(self._collect_edges())

    def _collect_edges_from_paths(
        self,
        paths: list[list[str]],
    ) -> Set[tuple[str, str]]:
        edges = set()
        for path in paths:
            nodes = path[: self.depth + 1] if self.depth else path
            for i in range(len(nodes) - 1):
                edges.add((nodes[i], nodes[i + 1]))
        return edges

    def _collect_edges(self) -> Set[tuple[str, str]]:
        allowed_nodes = self._overview_nodes() if self.overview else None
        flow = self.flow

        edges = set()
        for src, dst in flow.edges:
            if self.depth and flow.depths.get(src, 0) >= self.depth:
                continue
            if allowed_nodes and (src not in allowed_nodes or dst not in allowed_nodes):
                continue
            edges.add((src, dst))
        return edges

    def _overview_nodes(self) -> Set[str]:
        nodes = set()
        for ep in self.flow.entry_points:
            nodes.add(ep.file)
        for f in self.flow.layers.get("core", []):
            nodes.add(f)
        return nodes

    # =====================================================
    # Layer helpers
    # =====================================================

    def _emit_layer_defs(self, lines: list[str]):
        lines.extend(
            [
                "classDef entry fill:#e3f2fd,stroke:#1e88e5,stroke-width:2px",
                "classDef core fill:#e8f5e9,stroke:#43a047,stroke-width:2px",
                "classDef leaf fill:#f5f5f5,stroke:#757575,stroke-width:2px",
                "",
            ]
        )

    def _common_prefix(self, paths: list[list[str]]) -> list[str]:
        """
        Compute the common prefix across multiple execution paths.
        """
        if not paths:
            return []

        prefix = paths[0]

        for path in paths[1:]:
            i = 0
            while i < len(prefix) and i < len(path) and prefix[i] == path[i]:
                i += 1
            prefix = prefix[:i]

            if not prefix:
                break

        return prefix

    def _deduplicate_paths(
        self,
        paths: list[list[str]],
        min_prefix: int = 2,
    ) -> list[list[list[str]]]:
        """
        Group near-identical execution paths based on common prefix length.

        Returns a list of path groups.
        Each group is a list[list[str]].
        """
        groups: list[list[list[str]]] = []
        used = set()

        for i, p in enumerate(paths):
            if i in used:
                continue

            group = [p]
            used.add(i)

            for j in range(i + 1, len(paths)):
                if j in used:
                    continue

                other = paths[j]
                if len(self._common_prefix([p, other])) >= min_prefix:
                    group.append(other)
                    used.add(j)

            groups.append(group)

        return groups

    def _node_layer(self, node: str) -> str:
        if node in self.flow.layers.get("entry", []):
            return "Entry"
        if node in self.flow.layers.get("core", []):
            return "Core"
        return "Leaf"

    def _layer_class(self, node: str) -> str:
        return self._node_layer(node).lower()

    def _shorten(self, path: str) -> str:
        return shorten(path, self.root)


def render_call_tree(tree, root: str, direction: str = "LR") -> str:
    """Mermaid diagram of a function call tree (see gnost.core.callgraph)."""
    import os

    def rel(path: str) -> str:
        return os.path.relpath(path, root).replace(os.sep, "/")

    nodes: Dict[str, DiagramNode] = {}
    edges: Dict[Tuple[str, str], DiagramEdge] = {}

    def key(node) -> str:
        return f"{rel(node.file)}::{node.function}"

    def visit(node) -> None:
        nodes.setdefault(
            key(node),
            DiagramNode(key(node), f"{node.function}<br/>{rel(node.file)}"),
        )
        for child in node.calls:
            nodes.setdefault(
                key(child),
                DiagramNode(key(child), f"{child.function}<br/>{rel(child.file)}"),
            )
            style = DEFERRED if child.repeat else "normal"  # dotted: shown elsewhere
            edges.setdefault(
                (key(node), key(child)), DiagramEdge(key(node), key(child), style)
            )
            if not child.repeat:
                visit(child)

    visit(tree)
    diagram = Diagram(
        nodes=nodes,
        edges=sorted(edges.values(), key=lambda e: (e.src, e.dst)),
        total_edges=len(edges),
    )
    empty = FlowResult(entry_points=[], paths=[], layers={})
    return MermaidFlowReporter(empty, root)._draw(diagram, direction, True)


def render_function_flows(flows, root: str, limit: int = 5) -> str:
    """The function-flow.md document: one call-tree diagram per entry."""
    import os

    lines = [
        "# Function-level Flow\n",
        "What each entry point calls, function by function (Python only). Dotted "
        "arrows lead to a function already drawn elsewhere in the same diagram. "
        "Calls through other objects (`self.client.send()`) are not followed.\n",
    ]
    for flow in flows[:limit]:
        entry = flow.entry
        where = os.path.relpath(entry.file, root).replace(os.sep, "/")
        lines.append(f"## `{flow.label}` → `{entry.function}`\n")
        lines.append(
            f"`{where}:{entry.line}` · {flow.size} functions"
            + (" · cut short" if flow.truncated else "")
            + "\n"
        )
        lines.append(render_call_tree(entry, root))
        lines.append("")
    if len(flows) > limit:
        lines.append(
            f"_...and {len(flows) - limit} more entry points; see the insights JSON (`--json`)._"
        )
    return "\n".join(lines) + "\n"
