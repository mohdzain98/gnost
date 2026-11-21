import os
import json
import logging
import asyncio
import argparse
import dataclasses
import traceback
import sys
from typing import Any, Optional, Set
import datetime
import enum
import pathlib
import shlex
import webbrowser
from termcolor import cprint
from dataclasses import is_dataclass, asdict
from rich.console import Console
from rich.table import Table

from gnost import __version__
from gnost.scanner.loc import scan
from gnost.reporters import stats, folders, files, loc_summary
from gnost.reporters.analysis_html import render_analysis_html
from gnost.analysis.core.models import (
    AnalysisConfiguration,
    SeverityLevel,
)
from gnost.cli.commands.init import InitCommand
from gnost.cli.commands.remote import RemoteTarget
from gnost.vcs.remote import RemoteError
from gnost.cli.commands.onboard import run as onboard_run
from gnost.config.settings import (
    ANALYZE_MAX_FINDINGS,
    ANALYZE_TIMEOUT,
    ConfigError,
    load_config,
    report_warnings,
)
from gnost.reporters.mermaid import DEFAULT_MAX_EDGES
from gnost.cli.commands.analysis import Analysis
from gnost.ci.baseline import BaselineError
from gnost.ci.exit_codes import ExitCode
from gnost.ci.run import CiOptions, CiRun
from gnost.ci.scorecard import ScoreCard
from gnost.analysis.utils.tool_command import RUN_TOOL_FLAG, run_tool_entry
from gnost.utils.logger import AppLogger
from gnost.utils.layout import OutputLayout

AppLogger.init(level=logging.INFO)
logger = AppLogger.get_logger(__name__)
analysis = Analysis()


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


def _resolve_repo_root(path: str) -> str:
    """Nearest parent with .git or pyproject.toml; the project folder if none."""
    current = os.path.abspath(path)
    if os.path.isfile(current):
        current = os.path.dirname(current)
    start = current

    while True:
        if os.path.isdir(os.path.join(current, ".git")) or os.path.isfile(
            os.path.join(current, "pyproject.toml")
        ):
            return current

        parent = os.path.dirname(current)
        if parent == current:
            return start
        current = parent


def _layout(
    target_path: str,
    output_dir: Optional[str] = None,
    output_root: Optional[str] = None,
) -> OutputLayout:
    """Output paths; `output_root` replaces the project root (used for remote repositories)."""
    return OutputLayout(output_root or _resolve_repo_root(target_path), output_dir)


def _analysis_output_path(
    target_path: str,
    output_dir: Optional[str] = None,
    output_root: Optional[str] = None,
) -> str:
    return _layout(target_path, output_dir, output_root).analysis_json


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
        return webbrowser.open(pathlib.Path(abs_path).as_uri())
    except Exception:
        return False


def _analysis_html_output_path(
    target_path: str,
    output_dir: Optional[str] = None,
    output_root: Optional[str] = None,
) -> str:
    return _layout(target_path, output_dir, output_root).analysis_html


def _print_analysis_scores(card: ScoreCard) -> None:
    """Print the per-analyzer score table and the final score."""
    if not card.analyzers:
        return

    table = Table(title="Analysis Scores")
    table.add_column("Analyzer", justify="left", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Findings", justify="right")
    table.add_column("High", justify="right", style="red")
    table.add_column("Medium", justify="right", style="yellow")
    table.add_column("Low", justify="right", style="green")

    for item in card.analyzers:
        style = ScoreCard.style(item.score)
        table.add_row(
            item.name,
            f"[{style}]{item.score:.2f}[/]",
            f"{item.findings}",
            f"{item.high}",
            f"{item.medium}",
            f"{item.low}",
        )

    console = Console()
    console.print(table)
    style = ScoreCard.style(card.final_score)
    console.print(f"[bold]final score:[/]  [{style}]{card.final_score:.2f}[/] / 10.00")


def _update_notice() -> None:
    """Say on stderr if a newer gnost exists (silent offline, in CI and in scripts)."""
    from gnost.utils.update_check import UpdateNotifier

    try:
        allowed = load_config(os.getcwd()).check_updates
    except ConfigError:
        allowed = True
    UpdateNotifier.standard(__version__, config_allows=allowed).notify()


class _VersionAction(argparse.Action):
    """`gnost --version`: print the version, then the update notice, then exit."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: Optional[str] = None,
    ) -> None:
        """Print the version and the notice, then exit."""
        print(f"gnost {__version__}")
        _update_notice()
        parser.exit()


def _open(args: argparse.Namespace) -> int:
    """gnost open: the flow explorer, the analysis report or a file."""
    from gnost.cli.commands.onboard import resolve_repo_root
    from gnost.cli.commands.show import run as show_run

    try:
        config = load_config(os.getcwd())
    except ConfigError:
        config = None
    layout = OutputLayout(
        resolve_repo_root(os.getcwd()), config.output_dir if config else None
    )
    target = str(args.target).lower()

    if target == "flow":
        flow_file = args.path
        explicit_view = args.view != "auto"
        if not flow_file:
            candidates = [
                layout.flow_html if not explicit_view else None,
                os.path.join(layout.flow_dir, "flow-complete.mmd"),
            ]
            flow_file = next((c for c in candidates if c and os.path.isfile(c)), None)
        if not flow_file:
            legacy = os.path.join(layout.legacy_flow_dir, "flow-complete.mmd")
            if os.path.isfile(legacy):
                print(f"gnost: {layout.moved_notice()}", file=sys.stderr)
                flow_file = legacy
        if not flow_file or not os.path.isfile(flow_file):
            logger.error(f"Flow diagram not found in {layout.folder}")
            logger.error("Run `gnost onboard .` first")
            return 1
        return show_run(flow_file, args.output, not args.no_open, args.view)

    if target not in {"report", "rpt"}:
        if not os.path.isfile(args.target):
            logger.error(
                f"Unsupported target: {args.target}. Use report, flow, "
                "or the path of a .mmd, .md or .html file"
            )
            return 2
        return show_run(args.target, args.output, not args.no_open, args.view)

    if getattr(args, "path", None):
        report_path = os.path.abspath(args.path)
    else:
        report_path = layout.analysis_html
        if not os.path.isfile(report_path) and os.path.isfile(
            layout.legacy_analysis_html
        ):
            print(f"gnost: {layout.moved_notice()}", file=sys.stderr)
            report_path = layout.legacy_analysis_html
    if not os.path.isfile(report_path):
        logger.error(f"Report not found: {report_path}")
        logger.error(
            "Run `gnost analyze -o` first to generate "
            f"{layout.relative_name}/analysis/analysis.html"
        )
        return 1

    if not _open_analysis_report(report_path):
        fallback = _analysis_open_command(report_path)
        logger.error(
            f"Unable to open report automatically using webbrowser. Use: {fallback}"
        )
        return 1

    cprint(f"Opened report: {report_path}", "green")
    return 0


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) > 2 and sys.argv[1] == RUN_TOOL_FLAG:
        raise SystemExit(run_tool_entry(sys.argv[2:]))
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
            "    --depth DEPTH  Limit execution flow depth (e.g. --depth 2)\n"
            "    --json FILE    Write the insights JSON to FILE instead of .gnost/insights.json\n"
            "    --no-html      Do not write the flow explorer page (.gnost/flow.html)\n"
            "    --insights-only  Write only the insights JSON\n"
            "    --max-edges N  Largest diagram drawn file by file (default 80); bigger ones group by folder\n"
            "    --collapse [LEVEL]  Group diagrams by folder, LEVEL folders deep (default 1)\n\n"
            "  analyze:\n"
            "    path                 File or directory to analyze (default: .)\n"
            "    -a, --analyzer       Enable only specific analyzers\n"
            "    --parallel           Run analyzers in parallel\n"
            "    -o, --out            Write the report to .gnost/analysis/analysis.json and analysis.html\n"
            "    -v, --verbose        Show traceback on failures\n"
            "    --quiet              Reduce logs; keep warnings/errors only\n"
            "    --list-analyzers     List available analyzers and exit\n"
            "    --timeout SECONDS    Analyzer timeout (default: 900)\n"
            "    --compact            Write compact JSON when --out is used\n"
            "    --no-progress        Hide progress updates\n"
            "    --max-findings N     Per-analyzer findings limit (default: 1000)\n\n"
            "  files:\n"
            "    --top          Number of files to show (default: 5)\n\n"
            "  init:\n"
            "    path             Project folder (default: .)\n"
            "    --print          Print the default settings instead of writing .gnost.toml\n"
            "    --force          Overwrite files that already exist\n"
            "    --dry-run        Show what would change, write nothing\n"
            + "".join(
                f"    {'--' + i.flag:<16} {i.help}\n" for i in InitCommand.available()
            )
            + "\n"
            "  onboard|analyze|changes also take an https:// or ssh repository address\n"
            "    in place of the folder (cloned to a temporary folder, results go to the\n"
            "    current folder), and --ref BRANCH to pick a branch or tag.\n\n"
            "  changes:\n"
            "    refs             BASE or BASE..HEAD, compared like a pull request\n"
            "    --depth N        How far to follow importers (default 3)\n"
            "    --format text|markdown|json  What to print (files go to .gnost/changes/)\n"
            "    --findings       Also run the analyzers on the changed Python files\n"
            "    --no-cycles      Skip scanning the base commit\n\n"
            "  open|show:\n"
            "    target                  report|rpt (default): the analysis report;\n"
            "                            flow: the flow explorer; or a .mmd, .md or .html file\n"
            "                            (`show` takes only a file)\n"
            "    --path FILE             Custom report or diagram path\n"
            "    --view auto|graph|mermaid  Interactive graph for big diagrams (auto), or force one\n"
            "    -o, --output FILE       Where to save the HTML page (default: a temp file)\n"
            "    --no-open               Write the HTML but do not open a browser\n\n"
            "Use `gnost <command> --help` for full command options."
        ),
    )
    parser.add_argument("--version", action=_VersionAction, nargs=0)

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
    onboard.add_argument(
        "--json",
        nargs="?",
        const="",
        default=None,
        metavar="FILE",
        help="Write the insights JSON to FILE instead of the default "
        "(.gnost/insights.json, which is always written)",
    )
    onboard.add_argument(
        "--no-html",
        action="store_true",
        help="Do not write the flow explorer page (.gnost/flow.html)",
    )
    onboard.add_argument(
        "--insights-only",
        action="store_true",
        help="Write only the insights JSON; skip ONBOARD.md, the diagrams and the page",
    )
    onboard.add_argument(
        "--max-edges",
        type=int,
        default=None,
        metavar="N",
        help=f"Largest diagram to draw file by file (default: {DEFAULT_MAX_EDGES}); "
        "bigger ones are grouped by folder",
    )
    onboard.add_argument(
        "--collapse",
        nargs="?",
        type=int,
        const=1,
        default=None,
        metavar="LEVEL",
        help="Group diagrams by folder, LEVEL folders deep (default 1: top-level folders)",
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
        "--timeout", type=int, default=None, help="Waiting time in sec, default 900"
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
        "--fail-under",
        type=float,
        default=None,
        metavar="SCORE",
        help="Exit with code 3 when the final score (0 to 10) is below SCORE",
    )
    analyze.add_argument(
        "--baseline",
        nargs="?",
        const="",
        default=None,
        metavar="FILE",
        help="Report only findings that are not in this baseline "
        "(default file: .gnost/baseline.json)",
    )
    analyze.add_argument(
        "--write-baseline",
        nargs="?",
        const="",
        default=None,
        metavar="FILE",
        help="Save today's findings as the baseline (default file: .gnost/baseline.json)",
    )
    analyze.add_argument(
        "--fail-on-new",
        action="store_true",
        help="Exit with code 3 when there are findings that are not in the baseline",
    )
    analyze.add_argument(
        "--sarif",
        nargs="?",
        const="",
        default=None,
        metavar="FILE",
        help="Write the findings as SARIF 2.1.0 (default file: .gnost/analysis/analysis.sarif)",
    )
    analyze.add_argument(
        "--max-findings",
        type=int,
        default=None,
        help="Finding threshold for individual analyzer, default 1000",
    )

    open_cmd = sub.add_parser(
        "open", help="Open a report or diagram in the browser (report, flow or a file)"
    )
    open_cmd.add_argument(
        "target",
        nargs="?",
        default="report",
        help=(
            "report (default, alias: rpt): the analysis report; "
            "flow: the flow explorer (.gnost/flow.html); "
            "or a .mmd, .md or .html file"
        ),
    )
    open_cmd.add_argument(
        "--path",
        help="Custom report or diagram path (optional)",
    )
    open_cmd.add_argument(
        "--view",
        choices=["auto", "graph", "mermaid"],
        default="auto",
        help="auto: interactive graph for big diagrams, Mermaid otherwise",
    )
    open_cmd.add_argument("-o", "--output", help="Where to save the HTML page")
    open_cmd.add_argument(
        "--no-open", action="store_true", help="Write the HTML page but do not open it"
    )

    changes_cmd = sub.add_parser(
        "changes",
        help="What a change touches: files, blast radius, risk, routes, cycles",
    )
    changes_cmd.add_argument(
        "refs", help="BASE or BASE..HEAD (for example origin/main or v0.5.3..HEAD)"
    )
    changes_cmd.add_argument(
        "path", nargs="?", default=".", help="Project folder or repository address"
    )
    changes_cmd.add_argument(
        "--depth", type=int, default=3, help="How far to follow importers (default 3)"
    )
    changes_cmd.add_argument(
        "--format",
        choices=["text", "markdown", "json"],
        default="text",
        help="What to print (the files in .gnost/changes/ are always written)",
    )
    changes_cmd.add_argument(
        "--findings",
        action="store_true",
        help="Also run the analyzers on the changed Python files (slower)",
    )
    changes_cmd.add_argument(
        "--no-cycles",
        action="store_true",
        help="Skip scanning the base commit (no new-cycle or removed-route comparison)",
    )
    changes_cmd.add_argument(
        "--no-write", action="store_true", help="Do not write .gnost/changes/"
    )

    for command in (onboard, analyze, changes_cmd):
        command.add_argument(
            "--ref",
            help="For a repository address: the branch or tag to clone (default: its default branch)",
        )

    init_cmd = sub.add_parser(
        "init",
        help="Write a complete .gnost.toml, and optionally add GNOST to your build",
    )
    init_cmd.add_argument("path", nargs="?", default=".", help="Project folder")
    init_cmd.add_argument(
        "--force", action="store_true", help="Overwrite files that already exist"
    )
    init_cmd.add_argument(
        "--print",
        dest="print_only",
        action="store_true",
        help="Print the default settings instead of writing the file",
    )
    init_cmd.add_argument(
        "--dry-run", action="store_true", help="Show what would change, write nothing"
    )
    for integration in InitCommand.available():
        init_cmd.add_argument(
            f"--{integration.flag}",
            action="append_const",
            const=integration.flag,
            dest="integrations",
            help=integration.help,
        )

    show_cmd = sub.add_parser(
        "show", help="Same as `gnost open FILE` (kept as a shorter name)"
    )
    show_cmd.add_argument("file", help="Mermaid (.mmd) or Markdown (.md) file")
    show_cmd.add_argument("-o", "--output", help="Where to save the HTML page")
    show_cmd.add_argument(
        "--view",
        choices=["auto", "graph", "mermaid"],
        default="auto",
        help="auto: interactive graph for big diagrams, Mermaid otherwise",
    )
    show_cmd.add_argument(
        "--no-open", action="store_true", help="Write the HTML page but do not open it"
    )

    args = parser.parse_args()
    return _run_remote_or_local(args)


def _run_remote_or_local(args: argparse.Namespace) -> int:
    """Run the command; if the path is a repository address, clone it first (and clean up)."""
    try:
        target = RemoteTarget.from_args(args)
        if target is None:
            return _dispatch(args)
        with target.open() as folder:
            args.path = folder
            args.output_root = (
                os.getcwd()
            )  # results go to the current folder, not the clone
            args.remote = True
            args.source = target.url.text
            return _dispatch(args)
    except RemoteError as exc:
        print(f"gnost: {exc}", file=sys.stderr)
        return ExitCode.USAGE


def _dispatch(args: argparse.Namespace) -> int:
    """Run one parsed command."""
    output_root = getattr(args, "output_root", None)
    remote = getattr(args, "remote", False)
    if args.cmd == "init":
        from gnost.cli.commands.init import run as init_run

        return init_run(
            args.path,
            selected=args.integrations or [],
            force=args.force,
            print_only=args.print_only,
            dry_run=args.dry_run,
        )

    if args.cmd == "changes":
        from gnost.cli.commands.changes import run as changes_run

        return changes_run(
            args.path,
            args.refs,
            depth=args.depth,
            output_format=args.format,
            findings=args.findings,
            compare_base=not args.no_cycles,
            write=not args.no_write,
            output_root=output_root,
            remote=remote,
        )

    if args.cmd == "show":
        from gnost.cli.commands.show import run as show_run

        return show_run(args.file, args.output, not args.no_open, args.view)

    if args.cmd == "version":
        print(f"gnost {__version__}")
        _update_notice()
        return 0

    if args.cmd in ("onboard", "analyze"):
        try:
            # A remote repository's own .gnost.toml is never read (output_dir could point anywhere).
            config = load_config(output_root if remote else args.path)
        except ConfigError as exc:
            print(f"gnost: {exc}", file=sys.stderr)
            return 2
        report_warnings(config)

    if args.cmd == "onboard":
        onboard_run(
            args.path,
            diagram_only=getattr(args, "mermaid", False),
            progress=getattr(args, "progress", False),
            inject=getattr(args, "inject", False),
            depth=config.pick("onboard", "depth", getattr(args, "depth", None), None),
            layered=getattr(args, "layered", False),
            json_out=getattr(args, "json", None),
            insights_only=getattr(args, "insights_only", False),
            max_edges=config.pick(
                "onboard",
                "max_edges",
                getattr(args, "max_edges", None),
                DEFAULT_MAX_EDGES,
            ),
            collapse=config.pick(
                "onboard", "collapse", getattr(args, "collapse", None), None
            ),
            exclude=config.exclude,
            caution=config.caution_settings(),
            output_dir=config.output_dir,
            html=not getattr(args, "no_html", False),
            history=(
                dataclasses.replace(config.history_settings(), allow_shallow=True)
                if remote
                else config.history_settings()
            ),
            risk=config.risk_settings(),
            output_root=output_root,
            source=args.source if remote else None,
            footer=config.footer,
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
            return ExitCode.USAGE

        ci_options = CiOptions.from_args(
            args, config, _layout(target_path, config.output_dir, output_root)
        )
        if ci_options.problem():
            logger.error(f"Error: {ci_options.problem()}")
            return ExitCode.USAGE

        if not args.verbose:
            logging.getLogger("asyncio").setLevel(logging.CRITICAL)

        if config.exclude:
            reader_files, count = analysis.collect_code_files(
                target_path, exclude=config.exclude
            )
        else:
            reader_files, count = analysis.collect_code_files(target_path)
        if args.quiet:
            cprint(f"Total Files for Analysis : {count}", "green")
            analysis.set_quiet_logging()
        logger.info(f"Total Files for Analysis : {count}")

        if not reader_files:
            logger.warning("⚠️ No Python files found after filtering.")
            return ExitCode.OK

        enabled_analyzers: Set[str] = set(
            args.analyzer or config.get("analyze", "analyzers", [])
        )
        cfg = AnalysisConfiguration(
            target_path=target_path,
            enabled_analyzers=enabled_analyzers,
            severity_threshold=SeverityLevel.INFO,
            parallel_execution=bool(
                args.parallel or config.get("analyze", "parallel", False)
            ),
            include_low_confidence=False,
            timeout_seconds=int(
                config.pick("analyze", "timeout", args.timeout, ANALYZE_TIMEOUT)
            ),
            max_findings_per_analyzer=int(
                config.pick(
                    "analyze", "max_findings", args.max_findings, ANALYZE_MAX_FINDINGS
                )
            ),
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
            return ExitCode.INTERRUPTED
        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            if args.verbose:
                traceback.print_exc()
            return ExitCode.ERROR

        try:
            outcome = CiRun(
                ci_options, _resolve_repo_root(target_path), reader_files
            ).process(report)
        except BaselineError as exc:
            logger.error(f"Error: {exc}")
            return ExitCode.USAGE

        payload = _to_dict_payload(outcome.report)
        if outcome.baseline_summary():
            payload["baseline"] = outcome.baseline_summary()
        html_output = _analysis_html_output_path(
            target_path, config.output_dir, output_root
        )
        if args.out:
            try:
                _layout(target_path, config.output_dir, output_root).prepare()
                output_file = _analysis_output_path(
                    target_path, config.output_dir, output_root
                )
                analysis.write_json_file(output_file, payload, compact=args.compact)
                logger.info(f"✅ Findings saved to {output_file}")
                if args.quiet:
                    cprint(f"✅ Findings saved to {output_file}", "green")
                html_output = _analysis_html_output_path(
                    target_path, config.output_dir, output_root
                )
                render_analysis_html(payload, html_output)
                logger.info(f"✅ Interactive HTML report saved to {html_output}")
                if args.quiet:
                    cprint(
                        f"✅ Interactive HTML report saved to {html_output}", "green"
                    )
            except Exception as e:
                logger.error(
                    f"❌ Failed to write output file '{_analysis_output_path(target_path, config.output_dir, output_root)}': {e}, use verbose to check"
                )
                if args.verbose:
                    traceback.print_exc()
                return ExitCode.ERROR

        _print_analysis_scores(outcome.card)
        for note in outcome.notes:
            if args.quiet:
                cprint(note, "green")
            else:
                logger.info(note)
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
        if not outcome.gate.passed:
            for message in outcome.gate.messages:
                logger.error(f"Quality gate failed: {message}")
            return ExitCode.GATE_FAILED
        return ExitCode.OK

    if args.cmd == "open":
        return _open(args)

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
