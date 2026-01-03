import argparse
from gnost import __version__
from gnost.scanner.engine import scan
from gnost.reporters import stats, folders, files, loc_summary
from gnost.cli.commands.onboard import run as onboard_run


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
            "  files:\n"
            "    --top          Number of files to show (default: 5)\n"
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

    args = parser.parse_args()

    if args.cmd == "version":
        print(f"gnost {__version__}")
        return

    if args.cmd == "onboard":
        onboard_run(
            args.path,
            diagram_only=getattr(args, "mermaid", False),
            progress=getattr(args, "progress", False),
            inject=getattr(args, "inject", False),
            depth=getattr(args, "depth", None),
            layered=getattr(args, "layered", False),
        )
        return

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


if __name__ == "__main__":
    main()
