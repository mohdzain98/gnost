"""Applies the CI options to a finished analysis: baseline, SARIF file and quality gate.

`CiOptions` holds what was asked for; `CiRun.process` does it in one place and returns a
`CiOutcome` with the report to show, the score, the gate result and notes to print.
"""

from __future__ import annotations

import argparse
import dataclasses
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from gnost.analysis.core.models import ConsolidatedReport
from gnost.ci.baseline import Baseline
from gnost.ci.fingerprint import FindingFingerprint
from gnost.ci.gate import GateResult, QualityGate
from gnost.ci.paths import PathResolver
from gnost.ci.sarif import SarifWriter
from gnost.ci.scorecard import ScoreCard
from gnost.config.settings import GnostConfig
from gnost.utils.layout import OutputLayout


@dataclass(frozen=True)
class CiOptions:
    """What the user asked for on the command line or in `[analyze]` of .gnost.toml."""

    fail_under: Optional[float] = None
    fail_on_new: bool = False
    baseline: Optional[str] = None  # file to compare against
    write_baseline: Optional[str] = None  # file to create from today's findings
    sarif: Optional[str] = None  # SARIF file to write

    @classmethod
    def from_args(
        cls, args: argparse.Namespace, config: GnostConfig, layout: OutputLayout
    ) -> "CiOptions":
        """Combine flags (first), the config file and the default paths in the output folder."""
        configured = config.get("analyze", "baseline")
        baseline = cls._path(
            getattr(args, "baseline", None),
            layout.baseline_json,
            os.path.join(layout.root, configured) if configured else None,
        )
        return cls(
            fail_under=config.pick(
                "analyze", "fail_under", getattr(args, "fail_under", None), None
            ),
            fail_on_new=bool(getattr(args, "fail_on_new", False)),
            baseline=baseline,
            write_baseline=cls._path(
                getattr(args, "write_baseline", None), layout.baseline_json
            ),
            sarif=cls._path(getattr(args, "sarif", None), layout.analysis_sarif),
        )

    def problem(self) -> Optional[str]:
        """A mistake in the combination of options, as one sentence, or None."""
        if self.fail_on_new and not self.baseline:
            return "--fail-on-new needs a baseline to compare with (--baseline)"
        return None

    @staticmethod
    def _path(
        given: Optional[str], default: str, configured: Optional[str] = None
    ) -> Optional[str]:
        """None when not asked for, the default for a bare flag (""), else the path given."""
        if given is None:
            return configured
        return given or default


@dataclass
class CiOutcome:
    """The result of applying the CI options to one report."""

    report: ConsolidatedReport  # what to print and write (new findings only with a baseline)
    card: ScoreCard  # scores of the full report
    gate: GateResult
    new_findings: Optional[int] = None  # None when no baseline is used
    known_findings: int = 0
    notes: List[str] = field(default_factory=list)

    def baseline_summary(self) -> Optional[Dict[str, Any]]:
        """Counts to add to the JSON payload when a baseline hid findings."""
        if self.new_findings is None:
            return None
        return {
            "new_findings": self.new_findings,
            "known_findings_hidden": self.known_findings,
        }


class CiRun:
    """Runs the baseline, SARIF and gate steps for one analysis."""

    def __init__(self, options: CiOptions, root: str, files: Sequence[str]) -> None:
        self.options = options
        self.resolver = PathResolver(files, root)
        self.fingerprint = FindingFingerprint(self.resolver)

    def process(self, report: ConsolidatedReport) -> CiOutcome:
        """Apply the options. Raises BaselineError if a baseline file cannot be used."""
        notes: List[str] = []
        opts = self.options
        if opts.write_baseline:
            Baseline.from_findings(report.findings, self.fingerprint).save(
                opts.write_baseline
            )
            notes.append(
                f"Baseline written to {opts.write_baseline} ({len(report.findings)} findings)"
            )

        visible, new, known = report, None, 0
        if opts.baseline:
            fresh, old = Baseline.load(opts.baseline).split(
                report.findings, self.fingerprint
            )
            visible = dataclasses.replace(report, findings=fresh)
            new, known = len(fresh), len(old)
            notes.append(f"Baseline: {known} known findings hidden, {new} new")

        if opts.sarif:
            SarifWriter(self.resolver, self.fingerprint).write(
                opts.sarif, visible.findings
            )
            notes.append(f"SARIF written to {opts.sarif}")

        card = ScoreCard.from_report(report)
        gate = QualityGate(opts.fail_under, opts.fail_on_new).evaluate(
            card.final_score, new
        )
        return CiOutcome(visible, card, gate, new, known, notes)
