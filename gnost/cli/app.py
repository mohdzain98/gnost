import os
import json
import logging
import asyncio
import argparse
import traceback
import sys
from typing import Set
import datetime
import enum
import pathlib
import shlex
import webbrowser
from termcolor import cprint
from dataclasses import is_dataclass, asdict
from collections import defaultdict
from rich.console import Console
from rich.table import Table

from gnost import __version__
from gnost.scanner.loc import scan
from gnost.reporters import stats, folders, files, loc_summary
from gnost.reporters.analysis_html import render_analysis_html
from gnost.analysis.core.models import (
    AnalysisConfiguration,
    SeverityLevel,
    UnifiedFinding,
    ConsolidatedReport,
)
from gnost.cli.commands.onboard import run as onboard_run
from gnost.cli.commands.analysis import Analysis
from gnost.utils.logger import AppLogger

AppLogger.init(level=logging.INFO)
logger = AppLogger.get_logger(__name__)
analysis = Analysis()


SEVERITY_WEIGHTS = {
    SeverityLevel.CRITICAL: 1.0,
    SeverityLevel.HIGH: 0.6,
    SeverityLevel.MEDIUM: 0.3,
    SeverityLevel.LOW: 0.1,
    SeverityLevel.INFO: 0.05,
}


def _to_dict_payload(report):
    payload = None
    if hasattr(report, "to_dict"):
        payload = report.to_dict()  # type: ignore
    elif is_dataclass(report):
        payload = asdict(report)  # type: ignore
    elif hasattr(report, "model_dump"):
        payload = report.model_dump()  # type: ignore
    elif hasattr(report, "dict"):
        payload = report.dict()  # type: ignore
    elif hasattr(report, "json"):
        try:
            payload = json.loads(report.json())  # type: ignore
        except Exception:
            payload = None
    if payload is None and hasattr(report, "__dict__"):
        payload = report.__dict__  # type: ignore
    if payload is None:
        payload = {"result": report}

    return _normalize_for_json(payload)


def _normalize_for_json(value):
    """Convert dataclass/report payload objects into JSON serializable types."""
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, datetime.time):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, pathlib.Path):
        return str(value)
    if isinstance(value, (set, tuple)):
        return [_normalize_for_json(v) for v in value]
    if is_dataclass(value):
        return _normalize_for_json(asdict(value))
    if hasattr(value, "to_dict") and callable(getattr(value, "to_dict")):
        return _normalize_for_json(value.to_dict())
    if hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
        return _normalize_for_json(value.model_dump())
    if isinstance(value, dict):
        return {str(k): _normalize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_for_json(v) for v in value]
    return value


def _risk_to_score(risk_score: float) -> float:
    clamped = max(0.0, min(100.0, risk_score))
    return round(10.0 * (1.0 - clamped / 100.0), 2)


def _resolve_repo_root(path: str) -> str:
    current = os.path.abspath(path)
    if os.path.isfile(current):
        current = os.path.dirname(current)

    while True:
        if os.path.isdir(os.path.join(current, ".git")) or os.path.isfile(
            os.path.join(current, "pyproject.toml")
        ):
            return current

        parent = os.path.dirname(current)
        if parent == current:
            return current
        current = parent


def _analysis_output_path(target_path: str) -> str:
    repo_root = _resolve_repo_root(target_path)
    return os.path.join(repo_root, "docs", "analysis", "gnost_analysis.json")


def _analysis_open_command(report_path: str) -> str:
    safe_path = shlex.quote(os.path.abspath(report_path))
    if sys.platform == "darwin":
        return f"open {safe_path}"
    if sys.platform.startswith("linux"):
        return f"xdg-open {safe_path}"
    if os.name == "nt":
        return f'start "" "{os.path.abspath(report_path)}"'
    return os.path.abspath(report_path)


def _open_analysis_report(report_path: str) -> bool:
    abs_path = os.path.abspath(report_path)
    if not os.path.isfile(abs_path):
        return False
    try:
        return webbrowser.open(f"file://{abs_path}")
    except Exception:
        return False


def _analysis_html_output_path(target_path: str) -> str:
    return _analysis_output_path(target_path).replace(".json", ".html")


def _score_style(score: float) -> str:
    if score >= 8.0:
        return "green"
    if score >= 6.0:
        return "yellow"
    return "red"


def _analyzer_risk(findings: list[UnifiedFinding]) -> float:
    if not findings:
        return 0.0
    total_weight = sum(SEVERITY_WEIGHTS.get(f.severity, 0.2) for f in findings)
    max_weight = max(SEVERITY_WEIGHTS.values())
    return round((total_weight / (len(findings) * max_weight)) * 100.0, 2)


def _severity_counts(findings: list[UnifiedFinding]) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0, "info": 0}
    for finding in findings:
        sev = str(finding.severity).split(".")[-1].lower()
        if sev not in counts:
            sev = "info"
        counts[sev] += 1
    return counts


def _print_analysis_scores(report: ConsolidatedReport) -> None:
    metrics = getattr(report, "analysis_metrics", [])
    findings_by_analyzer = defaultdict(list)
    for finding in getattr(report, "findings", []):
        findings_by_analyzer[finding.source_analyzer].append(finding)

    analyzer_scores = {}
    for metric in metrics:
        analyzer_scores[metric.analyzer_name] = _risk_to_score(
            _analyzer_risk(findings_by_analyzer.get(metric.analyzer_name, []))
        )

    if not analyzer_scores:
        return

    table = Table(title="Analysis Scores")
    table.add_column("Analyzer", justify="left", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Findings", justify="right")
    table.add_column("High", justify="right", style="red")
    table.add_column("Medium", justify="right", style="yellow")
    table.add_column("Low", justify="right", style="green")

    for name in sorted(analyzer_scores.keys()):
        score = analyzer_scores[name]
        findings_count = len(findings_by_analyzer.get(name, []))
        severity_summary = _severity_counts(findings_by_analyzer.get(name, []))
        score_style = _score_style(score)
        table.add_row(
            name,
            f"[{score_style}]{score:.2f}[/]",
            f"{findings_count}",
            f"{severity_summary['high']}",
            f"{severity_summary['medium']}",
            f"{severity_summary['low']}",
        )

    console = Console()
    console.print(table)

    final_score = 0.0
    summary = getattr(report, "summary", {})
    if isinstance(summary, dict):
        final_score = _risk_to_score(summary.get("risk_score", 0.0))
    else:
        final_score = 0.0
    final_style = _score_style(final_score)
    console.print(f"[bold]final score:[/]  [{final_style}]{final_score:.2f}[/] / 10.00")


def main():
    parser = argparse.ArgumentParser(
        prog="gnost",
        usage="gnost [command]",
        description="GNOST — Codebase Knowledge",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Command Options:\n"
            "  summary|stats|folders|files:\n"
            "    --include      Comma-separated folder names to include\n"
            "    --exclude      Comma-separated folder names to exclude\n"
            "    --progress     Show a progress bar while scanning\n\n"
            "  onboard:\n"
            "    --progress     Show a progress bar while onboarding\n"
            "    --mermaid      Generate only Mermaid flow diagram\n"
            "    --inject       Inject onboarding link into README.md\n"
            "    --layered      Produce Layered mermaid as Entry -> Core -> Leaf\n"
            "    --depth DEPTH  Limit execution flow depth (e.g. --depth 2)\n\n"
            "  analyze:\n"
            "    path                 File or directory to analyze (default: .)\n"
            "    -a, --analyzer       Enable only specific analyzers\n"
            "    --parallel           Run analyzers in parallel\n"
            "    -o, --out            Write report to docs/analysis/gnost_analysis.json and gnost_analysis.html\n"
            "    -v, --verbose        Show traceback on failures\n"
            "    --quiet              Reduce logs; keep warnings/errors only\n"
            "    --list-analyzers     List available analyzers and exit\n"
            "    --timeout SECONDS    Analyzer timeout (default: 900)\n"
            "    --compact            Write compact JSON when --out is used\n"
            "    --no-progress        Hide progress updates\n"
            "    --max-findings N     Per-analyzer findings limit (default: 1000)\n\n"
            "  files:\n"
            "    --top          Number of files to show (default: 5)\n"
            "  open:\n"
            "    report|rpt        Open the generated report in browser\n"
            "                      Shortcut alias: gnost open rpt\n"
            "Use `gnost <command> --help` for full command options."
        ),
    )
    parser.add_argument("--version", action="version", version=f"gnost {__version__}")

    sub = parser.add_subparsers(
        dest="cmd",
        required=True,
        title="Available Commands",
        metavar="command",
    )

    base = argparse.ArgumentParser(add_help=False)
    base.add_argument("path", nargs="?", default=".", help="Directory to scan")
    base.add_argument(
        "--exclude",
        help="Comma-separated folder names to exclude (e.g. node_modules,dist)",
    )
    base.add_argument(
        "--include",
        help="Comma-separated folder names to include (only these are scanned)",
    )
    base.add_argument(
        "--progress",
        action="store_true",
        help="Show a progress bar while scanning",
    )

    sub.add_parser("summary", parents=[base], help="Show a summary table")
    sub.add_parser("stats", parents=[base], help="Show detailed stats per language")
    sub.add_parser("folders", parents=[base], help="Show LOC grouped by folder")

    files_parser = sub.add_parser(
        "files", parents=[base], help="Show the largest files by LOC"
    )
    files_parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of files to show (default: 5)",
    )

    sub.add_parser("version", help="Display gnost version")
    onboard = sub.add_parser("onboard", help="Onboard a new codebase")
    onboard.add_argument("path", nargs="?", default=".")
    onboard.add_argument(
        "--mermaid",
        action="store_true",
        help="Generate only Mermaid flow diagram (FLOW.mmd)",
    )
    onboard.add_argument(
        "--progress",
        action="store_true",
        help="Show a progress bar while onboarding",
    )
    onboard.add_argument(
        "--inject",
        action="store_true",
        help="Inject onboarding link into README.md",
    )
    onboard.add_argument(
        "--layered",
        action="store_true",
        help="Produce Layered mermaid as Entry -> Core -> Leaf",
    )
    onboard.add_argument(
        "--depth",
        type=int,
        default=None,
        help="Limit execution flow depth (e.g. --depth 2)",
    )
    analyze = sub.add_parser("analyze", help="Analyze the codebase")
    analyze.add_argument(
        "path",
        nargs="?",
        default=".",
        help="File or directory to analyze. By default scan the current folder from terminal",
    )
    analyze.add_argument(
        "-a",
        "--analyzer",
        action="append",
        default=[],
        help="Enable only these analyzers (repeatable, by name).",
    )
    analyze.add_argument(
        "--parallel",
        action="store_true",
        help="Does Parallel Processing for faster execution",
    )
    analyze.add_argument(
        "-o",
        "--out",
        action="store_true",
        help="Write JSON and HTML report to docs/analysis/gnost_analysis.[json|html]",
    )
    analyze.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Use for checking error i.e. traceback",
    )
    analyze.add_argument(
        "--quiet",
        action="store_true",
        help="Only show warnings and errors logs, hides info logs.",
    )
    analyze.add_argument(
        "--list-analyzers",
        action="store_true",
        help="List available analyzers and exit.",
    )
    analyze.add_argument(
        "--timeout", type=int, default=900, help="Waiting time in sec, default 900"
    )
    analyze.add_argument(
        "--compact",
        action="store_true",
        help="Write compact JSON output when --out is provided.",
    )
    analyze.add_argument(
        "--no-progress",
        action="store_true",
        help="Hide progress updates while analysis is running.",
    )
    analyze.add_argument(
        "--max-findings",
        type=int,
        default=1000,
        help="Finding threshold for individual analyzer, default 1000",
    )

    open_cmd = sub.add_parser("open", help="Open generated reports")
    open_cmd.add_argument(
        "target",
        nargs="?",
        default="report",
        help="Currently supported: report (alias: rpt)",
    )
    open_cmd.add_argument(
        "--path",
        help="Custom report path (optional). Defaults to docs/analysis/gnost_analysis.html",
    )

    args = parser.parse_args()

    if args.cmd == "version":
        print(f"gnost {__version__}")
        return 0

    if args.cmd == "onboard":
        onboard_run(
            args.path,
            diagram_only=getattr(args, "mermaid", False),
            progress=getattr(args, "progress", False),
            inject=getattr(args, "inject", False),
            depth=getattr(args, "depth", None),
            layered=getattr(args, "layered", False),
        )
        return 0

    if args.cmd == "analyze":
        analysis.initialize_analyzers()
        analyzer_registry = analysis.get_analyzer_registry()
        if args.list_analyzers:
            for name in analyzer_registry.list_analyzer_names():
                print(name)
            return 0

        target_path = os.path.abspath(args.path)
        if not os.path.exists(target_path):
            logger.error(f"Error: path not found: {target_path}")
            return 2

        if not args.verbose:
            logging.getLogger("asyncio").setLevel(logging.CRITICAL)

        reader_files, count = analysis.collect_code_files(target_path)
        if args.quiet:
            cprint(f"Total Files for Analysis : {count}", "green")
            analysis.set_quiet_logging()
        logger.info(f"Total Files for Analysis : {count}")

        if not reader_files:
            logger.warning("⚠️ No Python files found after filtering.")
            return 0

        enabled_analyzers: Set[str] = set(args.analyzer or [])
        cfg = AnalysisConfiguration(
            target_path=target_path,
            enabled_analyzers=enabled_analyzers,
            severity_threshold=SeverityLevel.INFO,
            parallel_execution=bool(args.parallel),
            include_low_confidence=False,
            timeout_seconds=int(args.timeout),
            max_findings_per_analyzer=int(args.max_findings),
            files=reader_files,
        )

        try:
            if args.quiet and args.no_progress:
                cprint("Running", "green")

            report = asyncio.run(
                analysis.run_async(cfg, show_progress=not args.no_progress)
            )
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Interrupted.")
            return 130
        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            if args.verbose:
                traceback.print_exc()
            return 1

        payload = _to_dict_payload(report)
        html_output = _analysis_html_output_path(target_path)
        if args.out:
            try:
                output_file = _analysis_output_path(target_path)
                analysis.write_json_file(output_file, payload, compact=args.compact)
                logger.info(f"✅ Findings saved to {output_file}")
                if args.quiet:
                    cprint(f"✅ Findings saved to {output_file}", "green")
                html_output = _analysis_html_output_path(target_path)
                render_analysis_html(payload, html_output)
                logger.info(f"✅ Interactive HTML report saved to {html_output}")
                if args.quiet:
                    cprint(
                        f"✅ Interactive HTML report saved to {html_output}", "green"
                    )
            except Exception as e:
                logger.error(
                    f"❌ Failed to write output file '{_analysis_output_path(target_path)}': {e}, use verbose to check"
                )
                if args.verbose:
                    traceback.print_exc()
                return 1

        _print_analysis_scores(report)
        if args.out:
            open_cmd = _analysis_open_command(html_output)
            console = Console()
            console.print("[blue]To open the findings report in browser:[/blue]")
            console.print(
                "  Either run: [cyan]gnost open report[/cyan] (or [cyan]gnost open rpt[/cyan])"
            )
            console.print(f"  or run: [cyan]{open_cmd}[/cyan]")
        if not args.out:
            msg = "To see the findings, use the -o/--out argument."
            if args.quiet:
                cprint(msg, "yellow")
            else:
                logger.info(msg)
        return 0

    if args.cmd == "open":
        normalized_target = str(args.target).lower()
        if normalized_target not in {"report", "rpt"}:
            logger.error('Unsupported target. Use: "gnost open report" or "gnost open rpt"')
            return 2

        report_path = (
            os.path.abspath(args.path)
            if getattr(args, "path", None)
            else _analysis_html_output_path(os.getcwd())
        )
        if not os.path.isfile(report_path):
            logger.error(f"Report not found: {report_path}")
            logger.error(
                "Run `gnost analyze -o` first to generate "
                "docs/analysis/gnost_analysis.html"
            )
            return 1

        if not _open_analysis_report(report_path):
            fallback = _analysis_open_command(report_path)
            logger.error(
                "Unable to open report automatically using webbrowser. "
                f"Use: {fallback}"
            )
            return 1

        cprint(f"Opened report: {report_path}", "green")
        return 0

    include = args.include.split(",") if args.include else []
    exclude = args.exclude.split(",") if args.exclude else []

    data = scan(args.path, include, exclude, progress=args.progress)

    if args.cmd == "stats":
        stats.render(data)
    elif args.cmd == "folders":
        folders.render(data)
    elif args.cmd == "files":
        files.render(data, args.top)
    else:
        loc_summary.render(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
