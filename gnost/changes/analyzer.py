"""Builds a ChangeReport: diff, blast radius, risk, routes and circular dependencies.

`ChangeAnalyzer` scans the current folder (the head side), optionally exports the base commit to
a temporary folder and scans that too, then compares the two. Nothing in the working tree is
modified. History and risk reuse the same classes as `gnost onboard`.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence, Set

from gnost.changes.findings import ChangedFindings
from gnost.changes.impact import DEFAULT_DEPTH, AffectedFile, BlastRadius
from gnost.changes.refs import ChangedFile, DiffReader, RefRange
from gnost.changes.report import (
    ChangeReport,
    ArchitectureChange,
    CycleChange,
    FileRisk,
    RouteChange,
)
from gnost.changes.snapshot import ProjectSnapshot, RefCheckout
from gnost.core.architecture import ArchitectureChecker, ArchitectureSettings
from gnost.core.caution import CautionSettings, rank_files
from gnost.core.risk import REASON_WORDS, RiskCalculator, RiskSettings
from gnost.vcs.git import GitRepository
from gnost.vcs.history import HistoryReader, HistorySettings


class ChangeAnalyzer:
    """Compares HEAD with the point where it split from BASE for one project folder."""

    def __init__(
        self,
        repo: GitRepository,
        scan_root: str,
        exclude: Optional[Sequence[str]] = None,
        depth: int = DEFAULT_DEPTH,
        compare_base: bool = True,
        findings: bool = False,
        architecture: Optional[ArchitectureSettings] = None,
        caution: Optional[CautionSettings] = None,
        history: Optional[HistorySettings] = None,
        risk: Optional[RiskSettings] = None,
    ) -> None:
        self.repo = repo
        self.scan_root = scan_root
        self.exclude = list(exclude or [])
        self.depth = depth
        self.compare_base = compare_base
        self.findings = findings
        self.architecture = architecture or ArchitectureSettings()
        self.caution = caution or CautionSettings()
        self.history = history or HistorySettings()
        self.risk = risk or RiskSettings()

    def analyze(self, refs: RefRange) -> ChangeReport:
        """The full report for a range; the head side is the current working folder."""
        files = DiffReader(self.repo).read(refs, self.scan_root)
        head = ProjectSnapshot.scan_folder(self.scan_root, self.exclude)
        base = self._scan_base(refs) if self.compare_base and files else None

        changed_now = [f.path for f in files if f.status != "deleted"]
        report = ChangeReport(
            base=refs.base,
            head=refs.head,
            base_commit=refs.base_commit,
            head_commit=refs.head_commit,
            files=files,
            affected=self._affected(head, base, files),
            depth=self.depth,
            cycles_compared=base is not None,
            languages=dict(head.scan.languages),
        )
        report.risks = self._risks(head, changed_now)
        report.routes = self._routes(head, base, files, report.affected)
        if base is not None:
            self._compare_cycles(report, head, base)
        elif self.compare_base and files:
            report.notes.append(
                "Circular dependencies were not compared (base scan failed)."
            )
        report.architecture = self._architecture(head, base, files)
        if self.findings:
            absolute = [os.path.join(self.scan_root, p) for p in changed_now]
            report.findings = ChangedFindings(self.scan_root).run(absolute)
        if not self._head_is_checked_out(refs):
            report.notes.append(
                f"`{refs.head}` is not the commit checked out here; "
                "the working folder was scanned for the blast radius, risk and routes."
            )
        return report

    # ------------------------------------------------------------ sections

    def _scan_base(self, refs: RefRange) -> Optional[ProjectSnapshot]:
        """Scan the base commit in a temporary folder; None if it cannot be exported."""
        subpath = os.path.relpath(self.scan_root, self.repo.root).replace(os.sep, "/")
        try:
            with RefCheckout(self.repo, refs.base_commit, subpath) as folder:
                return ProjectSnapshot.scan_folder(folder, self.exclude)
        except Exception:
            return None

    def _affected(
        self,
        head: ProjectSnapshot,
        base: Optional[ProjectSnapshot],
        files: Sequence[ChangedFile],
    ) -> List[AffectedFile]:
        """Dependents of changed files; for deleted files, dependents in the base version."""
        found = {
            a.path: a
            for a in BlastRadius(head.graph, head.relative).of(
                [f.path for f in files if f.status != "deleted"], self.depth
            )
        }
        if base is not None:
            gone = [
                f.old_path or f.path
                for f in files
                if f.status in ("deleted", "renamed")
            ]
            now = head.files()
            for a in BlastRadius(base.graph, base.relative).of(gone, self.depth):
                if a.path in now and a.path not in found:
                    found[a.path] = a
        changed = {f.path for f in files}
        items = [a for a in found.values() if a.path not in changed]
        return sorted(items, key=lambda a: (a.depth, a.path))

    def _risks(self, head: ProjectSnapshot, changed: Sequence[str]) -> List[FileRisk]:
        """Caution score (and risk, where history exists) of each changed file, riskiest first."""
        wanted: Set[str] = set(changed)
        structural = [
            s
            for s in rank_files(head.scan, head.graph, head.flow.cycles, self.caution)
            if head.relative(s.path) in wanted
        ]
        insights = HistoryReader(self.history).analyze(self.scan_root, head.files())
        everything = RiskSettings(0.0, 10**6, self.risk.churn_weight)
        by_path = {
            r.path: r
            for r in RiskCalculator(everything).rank(
                structural, insights.hotspots, self.scan_root
            )
        }
        out: List[FileRisk] = []
        for s in structural:
            rel = head.relative(s.path)
            scored = by_path.get(rel)
            why = ", ".join(REASON_WORDS.get(f.name, f.name) for f in s.factors[:2])
            out.append(
                FileRisk(
                    path=rel,
                    structural=s.score,
                    churn=scored.churn if scored else None,
                    risk=scored.risk if scored else None,
                    why=why,
                )
            )
        out.sort(key=lambda r: (-r.level, r.path))
        return [r for r in out if r.level >= self.risk.threshold]

    def _routes(
        self,
        head: ProjectSnapshot,
        base: Optional[ProjectSnapshot],
        files: Sequence[ChangedFile],
        affected: Sequence[AffectedFile],
    ) -> List[RouteChange]:
        """Routes added or removed (when the base is known) and routes in touched files."""
        changed = {f.path for f in files}
        near = {a.path for a in affected}
        key = lambda r: (r.method, r.path)  # noqa: E731
        old: Dict = {key(r): r for r in base.routes()} if base else {}
        new: Dict = {key(r): r for r in head.routes()}
        out: List[RouteChange] = []
        for k, r in sorted(new.items()):
            rel = head.relative(r.file)
            if base is not None and k not in old:
                state = "added"
            elif rel in changed:
                state = "changed"
            elif rel in near:
                state = "affected"
            else:
                continue
            out.append(RouteChange(r.method, r.path, r.handler, rel, state))
        for k, r in sorted(old.items()):
            if k not in new and base is not None:
                out.append(
                    RouteChange(
                        r.method, r.path, r.handler, base.relative(r.file), "removed"
                    )
                )
        return out

    @staticmethod
    def _compare_cycles(
        report: ChangeReport, head: ProjectSnapshot, base: ProjectSnapshot
    ) -> None:
        """Fill new and fixed cycles by comparing the file sets on each side."""
        before = base.cycle_keys()
        after = head.cycle_keys()
        for c in head.flow.cycles:
            if head.cycle_key(c) not in before:
                report.new_cycles.append(CycleChange(sorted(head.cycle_key(c)), c.kind))
        for c in base.flow.cycles:
            if base.cycle_key(c) not in after:
                report.fixed_cycles.append(
                    CycleChange(sorted(base.cycle_key(c)), c.kind)
                )

    def _architecture(
        self,
        head: ProjectSnapshot,
        base: Optional[ProjectSnapshot],
        files: Sequence[ChangedFile],
    ) -> ArchitectureChange:
        """Violations of the `[architecture]` rules that the change adds or removes."""
        if not self.architecture.configured:
            return ArchitectureChange(configured=False)
        checker = ArchitectureChecker.for_settings(self.architecture)
        now = checker.check(head.graph, head.relative)
        if base is None:
            changed = {f.path for f in files}
            touching = [v for v in now if v.source in changed or v.target in changed]
            return ArchitectureChange(
                True, [v.to_dict() for v in touching], [], len(now), compared=False
            )
        before = checker.check(base.graph, base.relative)
        renamed = {f.old_path: f.path for f in files if f.old_path}
        new, fixed = ArchitectureChecker.compare(before, now, renamed)
        return ArchitectureChange(
            True, [v.to_dict() for v in new], [v.to_dict() for v in fixed], len(now)
        )

    def _head_is_checked_out(self, refs: RefRange) -> bool:
        """Whether the head ref is the commit the working folder is on."""
        try:
            return self.repo.resolve("HEAD") == refs.head_commit
        except Exception:
            return True
