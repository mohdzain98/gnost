"""Risk: files that are fragile to change AND being changed (caution score x change activity).

`RiskCalculator` combines the structural caution score of each file with its change-hotspot
score from git history. A fragile file nobody touches, or a busy file that is simple, is not
listed: only the ones that are both. Shown by `gnost onboard` in ONBOARD.md and insights.json.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

from gnost.core.caution import CautionScore
from gnost.vcs.history import Hotspot

# Plain words for the caution signals, used where a reason is shown.
REASON_WORDS = {
    "cycles": "circular import",
    "size": "large file",
    "impact": "many files depend on it",
    "coupling": "imports many files",
    "complexity": "complex code",
    "observability": "errors swallowed silently",
}

DEFAULT_THRESHOLD = 20.0
DEFAULT_LIMIT = 10
DEFAULT_CHURN_WEIGHT = 1.0


@dataclass(frozen=True)
class RiskSettings:
    """The [risk] settings: lowest risk listed, how many to list, and how much churn counts."""

    threshold: float = DEFAULT_THRESHOLD
    limit: int = DEFAULT_LIMIT
    churn_weight: float = DEFAULT_CHURN_WEIGHT  # 1 = pure product, 0 = churn ignored


@dataclass
class RiskItem:
    """One file's risk with the two scores it comes from, so the number can be explained."""

    path: str  # relative to the scanned folder
    risk: float  # 0..100
    structural: float  # caution score, 0..100
    churn: float  # change-hotspot score, 0..100
    commits: int
    authors: int
    recent_commits: int
    reasons: List[str] = field(default_factory=list)  # strongest caution factors

    @property
    def why(self) -> str:
        """The reasons in plain words, for example 'large file, complex code'."""
        return ", ".join(REASON_WORDS.get(r, r) for r in self.reasons)


@dataclass
class RiskReport:
    """The ranked risky-and-changing files and the settings that produced them."""

    items: List[RiskItem]
    settings: RiskSettings


class RiskCalculator:
    """risk = structural x (1 - w + w x churn / 100), kept when it reaches the threshold."""

    REASONS_SHOWN = 2

    def __init__(self, settings: RiskSettings) -> None:
        self.settings = settings

    def rank(
        self, structural: Sequence[CautionScore], hotspots: Sequence[Hotspot], root: str
    ) -> List[RiskItem]:
        """Risky-and-changing files, highest risk first; ties broken by path."""
        churn: Dict[str, Hotspot] = {h.change.path: h for h in hotspots}
        items: List[RiskItem] = []
        for score in structural:
            rel = os.path.relpath(score.path, root).replace(os.sep, "/")
            hotspot = churn.get(rel)
            if hotspot is None:
                continue  # not changing, so not "changing and fragile"
            risk = round(score.score * self._churn_factor(hotspot.score), 1)
            if risk < self.settings.threshold:
                continue
            change = hotspot.change
            items.append(
                RiskItem(
                    path=rel,
                    risk=risk,
                    structural=score.score,
                    churn=hotspot.score,
                    commits=change.commits,
                    authors=change.author_count,
                    recent_commits=change.recent_commits,
                    reasons=[f.name for f in score.factors[: self.REASONS_SHOWN]],
                )
            )
        items.sort(key=lambda i: (-i.risk, i.path))
        return items

    def report(
        self, structural: Sequence[CautionScore], hotspots: Sequence[Hotspot], root: str
    ) -> RiskReport:
        """rank() together with the settings, ready for the reporters."""
        return RiskReport(self.rank(structural, hotspots, root), self.settings)

    def _churn_factor(self, churn_score: float) -> float:
        """How much of the structural score survives, from 1 - weight (no churn) to 1."""
        weight = self.settings.churn_weight
        return 1 - weight + weight * churn_score / 100
