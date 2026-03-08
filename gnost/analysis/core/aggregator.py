"""
Result aggregation logic for consolidating findings from multiple analyzers.
"""

from typing import List, Dict, Any, Set
from collections import defaultdict, Counter
from datetime import datetime

from gnost.analysis.core.models import (
    UnifiedFinding,
    ConsolidatedReport,
    SeverityLevel,
    FindingCategory,
    CodeLocation,
    ComplexityLevel,
)
from gnost.utils.logger import AppLogger

logger = AppLogger.get_logger(__name__)


class ResultAggregator:
    """
    Aggregates and consolidates findings from multiple analysis modules.
    Handles deduplication, cross-referencing, and summary generation.
    """

    def __init__(self):
        self.similarity_threshold = 0.8
        self.location_tolerance = 5  # lines

    async def aggregate_findings(
        self, findings: List[UnifiedFinding]
    ) -> List[UnifiedFinding]:
        """
        Aggregate findings from multiple analyzers.

        Args:
            findings: List of findings from all analyzers

        Returns:
            Deduplicated and enriched list of findings
        """
        logger.info(f"Aggregating {len(findings)} findings")
        # rprint(findings)
        # Step 1: Deduplicate similar findings
        deduplicated = await self._deduplicate_findings(findings)
        logger.debug(f"After deduplication: {len(deduplicated)} findings")
        # Step 2: Cross-reference related findings
        cross_referenced = await self._cross_reference_findings(deduplicated)
        logger.debug(f"After cross-referencing: {len(cross_referenced)} findings")

        # Step 3: Enrich findings with additional context
        enriched = await self._enrich_findings(cross_referenced)
        logger.debug(f"After enrichment: {len(enriched)} findings")

        # Step 4: Sort by priority
        sorted_findings = self._sort_by_priority(enriched)

        logger.info(f"Final aggregated findings: {len(sorted_findings)}")
        return sorted_findings

    async def generate_summary(self, report: ConsolidatedReport) -> Dict[str, Any]:
        """
        Generate comprehensive summary of analysis results.

        Args:
            report: Consolidated report to summarize

        Returns:
            Summary dictionary with metrics and insights
        """
        findings = report.findings
        metrics = report.analysis_metrics

        summary = {
            "timestamp": datetime.now().isoformat(),
            "target_path": report.target_path,
            "analysis_duration": report.total_execution_time,
            # Basic counts
            "total_findings": len(findings),
            "total_analyzers": len(metrics),
            "successful_analyzers": len([m for m in metrics if m.success]),
            "failed_analyzers": len([m for m in metrics if not m.success]),
            # Severity breakdown
            "severity_breakdown": self._get_severity_breakdown(findings),
            # Category breakdown
            "category_breakdown": self._get_category_breakdown(findings),
            # Risk assessment
            "risk_score": self._calculate_risk_score(findings),
            "risk_level": self._determine_risk_level(findings),
            # File analysis
            "files_with_issues": len(self._get_unique_files(findings)),
            "top_problematic_files": self._get_top_files_by_issues(findings, limit=5),
            # Remediation insights
            "remediation_complexity": self._get_remediation_breakdown(findings),
            "quick_wins": len(
                [
                    f
                    for f in findings
                    if f.remediation_complexity == ComplexityLevel.TRIVIAL
                ]
            ),
            # Compliance
            "compliance_issues": self._get_compliance_issues(findings),
            # Analyzer performance
            "analyzer_performance": self._get_analyzer_performance(metrics),
            # Trends (if historical data available)
            "trend_analysis": self._generate_trend_analysis(report),
        }

        return summary

    async def _deduplicate_findings(
        self, findings: List[UnifiedFinding]
    ) -> List[UnifiedFinding]:
        """Remove duplicate findings using multiple similarity checks."""
        if not findings:
            return findings

        # Group findings by file for efficiency
        file_groups = defaultdict(list)
        for finding in findings:
            file_groups[finding.location.file_path].append(finding)

        deduplicated = []

        for file_path, file_findings in file_groups.items():
            # Sort by line number for efficient comparison
            file_findings.sort(key=lambda f: f.location.line_number or 0)

            # Use greedy approach to find non-duplicate findings
            unique_findings = []
            for finding in file_findings:
                is_duplicate = False

                for unique_finding in unique_findings:
                    if self._are_findings_similar(finding, unique_finding):
                        # Merge duplicate finding information
                        self._merge_findings(unique_finding, finding)
                        is_duplicate = True
                        break

                if not is_duplicate:
                    unique_findings.append(finding)

            deduplicated.extend(unique_findings)

        return deduplicated

    def _normalize_snippet(self, s: str) -> str:
        return " ".join(s.split()).lower() if s else ""

    def _extra(self, f, key, default=None):
        extra = getattr(f, "extra_data", None)
        return extra.get(key, default) if isinstance(extra, dict) else default

    def _same_snippet(self, f1, f2) -> bool:
        s1 = getattr(f1, "code_snippet", None)
        s2 = getattr(f2, "code_snippet", None)
        if s1 is None or s2 is None:
            return False  # if either (or both) is None ⇒ not a match
        return self._normalize_snippet(s1) == self._normalize_snippet(s2)

    def _are_findings_similar(
        self, finding1: UnifiedFinding, finding2: UnifiedFinding
    ) -> bool:
        """Check if two findings are similar enough to be considered duplicates."""
        # Different files - not duplicates
        if finding1.location.file_path != finding2.location.file_path:
            return False
        # rprint(finding1)
        # 🚫 New: don't merge if they were triggered by different regex/AST patterns
        p1 = self._extra(finding1, "pattern_matched")
        p2 = self._extra(finding2, "pattern_matched")
        if p1 and p2 and p1 != p2:
            return False

        # ✅ Merge only if exact same line OR identical (normalized) snippet;
        # otherwise fall back to similarity score.
        same_line = finding1.location.line_number == finding2.location.line_number
        same_snippet = self._same_snippet(finding1, finding2)
        if same_line:
            if finding1.description != finding2.description:
                return False

        if same_line or same_snippet:
            return True

        # if the code snippet is different it is on whatever line number it is not same
        if not same_snippet:
            return False

        # for some cases ex lines 133 and 135 it is returning false as line threshold is set to 5
        # Check location proximity
        # if not self._are_locations_close(finding1.location, finding2.location):
        #     print(colored("line are so closed, returning", "red"))
        #     return False
        # Check content similarity
        content_similarity = self._calculate_content_similarity(finding1, finding2)

        return content_similarity > self.similarity_threshold

    def _are_locations_close(self, loc1: CodeLocation, loc2: CodeLocation) -> bool:
        """Check if two locations are close enough to be considered the same."""
        if loc1.line_number is None or loc2.line_number is None:
            return True  # Can't compare, assume close

        return abs(loc1.line_number - loc2.line_number) <= self.location_tolerance

    def _calculate_content_similarity(
        self, finding1: UnifiedFinding, finding2: UnifiedFinding
    ) -> float:
        """Calculate similarity score between two findings based on content."""
        # Check rule/CWE similarity
        rule_match = (
            (finding1.rule_id == finding2.rule_id)
            if finding1.rule_id and finding2.rule_id
            else False
        )
        cwe_match = (
            (finding1.cwe_id == finding2.cwe_id)
            if finding1.cwe_id and finding2.cwe_id
            else False
        )

        # Check description similarity
        desc_similarity = self._text_similarity(
            finding1.description, finding2.description
        )

        # Check category and severity
        category_match = finding1.category == finding2.category
        severity_match = finding1.severity == finding2.severity

        # Weighted similarity score
        similarity = 0.0
        if rule_match:
            similarity += 0.4
        if cwe_match:
            similarity += 0.3
        if category_match:
            similarity += 0.1
        if severity_match:
            similarity += 0.1

        similarity += desc_similarity * 0.1

        return min(similarity, 1.0)

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity between two strings."""
        if not text1 or not text2:
            return 0.0

        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _merge_findings(self, target: UnifiedFinding, source: UnifiedFinding) -> None:
        """Merge information from source finding into target finding."""
        # Keep the higher severity
        severity_order = [
            SeverityLevel.INFO,
            SeverityLevel.LOW,
            SeverityLevel.MEDIUM,
            SeverityLevel.HIGH,
            SeverityLevel.CRITICAL,
        ]
        if severity_order.index(source.severity) > severity_order.index(
            target.severity
        ):
            target.severity = source.severity

        # Keep the higher confidence
        target.confidence_score = max(target.confidence_score, source.confidence_score)

        # Merge tags
        target.tags.update(source.tags)

        # Merge compliance frameworks
        target.compliance_frameworks.extend(
            [
                fw
                for fw in source.compliance_frameworks
                if fw not in target.compliance_frameworks
            ]
        )

        # Add source analyzer to metadata
        if "merged_from" not in target.extra_data:
            target.extra_data["merged_from"] = []
        target.extra_data["merged_from"].append(source.source_analyzer)

        # Keep more detailed description if available
        if len(source.description) > len(target.description):
            target.description = source.description

        # Keep remediation guidance if target doesn't have it
        if not target.remediation_guidance and source.remediation_guidance:
            target.remediation_guidance = source.remediation_guidance

    async def _cross_reference_findings(
        self, findings: List[UnifiedFinding]
    ) -> List[UnifiedFinding]:
        """Cross-reference related findings to identify patterns and relationships."""
        # Group findings by various attributes for cross-referencing
        cwe_groups = defaultdict(list)
        file_groups = defaultdict(list)
        rule_groups = defaultdict(list)

        for finding in findings:
            if finding.cwe_id:
                cwe_groups[finding.cwe_id].append(finding)
            file_groups[finding.location.file_path].append(finding)
            if finding.rule_id:
                rule_groups[finding.rule_id].append(finding)

        # Add cross-reference information to findings
        for finding in findings:
            cross_refs = []

            # Add related CWE findings
            if finding.cwe_id and len(cwe_groups[finding.cwe_id]) > 1:
                cross_refs.extend(
                    [f.id for f in cwe_groups[finding.cwe_id] if f.id != finding.id]
                )

            # Add related file findings (only if significant)
            file_findings = file_groups[finding.location.file_path]
            if len(file_findings) > 3:  # Only if file has many issues
                cross_refs.extend(
                    [f.id for f in file_findings[:5] if f.id != finding.id]
                )

            if cross_refs:
                finding.extra_data["cross_references"] = list(set(cross_refs))

        return findings

    async def _enrich_findings(
        self, findings: List[UnifiedFinding]
    ) -> List[UnifiedFinding]:
        """Enrich findings with additional context and metadata."""
        for finding in findings:
            # Add file-level context
            file_findings = [
                f
                for f in findings
                if f.location.file_path == finding.location.file_path
            ]
            finding.extra_data["file_issue_count"] = len(file_findings)

            # Add category context
            category_findings = [f for f in findings if f.category == finding.category]
            finding.extra_data["category_prevalence"] = len(category_findings)

            # Calculate priority score
            finding.extra_data["priority_score"] = self._calculate_priority_score(
                finding
            )

            # Add remediation effort context
            if finding.remediation_complexity:
                complexity_counts = Counter(f.remediation_complexity for f in findings)
                finding.extra_data["complexity_rank"] = (
                    list(complexity_counts.keys()).index(finding.remediation_complexity)
                    + 1
                )

        return findings

    def _calculate_priority_score(self, finding: UnifiedFinding) -> float:
        """Calculate priority score for a finding (0-100)."""
        score = 0.0

        # Severity weight (40% of score)
        severity_weights = {
            SeverityLevel.CRITICAL: 40,
            SeverityLevel.HIGH: 30,
            SeverityLevel.MEDIUM: 20,
            SeverityLevel.LOW: 10,
            SeverityLevel.INFO: 5,
        }
        score += severity_weights.get(finding.severity, 0)

        # Confidence weight (20% of score)
        score += finding.confidence_score * 20

        # Category weight (20% of score)
        category_weights = {
            FindingCategory.SECURITY: 20,
            FindingCategory.PRIVACY: 18,
            FindingCategory.QUALITY: 15,
            FindingCategory.PERFORMANCE: 12,
            FindingCategory.TESTABILITY: 10,
            FindingCategory.READABILITY: 8,
            FindingCategory.OBSERVABILITY: 7,
            FindingCategory.DEPENDENCY: 16,
        }
        score += category_weights.get(finding.category, 10)

        # Remediation complexity weight (10% of score, inverted)
        complexity_weights = {
            ComplexityLevel.TRIVIAL: 10,
            ComplexityLevel.SIMPLE: 8,
            ComplexityLevel.MODERATE: 6,
            ComplexityLevel.COMPLEX: 4,
            ComplexityLevel.VERY_COMPLEX: 2,
        }
        score += complexity_weights.get(finding.remediation_complexity, 5)

        # CWE presence bonus (10% of score)
        if finding.cwe_id:
            score += 10

        return min(score, 100.0)

    def _sort_by_priority(self, findings: List[UnifiedFinding]) -> List[UnifiedFinding]:
        """Sort findings by priority (highest first)."""
        severity_weight = {
            SeverityLevel.CRITICAL: 100,
            SeverityLevel.HIGH: 75,
            SeverityLevel.MEDIUM: 50,
            SeverityLevel.LOW: 25,
            SeverityLevel.INFO: 10,
        }

        def compute_score(f: UnifiedFinding):
            priority = f.extra_data.get("priority_score", 0)
            confidence = f.confidence_score or 0
            severity_score = severity_weight.get(f.severity, 0)
            # final weighted score
            return (severity_score * 1.5) + (priority * 1.2) + (confidence * 100)

        # return sorted(
        #     findings,
        #     key=lambda f: (
        #         f.extra_data.get("priority_score", 0),
        #         f.confidence_score,
        #         [
        #             SeverityLevel.CRITICAL,
        #             SeverityLevel.HIGH,
        #             SeverityLevel.MEDIUM,
        #             SeverityLevel.LOW,
        #             SeverityLevel.INFO,
        #         ].index(f.severity),
        #     ),
        #     reverse=True,
        # )
        return sorted(findings, key=compute_score, reverse=True)

    def _get_severity_breakdown(self, findings: List[UnifiedFinding]) -> Dict[str, int]:
        """Get breakdown of findings by severity."""
        breakdown = {level.value: 0 for level in SeverityLevel}
        for finding in findings:
            breakdown[finding.severity.value] += 1
        return breakdown

    def _get_category_breakdown(self, findings: List[UnifiedFinding]) -> Dict[str, int]:
        """Get breakdown of findings by category."""
        breakdown = {category.value: 0 for category in FindingCategory}
        for finding in findings:
            breakdown[finding.category.value] += 1
        return breakdown

    def _calculate_risk_score(self, findings: List[UnifiedFinding]) -> float:
        """Calculate overall risk score (0-100)."""
        if not findings:
            return 0.0

        severity_weights = {
            SeverityLevel.CRITICAL: 10,
            SeverityLevel.HIGH: 7,
            SeverityLevel.MEDIUM: 4,
            SeverityLevel.LOW: 2,
            SeverityLevel.INFO: 1,
        }

        total_score = sum(
            severity_weights.get(f.severity, 0) * f.confidence_score for f in findings
        )
        max_possible = (
            len(findings) * 10
        )  # Max if all were critical with confidence 1.0

        return min((total_score / max_possible) * 100 if max_possible > 0 else 0, 100.0)

    def _determine_risk_level(self, findings: List[UnifiedFinding]) -> str:
        """Determine overall risk level."""
        risk_score = self._calculate_risk_score(findings)

        if risk_score >= 80:
            return "CRITICAL"
        elif risk_score >= 60:
            return "HIGH"
        elif risk_score >= 40:
            return "MEDIUM"
        elif risk_score >= 20:
            return "LOW"
        else:
            return "MINIMAL"

    def _get_unique_files(self, findings: List[UnifiedFinding]) -> Set[str]:
        """Get set of unique files with issues."""
        return {f.location.file_path for f in findings}

    def _get_top_files_by_issues(
        self, findings: List[UnifiedFinding], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get files with most issues."""
        file_counts = defaultdict(lambda: {"total": 0, "critical": 0, "high": 0})

        for finding in findings:
            file_path = finding.location.file_path
            file_counts[file_path]["total"] += 1
            if finding.severity == SeverityLevel.CRITICAL:
                file_counts[file_path]["critical"] += 1
            elif finding.severity == SeverityLevel.HIGH:
                file_counts[file_path]["high"] += 1

        sorted_files = sorted(
            file_counts.items(),
            key=lambda x: (x[1]["total"], x[1]["critical"], x[1]["high"]),
            reverse=True,
        )

        return [
            {"file": file_path, **counts} for file_path, counts in sorted_files[:limit]
        ]

    def _get_remediation_breakdown(
        self, findings: List[UnifiedFinding]
    ) -> Dict[str, int]:
        """Get breakdown of findings by remediation complexity."""
        breakdown = {level.value: 0 for level in ComplexityLevel}
        for finding in findings:
            breakdown[finding.remediation_complexity.value] += 1
        return breakdown

    def _get_compliance_issues(self, findings: List[UnifiedFinding]) -> Dict[str, int]:
        """Get breakdown of compliance-related issues."""
        compliance_counts = defaultdict(int)
        for finding in findings:
            for framework in finding.compliance_frameworks:
                compliance_counts[framework] += 1
        return dict(compliance_counts)

    def _get_analyzer_performance(self, metrics: List) -> Dict[str, Any]:
        """Get analyzer performance summary."""
        total_time = sum(m.execution_time_seconds for m in metrics)

        return {
            "total_execution_time": total_time,
            "average_time_per_analyzer": total_time / len(metrics) if metrics else 0,
            "fastest_analyzer": (
                min(metrics, key=lambda m: m.execution_time_seconds).analyzer_name
                if metrics
                else None
            ),
            "slowest_analyzer": (
                max(metrics, key=lambda m: m.execution_time_seconds).analyzer_name
                if metrics
                else None
            ),
            "success_rate": (
                len([m for m in metrics if m.success]) / len(metrics) if metrics else 0
            ),
        }

    def _generate_trend_analysis(self, report: ConsolidatedReport) -> Dict[str, Any]:
        """Generate trend analysis (placeholder for future historical comparison)."""
        return {
            "note": "Trend analysis requires historical data",
            "current_timestamp": report.timestamp.isoformat(),
            "baseline_established": True,
        }
