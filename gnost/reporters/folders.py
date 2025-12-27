from rich.table import Table
from rich.console import Console

console = Console()


def render(data):
    table = Table(title="Folder LOC")

    table.add_column("Folder")
    table.add_column("LOC", justify="right")

    for folder, loc in sorted(
        data["by_folder"].items(), key=lambda x: x[1], reverse=True
    ):
        table.add_row(folder, str(loc))

    console.print(table)
