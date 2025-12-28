# gnost/core/ranker.py

from dataclasses import dataclass
from typing import Dict, List

from gnost.core.graph import DependencyGraph
from gnost.core.flow import FlowResult


@dataclass
class Hotspot:
    file: str
    score: float
    fan_in: int
    fan_out: int
    path_frequency: int
    depth: int
    layer: str


class HotspotRanker:
    """
    Ranks files by importance (hotspots).
    """

    def __init__(
        self,
        graph: DependencyGraph,
        flow: FlowResult,
    ):
        self.graph = graph
        self.flow = flow

    # -------------------------
    # Public API
    # -------------------------

    def rank(self, top: int | None = None) -> List[Hotspot]:
        stats = self._collect_stats()
        hotspots = []

        for file, data in stats.items():
            score = self._score(data)
            hotspots.append(
                Hotspot(
                    file=file,
                    score=score,
                    fan_in=data["fan_in"],
                    fan_out=data["fan_out"],
                    path_frequency=data["path_freq"],
                    depth=data["depth"],
                    layer=data["layer"],
                )
            )

        hotspots.sort(key=lambda h: h.score, reverse=True)

        if top:
            return hotspots[:top]
        return hotspots

    # -------------------------
    # Internals
    # -------------------------

    def _collect_stats(self) -> Dict[str, dict]:
        stats: Dict[str, dict] = {}

        # Init nodes
        for node in self.graph.all_nodes():
            stats[node] = {
                "fan_in": self.graph.fan_in(node),
                "fan_out": self.graph.fan_out(node),
                "path_freq": 0,
                "depth": 999,
                "layer": self._layer_of(node),
            }

        # Count path frequency + depth
        for path in self.flow.paths:
            for depth, file in enumerate(path.path):
                stats[file]["path_freq"] += 1
                stats[file]["depth"] = min(stats[file]["depth"], depth)

        return stats

    def _layer_of(self, file: str) -> str:
        for layer, files in self.flow.layers.items():
            if file in files:
                return layer
        return "unknown"

    # -------------------------
    # Scoring
    # -------------------------

    def _score(self, d: dict) -> float:
        score = 0.0

        # Core importance
        score += d["fan_in"] * 3
        score += d["path_freq"] * 2

        # Layer weight
        if d["layer"] == "entry":
            score += 5
        elif d["layer"] == "core":
            score += 10
        elif d["layer"] == "leaf":
            score += 1

        # Depth penalty (deeper = less important)
        score -= d["depth"] * 0.5

        return round(score, 2)
