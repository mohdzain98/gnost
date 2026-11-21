"""A saved list of known findings, so CI can report only the new ones.

`gnost analyze --write-baseline` records how many findings of each fingerprint exist today;
`--baseline` then treats up to that many of each as known and reports the rest. Counting (not
a plain yes/no) means fixing one of three similar findings never hides a newly added one.
The file is small, sorted JSON, meant to be committed.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Iterable, List, Tuple

from gnost import __version__
from gnost.analysis.core.models import UnifiedFinding
from gnost.ci.fingerprint import FindingFingerprint


class BaselineError(Exception):
    """The baseline file is missing or cannot be read; the message says what to do."""


class Baseline:
    """Known findings as a count per fingerprint."""

    VERSION = 1

    def __init__(self, counts: Dict[str, int]) -> None:
        self.counts = counts

    @classmethod
    def from_findings(
        cls, findings: Iterable[UnifiedFinding], fingerprint: FindingFingerprint
    ) -> "Baseline":
        """The baseline that makes every one of these findings known."""
        counts: Dict[str, int] = {}
        for finding in findings:
            key = fingerprint.of(finding)
            counts[key] = counts.get(key, 0) + 1
        return cls(counts)

    @classmethod
    def load(cls, path: str) -> "Baseline":
        """Read a baseline file; raises BaselineError if it is missing or not a baseline."""
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except OSError:
            raise BaselineError(
                f"baseline file not found: {path} (create it with --write-baseline)"
            ) from None
        except ValueError as exc:
            raise BaselineError(f"{path} is not valid JSON ({exc})") from exc
        counts = data.get("fingerprints") if isinstance(data, dict) else None
        if not isinstance(counts, dict) or not all(
            isinstance(v, int) for v in counts.values()
        ):
            raise BaselineError(f"{path} is not a gnost baseline file")
        return cls({str(k): int(v) for k, v in counts.items()})

    def save(self, path: str) -> None:
        """Write the baseline (sorted, so the file only changes when the findings do)."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        data = {
            "version": self.VERSION,
            "generator": f"gnost {__version__}",
            "total": sum(self.counts.values()),
            "fingerprints": dict(sorted(self.counts.items())),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    def split(
        self, findings: List[UnifiedFinding], fingerprint: FindingFingerprint
    ) -> Tuple[List[UnifiedFinding], List[UnifiedFinding]]:
        """(new, known): per fingerprint the first N by line are known, the rest are new."""
        groups: Dict[str, List[UnifiedFinding]] = {}
        for finding in findings:
            groups.setdefault(fingerprint.of(finding), []).append(finding)
        known_ids = set()
        for key, group in groups.items():
            ordered = sorted(group, key=lambda f: f.location.line_number or 0)
            known_ids.update(id(f) for f in ordered[: self.counts.get(key, 0)])
        new = [f for f in findings if id(f) not in known_ids]
        known = [f for f in findings if id(f) in known_ids]
        return new, known
