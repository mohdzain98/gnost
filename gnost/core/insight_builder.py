from collections import Counter, defaultdict
from typing import List

from gnost.core.flow import FlowResult
from gnost.core.graph import DependencyGraph
from gnost.scanner.models import ScanResult

from gnost.models.insights import (
    OnboardingInsights,
    FileInsight,
    ArchitectureLayers,
    CautionInsight,
    CautionType,
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
    ):
        self.scan = scan
        self.flow = flow
        self.graph = graph

    def build(self) -> OnboardingInsights:
        return OnboardingInsights(
            first_files=self._build_first_files(),
            layers=self._build_architecture_layers(),
            caution_areas=self._build_caution_areas(),
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

    def _build_caution_areas(self) -> List[CautionInsight]:
        """Build caution roots"""
        cautions: List[CautionInsight] = []

        # Fan-in analysis
        fan_in = defaultdict(int)
        for src, deps in self.graph.adjacency.items():
            for dst in deps:
                fan_in[dst] += 1

        for file, count in fan_in.items():
            if count >= 5:
                cautions.append(
                    CautionInsight(
                        path=file,
                        category=CautionType.HIGH_IMPACT,
                        severity=min(5, count),
                        description="Many files depend on this module",
                        metrics={"fan_in": count},
                    )
                )

        # -------------------------
        # High import complexity (proxy for large/complex files)
        # -------------------------
        for fi in self.scan.files:
            import_count = len(fi.imports)
            if import_count >= 10:
                cautions.append(
                    CautionInsight(
                        path=fi.path,
                        category=CautionType.TIGHT_COUPLING,
                        severity=min(5, import_count // 3),
                        description="File has a high number of dependencies",
                        metrics={"imports": import_count},
                    )
                )

        # Circular dependencies - yet to be added in 0.3.0

        return cautions
