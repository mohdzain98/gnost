"""The mind map as a rotating 3D GIF for a README (`--mindmap-format gif`).

`MindMapScene` places the tree in 3D with no randomness and no force simulation, so the same
project always gives the same image. `MindMapGif` rotates it about the vertical axis and draws
the frames with Pillow, an optional extra (`pip install "gnost[media]"`).
"""

from __future__ import annotations

import colorsys
import io
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from gnost.reporters.mindmap.layout import RadialLayout
from gnost.reporters.mindmap.model import Folder, MindMap

Color = Tuple[int, int, int]

BACKGROUND: Color = (
    13,
    17,
    23,
)  # GitHub's dark background; a GIF cannot follow the theme
ROOT: Color = (79, 124, 255)
ENTRY: Color = (63, 185, 80)
TOP: Color = (210, 153, 34)


@dataclass(frozen=True)
class Point3d:
    """One node of the scene: its position, parent index, colour, radius and optional label."""

    x: float
    y: float
    z: float
    parent: int
    color: Color
    radius: float
    label: str = ""
    level: int = (
        0  # 0 the project, 1 a top-level folder, 2 a folder inside one, 3 the rest
    )


class MindMapScene:
    """Places a `MindMap` in 3D: each folder's contents on a sphere around that folder.

    Sphere sizes are worked out bottom-up from what they hold, so sibling folders do not
    overlap. The scene is centred on its middle, so it turns in place. Closed folders are one node.
    """

    MIN_TOP = 160.0
    FILE_EXTENT = 5.0

    def __init__(self, mind: MindMap, max_leaves: int = 300) -> None:
        self.mind = mind
        self.choices = RadialLayout(mind).fit(max_leaves)
        self.points: List[Point3d] = []
        self._colors: Dict[str, Color] = {}
        self._extent: Dict[str, Tuple[float, float]] = {}

    def build(self) -> List[Point3d]:
        """The points, the project first; every other point names its parent's index."""
        self.points = [Point3d(0.0, 0.0, 0.0, -1, ROOT, 9.0, self._root_label(), 0)]
        self._paint(self.mind.tree)
        self._place(self.mind.tree, 0, (0.0, 0.0, 0.0), 0)
        return self._centred(self.points)

    def _root_label(self) -> str:
        return self.mind.tree.label.split("\n")[0]

    def _kids(self, folder: Folder) -> List[Any]:
        dirs: List[Any] = sorted(folder.dirs.values(), key=lambda d: d.name)
        return dirs + sorted(folder.files)

    @staticmethod
    def fibonacci(i: int, n: int) -> Tuple[float, float, float]:
        """The i-th of n evenly spread points on a unit sphere."""
        y = 1 - (2 * (i + 0.5)) / n
        r = math.sqrt(max(0.0, 1 - y * y))
        theta = math.pi * (3 - math.sqrt(5)) * i
        return (math.cos(theta) * r, y, math.sin(theta) * r)

    @staticmethod
    def _hue(index: int) -> float:
        """Golden-angle hues, kept out of the green that marks entry points."""
        hue = (index * 137.5 + 12) % 360
        if 95 < hue < 165:
            hue = (hue + 75) % 360
        return hue / 360

    def _paint(self, tree: Folder) -> None:
        """One hue per top-level folder; its sub-folders get nearby shades of it."""
        families = [c for c in self._kids(tree) if isinstance(c, Folder)]
        for index, family in enumerate(families):
            hue = self._hue(index)
            self._colors[family.path] = self._rgb(hue, 0.62)
            subs = sorted(family.dirs.values(), key=lambda d: d.name)
            for k, sub in enumerate(subs):
                shade = (hue + (k - len(subs) / 2) * 0.025) % 1.0
                self._shade(sub, self._rgb(shade, 0.55 + 0.12 * (k % 3) / 2))

    def _shade(self, folder: Folder, color: Color) -> None:
        self._colors[folder.path] = color
        for child in folder.dirs.values():
            self._shade(child, color)

    @staticmethod
    def _rgb(hue: float, light: float) -> Color:
        r, g, b = colorsys.hls_to_rgb(hue, light, 0.65)
        return (round(r * 255), round(g * 255), round(b * 255))

    def _color(self, folder: str, path: str) -> Color:
        if path in self.mind.entry:
            return ENTRY
        if path in self.mind.top:
            return TOP
        return self._colors.get(folder, self._rgb(0.6, 0.62))

    def _open(self, folder: Folder, depth: int) -> bool:
        return self.mind.is_open(folder, depth, self.choices)

    def _size(self, folder: Folder, depth: int) -> Tuple[float, float]:
        """(sphere radius for its children, how far its drawing reaches from its centre)."""
        if folder.path in self._extent:
            return self._extent[folder.path]
        kids = self._kids(folder)
        reach = [
            self._size(c, depth + 1)[1]
            if isinstance(c, Folder) and self._open(c, depth + 1)
            else self.FILE_EXTENT
            for c in kids
        ]
        ranked = sorted(reach + [self.FILE_EXTENT, self.FILE_EXTENT], reverse=True)
        widest, second = ranked[0], ranked[1]
        n = max(1, len(kids))
        radius = max(
            22 + 6 * math.sqrt(n),  # room for the files themselves
            widest + 12,  # a child's own cluster stays clear of its parent
            # neighbours on the sphere are about R * sqrt(4 pi / n) apart: keep the two
            # widest clusters from touching
            1.1 * (widest + second) * math.sqrt(n / (4 * math.pi)),
        )
        if depth == 0:
            radius = max(radius, self.MIN_TOP)
        self._extent[folder.path] = (radius, radius + widest)
        return self._extent[folder.path]

    def _place(
        self,
        folder: Folder,
        depth: int,
        centre: Tuple[float, float, float],
        parent: int,
    ) -> None:
        """Put the folder's children on its sphere around `centre`, recursing into open ones."""
        kids = self._kids(folder)
        radius = self._size(folder, depth)[0]
        for i, child in enumerate(kids):
            ux, uy, uz = self.fibonacci(i, len(kids))
            x, y, z = (
                centre[0] + ux * radius,
                centre[1] + uy * radius,
                centre[2] + uz * radius,
            )
            if isinstance(child, str):
                size = 2.5 + 0.9 * math.log2(1 + self.mind.fan_in.get(child, 0))
                if child in self.mind.entry:
                    size = 6.0
                where = child.rsplit("/", 1)[0] if "/" in child else ""
                self.points.append(
                    Point3d(x, y, z, parent, self._color(where, child), size, "", 3)
                )
                continue
            size = min(8.0, 4.0 + math.sqrt(child.n) / 2)
            level = min(depth + 1, 3)
            self.points.append(
                Point3d(
                    x,
                    y,
                    z,
                    parent,
                    self._color(child.path, ""),
                    size,
                    child.name,
                    level,
                )
            )
            if self._open(child, depth + 1):
                self._place(child, depth + 1, (x, y, z), len(self.points) - 1)

    @staticmethod
    def _centred(points: List[Point3d]) -> List[Point3d]:
        """The points moved so their middle is the origin, the axis the GIF turns about."""
        n = len(points)
        mx = sum(p.x for p in points) / n
        my = sum(p.y for p in points) / n
        mz = sum(p.z for p in points) / n
        return [
            Point3d(
                p.x - mx,
                p.y - my,
                p.z - mz,
                p.parent,
                p.color,
                p.radius,
                p.label,
                p.level,
            )
            for p in points
        ]


class MindMapGif:
    """Draws a `MindMapScene` turning once around, as an animated GIF.

    Frames are drawn at twice the size and scaled down for smooth edges, then share one
    256-colour palette. Same input, same bytes.
    """

    def __init__(
        self,
        mind: MindMap,
        size: int = 600,
        frames: int = 60,  # 6 degrees a frame: smooth
        frame_ms: int = 110,  # one turn in 6.6 s, slow enough to read
        max_leaves: int = 300,
    ) -> None:
        self.points = MindMapScene(mind, max_leaves).build()
        self.size = size
        self.frames = frames
        self.frame_ms = frame_ms

    @staticmethod
    def available() -> bool:
        """Whether Pillow is installed (`pip install "gnost[media]"`)."""
        try:
            import PIL  # noqa: F401
        except ImportError:
            return False
        return True

    def render(self) -> bytes:
        """The GIF file's bytes."""
        from PIL import Image

        frames = [
            self._frame(2 * math.pi * k / self.frames) for k in range(self.frames)
        ]
        first = frames[0].quantize(colors=256)
        rest = [f.quantize(palette=first, dither=Image.Dither.NONE) for f in frames[1:]]
        out = io.BytesIO()
        first.save(
            out,
            format="GIF",
            save_all=True,
            append_images=rest,
            duration=self.frame_ms,
            loop=0,
            disposal=1,
        )
        return out.getvalue()

    def _font(self, size: int) -> Any:
        from PIL import ImageFont

        try:
            return ImageFont.load_default(size=size)
        except TypeError:  # Pillow < 10.1 has only the small bitmap font
            return ImageFont.load_default()

    @staticmethod
    def _mix(color: Color, amount: float) -> Color:
        """`color` faded towards the background by `amount` (0 keeps it, 1 is background)."""
        return tuple(  # type: ignore[return-value]
            round(c + (b - c) * amount) for c, b in zip(color, BACKGROUND)
        )

    def _labels(
        self,
        draw: Any,
        placed: List[Optional[Tuple[float, float, float, float]]],
        extent: float,
        depth: Any,
        scale: int,
    ) -> None:
        """Names of the project and the first two folder levels, front first, never overlapping.

        A label that would touch one already drawn is skipped in this frame.
        """
        fonts = {
            0: self._font(16 * scale),
            1: self._font(13 * scale),
            2: self._font(11 * scale),
        }
        wanted = [
            i
            for i, p in enumerate(self.points)
            if p.label and p.level <= 2 and placed[i] is not None
        ]
        wanted.sort(key=lambda i: (self.points[i].level, -placed[i][2]))  # type: ignore[index]
        taken: List[Tuple[float, float, float, float]] = []
        for i in wanted:
            p = self.points[i]
            cx, cy, z, near = placed[i]  # type: ignore[misc]
            if p.level > 0 and z < -extent * 0.25:
                continue  # behind the scene: its label would float over the front
            font = fonts[p.level]
            anchor_y = cy - p.radius * scale * near * 1.15 - 4 * scale
            box = draw.textbbox((cx, anchor_y), p.label, font=font, anchor="ms")
            pad = 3 * scale
            box = (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad)
            if any(
                box[0] < t[2] and box[2] > t[0] and box[1] < t[3] and box[3] > t[1]
                for t in taken
            ):
                continue
            taken.append(box)
            draw.text(
                (cx, anchor_y),
                p.label,
                fill=self._mix((230, 237, 243), depth(z)),
                font=font,
                anchor="ms",
                stroke_width=2 * scale,
                stroke_fill=BACKGROUND,
            )

    def _frame(self, angle: float) -> Any:
        """One frame, rotated by `angle` radians about the vertical axis."""
        from PIL import Image, ImageDraw

        scale = 2
        side = self.size * scale
        image = Image.new("RGB", (side, side), BACKGROUND)
        draw = ImageDraw.Draw(image)
        extent = max(math.hypot(p.x, p.y, p.z) + p.radius for p in self.points) or 1.0
        camera = extent * 3.2
        fit = side * 0.40 / extent
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        placed: List[Optional[Tuple[float, float, float, float]]] = []
        for p in self.points:
            x = p.x * cos_a + p.z * sin_a
            z = -p.x * sin_a + p.z * cos_a
            near = camera / (camera - z)  # larger when closer to the viewer
            placed.append(
                (side / 2 + x * fit * near, side / 2 - p.y * fit * near, z, near)
            )
        depth = lambda z: 0.55 * (1 - (z / extent + 1) / 2)  # noqa: E731  far is faded
        for p, here in zip(self.points, placed):
            if p.parent < 0 or here is None:
                continue
            there = placed[p.parent]
            if there is None:
                continue
            fade = 0.55 + depth((here[2] + there[2]) / 2)
            draw.line(
                [(here[0], here[1]), (there[0], there[1])],
                fill=self._mix(p.color, min(0.9, fade)),
                width=scale,
            )
        order = sorted(
            range(len(self.points)),
            key=lambda i: placed[i][2],  # type: ignore[index]
        )
        for i in order:
            p, here = self.points[i], placed[i]
            assert here is not None
            cx, cy, z, near = here
            r = p.radius * scale * near * 1.15
            draw.ellipse(
                [cx - r, cy - r, cx + r, cy + r], fill=self._mix(p.color, depth(z))
            )
        self._labels(draw, placed, extent, depth, scale)
        return image.resize((self.size, self.size), Image.LANCZOS)
