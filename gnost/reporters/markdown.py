from pathlib import Path
from gnost.config.languages import LANGUAGES
from gnost.scanner.models import ScanResult
from gnost.core.flow import FlowResult
from gnost.reporters.mermaid import MermaidFlowReporter
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
        output_root: str | None = None,
        loc_data: dict | None = None,
        insights: OnboardingInsights = None,
        mermaid_depth: int | None = None,
        mermaid_layered: bool | None = False,
    ):
        self.scan = scan
        self.flow = flow
        self.insights = insights
        self.loc_data = loc_data
        base_output_root = Path(output_root) if output_root else Path(scan.root)
        self.output_file = base_output_root / output_file
        self.mermaid_depth = mermaid_depth
        self.mermaid_layered = mermaid_layered

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
            self._execution_flow(),
            self._mermaid_flow(),
            self._reading_guide(),
        ]
        if self.insights:
            sections.extend(
                [
                    self._first_files_md(),
                    self._caution_areas_md(),
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
            return "## Entry Points\n\n" "_No explicit entry point detected._"

        lines = ["## Entry Points\n"]
        for ep in self.flow.entry_points:
            lines.append(f"- `{self._shorten(ep.file)}` — {ep.reason}")

        return "\n".join(lines)

    def _execution_flow(self) -> str:
        if not self.flow.paths:
            return "## Execution Flow\n\n" "_Unable to infer execution flow._"

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

    def _reading_guide(self) -> str:
        layers = self.flow.layers

        lines = ["## Recommended Reading Order\n"]

        if layers.get("entry"):
            lines.append("### Start Here\n")
            for f in sorted(layers["entry"]):
                lines.append(f"- `{self._shorten(f)}`")

        if layers.get("core"):
            lines.append("\n### Core Logic\n")
            for f in sorted(layers["core"]):
                lines.append(f"- `{self._shorten(f)}`")

        if layers.get("leaf"):
            lines.append("\n### Supporting / Leaf Code\n")
            for f in sorted(layers["leaf"]):
                lines.append(f"- `{self._shorten(f)}`")

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
        )
        overview_diagram = overview_reporter.render()

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

    def _short_path(self, path: str, depth: int = 2) -> str:
        """
        Shorten a file path to the last `depth` components.
        Example:
        gnost/core/flow.py  → core/flow.py
        """
        parts = path.replace("\\", "/").split("/")
        return "/".join(parts[-depth:])

    def _first_files_md(self) -> str:
        lines = ["## 📘 First Files to Read"]

        for item in self.insights.first_files:
            short_path = self._short_path(path=item.path, depth=3)
            lines.append(f"- **`{short_path}`**")
            lines.append(f"  - {item.reason}")

        return "\n".join(lines)

    def _caution_areas_md(self) -> str:
        lines = ["## ⚠️ Caution Areas"]

        for c in self.insights.caution_areas:
            short_path = self._short_path(path=c.path, depth=3)
            lines.append(f"### `{short_path}`")
            lines.append(f"- **Type:** {c.category.value}")
            lines.append(f"- **Severity:** {c.severity}")
            lines.append(f"- {c.description}")

        return "\n".join(lines)

    # -------------------------
    # Helpers
    # -------------------------

    def _shorten(self, path: str) -> str:
        return path.replace(self.scan.root + "/", "")
