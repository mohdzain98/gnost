from rich.console import Console
from gnost.config.languages import LANGUAGES

console = Console()


def render(data):
    for ext, stats in data["by_language"].items():
        console.print(f"[bold]{LANGUAGES[ext]['name']}[/bold]")
        console.print(f"  files     : {stats['files']}")
        console.print(f"  code      : {stats['code']}")
        console.print(f"  comments  : {stats['comments']}")
        console.print(f"  blanks    : {stats['blanks']}\n")
