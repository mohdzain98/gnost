"""The JavaScript and TypeScript rules, and `register_rules` to add them to a registry."""

from __future__ import annotations

from gnost.analysis.rules.ecmascript.maintainability import (
    Complexity,
    DeepNesting,
    LongFile,
    LongFunction,
    ManyParameters,
)
from gnost.analysis.rules.ecmascript.observability import PrintLogging, SwallowedError
from gnost.analysis.rules.ecmascript.readability import (
    CommentedCode,
    LongLine,
    Naming,
    TodoComment,
)
from gnost.analysis.rules.ecmascript.robustness import (
    EmptyCatch,
    LooseEquality,
    TsSuppress,
    UnsafeEval,
    UnsafeHtml,
    UntypedAny,
)
from gnost.analysis.rules.registry import RuleRegistry

RULES = (
    EmptyCatch,
    LooseEquality,
    UnsafeEval,
    UnsafeHtml,
    UntypedAny,
    TsSuppress,
    Complexity,
    LongFunction,
    LongFile,
    DeepNesting,
    ManyParameters,
    SwallowedError,
    PrintLogging,
    Naming,
    LongLine,
    CommentedCode,
    TodoComment,
)


def register_rules(registry: RuleRegistry) -> None:
    """Add every JavaScript and TypeScript rule to the registry."""
    for rule_class in RULES:
        registry.register(rule_class())
