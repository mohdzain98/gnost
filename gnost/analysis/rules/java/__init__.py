"""The Java rules, and `register_rules` to add them to a registry."""

from __future__ import annotations

from gnost.analysis.rules.java.maintainability import (
    Complexity,
    DeepNesting,
    GodClass,
    LongFile,
    LongFunction,
    ManyParameters,
)
from gnost.analysis.rules.java.observability import (
    PrintLogging,
    PrintStackTrace,
    SwallowedError,
)
from gnost.analysis.rules.java.readability import (
    CommentedCode,
    LongLine,
    Naming,
    TodoComment,
)
from gnost.analysis.rules.java.robustness import (
    CatchGeneric,
    EmptyCatch,
    StringEquality,
    UnsafeExec,
)
from gnost.analysis.rules.registry import RuleRegistry

RULES = (
    EmptyCatch,
    CatchGeneric,
    StringEquality,
    UnsafeExec,
    Complexity,
    LongFunction,
    LongFile,
    DeepNesting,
    ManyParameters,
    GodClass,
    SwallowedError,
    PrintLogging,
    PrintStackTrace,
    Naming,
    LongLine,
    CommentedCode,
    TodoComment,
)


def register_rules(registry: RuleRegistry) -> None:
    """Add every Java rule to the registry."""
    for rule_class in RULES:
        registry.register(rule_class())
