# gnost/reporters/markdown.py

from pathlib import Path
from typing import List

from gnost.scanner.models import ScanResult
from gnost.core.flow import FlowResult
from gnost.reporters.mermaid import MermaidFlowReporter


class MarkdownReporter:
    """
    Generates onboarding documentation in Markdown format.
    """

    def __init__(
        self,
        scan: ScanResult,
        flow: FlowResult,
        output_file: str = "ONBOARD.md",
    ):
        self.scan = scan
        self.flow = flow
        self.output_file = Path(scan.root) / output_file

    # -------------------------
    # Public API
    # -------------------------

    def write(self):
        content = self._render()
        self.output_file.write_text(content, encoding="utf-8")

    # -------------------------
    # Rendering
    # -------------------------

    def _render(self) -> str:
        sections = [
            self._header(),
            self._project_overview(),
            self._entry_points(),
            self._execution_flow(),
            self._mermaid_flow(),
            self._reading_guide(),
        ]
        return "\n\n".join(sections).strip() + "\n"

    # -------------------------
    # Sections
    # -------------------------

    def _header(self) -> str:
        return (
            f"# {self.scan.root.split('/')[-1]} — Project Onboarding Guide\n\n"
            "_Generated automatically by GNOST._"
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

    def _mermaid_flow(self) -> str:
        reporter = MermaidFlowReporter(
            flow=self.flow,
            root=self.scan.root,
        )
        return "## Execution Flow Diagram\n\n" + reporter.render()

    # -------------------------
    # Helpers
    # -------------------------

    def _shorten(self, path: str) -> str:
        return path.replace(self.scan.root + "/", "")
