from rich.console import Console
from gnost.config.languages import by_language_name

console = Console()


def render(data):
    for name, stats in by_language_name(data["by_language"]).items():
        console.print(f"[bold]{name}[/bold]")
        console.print(f"  files     : {stats['files']}")
        console.print(f"  code      : {stats['code']}")
        console.print(f"  comments  : {stats['comments']}")
        console.print(f"  blanks    : {stats['blanks']}\n")
