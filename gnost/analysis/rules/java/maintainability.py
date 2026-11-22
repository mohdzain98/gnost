"""Maintainability rules for Java: the shared rules with Java's syntax, plus the god-class check."""

from __future__ import annotations

from typing import Iterable

from gnost.analysis.core.models import SeverityLevel
from gnost.analysis.rules import shared
from gnost.analysis.rules.base import Rule, RuleContext, RuleHit
from gnost.analysis.rules.java.syntax import JAVA

LANGUAGES = ("java",)


class Complexity(shared.Complexity):
    languages = LANGUAGES
    syntax = JAVA


class LongFunction(shared.LongFunction):
    languages = LANGUAGES
    syntax = JAVA


class LongFile(shared.LongFile):
    languages = LANGUAGES


class DeepNesting(shared.DeepNesting):
    languages = LANGUAGES
    syntax = JAVA


class ManyParameters(shared.ManyParameters):
    languages = LANGUAGES
    syntax = JAVA


class GodClass(Rule):
    """A class with very many methods usually does too many things."""

    id = "MNT-GOD-CLASS"
    title = "Class has too many methods"
    analyzer = "maintainability"
    severity = SeverityLevel.LOW
    remediation = "Split the class by responsibility; move groups of related methods into their own classes."
    tags = ("design",)
    languages = LANGUAGES
    skip_tests = True

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        limit = ctx.settings.max_class_methods
        for node in ctx.tree.walk():
            if node.type != "class_declaration":
                continue
            body = node.child_by_field_name("body")
            if body is None:
                continue
            count = sum(
                1 for c in body.named_children if c.type == "method_declaration"
            )
            if count > limit:
                name = node.child_by_field_name("name")
                label = ctx.tree.text(name) if name is not None else "<class>"
                yield RuleHit(
                    ctx.tree.line(node),
                    f"`{label}` has {count} methods (limit {limit})",
                    severity=SeverityLevel.MEDIUM
                    if count > 2 * limit
                    else SeverityLevel.LOW,
                )
