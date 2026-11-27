from __future__ import annotations

import os
import re
from typing import Optional

from rich.console import Console
from rich.markup import escape

from gnost.utils.paths import shorten
from gnost.languages.python import PythonAdapter
from gnost.languages.javascript import JavaScriptAdapter
from gnost.languages.typescript import TypeScriptAdapter
from gnost.languages.java import JavaAdapter
from gnost.routes import find_routes
from gnost.scanner.engine import ScannerEngine
from gnost.scanner.loc import scan as loc_scan
from gnost.core.callgraph import build_call_graph, find_flows
from gnost.core.caution import CautionSettings
from gnost.core.resolver import ImportResolver
from gnost.core.insight_builder import InsightBuilder
from gnost.core.architecture import (
    ArchitectureChecker,
    ArchitectureSettings,
    relative_to,
)
from gnost.core.risk import RiskCalculator, RiskSettings
from gnost.core.graph import DependencyGraph
from gnost.core.flow import FlowBuilder
from gnost.reporters.summary import SummaryReporter
from gnost.reporters.markdown import MarkdownReporter
from gnost.reporters.mermaid import (
    DEFAULT_MAX_EDGES,
    MermaidFlowReporter,
    render_function_flows,
)
from gnost.reporters.pages import PagesPublisher, PagesRequest, PagesResult
from gnost.reporters.readme import ReadmeInjector
from gnost.reporters.insights_json import build_payload, write_payload
from gnost.quickstart import QuickstartDetector
from gnost.utils.footer import Footer
from gnost.utils.layout import LEGACY_OUTPUT_PATHS, OutputLayout
from gnost.utils.progress import StepProgress
from gnost.vcs.git import GitError, GitRepository
from gnost.vcs.history import HistoryReader, HistorySettings


def _print_pages(published: PagesResult, output_name: str) -> None:
    """Print what --pages did, with "Pages:" in green and warnings in yellow.

    Rich drops the colours when the output is not a terminal or NO_COLOR is set.
    """
    err = Console(stderr=True, highlight=False, soft_wrap=True)
    for line in published.lines:
        head, _, rest = line.partition(": ")
        err.print(
            f"[bold green]{escape(head)}:[/] {escape(rest)}" if rest else escape(line)
        )
    for warning in published.warnings:
        err.print(f"[bold yellow]gnost: warning:[/] {escape(warning)}")
    where = f" ({escape(published.url)})" if published.url else ""
    Console(highlight=False, soft_wrap=True).print(
        f"  [bold green]GitHub Pages:[/] [bold]{escape(published.path)}[/], outside "
        f"{escape(output_name)}/, so commit it{where}"
    )


def _pages_root(scan_root: str, output_root: str) -> str:
    """The git top folder for `--pages` (Pages serves from there), else the output root."""
    try:
        repository = GitRepository.containing(scan_root)
    except GitError:
        repository = None
    return repository.root if repository else output_root


def resolve_repo_root(path: str) -> str:
    """Resolve repository root from a starting path.

    Prefers nearest parent containing pyproject.toml or .git.
    """
    current = os.path.abspath(path)
    if os.path.isfile(current):
        current = os.path.dirname(current)

    while True:
        if os.path.exists(os.path.join(current, "pyproject.toml")) or os.path.isdir(
            os.path.join(current, ".git")
        ):
            return current

        parent = os.path.dirname(current)
        if parent == current:
            return os.path.abspath(path)
        current = parent


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
        dirnames[:] = [
            d for d in dirnames if d.lower() not in IGNORE and not d.startswith(".")
        ]
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
    path: Optional[str] = None,
    diagram_only: bool = False,
    progress: bool = False,
    inject: bool = False,
    depth: Optional[int] = None,
    layered: bool = False,
    json_out: Optional[str] = None,
    insights_only: bool = False,
    max_edges: int = DEFAULT_MAX_EDGES,
    collapse: Optional[int] = None,
    exclude: Optional[list] = None,
    caution: Optional[CautionSettings] = None,
    output_dir: Optional[str] = None,
    html: bool = True,
    history: Optional[HistorySettings] = None,
    risk: Optional[RiskSettings] = None,
    output_root: Optional[str] = None,
    source: Optional[str] = None,
    footer: bool = True,
    architecture: Optional[ArchitectureSettings] = None,
    pages: Optional[PagesRequest] = None,
) -> None:
    """Onboard a codebase: write the guide, diagrams, insights JSON and explorer page.

    Everything goes into the output folder (`.gnost/`, see OutputLayout). `diagram_only` writes only the diagram.
    `pages` also copies the explorer where GitHub Pages serves it; raises PagesError instead of overwriting.
    """
    scan_root = os.path.abspath(path or ".")
    # A remote clone passes output_root so the files land in the current folder.
    output_root = output_root or resolve_repo_root(scan_root)
    layout = OutputLayout(output_root, output_dir)
    flow_dir = layout.flow_dir
    write_documents = not insights_only
    if insights_only and json_out is None:
        json_out = ""
    stamp = Footer(footer)
    published: Optional[PagesResult] = None
    publisher = (
        PagesPublisher(_pages_root(scan_root, output_root), pages.folder, pages.origin)
        if pages is not None and html and not diagram_only and not insights_only
        else None
    )
    if publisher is not None:
        publisher.check()  # a foreign page stops the run before the slow work
    first_run = not os.path.isdir(layout.folder)
    # The scanners must never read GNOST's own output.
    own_output = [layout.relative_name] + list(LEGACY_OUTPUT_PATHS)
    exclude = list(exclude or []) + own_output
    if json_out is not None or write_documents:
        layout.prepare()
    if write_documents:
        os.makedirs(flow_dir, exist_ok=True)

    steps = ["Scanning files", "Building graph", "Tracing flow", "Writing files"]
    with StepProgress(progress, steps, announce=f"Onboarding {scan_root} ...") as bar:
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
        scanner = ScannerEngine(adapters=adapters, exclude=exclude)
        scan_result = scanner.scan(scan_root)
        scan_result.routes = find_routes(scan_result)
        stamp = stamp.for_languages(scan_result.languages)
        # The line-count tables only understand plain folder names, not globs.
        loc_exclude = [p for p in (exclude or []) if not re.search(r"[*?\[/]", p)]
        loc_data = loc_scan(scan_root, exclude=loc_exclude)
        bar.advance()

        # -------------------------
        # 3. Build dependency graph
        # -------------------------
        graph = DependencyGraph.from_scan(scan_result)
        bar.advance()

        # -------------------------
        # 4. Build execution flow
        # -------------------------
        flow_builder = FlowBuilder(graph=graph, scan=scan_result)
        flow_result = flow_builder.build()
        bar.advance()

        # -------------------------
        # 4.4 Function-level call graph (Python)
        # -------------------------
        call_graph = build_call_graph(
            scan_result, ImportResolver(scan_result.root, scan_result.files)
        )
        function_flows = find_flows(scan_result, call_graph)

        # -------------------------
        # 4.5 Build onboarding insights (NEW)
        # -------------------------
        insight_builder = InsightBuilder(
            scan=scan_result,
            flow=flow_result,
            graph=graph,
            caution=caution,
        )
        insights = insight_builder.build()

        # -------------------------
        # 4.55 Change history (git), if there is any
        # -------------------------
        scanned = {
            os.path.relpath(f.path, scan_root).replace(os.sep, "/")
            for f in scan_result.files
        }
        changes = HistoryReader(history or HistorySettings()).analyze(
            scan_root, scanned
        )
        risks = RiskCalculator(risk or RiskSettings()).report(
            insight_builder.caution_scores, changes.hotspots, scan_root
        )

        # -------------------------
        # 4.55 Architecture rules from .gnost.toml (the import graph against the layers)
        # -------------------------
        arch_settings = architecture or ArchitectureSettings()
        arch_report = ArchitectureChecker.for_settings(arch_settings).report(
            graph, relative_to(scan_root), arch_settings
        )

        # -------------------------
        # 4.56 How to get the project running (read from its own files)
        # -------------------------
        quickstart = QuickstartDetector().detect(scan_root)

        # -------------------------
        # 4.6 Insights JSON (optional)
        # -------------------------
        if json_out is not None or not diagram_only:
            json_path = json_out or layout.insights_json
            payload = build_payload(
                scan_result,
                flow_result,
                graph,
                insights,
                flows=function_flows,
                call_graph=call_graph,
                changes=changes,
                risks=risks,
                quickstart=quickstart,
                architecture=arch_report,
            )
            write_payload(payload, json_path)
            print(f"Insights JSON written to {json_path}")
            if insights_only:
                bar.advance()
                return

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
                max_edges=max_edges,
                collapse=collapse,
            ).render(markdown=False)

            output_path = os.path.join(flow_dir, "FLOW-full.mmd")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_diagram + "\n")

            bar.advance()

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
            max_edges=max_edges,
            collapse=collapse,
        ).render(markdown=False)

        with open(os.path.join(flow_dir, "FLOW-full.mmd"), "w", encoding="utf-8") as f:
            f.write(full_diagram + "\n")

        complete = MermaidFlowReporter(
            flow=flow_result,
            root=scan_result.root,
            overview=False,
            depth=depth,
            layered=False,
        ).render_complete()
        with open(
            os.path.join(flow_dir, "flow-complete.mmd"), "w", encoding="utf-8"
        ) as f:
            f.write(complete + "\n")

        full_md = MermaidFlowReporter(
            flow=flow_result,
            root=scan_result.root,
            overview=False,
            depth=depth,
            layered=layered,
            max_edges=max_edges,
            collapse=collapse,
        ).render_document()

        with open(os.path.join(flow_dir, "FLOW-full.md"), "w", encoding="utf-8") as f:
            f.write(
                stamp.append(
                    "# Full Execution Flow\n\n" + full_md + "\n\n"
                    "> ℹ️ This file renders the complete Mermaid diagram on GitHub.\n"
                    "> For raw Mermaid source, see "
                    "[**FLOW-full.mmd**](./FLOW-full.mmd). Every file and import, "
                    "ungrouped and nothing omitted: "
                    "[**flow-complete.mmd**](./flow-complete.mmd)\n"
                )
            )

        if function_flows:
            with open(
                os.path.join(flow_dir, "function-flow.md"), "w", encoding="utf-8"
            ) as f:
                f.write(
                    stamp.append(
                        render_function_flows(function_flows, scan_result.root)
                    )
                )

        # Overview diagram (optional standalone file)
        overview_diagram = MermaidFlowReporter(
            flow=flow_result,
            root=scan_result.root,
            overview=True,
            depth=depth,
            layered=layered,
            max_edges=max_edges,
            collapse=collapse,
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
            max_edges=max_edges,
            collapse=collapse,
        )

        lines = []
        lines.append("# Entry-based Execution Paths\n")
        lines.append(
            "These diagrams show individual execution paths starting from "
            "application entry points. Each path represents one possible "
            "flow through the system.\n"
        )

        for idx, p in enumerate(sorted_paths[:MAX_PATHS], start=1):
            entry = shorten(p.path[0], scan_result.root)
            lines.append(f"## Path {idx} — `{entry}`\n")

            diagram = reporter.render_path(p.path, markdown=True)
            lines.append(diagram)
            lines.append("")  # spacing

            chain = " → ".join(shorten(x, scan_result.root) for x in p.path)
            lines.append(f"**Execution chain:** {chain}\n")

        with open(os.path.join(flow_dir, "entry-paths.md"), "w", encoding="utf-8") as f:
            f.write(stamp.append("\n".join(lines)))

        # -------------------------
        # 5.7 Keyword-based paths
        # -------------------------
        DEFAULT_KEYWORDS = ["auth", "user", "payment", "order", "login"]

        auto_keywords = detect_keywords_from_folders(scan_root)

        KEYWORDS = sorted(set(DEFAULT_KEYWORDS + auto_keywords))
        MAX_REPRESENTATIVE_PATHS = 2

        reporter = MermaidFlowReporter(
            flow=flow_result,
            root=scan_result.root,
            overview=False,
            depth=depth,
            layered=layered,
            max_edges=max_edges,
            collapse=collapse,
        )

        lines = []
        lines.append("# Keyword-based Execution Paths\n")
        lines.append(
            "These diagrams show execution flows related to key features, "
            "auto-detected from the project structure.\n"
        )

        # Features worth a section: keywords matching some paths, but not nearly
        # all of them (the root package name says nothing). Biggest first, and
        # capped so the file stays readable on big projects.
        MAX_FEATURES = 12
        by_keyword = {}
        for keyword in KEYWORDS:
            hits = [
                p
                for p in flow_result.paths
                if any(
                    keyword.lower() in node.replace(scan_result.root, "").lower()
                    for node in p.path
                )
            ]
            too_broad = len(flow_result.paths) > 10 and len(hits) > 0.9 * len(
                flow_result.paths
            )
            if hits and not too_broad:
                by_keyword[keyword] = hits
        features = sorted(by_keyword, key=lambda k: (-len(by_keyword[k]), k))[
            :MAX_FEATURES
        ]

        for keyword in sorted(features):
            matched = by_keyword[keyword]

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

                chain = " → ".join(shorten(x, scan_result.root) for x in group[0])
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
            f.write(stamp.append("\n".join(lines)))

        # -------------------------
        # 6. Normal onboarding
        # -------------------------
        SummaryReporter(
            scan=scan_result,
            flow=flow_result,
            graph=graph,
            insights=insights,
            changes=changes,
            risks=risks,
            root_label=source,
            quickstart=quickstart,
            architecture=arch_report,
        ).render()

        MarkdownReporter(
            scan=scan_result,
            flow=flow_result,
            output_file="ONBOARD.md",
            output_root=layout.folder,
            loc_data=loc_data,
            mermaid_depth=depth,
            mermaid_layered=layered,
            mermaid_max_edges=max_edges,
            mermaid_collapse=collapse,
            insights=insights,
            function_flows=function_flows,
            changes=changes,
            risks=risks,
            root_label=source,
            footer=stamp,
            quickstart=quickstart,
            architecture=arch_report,
        ).write()

        if html:
            from gnost.cli.commands.show import build_page

            page = build_page(os.path.join(flow_dir, "flow-complete.mmd"))
            with open(layout.flow_html, "w", encoding="utf-8") as f:
                f.write(page)
            if publisher is not None:
                published = publisher.publish(page)

        if inject:
            injector = ReadmeInjector(
                output_root, link=f"./{layout.relative_name}/ONBOARD.md"
            )
            changed = injector.inject()

            if changed:
                print("✅ README.md updated with onboarding link")
            else:
                print("ℹ️  README.md not found, skipping injection")

        bar.advance()

    print(f"\nGNOST wrote its files to {layout.folder}")
    print(f"  Guide: {layout.relative_name}/ONBOARD.md")
    if html:
        # a remote repository has its own subfolder, which plain `open flow` does not look in
        command = (
            f"gnost open {layout.relative_name}/flow.html"
            if source
            else "gnost open flow"
        )
        print(f"  Open the explorer: {command}")
    if published is not None:
        _print_pages(published, layout.relative_name)
    if first_run and layout.has_legacy_output():
        print(f"\nNote: {layout.moved_notice()}")
