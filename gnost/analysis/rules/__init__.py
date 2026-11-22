"""A small rule engine for languages that are not checked by external tools.

A `Rule` looks at one parsed file and reports hits; `RuleRegistry` keeps the rules of each language;
`RuleRunner` runs them and turns hits into the same `UnifiedFinding`s the rest of `analyze` uses, so
scores, SARIF and baselines work for every language without changes.
"""

from gnost.analysis.rules.base import Rule, RuleContext, RuleHit, RuleSettings
from gnost.analysis.rules.registry import RuleRegistry, default_registry
from gnost.analysis.rules.runner import RuleRunner

__all__ = [
    "Rule",
    "RuleContext",
    "RuleHit",
    "RuleRegistry",
    "RuleRunner",
    "RuleSettings",
    "default_registry",
]
