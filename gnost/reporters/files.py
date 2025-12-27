from rich.table import Table
from rich.console import Console

console = Console()


def render(data, top=5):
    table = Table(title=f"Top {top} Largest Files")

    table.add_column("File")
    table.add_column("LOC", justify="right")

    files = sorted(data["files"], key=lambda x: x["loc"], reverse=True)[:top]

    for f in files:
        table.add_row(f["path"], str(f["loc"]))

    console.print(table)
