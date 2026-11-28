"""The mind map as a static SVG image for a README (`gnost onboard --inject-mindmap`).

No JavaScript, so GitHub and other hosts render it as an image. Colours follow the reader's
light or dark preference through `prefers-color-scheme`. Large projects are kept readable by
closing the deepest folders until at most `MAX_LEAVES` leaves are left.
"""

from __future__ import annotations

import html
import math
from typing import Dict, List, Tuple

from gnost.reporters.mindmap.layout import MindItem, MindLayout, RadialLayout
from gnost.reporters.mindmap.model import MindMap

STYLE = """
  .b { stroke:#4f7cff; stroke-opacity:.35; fill:none }
  .l { stroke:#2da44e; stroke-opacity:.45; fill:none; stroke-width:1.2 }
  .d { fill:#4f7cff } .c { fill:#4f7cff; fill-opacity:.35; stroke:#4f7cff; stroke-width:1.5 }
  .f { fill:#8b949e } .t { fill:#d29922 } .e { fill:#2da44e; stroke:#2da44e; stroke-width:2 }
  text { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
         dominant-baseline:central; paint-order:stroke; stroke:#ffffff; stroke-width:3px;
         stroke-linejoin:round; fill:#1f2328 }
  text.fl { font-size:10px; fill:#656d76; stroke-width:0 }
  text.tl { font-size:12px; font-weight:600; fill:#9a6700; stroke-width:0 }
  text.el { font-size:13px; font-weight:700; fill:#1a7f37; stroke-width:0 }
  text.dl { font-size:12px; font-weight:700 }
  text.rl { font-size:15px; font-weight:700; text-anchor:middle }
  @media (prefers-color-scheme: dark) {
    text { stroke:#0d1117; fill:#e6edf3 }
    text.fl { fill:#8b949e } text.tl { fill:#d29922 } text.el { fill:#3fb950 }
  }
"""


class MindMapSvg:
    """Draws a `MindMap` as a self-contained SVG string.

    Every name is escaped, because file names in a remote repository can be hostile.
    """

    MAX_LEAVES = 300
    WIDTH = 900  # displayed width; the viewBox keeps the drawing's own scale
    PAD = 24.0
    LABEL_GAP = 6.0

    def __init__(self, mind: MindMap, max_leaves: int = MAX_LEAVES) -> None:
        self.mind = mind
        self.max_leaves = max_leaves

    def render(self) -> str:
        """The SVG document."""
        layout = RadialLayout(self.mind)
        placed = layout.place(layout.fit(self.max_leaves))
        by_id = {item.id: item for item in placed.items}
        x0, y0, x1, y1 = self._bounds(placed.items)
        width, height = x1 - x0, y1 - y0
        shown = round(self.WIDTH * height / width) if width else self.WIDTH
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.1f} {y0:.1f} '
            f'{width:.1f} {height:.1f}" width="{self.WIDTH}" height="{shown}" '
            'role="img" aria-labelledby="t">',
            f'<title id="t">{self._esc(self._title())}</title>',
            f"<style>{STYLE}</style>",
        ]
        parts += self._branches(placed.items, by_id)
        parts += self._links(placed, by_id)
        parts += [self._node(item) for item in placed.items]
        parts += [self._label(item) for item in placed.items]
        parts.append("</svg>")
        return "\n".join(parts) + "\n"

    def _title(self) -> str:
        name = self.mind.tree.label.split("\n")[0]
        return f"Project map of {name}: {len(self.mind.files)} files"

    @staticmethod
    def _esc(text: str) -> str:
        return html.escape(text, quote=True)

    def _branches(self, items: List[MindItem], by_id: Dict[str, MindItem]) -> List[str]:
        """The tree lines: thick from the project, thin further out."""
        lines = []
        for item in items:
            if item.parent is None:
                continue
            parent = by_id[item.parent]
            width = 3 if parent.kind == "root" else 1.5
            lines.append(
                f'<line class="b" stroke-width="{width}" x1="{parent.x:.1f}" '
                f'y1="{parent.y:.1f}" x2="{item.x:.1f}" y2="{item.y:.1f}"/>'
            )
        return lines

    def _links(self, placed: MindLayout, by_id: Dict[str, MindItem]) -> List[str]:
        """Curved lines from each entry point to what it imports (deduplicated per target)."""
        paths = []
        for entry in sorted(self.mind.entry):
            source = placed.at.get(entry)
            seen = set()
            for target in self.mind.imports[entry]:
                end = placed.at.get(target)
                if not source or not end or end == source or end in seen:
                    continue
                seen.add(end)
                a, b = by_id[source], by_id[end]
                mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
                length = math.hypot(b.x - a.x, b.y - a.y) or 1.0
                cx, cy = mx - 40 * (b.y - a.y) / length, my + 40 * (b.x - a.x) / length
                paths.append(
                    f'<path class="l" d="M{a.x:.1f},{a.y:.1f} '
                    f'Q{cx:.1f},{cy:.1f} {b.x:.1f},{b.y:.1f}"/>'
                )
        return paths

    def _node(self, item: MindItem) -> str:
        r = item.size / 2
        if item.kind == "dir" and not item.open:
            return (
                f'<rect class="c" x="{item.x - r:.1f}" y="{item.y - r:.1f}" '
                f'width="{item.size:.1f}" height="{item.size:.1f}" rx="4"/>'
            )
        css = "d"
        if item.kind == "file":
            css = (
                "e"
                if item.id in self.mind.entry
                else "t"
                if item.id in self.mind.top
                else "f"
            )
        return (
            f'<circle class="{css}" cx="{item.x:.1f}" cy="{item.y:.1f}" r="{r:.1f}"/>'
        )

    def _label(self, item: MindItem) -> str:
        """Names point outwards along their branch; the left half is flipped to stay upright."""
        if item.kind == "root":
            lines = item.label.split("\n")
            first = -(len(lines) - 1) * 9
            spans = "".join(
                f'<tspan x="0" y="{first + k * 18}">{self._esc(line)}</tspan>'
                for k, line in enumerate(lines)
            )
            return f'<text class="rl">{spans}</text>'
        css = "dl"
        if item.kind == "file":
            css = (
                "el"
                if item.id in self.mind.entry
                else "tl"
                if item.id in self.mind.top
                else "fl"
            )
        left = math.cos(item.angle) < 0
        degrees = math.degrees(item.angle + (math.pi if left else 0.0))
        offset = item.size / 2 + self.LABEL_GAP
        x = item.x - offset if left else item.x + offset
        anchor = "end" if left else "start"
        return (
            f'<text class="{css}" text-anchor="{anchor}" x="{x:.1f}" y="{item.y:.1f}" '
            f'transform="rotate({degrees:.2f} {item.x:.1f} {item.y:.1f})">'
            f"{self._esc(item.label)}</text>"
        )

    def _bounds(self, items: List[MindItem]) -> Tuple[float, float, float, float]:
        """The drawing's extent, labels included (their width estimated from their length)."""
        xs: List[float] = []
        ys: List[float] = []
        for item in items:
            reach = item.size / 2
            if item.kind != "root":
                font = 13.0 if item.id in self.mind.entry else 12.0
                reach += self.LABEL_GAP + len(item.label) * font * 0.6
            else:
                reach = max(reach, max(len(s) for s in item.label.split("\n")) * 5.0)
            xs += [item.x + reach * math.cos(item.angle), item.x - item.size]
            ys += [item.y + reach * math.sin(item.angle), item.y - item.size]
            xs.append(item.x + item.size)
            ys.append(item.y + item.size)
            if item.kind == "root":
                xs += [-reach, reach]
                ys += [-reach, reach]
        return (
            min(xs) - self.PAD,
            min(ys) - self.PAD,
            max(xs) + self.PAD,
            max(ys) + self.PAD,
        )
