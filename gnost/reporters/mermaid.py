# gnost/reporters/mermaid.py

from typing import Dict, Set

from gnost.core.flow import FlowResult


class MermaidFlowReporter:
    """
    Generates Mermaid flowchart diagrams from FlowResult.
    """

    def __init__(self, flow: FlowResult, root: str):
        self.flow = flow
        self.root = root

    # -------------------------
    # Public API
    # -------------------------

    def render(self, markdown: bool = True) -> str:
        if markdown:
            return self._render_markdown()
        return self._render_raw()

    def _render_markdown(self) -> str:
        lines = ["```mermaid", "flowchart TD"]
        self._append_edges(lines)
        lines.append("```")
        return "\n".join(lines)

    def _render_raw(self) -> str:
        lines = ["flowchart TD"]
        self._append_edges(lines)
        return "\n".join(lines)

    def _append_edges(self, lines: list[str]):
        edges = self._collect_edges()
        node_ids = self._build_node_ids(edges)

        for src, dst in edges:
            lines.append(f"  {node_ids[src]} --> {node_ids[dst]}")

    # -------------------------
    # Internal helpers
    # -------------------------

    def _collect_edges(self) -> Set[tuple[str, str]]:
        edges = set()

        for path in self.flow.paths:
            for i in range(len(path.path) - 1):
                edges.add((path.path[i], path.path[i + 1]))

        return edges

    def _build_node_ids(self, edges: Set[tuple[str, str]]) -> Dict[str, str]:
        """
        Mermaid node IDs must be simple identifiers.
        """
        nodes = set()
        for src, dst in edges:
            nodes.add(src)
            nodes.add(dst)

        mapping = {}
        for path in nodes:
            short = self._shorten(path)
            safe = short.replace("/", "_").replace(".", "_").replace("-", "_")
            mapping[path] = safe

        return mapping

    def _shorten(self, path: str) -> str:
        return path.replace(self.root + "/", "")
