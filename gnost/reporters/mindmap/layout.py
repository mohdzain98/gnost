"""Radial layout of a mind map: where every folder and file is drawn.

Mirrors `mindLayout` in the flow explorer (templates/graph_viewer.html); a test runs both on
the same graph and compares the positions. The project sits in the middle, open folders on
inner rings and every leaf (a file or a closed folder) on the outer ring.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from gnost.reporters.mindmap.model import Folder, MindMap

ROOT_ID = "m:"


@dataclass(frozen=True)
class MindItem:
    """One thing to draw: the project ("root"), a folder ("dir") or a file ("file").

    `angle` is in radians from the centre; `parent` is the id of the node it branches from.
    """

    id: str
    kind: str
    label: str
    x: float
    y: float
    angle: float
    size: float
    parent: Optional[str]
    dir: str = ""
    n: int = 0
    open: bool = False


@dataclass
class MindLayout:
    """The placed items and, for every file, the id it is drawn as (itself or a closed folder)."""

    items: List[MindItem]
    at: Dict[str, str]


class RadialLayout:
    """Places a `MindMap` on rings, each child getting an angle in proportion to its leaves.

    `fit` closes the deepest folders until the map has at most a given number of leaves,
    which keeps a static image readable.
    """

    def __init__(self, mind: MindMap) -> None:
        self.mind = mind
        self.settings = mind.settings

    def place(self, open_: Optional[Dict[str, bool]] = None) -> MindLayout:
        """Lay out the tree with the given folder choices (path -> open)."""
        choices = dict(open_ or {})
        tree = self.mind.tree
        total = self._leaves(tree, 0, choices)
        rings = max(1, self._deepest(tree, 0, choices))
        radius = max(
            self.settings.ring, (total * self.settings.gap) / (2 * math.pi * rings)
        )
        items = [
            MindItem(ROOT_ID, "root", tree.label, 0.0, 0.0, 0.0, 46.0, None),
        ]
        at: Dict[str, str] = {}
        self._place(tree, 0, -math.pi, math.pi, rings, radius, choices, items, at)
        return MindLayout(items, at)

    def fit(self, max_leaves: int) -> Dict[str, bool]:
        """Folder choices that close the deepest open folders until there are few enough leaves.

        Closes one depth level at a time; the top of the tree always stays open.
        """
        choices: Dict[str, bool] = {}
        while self._leaves(self.mind.tree, 0, choices) > max_leaves:
            opened = self.mind.open_folders(choices)
            if not opened:
                break
            deepest = max(depth for _, depth in opened)
            for folder, depth in opened:
                if depth == deepest:
                    choices[folder.path] = False
        return choices

    def _kids(self, folder: Folder) -> List[Union[Folder, str]]:
        """Subfolders by name, then files by path (code-point order, as in the explorer)."""
        dirs: List[Union[Folder, str]] = sorted(
            folder.dirs.values(), key=lambda d: d.name
        )
        return dirs + sorted(folder.files)

    def _leaves(self, folder: Folder, depth: int, choices: Dict[str, bool]) -> int:
        if not self.mind.is_open(folder, depth, choices):
            return 1
        return max(
            1,
            sum(
                1 if isinstance(c, str) else self._leaves(c, depth + 1, choices)
                for c in self._kids(folder)
            ),
        )

    def _deepest(self, folder: Folder, depth: int, choices: Dict[str, bool]) -> int:
        if not self.mind.is_open(folder, depth, choices):
            return depth
        here = depth + (1 if folder.files else 0)
        return max(
            [here]
            + [self._deepest(c, depth + 1, choices) for c in folder.dirs.values()]
        )

    def _place(
        self,
        folder: Folder,
        depth: int,
        a0: float,
        a1: float,
        rings: int,
        radius: float,
        choices: Dict[str, bool],
        items: List[MindItem],
        at: Dict[str, str],
    ) -> None:
        """Place the children of `folder` between angles a0 and a1, recursing into open ones."""
        kids = self._kids(folder)
        sizes = [
            1 if isinstance(c, str) else self._leaves(c, depth + 1, choices)
            for c in kids
        ]
        total = sum(sizes) or 1
        parent = ROOT_ID if depth == 0 else ROOT_ID + folder.path
        angle = a0
        for child, size in zip(kids, sizes):
            span = (a1 - a0) * size / total
            mid = angle + span / 2
            if isinstance(child, str):
                r = rings * radius
                weight = (
                    16.0
                    if child in self.mind.entry
                    else 6 + 3 * math.log2(1 + self.mind.fan_in[child])
                )
                items.append(
                    MindItem(
                        child,
                        "file",
                        child.split("/")[-1],
                        r * math.cos(mid),
                        r * math.sin(mid),
                        mid,
                        weight,
                        parent,
                    )
                )
                at[child] = child
            else:
                opened = self.mind.is_open(child, depth + 1, choices)
                r = (depth + 1 if opened else rings) * radius
                node_id = ROOT_ID + child.path
                items.append(
                    MindItem(
                        node_id,
                        "dir",
                        child.name if opened else f"{child.name} ({child.n})",
                        r * math.cos(mid),
                        r * math.sin(mid),
                        mid,
                        min(32.0, (12 if opened else 10) + 2 * math.sqrt(child.n)),
                        parent,
                        dir=child.path,
                        n=child.n,
                        open=opened,
                    )
                )
                if opened:
                    self._place(
                        child,
                        depth + 1,
                        angle,
                        angle + span,
                        rings,
                        radius,
                        choices,
                        items,
                        at,
                    )
                else:
                    self._hold(child, node_id, at)
            angle += span

    def _hold(self, folder: Folder, holder: str, at: Dict[str, str]) -> None:
        """Every file under a closed folder is drawn as that folder."""
        for path in folder.files:
            at[path] = holder
        for child in folder.dirs.values():
            self._hold(child, holder, at)
