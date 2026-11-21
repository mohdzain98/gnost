from collections import Counter
from typing import List, Optional

from gnost.core.flow import FlowResult
from gnost.core.caution import CautionScore, CautionSettings, rank_files
from gnost.core.cycles import IMPORT_TIME, Cycle
from gnost.core.graph import DependencyGraph
from gnost.scanner.models import ScanResult

from gnost.models.insights import (
    OnboardingInsights,
    FileInsight,
    ArchitectureLayers,
    CautionFactor,
    CautionInsight,
    CautionType,
    CycleInsight,
)


class InsightBuilder:
    """
    Builds high-level onboarding insights from scan + flow + dependency graph.
    """

    def __init__(
        self,
        scan: ScanResult,
        flow: FlowResult,
        graph: DependencyGraph,
        caution: Optional[CautionSettings] = None,
    ) -> None:
        self.caution = caution or CautionSettings()
        self.caution_scores: List[CautionScore] = []
        self.scan = scan
        self.flow = flow
        self.graph = graph

    def build(self) -> OnboardingInsights:
        return OnboardingInsights(
            first_files=self._build_first_files(),
            layers=self._build_architecture_layers(),
            caution_areas=self._build_caution_areas(),
            cycles=self._build_cycles(),
        )

    def _build_first_files(self) -> List[FileInsight]:
        """
        Identify the most important files to read first.
        """
        scores = Counter()

        # 1. Entry points are highest priority
        for ep in self.flow.entry_points:
            scores[ep.file] += 5.0

        # 2. Files appearing early in execution paths
        for path in self.flow.paths:
            for idx, file in enumerate(path.path[:3]):  # only first 3 matter
                scores[file] += max(3 - idx, 1)

        # 3. High fan-out nodes (control many others)
        for node, deps in self.graph.adjacency.items():
            scores[node] += len(deps) * 0.5

        insights: List[FileInsight] = []

        for file, score in scores.most_common(10):
            insights.append(
                FileInsight(
                    path=file,
                    score=round(score, 2),
                    reason=self._first_file_reason(file),
                )
            )

        return insights

    def _first_file_reason(self, file: str) -> str:
        """Provide reason for first read files"""
        if file in [ep.file for ep in self.flow.entry_points]:
            return "Primary entry point into the application"

        if file in self.flow.layers.get("core", []):
            return "Core logic file referenced by multiple execution paths"

        return "Frequently involved in execution flow"

    def _build_architecture_layers(self) -> ArchitectureLayers:
        return ArchitectureLayers(
            entry=sorted(self.flow.layers.get("entry", [])),
            core=sorted(self.flow.layers.get("core", [])),
            leaf=sorted(self.flow.layers.get("leaf", [])),
        )

    _CATEGORY = {
        "cycles": CautionType.CIRCULAR_DEPENDENCY,
        "size": CautionType.LARGE_FILE,
        "impact": CautionType.HIGH_IMPACT,
        "coupling": CautionType.TIGHT_COUPLING,
        "complexity": CautionType.HIGH_COMPLEXITY,
        "observability": CautionType.LOW_OBSERVABILITY,
    }

    def _build_caution_areas(self) -> List[CautionInsight]:
        """Files that are risky to change, from the rule-based caution score."""
        ranked = rank_files(self.scan, self.graph, self.flow.cycles, self.caution)
        self.caution_scores = ranked  # every file's score, for the risk calculation
        reported = [s for s in ranked if s.score >= self.caution.threshold]
        return [self._to_insight(s) for s in reported[: self.caution.limit]]

    def _to_insight(self, scored: CautionScore) -> CautionInsight:
        top = scored.factors[0]
        return CautionInsight(
            path=scored.path,
            category=self._CATEGORY[top.name],
            severity=scored.severity,
            description=self._describe(scored),
            metrics={f.name: f.value for f in scored.factors if f.name != "cycles"},
            score=scored.score,
            partial=scored.partial,
            factors=[
                CautionFactor(f.name, f.value, f.contribution, f.estimated)
                for f in scored.factors
            ],
        )

    def _describe(self, scored: CautionScore) -> str:
        cycle_kind = {
            c.kind for c in self.flow.cycles for f in c.files if f == scored.path
        }
        phrases = []
        for f in scored.factors[:3]:
            if f.name == "cycles":
                phrases.append(
                    "part of an import-time circular dependency"
                    if IMPORT_TIME in cycle_kind
                    else "part of a deferred circular dependency"
                )
            elif f.name == "size":
                phrases.append(f"{int(f.value):,} lines of code")
            elif f.name == "impact":
                phrases.append(f"imported by {int(f.value)} files")
            elif f.name == "coupling":
                phrases.append(f"imports {int(f.value)} project files")
            elif f.name == "complexity":
                phrases.append(
                    f"about {int(f.value)} branches (estimated)"
                    if f.estimated
                    else f"a function with complexity {int(f.value)}"
                )
            elif f.name == "observability":
                phrases.append(
                    f"{int(f.value)} except blocks that neither log nor re-raise"
                )
        text = "; ".join(phrases)
        return text[:1].upper() + text[1:] if text else "Risky to change"

    def _cycles(self) -> List[Cycle]:
        return self.flow.cycles

    def _build_cycles(self) -> List[CycleInsight]:
        return [
            CycleInsight(files=c.files, example=c.example, kind=c.kind)
            for c in self._cycles()
        ]
