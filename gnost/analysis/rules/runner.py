"""Runs the rules of one analyzer over a list of files and returns findings.

`RuleRunner` picks each file's language, parses it with tree-sitter, runs the matching rules and turns
every hit into a `UnifiedFinding`. A file that cannot be read or parsed, or a rule that raises, is
skipped and counted; one bad file never stops an analysis.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from gnost.analysis.core.models import UnifiedFinding
from gnost.analysis.languages import AnalysisLanguages
from gnost.analysis.rules.base import RuleContext, RuleSettings
from gnost.analysis.rules.registry import RuleRegistry, default_registry
from gnost.parsing import ParserFactory, default_factory
from gnost.utils.logger import AppLogger

logger = AppLogger.get_logger(__name__)
MAX_FILE_BYTES = 2_000_000  # bigger files are bundles or data, not hand-written code


@dataclass
class RuleRun:
    """What one analyzer's rules found over a set of files."""

    findings: List[UnifiedFinding] = field(default_factory=list)
    files_analyzed: int = 0
    skipped: List[str] = field(default_factory=list)  # "path: reason"


class RuleRunner:
    """Applies the registry's rules, for one analyzer at a time."""

    def __init__(
        self,
        registry: Optional[RuleRegistry] = None,
        factory: Optional[ParserFactory] = None,
        languages: Optional[AnalysisLanguages] = None,
        settings: Optional[RuleSettings] = None,
    ) -> None:
        self.registry = registry or default_registry()
        self.factory = factory or default_factory()
        self.languages = languages or AnalysisLanguages()
        self.settings = settings or RuleSettings()

    def handles(self, path: str) -> bool:
        """True for files this runner analyzes (a supported language other than Python)."""
        language = self.languages.language_of(path)
        return language is not None and language != "python"

    def run(self, files: Sequence[str], analyzer: str, root: str) -> RuleRun:
        """Run `analyzer`'s rules on every file this runner handles."""
        result = RuleRun()
        for path in files:
            if not self.handles(path):
                continue
            ctx = self._context(path, root, result)
            if ctx is None:
                continue
            result.files_analyzed += 1
            for rule in self.registry.rules_for(ctx.language, analyzer):
                try:
                    hits = rule.collect(ctx)
                except Exception as exc:  # one broken rule must not stop the run
                    logger.debug(f"rule {rule.id} failed on {path}: {exc}")
                    result.skipped.append(f"{path}: rule {rule.id} failed")
                    continue
                result.findings.extend(rule.finding(hit, ctx) for hit in hits)
        return result

    def _context(self, path: str, root: str, result: RuleRun) -> Optional[RuleContext]:
        language = self.languages.language_of(path) or ""
        grammar = self.factory.grammar_for(os.path.splitext(path)[1])
        try:
            if os.path.getsize(path) > MAX_FILE_BYTES:
                result.skipped.append(f"{path}: file too large")
                return None
            with open(path, "rb") as handle:
                source = handle.read()
        except OSError as exc:
            result.skipped.append(f"{path}: {exc}")
            return None
        tree = self.factory.parse(grammar, source) if grammar else None
        if tree is None:
            reason = self.factory.reason(grammar) if grammar else "no grammar"
            result.skipped.append(f"{path}: cannot parse ({reason})")
            return None
        # real paths on both sides: a symlinked folder (macOS /tmp) must not give "../../.." names
        display = os.path.relpath(
            os.path.realpath(path), os.path.realpath(root)
        ).replace(os.sep, "/")
        return RuleContext(display, tree, language, self.settings)
