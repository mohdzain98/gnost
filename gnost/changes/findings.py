"""Analyzer findings that sit in changed files only.

`ChangedFindings` runs the normal `gnost analyze` analyzers on just the changed Python files
and maps each finding back to a path relative to the project. It is slower than the rest of
`gnost changes`, so it only runs when asked for (`--findings`).
"""

from __future__ import annotations

import asyncio
from typing import List, Sequence

from gnost.analysis.core.models import AnalysisConfiguration, SeverityLevel
from gnost.changes.report import FindingInChange
from gnost.ci.paths import PathResolver
from gnost.cli.commands.analysis import Analysis


class ChangedFindings:
    """Runs the analyzers on a list of files and returns their findings."""

    def __init__(self, root: str, timeout: int = 900, max_findings: int = 1000) -> None:
        self.root = root
        self.timeout = timeout
        self.max_findings = max_findings

    def run(self, files: Sequence[str]) -> List[FindingInChange]:
        """Findings for these absolute file paths (Python only), worst first."""
        python = [f for f in files if f.endswith(".py")]
        if not python:
            return []
        analysis = Analysis()
        analysis.initialize_analyzers()
        cfg = AnalysisConfiguration(
            target_path=self.root,
            enabled_analyzers=set(),
            severity_threshold=SeverityLevel.INFO,
            timeout_seconds=self.timeout,
            max_findings_per_analyzer=self.max_findings,
            files=python,
        )
        report = asyncio.run(analysis.run_async(cfg, show_progress=False))
        resolver = PathResolver(python, self.root)
        order = [s.value for s in SeverityLevel]
        found = [
            FindingInChange(
                file=resolver.resolve(f.location.file_path),
                line=f.location.line_number or 0,
                severity=f.severity.value,
                title=f.title,
                analyzer=f.source_analyzer or "",
            )
            for f in report.findings
        ]
        return sorted(found, key=lambda x: (order.index(x.severity), x.file, x.line))
