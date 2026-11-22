"""An analyzer that checks Python with its own tools and every other language with the rule engine.

`PolyglotAnalyzer` wraps one of the four analyzers (robustness, maintainability, observability,
readability). Python files still go to the wrapped analyzer (mypy, bandit, radon, ruff), so Python
results do not change. Other files go to `RuleRunner`, and both sets of findings are merged under the
same analyzer name, so scores, reports, SARIF and baselines need no changes.
"""

from __future__ import annotations

import dataclasses
import os
from typing import Any, Dict, List, Optional

from gnost.analysis.core.interfaces import AnalysisResult, BaseAnalyzer
from gnost.analysis.core.models import AnalysisConfiguration, AnalysisMetrics
from gnost.analysis.languages import AnalysisLanguages
from gnost.analysis.rules.runner import RuleRun, RuleRunner


class PolyglotAnalyzer(BaseAnalyzer):
    """One analyzer name, two engines: the wrapped tools for Python and rules for other languages."""

    def __init__(
        self,
        inner: BaseAnalyzer,
        runner: Optional[RuleRunner] = None,
        languages: Optional[AnalysisLanguages] = None,
    ) -> None:
        super().__init__(inner.name, inner.version)
        self.inner = inner
        self.languages = languages or AnalysisLanguages()
        self.runner = runner or RuleRunner(languages=self.languages)

    def get_supported_file_types(self) -> List[str]:
        """The wrapped analyzer's types plus the extensions of the rule-engine languages."""
        types = set(self.inner.get_supported_file_types())
        types |= {
            e for e in self.languages.extensions() if self.runner.handles(f"x{e}")
        }
        return sorted(types)

    def get_default_config(self) -> Dict[str, Any]:
        """The wrapped analyzer's defaults."""
        return self.inner.get_default_config()

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """The wrapped analyzer's validation."""
        return self.inner.validate_config(config)

    def __getattr__(self, name: str) -> Any:
        """Anything else (quality metrics, config helpers) comes from the wrapped analyzer."""
        return getattr(self.inner, name)

    async def analyze(self, config: AnalysisConfiguration) -> AnalysisResult:
        """Analyze the Python files with the wrapped analyzer and the rest with the rules."""
        files = (
            list(config.files) if config.files else self._discover(config.target_path)
        )
        python = [f for f in files if self.languages.language_of(f) == "python"]
        others = [f for f in files if self.runner.handles(f)]
        python_result = None
        if python:
            python_result = await self.inner.analyze(
                dataclasses.replace(config, files=python)
            )
        rules = self.runner.run(others, self.name, self._root(config.target_path))
        return self._merge(python_result, rules)

    # ------------------------------------------------------------ internals

    def _merge(
        self, python: Optional[AnalysisResult], rules: RuleRun
    ) -> AnalysisResult:
        findings = list(python.findings if python else []) + rules.findings
        metadata: Dict[str, Any] = dict(python.metadata) if python else {}
        if rules.files_analyzed or rules.skipped:
            metadata["rule_engine"] = {
                "files": rules.files_analyzed,
                "findings": len(rules.findings),
                "skipped": rules.skipped[:20],
            }
        base = python.metrics if python else None
        metrics = AnalysisMetrics(
            analyzer_name=self.name,
            execution_time_seconds=base.execution_time_seconds if base else 0.0,
            files_analyzed=(base.files_analyzed if base else 0) + rules.files_analyzed,
            findings_count=len(findings),
            error_count=base.error_count if base else 0,
            warnings_count=(base.warnings_count if base else 0) + len(rules.skipped),
            success=base.success if base else True,
            error_message=base.error_message if base else None,
        )
        return AnalysisResult(findings=findings, metrics=metrics, metadata=metadata)

    @staticmethod
    def _root(target: str) -> str:
        return (
            target
            if os.path.isdir(target)
            else os.path.dirname(os.path.abspath(target))
        )

    def _discover(self, target: str) -> List[str]:
        """Supported files under the target, when no explicit list was given."""
        if os.path.isfile(target):
            return [target]
        found: List[str] = []
        for base, dirs, names in os.walk(target):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules"]
            found.extend(
                os.path.join(base, n)
                for n in names
                if self.languages.language_of(n) is not None
            )
        return sorted(found)
