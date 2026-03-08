"""
Core data models for the unified code review tool.
Defines standardized data structures for findings, reports, and analysis results.
"""

# Flake8: noqa: E501
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any, Set, Type, TypeVar
from datetime import datetime
import uuid


class SeverityLevel(Enum):
    """Standardized severity levels across all analysis modules."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(Enum):
    """Categories of findings from different analysis modules."""

    SECURITY = "security"
    PRIVACY = "privacy"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    TESTABILITY = "testability"
    READABILITY = "readability"
    OBSERVABILITY = "observability"
    DEPENDENCY = "dependency"
    MAINTAINABILITY = "maintainability"
    COMPLIANCE = "compliance"


class ComplexityLevel(Enum):
    """Complexity level for remediation efforts."""

    TRIVIAL = "trivial"  # < 1 hour
    SIMPLE = "simple"  # 1-4 hours
    MODERATE = "moderate"  # 1-2 days
    COMPLEX = "complex"  # 3-5 days
    VERY_COMPLEX = "very_complex"  # > 1 week


def _safe_int(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


@dataclass
class CodeLocation:
    """Standardized representation of code location."""

    file_path: str
    line_number: Optional[int] = None
    end_line_number: Optional[int] = None
    column: Optional[int] = None
    end_column: Optional[int] = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None

    def __str__(self) -> str:
        location_str = self.file_path
        if self.line_number:
            location_str += f":{self.line_number}"
            if self.column:
                location_str += f":{self.column}"
        return location_str

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CodeLocation":
        """Safely build from JSON or dict data."""
        if not isinstance(d, dict):
            # If a string was passed instead of dict
            return cls(file_path=str(d))
        return cls(
            file_path=d.get("file_path") or d.get("path") or "",
            line_number=_safe_int(d.get("line") or d.get("line_number")),
            end_line_number=_safe_int(d.get("end_line") or d.get("end_line_number")),
            column=_safe_int(d.get("column")),
            end_column=_safe_int(d.get("end_column")),
            function_name=d.get("function_name"),
            class_name=d.get("class_name"),
        )


TEnum = TypeVar("TEnum", bound=Enum)


def _parse_enum(
    enum_type: Type[TEnum], raw: Any, default: Optional[TEnum] = None
) -> TEnum:
    """
    Accept enum by name ('CRITICAL') or value ('CRITICAL', 'critical', etc).
    Falls back to provided default or the first enum member.
    """
    if raw is None:
        return default or list(enum_type)[0]
    # try exact member name
    try:
        return enum_type[str(raw)]
    except Exception:
        pass
    # try by value (case-insensitive string)
    for member in enum_type:
        if str(member.value).lower() == str(raw).lower():
            return member
        if str(member.name).lower() == str(raw).lower():
            return member
    return default or list(enum_type)[0]


@dataclass
class UnifiedFinding:
    """Standardized finding representation across all analysis modules."""

    # Core identification
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    details: Optional[Any] = None
    clubbed: Optional[Any] = None

    # Classification
    category: FindingCategory = FindingCategory.QUALITY
    severity: SeverityLevel = SeverityLevel.MEDIUM
    confidence_score: float = 1.0  # 0.0 to 1.0

    # Location information
    location: CodeLocation = field(default_factory=lambda: CodeLocation(""))

    # Technical details
    rule_id: Optional[str] = None
    cwe_id: Optional[str] = None
    cve_id: Optional[str] = None

    # Context and remediation
    code_snippet: Optional[str] = None
    remediation_guidance: Optional[str] = None
    remediation_complexity: ComplexityLevel = ComplexityLevel.MODERATE

    # Compliance and standards
    compliance_frameworks: List[str] = field(default_factory=list)
    owasp_category: Optional[str] = None

    # Metadata
    source_analyzer: str = ""  # Which analyzer found this
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Set[str] = field(default_factory=set)

    # Additional data for specific analyzers
    extra_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and normalize data after initialization."""
        if not self.title and self.description:
            # Generate title from description if not provided
            self.title = (
                self.description[:50] + "..."
                if len(self.description) > 50
                else self.description
            )

        # Ensure confidence score is in valid range
        self.confidence_score = max(0.0, min(1.0, self.confidence_score))

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "UnifiedFinding":
        return cls(
            id=d.get("id") or str(uuid.uuid4()),
            title=d.get("title", ""),
            description=d.get("description", ""),
            details=d.get("details"),
            clubbed=d.get("clubbed"),
            category=_parse_enum(
                FindingCategory, d.get("category"), default=FindingCategory.QUALITY
            ),
            severity=_parse_enum(
                SeverityLevel, d.get("severity"), default=SeverityLevel.MEDIUM
            ),
            confidence_score=float(d.get("confidence_score", 1.0)),
            location=CodeLocation.from_dict(d.get("location") or {}),
            rule_id=d.get("rule_id"),
            cwe_id=d.get("cwe_id"),
            cve_id=d.get("cve_id"),
            code_snippet=d.get("code_snippet"),
            remediation_guidance=d.get("remediation_guidance"),
            remediation_complexity=_parse_enum(
                ComplexityLevel,
                d.get("remediation_complexity"),
                default=ComplexityLevel.MODERATE,
            ),
            compliance_frameworks=list(d.get("compliance_frameworks", [])),
            owasp_category=d.get("owasp_category"),
            source_analyzer=d.get("source_analyzer", ""),
            timestamp=_parse_datetime(d.get("timestamp")),
            tags=set(d.get("tags", [])),
            # Accept unknown extras if your JSON has analyzer-specific fields
            extra_data=dict(d.get("extra_data", {})),
        )


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class AnalysisMetrics:
    """Metrics for individual analysis modules."""

    analyzer_name: str
    execution_time_seconds: float
    files_analyzed: int
    findings_count: int
    error_count: int = 0
    warnings_count: int = 0
    success: bool = True
    error_message: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AnalysisMetrics":
        """Safely build from JSON or dict data."""
        if not isinstance(d, dict):
            raise TypeError(f"Expected dict for AnalysisMetrics, got {type(d)}")

        return cls(
            analyzer_name=d.get("analyzer_name") or d.get("name") or "Unknown Analyzer",
            execution_time_seconds=_safe_float(
                d.get("execution_time_seconds") or d.get("time_seconds")
            ),
            files_analyzed=_safe_int(
                d.get("files_analyzed") or d.get("num_files") or 0
            ),
            findings_count=_safe_int(d.get("findings_count") or d.get("findings") or 0),
            error_count=_safe_int(d.get("error_count") or 0),
            warnings_count=_safe_int(d.get("warnings_count") or 0),
            success=bool(d.get("success", True)),
            error_message=d.get("error_message"),
        )


@dataclass
class AnalysisResult:
    """Result from an individual analyzer run."""

    findings: List["UnifiedFinding"]
    metrics: AnalysisMetrics
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceStatus:
    """Compliance status for different frameworks."""

    framework_name: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    compliance_percentage: float
    critical_failures: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ComplianceStatus":
        """Safely build from dict or JSON."""
        if not isinstance(d, dict):
            raise TypeError(f"Expected dict for ComplianceStatus, got {type(d)}")

        total = _safe_int(d.get("total_checks") or d.get("total") or 0)
        passed = _safe_int(d.get("passed_checks") or d.get("passed") or 0)
        failed = _safe_int(d.get("failed_checks") or d.get("failed") or 0)
        pct = _safe_float(d.get("compliance_percentage"))
        if pct == 0.0 and total > 0:
            pct = (passed / total) * 100

        return cls(
            framework_name=d.get("framework_name")
            or d.get("framework")
            or "Unknown Framework",
            total_checks=total,
            passed_checks=passed,
            failed_checks=failed,
            compliance_percentage=pct,
            critical_failures=list(d.get("critical_failures", [])),
        )


@dataclass
class TrendData:
    """Historical trend data for metrics."""

    timestamp: datetime
    metric_name: str
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TrendData":
        """Safely build from dict or JSON."""
        if not isinstance(d, dict):
            raise TypeError(f"Expected dict for TrendData, got {type(d)}")

        return cls(
            timestamp=_parse_datetime(d.get("timestamp")),
            metric_name=d.get("metric_name") or d.get("metric") or "unknown_metric",
            value=_safe_float(d.get("value")),
            metadata=dict(d.get("metadata", {})),
        )


def _parse_datetime(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, (int, float)):  # epoch seconds
        return datetime.fromtimestamp(raw)
    if isinstance(raw, str):
        # try ISO-8601; Streamlit/JSON usually has that
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            pass
    return datetime.now()


@dataclass
class ConsolidatedReport:
    """Unified report containing all analysis results."""

    # Report metadata
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    target_path: str = ""

    # Core findings
    findings: List[UnifiedFinding] = field(default_factory=list)

    # Analysis metrics
    analysis_metrics: List[AnalysisMetrics] = field(default_factory=list)
    total_execution_time: float = 0.0

    # Summary statistics
    summary: Dict[str, Any] = field(default_factory=dict)

    # Compliance information
    compliance_status: List[ComplianceStatus] = field(default_factory=list)

    # Trend analysis (for historical comparison)
    trend_data: List[TrendData] = field(default_factory=list)

    # Configuration used for analysis
    analysis_config: Dict[str, Any] = field(default_factory=dict)

    def get_findings_by_category(
        self, category: FindingCategory
    ) -> List[UnifiedFinding]:
        """Get all findings for a specific category."""
        return [f for f in self.findings if f.category == category]

    def get_findings_by_severity(self, severity: SeverityLevel) -> List[UnifiedFinding]:
        """Get all findings with specific severity."""
        return [f for f in self.findings if f.severity == severity]

    def get_critical_findings(self) -> List[UnifiedFinding]:
        """Get all critical and high severity findings."""
        return [
            f
            for f in self.findings
            if f.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]
        ]

    def get_summary_stats(self) -> Dict[str, int]:
        """Generate summary statistics."""
        stats = {
            "total_findings": len(self.findings),
            "critical_findings": len(
                [f for f in self.findings if f.severity == SeverityLevel.CRITICAL]
            ),
            "high_findings": len(
                [f for f in self.findings if f.severity == SeverityLevel.HIGH]
            ),
            "medium_findings": len(
                [f for f in self.findings if f.severity == SeverityLevel.MEDIUM]
            ),
            "low_findings": len(
                [f for f in self.findings if f.severity == SeverityLevel.LOW]
            ),
            "info_findings": len(
                [f for f in self.findings if f.severity == SeverityLevel.INFO]
            ),
        }

        # Add category-wise counts
        for category in FindingCategory:
            stats[f"{category.value}_findings"] = len(
                self.get_findings_by_category(category)
            )

        return stats

    def get_top_files_by_issues(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get files with most issues."""
        file_counts = {}
        for finding in self.findings:
            file_path = finding.location.file_path
            if file_path not in file_counts:
                file_counts[file_path] = {"count": 0, "critical": 0, "high": 0}
            file_counts[file_path]["count"] += 1
            if finding.severity == SeverityLevel.CRITICAL:
                file_counts[file_path]["critical"] += 1
            elif finding.severity == SeverityLevel.HIGH:
                file_counts[file_path]["high"] += 1

        # Sort by total count, then by critical, then by high
        sorted_files = sorted(
            file_counts.items(),
            key=lambda x: (x[1]["count"], x[1]["critical"], x[1]["high"]),
            reverse=True,
        )

        return [
            {"file_path": file_path, **counts}
            for file_path, counts in sorted_files[:limit]
        ]

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConsolidatedReport":
        return cls(
            id=d.get("id") or d.get("report_id") or str(uuid.uuid4()),
            timestamp=_parse_datetime(d.get("timestamp")),
            target_path=d.get("target_path") or d.get("target") or "",
            findings=[UnifiedFinding.from_dict(x) for x in d.get("findings", [])],
            analysis_metrics=[
                AnalysisMetrics.from_dict(x) for x in d.get("analysis_metrics", [])
            ],
            total_execution_time=float(d.get("total_execution_time", 0.0)),
            summary=dict(d.get("summary", {})),
            compliance_status=[
                ComplianceStatus.from_dict(x) for x in d.get("compliance_status", [])
            ],
            trend_data=[TrendData.from_dict(x) for x in d.get("trend_data", [])],
            analysis_config=dict(d.get("analysis_config", {})),
        )


@dataclass
class AnalysisConfiguration:
    """Configuration for analysis execution."""

    # Target configuration
    target_path: str = ""
    file_patterns: List[str] = field(default_factory=lambda: ["*.py"])
    exclude_patterns: List[str] = field(default_factory=list)
    files: Optional[List] = None

    # Analysis module selection
    enabled_analyzers: Set[str] = field(default_factory=set)
    analyzer_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Output configuration
    severity_threshold: SeverityLevel = SeverityLevel.LOW
    max_findings_per_analyzer: int = 1000
    include_low_confidence: bool = False

    # Performance configuration
    parallel_execution: bool = True
    timeout_seconds: int = 300

    # Report configuration
    include_code_snippets: bool = True
    include_remediation: bool = True
    output_formats: List[str] = field(default_factory=lambda: ["json"])
