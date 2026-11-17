from __future__ import annotations

from typing import Optional
from pathlib import Path
from gnost.utils.paths import shorten
from gnost.config.languages import LANGUAGES
from gnost.scanner.models import ScanResult
from gnost.core.flow import FlowResult
from gnost.reporters.mermaid import DEFAULT_MAX_EDGES, MermaidFlowReporter
from gnost.models.insights import OnboardingInsights


class MarkdownReporter:
    """
    Generates onboarding documentation in Markdown format.
    """

    def __init__(
        self,
        scan: ScanResult,
        flow: FlowResult,
        output_file: str = "ONBOARD.md",
        output_root: Optional[str] = None,
        loc_data: Optional[dict] = None,
        insights: OnboardingInsights = None,
        mermaid_depth: Optional[int] = None,
        mermaid_layered: Optional[bool] = False,
        mermaid_max_edges: int = DEFAULT_MAX_EDGES,
        mermaid_collapse: Optional[int] = None,
        function_flows: Optional[list] = None,
    ):
        self.scan = scan
        self.flow = flow
        self.insights = insights
        self.loc_data = loc_data
        base_output_root = Path(output_root) if output_root else Path(scan.root)
        self.output_file = base_output_root / output_file
        self.mermaid_depth = mermaid_depth
        self.mermaid_layered = mermaid_layered
        self.mermaid_max_edges = mermaid_max_edges
        self.mermaid_collapse = mermaid_collapse
        self.function_flows = function_flows or []

    # -------------------------
    # Public API
    # -------------------------

    def write(self):
        content = self._render()
        content += self._path_specific_flows()
        self.output_file.write_text(content, encoding="utf-8")

    # -------------------------
    # Rendering
    # -------------------------

    def _render(self) -> str:
        sections = [
            self._header(),
            self._project_overview(),
            self._summary_and_stats_tables(),
            self._entry_points(),
            self._routes_md(),
            self._execution_flow(),
            self._function_flows_md(),
            self._mermaid_flow(),
            self._reading_guide(),
        ]
        if self.insights:
            sections.extend(
                [
                    self._first_files_md(),
                    self._caution_areas_md(),
                    self._cycles_md(),
                ]
            )

        return "\n\n".join(s for s in sections if s).strip() + "\n"

    # -------------------------
    # Sections
    # -------------------------

    def _header(self) -> str:
        return (
            f"# {self.scan.root.split('/')[-1]} — Project Onboarding Guide\n\n"
            "_Generated automatically by <a href='https://gnost.readthedocs.io'>GNOST</a>._"
        )

    def _project_overview(self) -> str:
        languages = (
            ", ".join(
                f"{lang} ({count})" for lang, count in self.scan.languages.items()
            )
            or "Unknown"
        )

        framework = self.scan.framework or "Not detected"

        return (
            "## Project Overview\n\n"
            f"- **Root:** `{self.scan.root}`\n"
            f"- **Languages:** {languages}\n"
            f"- **Framework:** {framework}"
        )

    def _entry_points(self) -> str:
        if not self.flow.entry_points:
            return "## Entry Points\n\n_No explicit entry point detected._"

        lines = ["## Entry Points\n"]
        for ep in self.flow.entry_points:
            lines.append(f"- `{self._shorten(ep.file)}` — {ep.reason}")

        return "\n".join(lines)

    FLOW_ENTRIES = 5
    FLOW_DEPTH = 3
    FLOW_LINES = 25

    def _function_flows_md(self) -> str:
        if not self.function_flows:
            return ""

        lines = [
            "## Function-level Flow\n",
            "What each entry point calls, function by function (Python only; "
            "calls through other objects such as `self.client.send()` are not "
            "followed). Full diagrams: [function-flow.md](docs/flow/function-flow.md).\n",
        ]
        for flow in self.function_flows[: self.FLOW_ENTRIES]:
            entry = flow.entry
            lines.append(f"### `{flow.label}` → `{entry.function}`\n")
            lines.append(f"`{self._shorten(entry.file)}:{entry.line}`\n")
            body: list = []
            self._call_lines(entry, 0, body)
            if len(body) > self.FLOW_LINES:
                body = body[: self.FLOW_LINES] + ["- _...more calls not shown_"]
            lines += body + [""]
        if len(self.function_flows) > self.FLOW_ENTRIES:
            lines.append(
                f"_...and {len(self.function_flows) - self.FLOW_ENTRIES} more entry points "
                "in the insights JSON (`--json`)._"
            )
        return "\n".join(lines).rstrip()

    def _call_lines(self, node, depth: int, out: list) -> None:
        if depth >= self.FLOW_DEPTH:
            if node.calls:
                out.append("  " * depth + "- _..._")
            return
        for child in node.calls:
            mark = " _(shown above)_" if child.repeat else ""
            out.append(
                "  " * depth
                + f"- `{child.function}` (`{self._shorten(child.file)}:{child.line}`){mark}"
            )
            if not child.repeat:
                self._call_lines(child, depth + 1, out)

    ROUTE_LIMIT = 40

    def _routes_md(self) -> str:
        routes = self.scan.routes
        if not routes:
            return ""

        lines = [
            "## Routes\n",
            f"{len(routes)} endpoints found. Each row is a URL and the code that handles it.\n",
            "| Method | Path | Handler | File |",
            "|---|---|---|---|",
        ]
        for route in routes[: self.ROUTE_LIMIT]:
            path = route.path.replace("|", "\\|")
            lines.append(
                f"| {route.method} | `{path}` | `{route.handler}` | "
                f"`{self._shorten(route.file)}:{route.line}` |"
            )
        if len(routes) > self.ROUTE_LIMIT:
            lines.append(
                f"\n_...and {len(routes) - self.ROUTE_LIMIT} more; "
                "the full list is in the insights JSON (`--json`)._"
            )
        return "\n".join(lines)

    def _execution_flow(self) -> str:
        if not self.flow.paths:
            return "## Execution Flow\n\n_Unable to infer execution flow._"

        lines = ["## Execution Flow (High Level)\n"]

        MAX_PATHS = 5
        for path in self.flow.paths[:MAX_PATHS]:
            chain = " → ".join(f"`{self._shorten(p)}`" for p in path.path)
            lines.append(f"- {chain}")

        if len(self.flow.paths) > MAX_PATHS:
            lines.append(
                f"\n_({len(self.flow.paths) - MAX_PATHS} additional paths omitted for clarity.)_"
            )

        return "\n".join(lines)

    READING_LIMIT = 15

    def _reading_guide(self) -> str:
        lines = ["## Recommended Reading Order\n"]

        sections = [
            ("entry", "### Start Here\n"),
            ("core", "\n### Core Logic\n"),
            ("leaf", "\n### Supporting / Leaf Code\n"),
        ]
        for layer, heading in sections:
            files = self.flow.ordered_layer(layer)
            if not files:
                continue
            lines.append(heading)
            for f in files[: self.READING_LIMIT]:
                lines.append(f"- `{self._shorten(f)}`")
            if len(files) > self.READING_LIMIT:
                lines.append(
                    f"- _...and {len(files) - self.READING_LIMIT} more (closest to an entry point listed first)_"
                )

        return "\n".join(lines)

    def _path_specific_flows(self) -> str:
        return (
            "## Key Execution Paths\n\n"
            "To understand specific scenarios, see the entry-based execution paths:\n\n"
            "- 📍 [Entry-based Paths](docs/flow/entry-paths.md)\n\n"
            "- 🧭 [folder-based Paths](docs/flow/folder-paths.md)\n\n"
            "(Complete system flow: [flow/flow-full.md](docs/flow/FLOW-full.md))\n"
        )

    def _mermaid_flow(self) -> str:
        """
        Render a high-level overview Mermaid diagram and link to full flow.
        """

        overview_reporter = MermaidFlowReporter(
            flow=self.flow,
            root=self.scan.root,
            overview=True,
            depth=self.mermaid_depth,
            layered=self.mermaid_layered,
            max_edges=self.mermaid_max_edges,
            collapse=self.mermaid_collapse,
        )
        overview_diagram = overview_reporter.render()
        notes = overview_reporter.notes_markdown()
        if notes:
            overview_diagram += "\n\n" + notes

        return (
            "## Execution Flow (Overview)\n\n"
            f"{overview_diagram}\n\n"
            "> 📌 This diagram shows the high-level execution flow.<br>"
            "For the complete flow, see "
            "[**flow/flow-full.md**](./docs/flow/FLOW-full.md)<br>"
            "Raw Mermaid: [flow/flow-full.mmd](./docs/flow/FLOW-full.mmd)"
        )

    def _summary_and_stats_tables(self) -> str:
        if not self.loc_data or not self.loc_data.get("by_language"):
            return ""

        rows = []
        for ext, stats in self.loc_data["by_language"].items():
            language = LANGUAGES.get(ext, {}).get("name", ext.upper())
            rows.append((language, stats))

        rows.sort(key=lambda item: item[0].lower())

        summary_lines = [
            "## Summary Table",
            "",
            "| Language | Files | LOC |",
            "|---|---:|---:|",
        ]
        for language, stats in rows:
            summary_lines.append(f"| {language} | {stats['files']} | {stats['loc']} |")

        stats_lines = [
            "## Stats Table",
            "",
            "| Language | Files | Code | Comments | Blanks | LOC |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for language, stats in rows:
            stats_lines.append(
                f"| {language} | {stats['files']} | {stats['code']} | "
                f"{stats['comments']} | {stats['blanks']} | {stats['loc']} |"
            )

        return "\n".join(summary_lines + [""] + stats_lines)

    def _first_files_md(self) -> str:
        lines = ["## 📘 First Files to Read"]

        for item in self.insights.first_files:
            short_path = self._shorten(item.path)
            lines.append(f"- **`{short_path}`**")
            lines.append(f"  - {item.reason}")

        return "\n".join(lines)

    def _caution_areas_md(self) -> str:
        lines = ["## ⚠️ Caution Areas"]

        for c in self.insights.caution_areas:
            short_path = self._shorten(c.path)
            lines.append(f"### `{short_path}`")
            lines.append(f"- **Type:** {c.category.value}")
            lines.append(f"- **Severity:** {c.severity}")
            if c.score:
                note = " (partial: some checks need Python)" if c.partial else ""
                lines.append(f"- **Caution score:** {c.score:g}/100{note}")
            lines.append(f"- {c.description}")

        return "\n".join(lines)

    CYCLE_LIMIT = 10

    def _cycles_md(self) -> str:
        cycles = self.insights.cycles
        lines = ["## 🔁 Circular Dependencies", ""]
        if not cycles:
            lines.append("_No circular dependencies detected._")
            return "\n".join(lines)

        by_kind = {
            "import-time": [c for c in cycles if c.kind == "import-time"],
            "deferred": [c for c in cycles if c.kind == "deferred"],
        }
        lines.append(
            f"{len(by_kind['import-time'])} import-time, "
            f"{len(by_kind['deferred'])} deferred. Import-time cycles load as the "
            "modules start and can fail there; deferred ones go through an import "
            "inside a function, a type-only import or a dynamic `import()` and "
            "are usually intentional."
        )

        titles = {
            "import-time": "### Import-time",
            "deferred": "### Deferred",
        }
        for kind, group in by_kind.items():
            if not group:
                continue
            lines += ["", titles[kind], ""]
            for cycle in group[: self.CYCLE_LIMIT]:
                chain = " → ".join(f"`{self._shorten(f)}`" for f in cycle.example)
                extra = (
                    f" _(group of {len(cycle.files)} files)_"
                    if len(cycle.files) > len(set(cycle.example))
                    else ""
                )
                lines.append(f"- {chain}{extra}")
            if len(group) > self.CYCLE_LIMIT:
                lines.append(f"- _...and {len(group) - self.CYCLE_LIMIT} more_")

        return "\n".join(lines)

    # -------------------------
    # Helpers
    # -------------------------

    def _shorten(self, path: str) -> str:
        return shorten(path, self.scan.root)
