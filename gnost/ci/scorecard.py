"""The scores `gnost analyze` prints: one per analyzer and the final score out of 10.

`ScoreCard` is built from a finished report. The gate, the terminal table and the JSON/HTML
reports all read it, so the number you see is the number a CI threshold compares against.
Scores come from finding density (see `ScoreCard.density_to_score`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from gnost.analysis.core.models import ConsolidatedReport, SeverityLevel, UnifiedFinding


@dataclass(frozen=True)
class AnalyzerScore:
    """One analyzer's score (0 to 10, higher is better) with its finding counts."""

    name: str
    score: float
    findings: int
    high: int
    medium: int
    low: int


class ScoreCard:
    """Per-analyzer scores plus the final score of a report.

    Scores severity-weighted findings per 1,000 analyzed lines on a log curve, so both the
    number of findings and the project size count. The 0.7 "average" formula was removed in 0.8.0.
    """

    DENSITY = "density"

    SEVERITY_WEIGHTS: Dict[SeverityLevel, float] = {
        SeverityLevel.CRITICAL: 1.0,
        SeverityLevel.HIGH: 0.6,
        SeverityLevel.MEDIUM: 0.3,
        SeverityLevel.LOW: 0.1,
        SeverityLevel.INFO: 0.05,
    }
    UNKNOWN_WEIGHT = 0.2
    CURVE_SLOPE = 2.0  # score = 10 - CURVE_SLOPE * ln(1 + density)
    MIN_KLOC = 1.0  # smaller projects count as 1,000 lines, so one finding in 20 lines is not 0/10

    def __init__(
        self,
        analyzers: List[AnalyzerScore],
        final_score: float,
        method: str = DENSITY,
        lines: Optional[int] = None,
        density: Optional[float] = None,
    ) -> None:
        self.analyzers = analyzers
        self.final_score = final_score
        self.method = method
        self.lines = lines
        self.density = density

    @classmethod
    def from_report(cls, report: ConsolidatedReport) -> "ScoreCard":
        """Score every analyzer that ran and the report as a whole.

        Density uses `summary["analyzed_lines"]`; without it the project counts as 1,000 lines.
        """
        summary: Any = report.summary if isinstance(report.summary, dict) else {}
        lines = summary.get("analyzed_lines")
        lines = int(lines) if isinstance(lines, (int, float)) else None
        by_analyzer: Dict[str, List[UnifiedFinding]] = {}
        for finding in report.findings:
            by_analyzer.setdefault(finding.source_analyzer, []).append(finding)
        analyzers = []
        capped_total = 0.0
        for metric in sorted(report.analysis_metrics, key=lambda m: m.analyzer_name):
            found = by_analyzer.get(metric.analyzer_name, [])
            counts = cls.severity_counts(found)
            capped = cls.capped_weight(metric.capped_by_severity)
            capped_total += capped
            analyzers.append(
                AnalyzerScore(
                    name=metric.analyzer_name,
                    score=cls.score(found, lines, capped),
                    findings=len(found),
                    high=counts["high"],
                    medium=counts["medium"],
                    low=counts["low"],
                )
            )
        density = cls.density(report.findings, lines, capped_total)
        return cls(
            analyzers,
            cls.density_to_score(density),
            cls.DENSITY,
            lines,
            round(density, 3),
        )

    @classmethod
    def score(
        cls,
        findings: List[UnifiedFinding],
        lines: Optional[int],
        extra_weight: float = 0.0,
    ) -> float:
        """The 0-10 score of a group of findings, from their density.

        `extra_weight` is the weight of findings not in the list (left out by max_findings).
        """
        return cls.density_to_score(cls.density(findings, lines, extra_weight))

    @classmethod
    def density(
        cls,
        findings: Iterable[UnifiedFinding],
        lines: Optional[int],
        extra_weight: float = 0.0,
    ) -> float:
        """Severity-weighted findings per 1,000 analyzed lines (at least 1,000 lines assumed)."""
        weight = extra_weight + sum(
            cls.SEVERITY_WEIGHTS.get(f.severity, cls.UNKNOWN_WEIGHT) for f in findings
        )
        return weight / max((lines or 0) / 1000.0, cls.MIN_KLOC)

    @classmethod
    def capped_weight(cls, by_severity: Dict[str, int]) -> float:
        """Weight of the findings `max_findings` left out, from their count per severity."""
        by_value = {level.value: w for level, w in cls.SEVERITY_WEIGHTS.items()}
        return sum(
            by_value.get(str(sev).lower(), cls.UNKNOWN_WEIGHT) * int(count)
            for sev, count in (by_severity or {}).items()
        )

    @classmethod
    def density_to_score(cls, density: float) -> float:
        """10 - 2 * ln(1 + density), floored at 0: no findings is 10, density 1 is 8.61, 4 is 6.78."""
        return round(
            max(0.0, 10.0 - cls.CURVE_SLOPE * math.log1p(max(0.0, density))), 2
        )

    @staticmethod
    def count_lines(files: Iterable[str]) -> int:
        """Non-blank lines in the given files; unreadable files count as 0."""
        total = 0
        for path in files:
            try:
                with open(path, encoding="utf-8", errors="ignore") as handle:
                    total += sum(1 for line in handle if line.strip())
            except OSError:
                continue
        return total

    def to_dict(self) -> Dict[str, Any]:
        """The scores for the JSON report (`summary.score`), as the terminal shows them."""
        return {
            "method": self.method,
            "final_score": self.final_score,
            "analyzed_lines": self.lines,
            "density": self.density,
            "analyzers": {a.name: a.score for a in self.analyzers},
        }

    @staticmethod
    def severity_counts(findings: List[UnifiedFinding]) -> Dict[str, int]:
        """Counts of high (critical included), medium, low and info findings."""
        counts = {"high": 0, "medium": 0, "low": 0, "info": 0}
        for finding in findings:
            name = str(finding.severity).split(".")[-1].lower()
            counts[
                "high" if name == "critical" else name if name in counts else "info"
            ] += 1
        return counts

    @staticmethod
    def style(score: float) -> str:
        """The terminal colour for a score: green from 8, yellow from 6, else red."""
        return "green" if score >= 8.0 else "yellow" if score >= 6.0 else "red"
