"""Keeps the rules of every language and answers "which rules apply to this file?".

`RuleRegistry.register` is how a language or a rule is added: no other code changes. `default_registry`
builds the registry with every rule GNOST ships.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from gnost.analysis.rules.base import Rule


class RuleRegistry:
    """Rules grouped by language and analyzer."""

    def __init__(self) -> None:
        self._rules: List[Rule] = []

    def register(self, rule: Rule) -> None:
        """Add a rule; a duplicate id for the same languages is a programming error."""
        for other in self._rules:
            if other.id == rule.id and set(other.languages) & set(rule.languages):
                raise ValueError(f"duplicate rule id {rule.id}")
        self._rules.append(rule)

    def rules_for(self, language: str, analyzer: Optional[str] = None) -> List[Rule]:
        """The rules of a language, optionally only those of one analyzer."""
        return [
            r
            for r in self._rules
            if language in r.languages and (analyzer is None or r.analyzer == analyzer)
        ]

    def languages(self) -> List[str]:
        """Every language that has at least one rule."""
        return sorted({lang for r in self._rules for lang in r.languages})

    def ids_by_language(self) -> Dict[str, List[str]]:
        """Rule ids of each language (used by the parity test and the docs)."""
        out: Dict[str, List[str]] = {}
        for rule in self._rules:
            for lang in rule.languages:
                out.setdefault(lang, []).append(rule.id)
        return {k: sorted(v) for k, v in out.items()}


def default_registry() -> RuleRegistry:
    """The registry with every shipped rule."""
    from gnost.analysis.rules import ecmascript, java

    registry = RuleRegistry()
    ecmascript.register_rules(registry)
    java.register_rules(registry)
    return registry
