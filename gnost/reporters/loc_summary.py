"""The `gnost summary` tables: lines of code per language, or GitHub's language bar (`--git`).

The default counts lines in every file GNOST scans. `--git` counts bytes the way GitHub's
language bar does (see gnost.vcs.linguist), so the two can differ on purpose.
"""

from rich.console import Console
from rich.table import Table
from rich.text import Text

from gnost.config.languages import by_language_name
from gnost.vcs.linguist import GitLanguages

console = Console()

BAR_WIDTH = 60


def render(data):
    """Files and lines of code per language (the default summary)."""
    table = Table(title="GNOST — Summary")

    table.add_column("Language")
    table.add_column("Files", justify="right")
    table.add_column("LOC", justify="right")

    for name, stats in by_language_name(data["by_language"]).items():
        table.add_row(name, str(stats["files"]), str(stats["loc"]))

    console.print(table)


def render_git(result: GitLanguages) -> None:
    """GitHub's language bar for the last commit: a coloured bar, then one row per language."""
    if not result.languages:
        console.print("No files that GitHub's language bar counts.")
        return
    bar = Text()
    used = 0
    for k, lang in enumerate(result.languages):
        cells = round(BAR_WIDTH * lang.share / 100)
        if k == len(result.languages) - 1:
            cells = BAR_WIDTH - used  # the bar is always full width
        used += cells
        bar.append("█" * max(0, cells), style=lang.color)
    table = Table(title="GNOST — Languages as GitHub shows them")
    table.add_column("Language")
    table.add_column("Share", justify="right")
    table.add_column("Files", justify="right")
    table.add_column("Bytes", justify="right")
    for lang in result.languages:
        name = Text("● ", style=lang.color)
        name.append(lang.name)
        table.add_row(name, f"{lang.share:.1f}%", str(lang.files), f"{lang.bytes:,}")
    console.print(bar)
    console.print(table)
    left_out = ", ".join(f"{n} {why}" for why, n in sorted(result.skipped.items()))
    console.print(
        "Counted like GitHub's language bar: bytes of the files in the last commit, only "
        "programming and markup languages, without vendored, documentation or generated files."
        + (f" Left out: {left_out}." if left_out else ""),
        style="dim",
    )
