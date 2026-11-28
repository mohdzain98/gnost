"""The mind map as a Mermaid `mindmap` block (`--mindmap-format mermaid`).

GitHub renders Mermaid natively, so no image file has to be committed. Mermaid draws its own
layout and has no sizes or colours, so entry points are marked with a star instead. The same
leaf cap as the SVG keeps big projects readable.
"""

from __future__ import annotations

import re
from typing import Dict, List

from gnost.reporters.mindmap.layout import RadialLayout
from gnost.reporters.mindmap.model import Folder, MindMap

# Characters that open a node shape or break a line in Mermaid's mindmap syntax.
_UNSAFE = re.compile(r"[()\[\]{}<>\"`\n\r]")
# Mermaid reads labels as Markdown: `__init__.py` would turn bold, so escape these.
_MARKDOWN = re.compile(r"([_*])")


class MindMapMermaid:
    """Writes a `MindMap` as Mermaid mindmap source, one indented line per node.

    Closed folders become one line with their file count, like in the explorer.
    """

    MAX_LEAVES = 300

    def __init__(self, mind: MindMap, max_leaves: int = MAX_LEAVES) -> None:
        self.mind = mind
        self.max_leaves = max_leaves

    def render(self) -> str:
        """The Mermaid source, starting with `mindmap`."""
        choices = RadialLayout(self.mind).fit(self.max_leaves)
        name = self._safe(self.mind.tree.label.replace("\n", " "))
        lines = ["mindmap", f"  root(({name}))"]
        self._walk(self.mind.tree, 0, 2, choices, lines)
        return "\n".join(lines) + "\n"

    @staticmethod
    def _safe(text: str) -> str:
        """A label Mermaid shows as written: no shape characters, Markdown escaped."""
        return _MARKDOWN.sub(r"\\\1", _UNSAFE.sub(" ", text).strip()) or "\\_"

    def _walk(
        self,
        folder: Folder,
        depth: int,
        indent: int,
        choices: Dict[str, bool],
        lines: List[str],
    ) -> None:
        """Add the folder's children, opening only the folders the layout keeps open."""
        pad = "  " * indent
        for child in sorted(folder.dirs.values(), key=lambda d: d.name):
            if self.mind.is_open(child, depth + 1, choices):
                lines.append(f"{pad}{self._safe(child.name)}")
                self._walk(child, depth + 1, indent + 1, choices, lines)
            else:
                count = f"{child.n} file" + ("" if child.n == 1 else "s")
                lines.append(f"{pad}{self._safe(child.name)}, {count}")
        for path in sorted(folder.files):
            star = " ★" if path in self.mind.entry else ""
            lines.append(f"{pad}{self._safe(path.split('/')[-1])}{star}")
