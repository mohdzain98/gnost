from rich.console import Console
from rich.table import Table

console = Console()

def print_summary(results, file_count):
    total_loc = sum(results.values())
    table = Table(title="GNOST — Code Knowledge Scanner")

    table.add_column("Language")
    table.add_column("Files", justify="right")
    table.add_column("LOC", justify="right")
    table.add_column("%", justify="right")

    for ext, loc in results.items():
        pct = (loc / total_loc * 100) if total_loc else 0
        table.add_row(
            ext.upper(),
            str(file_count.get(ext, 0)),
            str(loc),
            f"{pct:.2f}%"
        )

    console.print(table)
    console.print(f"[bold green]Total LOC: {total_loc}[/bold green]")
