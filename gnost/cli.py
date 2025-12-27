import argparse
from gnost import __version__
from gnost.scanner.engine import scan
from gnost.reporters import summary, stats, folders, files


def main():
    parser = argparse.ArgumentParser(
        prog="gnost",
        usage="gnost [command]",
        description="GNOST — Code Knowledge Scanner",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Command Options:\n"
            "  summary|stats|folders|files:\n"
            "    --include  Comma-separated folder names to include\n"
            "    --exclude  Comma-separated folder names to exclude\n"
            "  files:\n"
            "    --top      Number of files to show (default: 5)\n"
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

    args = parser.parse_args()

    if args.cmd == "version":
        print(f"gnost {__version__}")
        return

    include = args.include.split(",") if args.include else []
    exclude = args.exclude.split(",") if args.exclude else []

    data = scan(args.path, include, exclude)

    if args.cmd == "stats":
        stats.render(data)
    elif args.cmd == "folders":
        folders.render(data)
    elif args.cmd == "files":
        files.render(data, args.top)
    else:
        summary.render(data)


if __name__ == "__main__":
    main()
