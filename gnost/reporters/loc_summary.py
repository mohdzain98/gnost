from rich.console import Console
from rich.table import Table

from gnost.config.languages import LANGUAGES

console = Console()


def render(data):
    table = Table(title="GNOST — Summary")

    table.add_column("Language")
    table.add_column("Files", justify="right")
    table.add_column("LOC", justify="right")

    for ext, stats in data["by_language"].items():
        table.add_row(LANGUAGES[ext]["name"], str(stats["files"]), str(stats["loc"]))

    console.print(table)
