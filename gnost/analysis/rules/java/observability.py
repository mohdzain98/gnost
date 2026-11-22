"""Observability rules for Java: swallowed errors, System.out instead of a logger, printStackTrace.

Findings feed the `observability` analyzer score.
"""

from __future__ import annotations

import re
from typing import Iterable

from gnost.analysis.core.models import FindingCategory, SeverityLevel
from gnost.analysis.rules import shared
from gnost.analysis.rules.base import Rule, RuleContext, RuleHit
from gnost.analysis.rules.java.syntax import JAVA

LANGUAGES = ("java",)


class SwallowedError(shared.SwallowedError):
    languages = LANGUAGES
    syntax = JAVA
    logger_names = re.compile(r"^(log|logger|LOG|LOGGER|LOGGING|Log|System\.err)\b")


class PrintLogging(shared.PrintLogging):
    """`System.out` is for quick debugging; production code should use a logger."""

    languages = LANGUAGES
    syntax = JAVA
    remediation = "Use a logger (SLF4J, java.util.logging) and remove debug output."
    PREFIXES = ("System.out.", "System.err.")
    METHODS = ("print", "println", "printf", "format")

    def is_console(self, target: str) -> bool:
        return any(
            target.startswith(prefix) and target[len(prefix) :] in self.METHODS
            for prefix in self.PREFIXES
        )


class PrintStackTrace(Rule):
    """`printStackTrace()` writes to standard error, outside the application's logging."""

    id = "OBS-PRINT-STACKTRACE"
    title = "printStackTrace() instead of logging"
    analyzer = "observability"
    severity = SeverityLevel.LOW
    category = FindingCategory.OBSERVABILITY
    remediation = 'Log the exception with a logger: `log.error("message", e)`.'
    tags = ("logging",)
    languages = LANGUAGES
    skip_tests = True
    aggregate = True

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        tree = ctx.tree
        for node in tree.walk():
            if node.type == "method_invocation":
                name = node.child_by_field_name("name")
                if name is not None and tree.text(name) == "printStackTrace":
                    yield RuleHit(tree.line(node), "`printStackTrace()` is called")
