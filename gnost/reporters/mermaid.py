# gnost/reporters/mermaid.py

from typing import Dict, Set
from gnost.core.flow import FlowResult


class MermaidFlowReporter:
    """
    Generates Mermaid flowchart diagrams from FlowResult.
    """

    def __init__(
        self,
        flow: FlowResult,
        root: str,
        overview: bool = False,
        depth: int | None = None,
        layered: bool = False,
    ):
        self.flow = flow
        self.root = root
        self.overview = overview
        self.depth = depth
        self.layered = layered

    # =====================================================
    # Public API
    # =====================================================

    def render(self, markdown: bool = True) -> str:
        return self._render_markdown() if markdown else self._render_raw()

    def render_path(self, path: list[str], markdown: bool = True) -> str:
        """
        Render a single execution path (used for entry + representative paths).
        """
        nodes = path[: self.depth + 1] if self.depth else path
        if len(nodes) < 2:
            return ""

        lines = []
        if markdown:
            lines.append("```mermaid")

        lines.append("flowchart LR")

        node_ids = {
            n: self._shorten(n).replace("/", "_").replace(".", "_").replace("-", "_")
            for n in nodes
        }

        for i in range(len(nodes) - 1):
            lines.append(f"  {node_ids[nodes[i]]} --> {node_ids[nodes[i + 1]]}")

        if markdown:
            lines.append("```")

        return "\n".join(lines)

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

        lines = []
        if markdown:
            lines.append("```mermaid")

        lines.append("flowchart LR")

        node_ids = self._build_node_ids(edges)

        if self.layered:
            self._emit_layer_defs(lines)
            self._emit_layered_nodes(lines, node_ids)

        for src, dst in edges:
            lines.append(f"  {node_ids[src]} --> {node_ids[dst]}")

        if self.layered:
            for node, nid in node_ids.items():
                lines.append(f"  class {nid} {self._layer_class(node)}")

        if markdown:
            lines.append("```")

        return "\n".join(lines)

    # =====================================================
    # Rendering entry points
    # =====================================================

    def _render_markdown(self) -> str:
        lines = ["```mermaid", "flowchart TD"]
        self._render_body(lines)
        lines.append("```")
        return "\n".join(lines)

    def _render_raw(self) -> str:
        lines = ["flowchart TD"]
        self._render_body(lines)
        return "\n".join(lines)

    def _render_body(self, lines: list[str]):
        if self.layered:
            self._emit_layer_defs(lines)

        self._append_edges(lines)

    # =====================================================
    # Core edge emission (IMPORTANT PART)
    # =====================================================

    def _append_edges(self, lines: list[str]):
        """
        OVERVIEW:
          - Uses node filtering (entry + core)
          - NO deduplication

        FULL FLOW:
          - Uses all paths
          - NO deduplication (keeps original behavior)
        """
        if self.overview:
            edges = self._collect_edges()
        else:
            paths = self._normalize_paths()
            edges = self._collect_edges_from_paths(paths)

        if not edges:
            return

        node_ids = self._build_node_ids(edges)

        if self.layered:
            self._emit_layered_nodes(lines, node_ids)

        for src, dst in edges:
            lines.append(f"  {node_ids[src]} --> {node_ids[dst]}")

        if self.layered:
            for node, nid in node_ids.items():
                lines.append(f"  class {nid} {self._layer_class(node)}")

    # =====================================================
    # Path helpers
    # =====================================================

    def _normalize_paths(self) -> list[list[str]]:
        return [p.path for p in self.flow.paths]

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

    # =====================================================
    # ORIGINAL overview logic (unchanged & correct)
    # =====================================================

    def _collect_edges(self) -> Set[tuple[str, str]]:
        edges = set()
        allowed_nodes = self._overview_nodes() if self.overview else None

        for p in self.flow.paths:
            nodes = p.path[: self.depth + 1] if self.depth else p.path
            for i in range(len(nodes) - 1):
                src, dst = nodes[i], nodes[i + 1]
                if allowed_nodes and (
                    src not in allowed_nodes or dst not in allowed_nodes
                ):
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

    def _emit_layered_nodes(self, lines, node_ids):
        layers = {"Entry": [], "Core": [], "Leaf": []}
        for node in node_ids:
            layers[self._node_layer(node)].append(node)

        for layer, nodes in layers.items():
            if not nodes:
                continue
            lines.append(f"  subgraph {layer}")
            for n in nodes:
                lines.append(f"    {node_ids[n]}")
            lines.append("  end")

        lines.append("")

    def _node_layer(self, node: str) -> str:
        if node in self.flow.layers.get("entry", []):
            return "Entry"
        if node in self.flow.layers.get("core", []):
            return "Core"
        return "Leaf"

    def _layer_class(self, node: str) -> str:
        return self._node_layer(node).lower()

    # =====================================================
    # Utilities
    # =====================================================

    def _build_node_ids(self, edges: Set[tuple[str, str]]) -> Dict[str, str]:
        nodes = set()
        for s, d in edges:
            nodes.add(s)
            nodes.add(d)

        return {
            n: self._shorten(n).replace("/", "_").replace(".", "_").replace("-", "_")
            for n in nodes
        }

    def _shorten(self, path: str) -> str:
        return path.replace(self.root + "/", "")
