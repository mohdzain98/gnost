"""The README badge `gnost analyze --badge` writes: "gnost | 9.62" as a small, self-contained SVG.

The colour follows the terminal (green from 8, yellow from 6, red below). The file has no
external references, so GitHub shows it straight from the repository: commit it and link it
from the README with the Markdown line `ScoreBadge.markdown` returns.
"""

from __future__ import annotations

import os
from html import escape

DEFAULT_BADGE = "badge.svg"  # inside the output folder (.gnost/)


class ScoreBadge:
    """A flat two-part badge: a grey label and the score on a coloured background.

    Text width is estimated per character (Verdana 11px, as shields.io badges use), which is
    close enough for short labels; the SVG scales cleanly if a viewer's font differs.
    """

    COLOURS = {"green": "#44cc11", "yellow": "#dfb317", "red": "#e05d44"}
    LABEL_COLOUR = "#555555"
    _NARROW = set("fijlrtI1., ")

    def __init__(self, score: float, label: str = "gnost") -> None:
        self.score = score
        self.label = label

    @property
    def message(self) -> str:
        """The score as shown, two decimals out of 10."""
        return f"{self.score:.2f}"

    @property
    def colour(self) -> str:
        """Green from 8, yellow from 6, red below (the terminal's colours)."""
        name = "green" if self.score >= 8 else "yellow" if self.score >= 6 else "red"
        return self.COLOURS[name]

    def svg(self) -> str:
        """The badge as SVG text."""
        left = self._width(self.label) + 10
        right = self._width(self.message) + 10
        total = left + right
        label, message = escape(self.label), escape(self.message)
        title = f"{label}: {message} / 10"
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="20" role="img" '
            f'aria-label="{title}">'
            f"<title>{title}</title>"
            '<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" '
            'stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>'
            f'<clipPath id="r"><rect width="{total}" height="20" rx="3" fill="#fff"/></clipPath>'
            f'<g clip-path="url(#r)"><rect width="{left}" height="20" fill="{self.LABEL_COLOUR}"/>'
            f'<rect x="{left}" width="{right}" height="20" fill="{self.colour}"/>'
            f'<rect width="{total}" height="20" fill="url(#s)"/></g>'
            '<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" '
            'font-size="11">'
            f'<text x="{left / 2}" y="15" fill="#010101" fill-opacity=".3">{label}</text>'
            f'<text x="{left / 2}" y="14">{label}</text>'
            f'<text x="{left + right / 2}" y="15" fill="#010101" fill-opacity=".3">{message}</text>'
            f'<text x="{left + right / 2}" y="14">{message}</text>'
            "</g></svg>\n"
        )

    def write(self, path: str) -> None:
        """Write the SVG, creating the folder if needed."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(self.svg())

    @staticmethod
    def markdown(path: str, root: str) -> str:
        """The README line for a badge file, relative to the repository root."""
        relative = os.path.relpath(os.path.abspath(path), os.path.abspath(root))
        return f"![GNOST score]({relative.replace(os.sep, '/')})"

    def _width(self, text: str) -> int:
        """Estimated text width in pixels."""
        return sum(4 if ch in self._NARROW else 7 for ch in text)
