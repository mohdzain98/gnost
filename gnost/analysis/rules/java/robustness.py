"""Robustness rules for Java: errors thrown away, too-broad catches, string comparison, shell commands.

Findings feed the `robustness` analyzer score. `ROB-EMPTY-CATCH` is shared with the other languages;
the rest are Java's own versions of the same ideas.
"""

from __future__ import annotations

from typing import Iterable

from gnost.analysis.core.models import FindingCategory, SeverityLevel
from gnost.analysis.rules import shared
from gnost.analysis.rules.base import Rule, RuleContext, RuleHit
from gnost.analysis.rules.java.syntax import JAVA

LANGUAGES = ("java",)


class EmptyCatch(shared.EmptyCatch):
    languages = LANGUAGES
    syntax = JAVA


class CatchGeneric(Rule):
    """Catching Exception or Throwable also catches bugs and errors nobody meant to handle."""

    id = "ROB-CATCH-GENERIC"
    title = "Catches Exception or Throwable"
    analyzer = "robustness"
    severity = SeverityLevel.LOW
    remediation = "Catch the specific exceptions you can handle."
    tags = ("error_handling",)
    languages = LANGUAGES
    BROAD = ("Exception", "Throwable")

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        tree = ctx.tree
        for node in tree.walk():
            if node.type != "catch_type":
                continue
            names = [tree.text(c) for c in node.children if c.type == "type_identifier"]
            broad = [n for n in names if n in self.BROAD]
            if broad:
                yield RuleHit(tree.line(node), f"`catch ({broad[0]} ...)` is too broad")


class StringEquality(Rule):
    """`==` compares references; two equal strings can still be different objects."""

    id = "ROB-STRING-EQUALITY"
    title = "String compared with == or !="
    analyzer = "robustness"
    severity = SeverityLevel.MEDIUM
    remediation = (
        'Use `.equals()` (put the literal first: `"x".equals(value)` is null-safe).'
    )
    tags = ("correctness",)
    languages = LANGUAGES

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        tree = ctx.tree
        for node in tree.walk():
            if node.type != "binary_expression" or JAVA.operator_of(node) not in (
                "==",
                "!=",
            ):
                continue
            sides = (
                node.child_by_field_name("left"),
                node.child_by_field_name("right"),
            )
            if any(s is not None and s.type == "string_literal" for s in sides):
                yield RuleHit(tree.line(node), "A string is compared with `==`")


class UnsafeExec(Rule):
    """Running an operating-system command built from a variable allows command injection."""

    id = "ROB-UNSAFE-EXEC"
    title = "Operating-system command from a non-literal"
    analyzer = "robustness"
    severity = SeverityLevel.HIGH
    category = FindingCategory.SECURITY
    remediation = "Avoid shelling out; if you must, pass a fixed command and validate every argument."
    tags = ("security", "injection")
    languages = LANGUAGES
    skip_tests = True

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        tree = ctx.tree
        for node in tree.walk():
            if node.type != "method_invocation":
                continue
            name = node.child_by_field_name("name")
            target = node.child_by_field_name("object")
            if name is None or tree.text(name) != "exec" or target is None:
                continue
            if not tree.text(target).endswith("getRuntime()"):
                continue
            arguments = node.child_by_field_name("arguments")
            first = (
                next((c for c in arguments.named_children), None)
                if arguments is not None
                else None
            )
            if first is not None and first.type != "string_literal":
                yield RuleHit(
                    tree.line(node),
                    "`Runtime.exec` runs a command that is not a literal",
                )
