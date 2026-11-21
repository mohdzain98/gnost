"""The scores `gnost analyze` prints: one per analyzer and the final score out of 10.

`ScoreCard` is built from a finished report. The gate and the terminal table both read it,
so the number you see is the number a CI threshold compares against.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

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
    """Per-analyzer scores plus the final score of a report."""

    SEVERITY_WEIGHTS: Dict[SeverityLevel, float] = {
        SeverityLevel.CRITICAL: 1.0,
        SeverityLevel.HIGH: 0.6,
        SeverityLevel.MEDIUM: 0.3,
        SeverityLevel.LOW: 0.1,
        SeverityLevel.INFO: 0.05,
    }

    def __init__(self, analyzers: List[AnalyzerScore], final_score: float) -> None:
        self.analyzers = analyzers
        self.final_score = final_score

    @classmethod
    def from_report(cls, report: ConsolidatedReport) -> "ScoreCard":
        """Score every analyzer that ran, and take the final score from the report summary."""
        by_analyzer: Dict[str, List[UnifiedFinding]] = {}
        for finding in report.findings:
            by_analyzer.setdefault(finding.source_analyzer, []).append(finding)
        analyzers = []
        for metric in sorted(report.analysis_metrics, key=lambda m: m.analyzer_name):
            found = by_analyzer.get(metric.analyzer_name, [])
            counts = cls.severity_counts(found)
            analyzers.append(
                AnalyzerScore(
                    name=metric.analyzer_name,
                    score=cls.risk_to_score(cls.analyzer_risk(found)),
                    findings=len(found),
                    high=counts["high"],
                    medium=counts["medium"],
                    low=counts["low"],
                )
            )
        summary: Any = report.summary
        risk = summary.get("risk_score", 0.0) if isinstance(summary, dict) else 0.0
        return cls(analyzers, cls.risk_to_score(risk))

    @staticmethod
    def risk_to_score(risk_score: float) -> float:
        """Turn a risk percentage (0 to 100, lower is better) into a score out of 10."""
        clamped = max(0.0, min(100.0, risk_score))
        return round(10.0 * (1.0 - clamped / 100.0), 2)

    @classmethod
    def analyzer_risk(cls, findings: List[UnifiedFinding]) -> float:
        """Risk percentage of one analyzer's findings, weighted by severity."""
        if not findings:
            return 0.0
        total = sum(cls.SEVERITY_WEIGHTS.get(f.severity, 0.2) for f in findings)
        worst = max(cls.SEVERITY_WEIGHTS.values())
        return round((total / (len(findings) * worst)) * 100.0, 2)

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
