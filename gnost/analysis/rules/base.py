"""The building blocks of a rule: settings, what a rule reports, and the rule base class.

A `Rule` has an id shared by every language that has the same check (`ROB-EMPTY-CATCH`), the analyzer
it belongs to (robustness, maintainability, observability, readability), a severity and a fix hint.
`check` yields `RuleHit`s for one file; `finding` turns a hit into a `UnifiedFinding`.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Tuple

from gnost.analysis.core.models import (
    CodeLocation,
    ComplexityLevel,
    FindingCategory,
    SeverityLevel,
    UnifiedFinding,
)
from gnost.parsing import SourceTree

TEST_PATH = re.compile(
    r"(^|/)(tests?|__tests__|__mocks__|e2e|cypress|spec)(/|$)|\.(test|spec|stories)\.[a-z]+$|(Tests?|IT)\.java$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RuleSettings:
    """The thresholds the rules use (fixed in 0.7.0)."""

    max_complexity: int = 10
    max_function_lines: int = 60
    max_file_lines: int = 500
    max_nesting: int = 4
    max_parameters: int = 5
    max_class_methods: int = 30
    max_line_length: int = 120


@dataclass(frozen=True)
class RuleHit:
    """One place where a rule found something."""

    line: int
    message: str
    function: Optional[str] = None
    severity: Optional[SeverityLevel] = None  # overrides the rule's severity when set


@dataclass
class RuleContext:
    """Everything a rule may look at for one file."""

    path: str  # shown in findings, relative to the analyzed folder
    tree: SourceTree
    language: str
    settings: RuleSettings = field(default_factory=RuleSettings)

    @property
    def is_test(self) -> bool:
        """True for test, mock and story files, where some rules stay quiet."""
        return bool(TEST_PATH.search(self.path.replace("\\", "/")))

    @property
    def lines(self) -> List[str]:
        """The source split into lines."""
        return self.tree.source.decode("utf-8", "replace").splitlines()


class Rule(ABC):
    """One check. Subclasses set the class attributes and implement `check`."""

    id: str = ""
    title: str = ""
    analyzer: str = ""  # robustness | maintainability | observability | readability
    severity: SeverityLevel = SeverityLevel.LOW
    category: FindingCategory = FindingCategory.QUALITY
    remediation: str = ""
    effort: ComplexityLevel = ComplexityLevel.SIMPLE
    confidence: float = 0.8
    tags: Tuple[str, ...] = ()
    languages: Tuple[str, ...] = ()  # set by each concrete rule
    skip_tests: bool = False  # stay quiet in test files
    aggregate: bool = (
        False  # one finding per file, with a count, instead of one per hit
    )

    @abstractmethod
    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        """Yield a hit for every place in this file where the rule applies."""

    def collect(self, ctx: RuleContext) -> List[RuleHit]:
        """The hits for a file, honouring `skip_tests` and `aggregate`."""
        if self.skip_tests and ctx.is_test:
            return []
        hits = list(self.check(ctx))
        if self.aggregate and len(hits) > 1:
            first = min(hits, key=lambda h: h.line)
            return [
                RuleHit(
                    first.line, self.summary(len(hits), first), severity=first.severity
                )
            ]
        return hits

    def summary(self, count: int, first: RuleHit) -> str:
        """The message of an aggregated finding."""
        return f"{first.message} ({count} in this file, the first is shown)"

    def finding(self, hit: RuleHit, ctx: RuleContext) -> UnifiedFinding:
        """Turn a hit into a finding in the shape the rest of `analyze` expects."""
        return UnifiedFinding(
            title=self.title,
            description=hit.message,
            category=self.category,
            severity=hit.severity or self.severity,
            confidence_score=self.confidence,
            location=CodeLocation(
                file_path=ctx.path, line_number=hit.line, function_name=hit.function
            ),
            rule_id=self.id,
            remediation_guidance=self.remediation,
            remediation_complexity=self.effort,
            source_analyzer=self.analyzer,
            tags=set(self.tags) | {ctx.language, "rule_engine"},
            extra_data={"language": ctx.language, "priority_score": 0.5},
        )
