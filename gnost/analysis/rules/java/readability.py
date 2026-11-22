"""Readability rules for Java: names, line length, commented-out code and TODO comments.

Findings feed the `readability` analyzer score; most are one finding per file with a count.
"""

from __future__ import annotations

import re
from typing import Iterable

from gnost.analysis.core.models import FindingCategory, SeverityLevel
from gnost.analysis.rules import shared
from gnost.analysis.rules.base import Rule, RuleContext, RuleHit
from gnost.analysis.rules.java.syntax import JAVA

LANGUAGES = ("java",)


class Naming(Rule):
    """Java uses camelCase for methods and variables, PascalCase for classes, UPPER_CASE for constants."""

    id = "RDB-NAMING"
    title = "Name does not follow the convention"
    analyzer = "readability"
    severity = SeverityLevel.INFO
    category = FindingCategory.READABILITY
    remediation = "Use camelCase for methods and variables, PascalCase for classes, UPPER_CASE for constants."
    tags = ("naming",)
    languages = LANGUAGES
    aggregate = True
    skip_tests = True  # JUnit test names are often snake_case or sentences
    SNAKE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        tree = ctx.tree
        for node in tree.walk():
            name = node.child_by_field_name("name")
            if name is None:
                continue
            text = tree.text(name)
            if node.type == "method_declaration" and (
                text[:1].isupper() or self.SNAKE.match(text)
            ):
                yield RuleHit(tree.line(node), f"Method `{text}` should be camelCase")
            elif node.type == "variable_declarator" and self.SNAKE.match(text):
                yield RuleHit(tree.line(node), f"`{text}` is in snake_case")
            elif node.type == "class_declaration" and text[:1].islower():
                yield RuleHit(
                    tree.line(node),
                    f"Class `{text}` should start with a capital letter",
                )


class LongLine(shared.LongLine):
    languages = LANGUAGES
    remediation = "Break the line, or let a formatter do it."
    exempt = re.compile(r"https?://|^\s*(import|package)\b")


class CommentedCode(shared.CommentedCode):
    languages = LANGUAGES
    syntax = JAVA
    code = re.compile(
        r"[;{}]\s*$|^\s*(if|else|for|while|return|import|throw|new|try|catch|switch)\b|\)\s*\{?\s*$"
    )


class TodoComment(shared.TodoComment):
    languages = LANGUAGES
    syntax = JAVA
