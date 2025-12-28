# gnost/cli/commands/onboard.py

import os

from gnost.languages.python import PythonAdapter
from gnost.languages.javascript import JavaScriptAdapter
from gnost.languages.typescript import TypeScriptAdapter
from gnost.languages.java import JavaAdapter
from gnost.scanner.engine import ScannerEngine
from gnost.core.graph import DependencyGraph
from gnost.core.flow import FlowBuilder
from gnost.reporters.summary import SummaryReporter
from gnost.reporters.markdown import MarkdownReporter
from gnost.reporters.mermaid import MermaidFlowReporter
from gnost.utils.progress import progress_bar


def run(path: str | None = None, diagram_only: bool = False, progress: bool = False):
    """
    gnost onboard [path] [--mermaid]
    Generates a high-level onboarding summary for a codebase.
    """
    root = os.path.abspath(path or ".")

    with progress_bar(enabled=progress, total=4, desc="Onboarding") as bar:
        # -------------------------
        # 1. Language adapters
        # -------------------------
        adapters = [
            PythonAdapter(),
            JavaScriptAdapter(),
            TypeScriptAdapter(),
            JavaAdapter(),
        ]

        # -------------------------
        # 2. Scan repository
        # -------------------------
        scanner = ScannerEngine(adapters=adapters)
        scan_result = scanner.scan(root)
        if bar is not None:
            bar.update(1)

        # -------------------------
        # 3. Build dependency graph
        # -------------------------
        graph = DependencyGraph.from_scan(scan_result)
        if bar is not None:
            bar.update(1)

        # -------------------------
        # 4. Build execution flow
        # -------------------------
        flow_builder = FlowBuilder(graph=graph, scan=scan_result)
        flow_result = flow_builder.build()
        if bar is not None:
            bar.update(1)

        # -------------------------
        # 5. Diagram-only mode
        # -------------------------
        if diagram_only:
            diagram = MermaidFlowReporter(
                flow=flow_result,
                root=scan_result.root,
            ).render(markdown=False)

            output_path = os.path.join(root, "FLOW.mmd")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(diagram + "\n")

            if bar is not None:
                bar.update(1)

            print(f"Mermaid flow diagram written to {output_path}")
            return

        # -------------------------
        # 6. Normal onboarding
        # -------------------------
        SummaryReporter(
            scan=scan_result,
            flow=flow_result,
            graph=graph,
        ).render()

        MarkdownReporter(
            scan=scan_result,
            flow=flow_result,
            output_file="ONBOARD.md",
        ).write()

        if bar is not None:
            bar.update(1)
