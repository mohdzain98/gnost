"""`gnost show`: open a Mermaid or Markdown file in the browser."""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import webbrowser
from typing import Optional

from gnost.reporters.diagram_viewer import render_viewer_html

_MERMAID_EXT = {".mmd", ".mermaid"}
_MARKDOWN_EXT = {".md", ".markdown"}


def build_page(path: str, mode: str = "auto") -> str:
    """The self-contained HTML page for a .mmd or .md file."""
    ext = os.path.splitext(path)[1].lower()
    kind = "mermaid" if ext in _MERMAID_EXT else "markdown"
    with open(path, encoding="utf-8") as f:
        source = f.read()
    if kind == "mermaid" and mode != "mermaid":
        kind = "graph"  # the interactive explorer for every size; --view mermaid draws it flat
    return render_viewer_html(source, os.path.basename(path), kind)  # type: ignore[arg-type]


def run(
    path: str,
    output: Optional[str] = None,
    open_browser: bool = True,
    mode: str = "auto",
) -> int:
    """Render `path` to an HTML page and open it. Returns an exit code."""
    if not os.path.isfile(path):
        print(f"gnost: file not found: {path}", file=sys.stderr)
        return 2

    ext = os.path.splitext(path)[1].lower()
    if ext in (".html", ".htm"):
        # Already a page (for example the analysis report): open it as it is.
        print(f"Opened {path}")
        if open_browser and not webbrowser.open(pathlib.Path(path).resolve().as_uri()):
            print("Could not open a browser; open the file above manually.")
        return 0
    if ext not in _MERMAID_EXT and ext not in _MARKDOWN_EXT:
        print(
            "gnost: supported files are .mmd, .mermaid, .md and .html", file=sys.stderr
        )
        return 2

    html = build_page(path, mode)
    if output is None:
        fd, output = tempfile.mkstemp(prefix="gnost-show-", suffix=".html")
        os.close(fd)
    with open(output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Viewer written to {output}")
    if open_browser and not webbrowser.open(pathlib.Path(output).resolve().as_uri()):
        print("Could not open a browser; open the file above manually.")
    return 0
