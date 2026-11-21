"""The result of `gnost changes`: plain data classes that the renderers and JSON share.

`ChangeReport` holds the changed files with their risk, the blast radius, routes, cycles and
findings. `to_dict` is the JSON written for tools; the Markdown and terminal views read the
same object so the three always agree.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from gnost.changes.impact import AffectedFile
from gnost.changes.refs import ChangedFile

SCHEMA_VERSION = "1.0"


@dataclass
class FileRisk:
    """How fragile and how busy one changed file is."""

    path: str
    structural: float  # caution score, 0..100
    churn: Optional[float] = None  # change-hotspot score, None without history
    risk: Optional[float] = None  # structural x churn, None without history
    why: str = ""  # strongest caution signals in plain words

    @property
    def level(self) -> float:
        """The number to rank by: the combined risk when known, else the structural score."""
        return self.risk if self.risk is not None else self.structural


@dataclass
class RouteChange:
    """An HTTP route touched by the change."""

    method: str
    path: str
    handler: str
    file: str
    state: str  # added, removed, changed (handler file changed) or affected


@dataclass
class CycleChange:
    """A circular dependency that exists on one side only."""

    files: List[str]
    kind: str


@dataclass
class FindingInChange:
    """An analyzer finding located in a changed file."""

    file: str
    line: int
    severity: str
    title: str
    analyzer: str


@dataclass
class ChangeReport:
    """Everything `gnost changes` found for one range."""

    base: str
    head: str
    base_commit: str
    head_commit: str
    files: List[ChangedFile]
    affected: List[AffectedFile]
    depth: int
    risks: List[FileRisk] = field(default_factory=list)
    routes: List[RouteChange] = field(default_factory=list)
    new_cycles: List[CycleChange] = field(default_factory=list)
    fixed_cycles: List[CycleChange] = field(default_factory=list)
    findings: Optional[List[FindingInChange]] = None  # None: not asked for
    cycles_compared: bool = True
    notes: List[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        """The range as shown to people, for example `main..feature`."""
        return f"{self.base}..{self.head}"

    @property
    def counts(self) -> Dict[str, int]:
        """Changed files per status."""
        out = {"added": 0, "modified": 0, "deleted": 0, "renamed": 0}
        for f in self.files:
            out[f.status] += 1
        return out

    def to_dict(self) -> Dict[str, Any]:
        """The JSON form (schema version 1.0), stable key order."""
        return {
            "schema_version": SCHEMA_VERSION,
            "range": {
                "base": self.base,
                "head": self.head,
                "base_commit": self.base_commit,
                "head_commit": self.head_commit,
            },
            "counts": self.counts,
            "files": [asdict(f) for f in self.files],
            "blast_radius": {
                "depth": self.depth,
                "affected": [asdict(a) for a in self.affected],
            },
            "risk": [asdict(r) for r in self.risks],
            "routes": [asdict(r) for r in self.routes],
            "cycles": {
                "compared": self.cycles_compared,
                "new": [asdict(c) for c in self.new_cycles],
                "fixed": [asdict(c) for c in self.fixed_cycles],
            },
            "findings": (
                None if self.findings is None else [asdict(f) for f in self.findings]
            ),
            "notes": list(self.notes),
        }
