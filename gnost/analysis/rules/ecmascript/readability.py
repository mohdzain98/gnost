"""Readability rules for JavaScript and TypeScript: names, line length, dead code in comments, TODOs.

Small things that add up. Most are aggregated to one finding per file, so a few hundred long
lines are one remark and not three hundred. Findings feed the `readability` analyzer score.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from gnost.analysis.core.models import FindingCategory, SeverityLevel
from gnost.analysis.rules import shared
from gnost.analysis.rules.base import Rule, RuleContext, RuleHit
from gnost.analysis.rules.ecmascript.syntax import ECMASCRIPT

LANGUAGES = ("javascript", "typescript")


class Naming(Rule):
    """JavaScript names functions and variables in camelCase and classes in PascalCase."""

    id = "RDB-NAMING"
    title = "Name does not follow the convention"
    analyzer = "readability"
    severity = SeverityLevel.INFO
    category = FindingCategory.READABILITY
    remediation = "Use camelCase for functions and variables, PascalCase for classes and components, UPPER_CASE for constants."
    tags = ("naming",)
    languages = LANGUAGES
    aggregate = True
    skip_tests = True
    SNAKE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        tree = ctx.tree
        for node in tree.walk():
            if node.type in ("function_declaration", "generator_function_declaration"):
                yield from self._function(ctx, node)
            elif node.type == "variable_declarator":
                yield from self._variable(ctx, node)
            elif node.type == "class_declaration":
                name = node.child_by_field_name("name")
                text = tree.text(name) if name is not None else ""
                if text and text[0].islower() and not text.startswith("_"):
                    yield RuleHit(
                        tree.line(node),
                        f"Class `{text}` should start with a capital letter",
                    )

    def _function(self, ctx: RuleContext, node: Any) -> Iterable[RuleHit]:
        name = node.child_by_field_name("name")
        if name is not None and self.SNAKE.match(ctx.tree.text(name)):
            yield RuleHit(
                ctx.tree.line(node),
                f"Function `{ctx.tree.text(name)}` is in snake_case",
            )

    def _variable(self, ctx: RuleContext, node: Any) -> Iterable[RuleHit]:
        name = node.child_by_field_name("name")
        if name is None or name.type != "identifier":
            return
        text = ctx.tree.text(name)
        if self.SNAKE.match(text):
            yield RuleHit(ctx.tree.line(node), f"`{text}` is in snake_case")


class LongLine(shared.LongLine):
    languages = LANGUAGES
    remediation = "Break the line, or let a formatter (Prettier) do it."
    exempt = re.compile(r"https?://|^\s*(import|export)\b.*from|require\(")


class CommentedCode(shared.CommentedCode):
    languages = LANGUAGES
    syntax = ECMASCRIPT


class TodoComment(shared.TodoComment):
    languages = LANGUAGES
    syntax = ECMASCRIPT
