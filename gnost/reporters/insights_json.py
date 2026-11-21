"""Machine-readable export of the onboarding insights.

The payload is versioned (`SCHEMA_VERSION`) and described by
`gnost/schemas/insights.schema.json`. Paths are relative to the scanned root and
use forward slashes, so the file is portable between machines and CI runs.

Versioning rule: adding a field bumps the minor version; renaming, removing or
changing the meaning of a field bumps the major version. Consumers should ignore
fields they do not know.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from gnost import __version__
from gnost.core.cycles import IMPORT_TIME
from gnost.core.flow import FlowResult
from gnost.core.graph import DependencyGraph
from gnost.core.ranker import HotspotRanker
from gnost.models.insights import OnboardingInsights
from gnost.scanner.models import ScanResult

SCHEMA_VERSION = "1.4"
SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "schemas", "insights.schema.json"
)
HOTSPOT_LIMIT = 20
CHANGE_HISTORY_LIMIT = 50


def build_payload(
    scan: ScanResult,
    flow: FlowResult,
    graph: DependencyGraph,
    insights: OnboardingInsights,
    flows: Optional[list] = None,
    call_graph: Any = None,
    changes: Any = None,
    risks: Any = None,
) -> Dict[str, Any]:
    root = scan.root

    def rel(path: str) -> str:
        return os.path.relpath(path, root).replace(os.sep, "/")

    def rels(paths) -> List[str]:
        return sorted(rel(p) for p in paths)

    hotspots = HotspotRanker(graph=graph, flow=flow).rank(top=HOTSPOT_LIMIT)
    edges = sorted(
        (rel(src), rel(dst), (src, dst) in graph.deferred_edges)
        for src in graph.all_nodes()
        for dst in graph.dependencies_of(src)
    )
    import_time = sum(1 for c in insights.cycles if c.kind == IMPORT_TIME)

    return {
        "schema_version": SCHEMA_VERSION,
        "generator": {"name": "gnost", "version": __version__},
        "project": {
            "name": os.path.basename(root.rstrip(os.sep)),
            "languages": dict(sorted(scan.languages.items())),
            "framework": scan.framework,
            "files": len(scan.files),
        },
        "entry_points": [
            {
                "file": rel(ep.file),
                "reason": ep.reason,
                "priority": "primary" if ep.priority == ep.PRIMARY else "secondary",
            }
            for ep in scan.entry_points
        ],
        "routes": [
            {
                "method": r.method,
                "path": r.path,
                "handler": r.handler,
                "file": rel(r.file),
                "line": r.line,
                "framework": r.framework,
            }
            for r in scan.routes
        ],
        "change_history": _change_history(changes),
        "risk": _risk(risks),
        "flows": [_flow(f, rel) for f in (flows or [])],
        "callgraph": {
            "functions": len(call_graph.functions) if call_graph else 0,
            "edges": call_graph.edge_count if call_graph else 0,
            "unparsed_files": rels(call_graph.unparsed) if call_graph else [],
        },
        "layers": {
            name: rels(flow.layers.get(name, ())) for name in ("entry", "core", "leaf")
        },
        "first_files": [
            {"path": rel(f.path), "reason": f.reason, "score": f.score}
            for f in insights.first_files
        ],
        "hotspots": [
            {
                "file": rel(h.file),
                "score": h.score,
                "fan_in": h.fan_in,
                "fan_out": h.fan_out,
                "depth": h.depth,
                "layer": h.layer,
            }
            for h in hotspots
        ],
        "caution_areas": [
            {
                "path": rel(c.path),
                "category": c.category.value,
                "severity": c.severity,
                "description": c.description,
                "metrics": dict(c.metrics),
                "score": c.score,
                "partial": c.partial,
                "factors": [
                    {
                        "name": f.name,
                        "value": f.value,
                        "contribution": f.contribution,
                        "estimated": f.estimated,
                    }
                    for f in c.factors
                ],
            }
            for c in insights.caution_areas
        ],
        "cycles": [
            {
                "kind": c.kind,
                "files": rels(c.files),
                "example": [rel(f) for f in c.example],
            }
            for c in insights.cycles
        ],
        "graph": {
            "nodes": rels(graph.all_nodes()),
            "edges": [{"source": s, "target": t, "deferred": d} for s, t, d in edges],
        },
        "stats": {
            "files": len(scan.files),
            "entry_points": len(scan.entry_points),
            "routes": len(scan.routes),
            "reachable_files": len(flow.depths),
            "edges": len(edges),
            "cycles_import_time": import_time,
            "cycles_deferred": len(insights.cycles) - import_time,
        },
    }


def _flow(flow, rel) -> Dict[str, Any]:
    def node(n) -> Dict[str, Any]:
        return {
            "function": n.function,
            "file": rel(n.file),
            "line": n.line,
            "repeat": n.repeat,
            "calls": [node(c) for c in n.calls],
        }

    return {
        "kind": flow.kind,
        "label": flow.label,
        "size": flow.size,
        "truncated": flow.truncated,
        "entry": node(flow.entry),
    }


def write_payload(payload: Dict[str, Any], path: str) -> str:
    """Write the payload atomically; returns the path."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    return path


def load_schema() -> Optional[Dict[str, Any]]:
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return None


def _change_history(changes: Any) -> Dict[str, Any]:
    """Change hotspots from git history (paths relative to the scanned folder)."""
    if changes is None or not changes.history.available:
        history = changes.history if changes is not None else None
        return {
            "available": False,
            "reason": history.reason if history else "not collected",
            "window_days": history.window_days if history else 0,
            "commits_analyzed": 0,
            "files": [],
        }
    return {
        "available": True,
        "reason": None,
        "window_days": changes.history.window_days,
        "commits_analyzed": changes.history.commits,
        "files": [
            {
                "path": h.change.path,
                "score": h.score,
                "commits": h.change.commits,
                "authors": h.change.author_count,
                "recent_commits": h.change.recent_commits,
                "lines_added": h.change.added,
                "lines_removed": h.change.removed,
                "last_changed": _date(h.change.last_changed),
            }
            for h in changes.hotspots[:CHANGE_HISTORY_LIMIT]
        ],
    }


def _date(stamp: int) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(stamp, tz=timezone.utc).strftime("%Y-%m-%d")


def _risk(risks: Any) -> Dict[str, Any]:
    """Files that are fragile to change and changing often (caution score x change activity)."""
    items = risks.items[: risks.settings.limit] if risks is not None else []
    return {
        "threshold": risks.settings.threshold if risks is not None else 0,
        "files": [
            {
                "path": i.path,
                "risk": i.risk,
                "structural_score": i.structural,
                "change_score": i.churn,
                "commits": i.commits,
                "authors": i.authors,
                "recent_commits": i.recent_commits,
                "reasons": list(i.reasons),
            }
            for i in items
        ],
    }
