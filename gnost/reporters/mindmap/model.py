"""The mind map's data: the folder tree of a project and the files it highlights.

Mirrors `mindModel` in the flow explorer (templates/graph_viewer.html), so the README image and
the interactive map show the same tree. `MindMapSettings` holds the rules both sides share; the
explorer receives them through the page's META, so they are defined only here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class MindMapSettings:
    """Rules shared by the explorer and the README image.

    Folders deeper than `depth`, or with more than `big` files directly inside, start closed; `gap` and `ring`
    set the spacing of the radial layout; `top_share`/`top_min` size the "most imported" set.
    """

    depth: int = 2
    big: int = 40
    gap: float = 15.0
    ring: float = 150.0
    top_share: float = 0.03
    top_min: int = 5

    def to_meta(self) -> Dict[str, float]:
        """The settings as the explorer reads them (`META.mind`)."""
        return {
            "depth": self.depth,
            "big": self.big,
            "gap": self.gap,
            "ring": self.ring,
            "topShare": self.top_share,
            "topMin": self.top_min,
        }


@dataclass
class Folder:
    """One folder in the tree, with its subfolders and its files (paths).

    `n` is the number of files under it, at any depth; `label` is set on the tree's top only.
    """

    name: str
    path: str
    dirs: Dict[str, "Folder"] = field(default_factory=dict)
    files: List[str] = field(default_factory=list)
    n: int = 0
    label: str = ""

    def count(self) -> int:
        """Set and return `n` for this folder and every folder under it."""
        self.n = len(self.files) + sum(child.count() for child in self.dirs.values())
        return self.n


class MindMap:
    """The folder tree of a project, its entry points and its most imported files.

    Files are forward-slash paths relative to the project root. A chain of single folders at
    the top (`src/app/`) is skipped, and its path is shown under the project name instead.
    """

    def __init__(
        self,
        files: Iterable[str],
        edges: Iterable[Tuple[str, str]],
        entry: Iterable[str] = (),
        project: str = "project",
        settings: Optional[MindMapSettings] = None,
    ) -> None:
        self.settings = settings or MindMapSettings()
        self.files = list(dict.fromkeys(files))
        known = set(self.files)
        importers: Dict[str, Set[str]] = {f: set() for f in self.files}
        imports: Dict[str, Set[str]] = {f: set() for f in self.files}
        for source, target in edges:
            if target in importers and source in known:
                importers[target].add(source)
                imports[source].add(target)
        self.imports = {f: sorted(targets) for f, targets in imports.items()}
        self.fan_in = {f: len(importers[f]) for f in self.files}
        self.entry = {f for f in entry if f in known}
        self.top = self._most_imported()
        self.tree = self._tree(project)

    def is_open(self, folder: Folder, depth: int, open_: Dict[str, bool]) -> bool:
        """Whether a folder is drawn open: a choice in `open_` wins, else the default rules.

        The top of the tree (depth 0) is always open.
        """
        if depth == 0:
            return True
        if folder.path in open_:
            return open_[folder.path]
        return depth <= self.settings.depth and len(folder.files) <= self.settings.big

    def open_folders(self, open_: Dict[str, bool]) -> List[Tuple[Folder, int]]:
        """Every open folder below the top, with its depth, in tree order."""
        found: List[Tuple[Folder, int]] = []

        def walk(folder: Folder, depth: int) -> None:
            for child in folder.dirs.values():
                if self.is_open(child, depth + 1, open_):
                    found.append((child, depth + 1))
                    walk(child, depth + 1)

        walk(self.tree, 0)
        return found

    def _most_imported(self) -> Set[str]:
        """Files imported by more than one file (entry points excluded), the most first."""
        ranked = sorted(
            (f for f in self.files if self.fan_in[f] > 1 and f not in self.entry),
            key=lambda f: (-self.fan_in[f], f),
        )
        limit = max(
            self.settings.top_min,
            math.ceil(len(self.files) * self.settings.top_share),
        )
        return set(ranked[:limit])

    def _tree(self, project: str) -> Folder:
        """The folder tree, starting below a shared prefix of single folders."""
        root = Folder(name="", path="")
        for path in self.files:
            parts = path.split("/")
            current = root
            for k, part in enumerate(parts[:-1]):
                if part not in current.dirs:
                    current.dirs[part] = Folder(part, "/".join(parts[: k + 1]))
                current = current.dirs[part]
            current.files.append(path)
        prefix: List[str] = []
        top = root
        while not top.files and len(top.dirs) == 1:
            top = next(iter(top.dirs.values()))
            prefix.append(top.name)
        top.count()
        shared = "/".join(prefix)
        top.label = project + ("\n" + shared if shared and shared != project else "")
        return top
