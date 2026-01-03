import os

from gnost.languages.python import PythonAdapter
from gnost.languages.javascript import JavaScriptAdapter
from gnost.languages.typescript import TypeScriptAdapter
from gnost.languages.java import JavaAdapter
from gnost.scanner.engine import ScannerEngine
from gnost.core.insight_builder import InsightBuilder
from gnost.core.graph import DependencyGraph
from gnost.core.flow import FlowBuilder
from gnost.reporters.summary import SummaryReporter
from gnost.reporters.markdown import MarkdownReporter
from gnost.reporters.mermaid import MermaidFlowReporter
from gnost.reporters.readme import ReadmeInjector
from gnost.utils.progress import progress_bar


def feature_entry_node(path: list[str], keyword: str) -> str:
    """
    Return the first node in the path that matches the keyword.
    Fallback to entry point if none found.
    """
    keyword = keyword.lower()

    for node in path:
        if keyword in node.lower():
            return node

    return path[0]


def detect_keywords_from_folders(root: str) -> list[str]:
    """
    Auto-detect feature keywords from top-level and second-level folders.
    """
    IGNORE = {
        "src",
        "lib",
        "dist",
        "build",
        "node_modules",
        "tests",
        "test",
        "__tests__",
        "__pycache__",
        "utils",
        "common",
        "shared",
        "core",
        "config",
        "configs",
        "settings",
        "public",
        "static",
        "assets",
        ".git",
        ".github",
    }

    keywords = set()

    for dirpath, dirnames, _ in os.walk(root):
        depth = dirpath.replace(root, "").count(os.sep)

        # Only consider shallow folders (important!)
        if depth > 2:
            continue

        for d in dirnames:
            name = d.lower()

            if name in IGNORE:
                continue

            if name.startswith("."):
                continue

            # basic sanity
            if len(name) < 3:
                continue

            keywords.add(name)

    return sorted(keywords)


def run(
    path: str | None = None,
    diagram_only: bool = False,
    progress: bool = False,
    inject: bool = False,
    depth: int | None = None,
    layered: bool = False,
):
    """
    gnost onboard [path] [--mermaid]
    Generates a high-level onboarding summary for a codebase.
    """
    root = os.path.abspath(path or ".")
    flow_dir = os.path.join(root, "flow")
    os.makedirs(flow_dir, exist_ok=True)

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
        # 4.5 Build onboarding insights (NEW)
        # -------------------------
        insight_builder = InsightBuilder(
            scan=scan_result,
            flow=flow_result,
            graph=graph,
        )
        insights = insight_builder.build()

        # -------------------------
        # 5. Diagram-only mode
        # -------------------------
        if diagram_only:
            full_diagram = MermaidFlowReporter(
                flow=flow_result,
                root=scan_result.root,
                overview=False,
                depth=depth,
                layered=layered,
            ).render(markdown=False)

            output_path = os.path.join(root, "FLOW-full.mmd")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_diagram + "\n")

            if bar is not None:
                bar.update(1)

            print(f"Mermaid flow diagram written to {output_path}")
            return

        # -------------------------
        # 5.5 Write Mermaid diagrams
        # -------------------------
        # Full diagram (for drill-down)
        full_diagram = MermaidFlowReporter(
            flow=flow_result,
            root=scan_result.root,
            overview=False,
            depth=depth,
            layered=layered,
        ).render(markdown=False)

        with open(os.path.join(flow_dir, "FLOW-full.mmd"), "w", encoding="utf-8") as f:
            f.write(full_diagram + "\n")

        full_md = MermaidFlowReporter(
            flow=flow_result,
            root=scan_result.root,
            overview=False,
            depth=depth,
            layered=layered,
        ).render(markdown=True)

        with open(os.path.join(flow_dir, "FLOW-full.md"), "w", encoding="utf-8") as f:
            f.write(
                "# Full Execution Flow\n\n" + full_md + "\n\n"
                "> ℹ️ This file renders the complete Mermaid diagram on GitHub.\n"
                "> For raw Mermaid source, see "
                "[**FLOW-full.mmd**](./FLOW-full.mmd)\n"
            )

        # Overview diagram (optional standalone file)
        overview_diagram = MermaidFlowReporter(
            flow=flow_result,
            root=scan_result.root,
            overview=True,
            depth=depth,
            layered=layered,
        ).render(markdown=False)

        with open(
            os.path.join(flow_dir, "FLOW-overview.mmd"), "w", encoding="utf-8"
        ) as f:
            f.write(overview_diagram + "\n")

        # -------------------------
        # 5.6 Entry-based path diagrams (single file)
        # -------------------------
        sorted_paths = sorted(
            flow_result.paths,
            key=lambda p: len(p.path),
            reverse=True,
        )

        MAX_PATHS = 3
        reporter = MermaidFlowReporter(
            flow=flow_result,
            root=scan_result.root,
            overview=False,
            depth=depth,
            layered=layered,
        )

        lines = []
        lines.append("# Entry-based Execution Paths\n")
        lines.append(
            "These diagrams show individual execution paths starting from "
            "application entry points. Each path represents one possible "
            "flow through the system.\n"
        )

        for idx, p in enumerate(sorted_paths[:MAX_PATHS], start=1):
            entry = p.path[0].replace(scan_result.root + "/", "")
            lines.append(f"## Path {idx} — `{entry}`\n")

            diagram = reporter.render_path(p.path, markdown=True)
            lines.append(diagram)
            lines.append("")  # spacing

            chain = " → ".join(x.replace(scan_result.root + "/", "") for x in p.path)
            lines.append(f"**Execution chain:** {chain}\n")

        with open(os.path.join(flow_dir, "entry-paths.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        # -------------------------
        # 5.7 Keyword-based paths
        # -------------------------
        DEFAULT_KEYWORDS = ["auth", "user", "payment", "order", "login"]

        auto_keywords = detect_keywords_from_folders(root)

        KEYWORDS = sorted(set(DEFAULT_KEYWORDS + auto_keywords))
        MAX_REPRESENTATIVE_PATHS = 2

        reporter = MermaidFlowReporter(
            flow=flow_result,
            root=scan_result.root,
            overview=False,
            depth=depth,
            layered=layered,
        )

        lines = []
        lines.append("# Keyword-based Execution Paths\n")
        lines.append(
            "These diagrams show execution flows related to key features, "
            "auto-detected from the project structure.\n"
        )

        for keyword in KEYWORDS:
            matched = []

            for p in flow_result.paths:
                if any(keyword.lower() in node.lower() for node in p.path):
                    matched.append(p)

            if not matched:
                continue

            lines.append(f"## Feature: `{keyword}`\n")

            # Sort longest first
            matched = sorted(matched, key=lambda p: len(p.path), reverse=True)

            groups = reporter._deduplicate_paths(
                [p.path for p in matched],
                min_prefix=2,
            )

            # -------------------------
            # Representative paths
            # -------------------------
            lines.append("### Representative Paths\n")

            for idx, group in enumerate(groups[:MAX_REPRESENTATIVE_PATHS], start=1):
                if len(group) == 1:
                    diagram = reporter.render_path(group[0], markdown=True)
                else:
                    diagram = reporter.render_combined_paths(group, markdown=True)

                lines.append(f"#### Path Group {idx}\n")
                lines.append(diagram)

                chain = " → ".join(
                    x.replace(scan_result.root + "/", "") for x in p.path
                )
                lines.append(f"**Execution chain:** {chain}\n")

            # -------------------------
            # Combined diagram
            # -------------------------
            lines.append(f"### Combined Flow (All `{keyword}` Paths)\n")

            combined_diagram = reporter.render_combined_paths(
                paths=[p.path for p in matched],
                markdown=True,
            )

            lines.append(combined_diagram)
            lines.append("")

        with open(
            os.path.join(flow_dir, "folder-paths.md"), "w", encoding="utf-8"
        ) as f:
            f.write("\n".join(lines))

        # -------------------------
        # 6. Normal onboarding
        # -------------------------
        SummaryReporter(
            scan=scan_result,
            flow=flow_result,
            graph=graph,
            insights=insights,
        ).render()

        MarkdownReporter(
            scan=scan_result,
            flow=flow_result,
            output_file="ONBOARD.md",
            mermaid_depth=depth,
            mermaid_layered=layered,
            insights=insights,
        ).write()

        if inject:
            injector = ReadmeInjector(root)
            changed = injector.inject()

            if changed:
                print("✅ README.md updated with onboarding link")
            else:
                print("ℹ️  README.md not found, skipping injection")

        if bar is not None:
            bar.update(1)
