"""A stable identity for a finding, so the same problem is recognised across runs.

The fingerprint uses what the finding is (analyzer, rule, normalised title, resolved file,
function and class) and never the line number or numbers in the message, which change
whenever code above or around it moves. Used by the baseline and as the SARIF fingerprint.
"""

from __future__ import annotations

import hashlib
import re

from gnost.analysis.core.models import UnifiedFinding
from gnost.ci.paths import PathResolver


class FindingFingerprint:
    """Computes a fingerprint for findings using one path resolver."""

    VERSION = "v1"
    _DIGITS = re.compile(r"\d+")
    _SPACES = re.compile(r"\s+")

    def __init__(self, resolver: PathResolver) -> None:
        self.resolver = resolver

    def of(self, finding: UnifiedFinding) -> str:
        """A 32-character hex fingerprint, the same for the same problem in the same place."""
        location = finding.location
        parts = [
            self.VERSION,
            finding.source_analyzer,
            finding.rule_id or "",
            self.normalise_title(finding.title),
            self.resolver.resolve(location.file_path),
            location.function_name or "",
            location.class_name or "",
        ]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]

    @classmethod
    def normalise_title(cls, title: str) -> str:
        """Lower case, numbers replaced, spaces collapsed: 'Function 12 is long' == 'function # is long'."""
        return cls._SPACES.sub(" ", cls._DIGITS.sub("#", title.lower())).strip()
