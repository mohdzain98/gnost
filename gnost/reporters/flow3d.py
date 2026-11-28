"""The 3D flow page (`flow-3d.html`): the import graph as folder clusters you can fly through.

Built from the insights JSON (`graph`, `cycles`, `entry_points`), so it can be written by
`gnost onboard --3d` or later from `.gnost/insights.json` by `gnost open flow --3d`. The 3D
library is about 1.4 MB, so it is inlined only into this page, never into flow.html.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Set

from gnost.reporters.diagram_viewer import TEMPLATES_DIR, _fill, _inline, _js_json

LIBRARY = "3d-force-graph.min.js"


class Flow3dData:
    """Turns an insights payload into the nodes and links the 3D page draws.

    Nodes carry their folder, import counts, entry-point flag and circular-import kind;
    links say whether they cross folders and which kind of cycle they close, if any.
    """

    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload

    def build(self) -> Dict[str, Any]:
        """The page's data: {project, nodes, links, cycles}."""
        graph = self.payload.get("graph") or {}
        files: List[str] = list(dict.fromkeys(graph.get("nodes") or []))
        known = set(files)
        edges = [
            e
            for e in graph.get("edges") or []
            if e.get("source") in known and e.get("target") in known
        ]
        cycle_of = self._cycle_kinds()
        entry = {e.get("file") for e in self.payload.get("entry_points") or []}
        outs: Dict[str, Set[str]] = {f: set() for f in files}
        ins: Dict[str, Set[str]] = {f: set() for f in files}
        for e in edges:
            outs[e["source"]].add(e["target"])
            ins[e["target"]].add(e["source"])
        nodes = [
            {
                "id": f,
                "name": f.rsplit("/", 1)[-1],
                "folder": f.rsplit("/", 1)[0] if "/" in f else "",
                "inn": len(ins[f]),
                "out": len(outs[f]),
                "entry": f in entry,
                "cyc": cycle_of.get(f, {}).get("kind", ""),
            }
            for f in files
        ]
        links = [
            {
                "source": e["source"],
                "target": e["target"],
                "cross": self._folder(e["source"]) != self._folder(e["target"]),
                "deferred": bool(e.get("deferred")),
                "cycle": self._shared_cycle(cycle_of, e["source"], e["target"]),
            }
            for e in edges
        ]
        project = (self.payload.get("project") or {}).get("name") or "project"
        cycles = [
            {"kind": c.get("kind", ""), "files": list(c.get("files") or [])}
            for c in self.payload.get("cycles") or []
        ]
        return {"project": project, "nodes": nodes, "links": links, "cycles": cycles}

    @staticmethod
    def _folder(path: str) -> str:
        return path.rsplit("/", 1)[0] if "/" in path else ""

    def _cycle_kinds(self) -> Dict[str, Dict[str, Any]]:
        """For each file in a cycle: that cycle's index and kind (import_time wins)."""
        found: Dict[str, Dict[str, Any]] = {}
        for index, cycle in enumerate(self.payload.get("cycles") or []):
            for path in cycle.get("files") or []:
                current = found.get(path)
                if current is None or current["kind"] != "import_time":
                    found[path] = {"index": index, "kind": cycle.get("kind", "")}
        return found

    @staticmethod
    def _shared_cycle(cycle_of: Dict[str, Dict[str, Any]], a: str, b: str) -> str:
        """The kind of the cycle a link closes, or "" when its files are in different cycles."""
        first, second = cycle_of.get(a), cycle_of.get(b)
        if first and second and first["index"] == second["index"]:
            return str(first["kind"])
        return ""


class Flow3dPage:
    """Renders `flow-3d.html`: the template, the inlined 3D library and the data.

    Names are escaped in the page (they are set as text, and the hover card escapes them).
    """

    TEMPLATE = os.path.join(TEMPLATES_DIR, "flow_3d.html")

    def __init__(self, payload: Dict[str, Any]) -> None:
        self.data = Flow3dData(payload).build()

    def render(self) -> str:
        """The self-contained page; it needs no network."""
        with open(self.TEMPLATE, encoding="utf-8") as handle:
            template = handle.read()
        title = f"{self.data['project']} · 3D flow".replace("<", "&lt;")
        return _fill(
            template,
            {
                "__TITLE__": title,
                "__LIBS__": _inline(LIBRARY),
                "__DATA__": _js_json(self.data),
            },
        )
