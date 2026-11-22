"""Robustness rules for JavaScript and TypeScript: errors thrown away, loose equality, unsafe code.

Each class is one check with a shared id (`ROB-...`), so the same idea in another language gets the
same id. Findings feed the `robustness` analyzer score.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Iterator, Optional

from gnost.analysis.core.models import FindingCategory, SeverityLevel
from gnost.analysis.rules.base import Rule, RuleContext, RuleHit
from gnost.analysis.rules import shared
from gnost.analysis.rules.ecmascript.syntax import ECMASCRIPT
from gnost.parsing import SourceTree

LANGUAGES = ("javascript", "typescript")


class EmptyCatch(shared.EmptyCatch):
    """A catch block with nothing in it throws the error away; so does an empty `.catch()` handler."""

    languages = LANGUAGES
    syntax = ECMASCRIPT

    def extra(self, tree: SourceTree, node: Any) -> Optional[RuleHit]:
        if node.type == "call_expression" and self._is_empty_promise_catch(tree, node):
            return RuleHit(tree.line(node), "The `.catch()` handler is empty")
        return None

    @staticmethod
    def _is_empty_promise_catch(tree: SourceTree, node: Any) -> bool:
        function = node.child_by_field_name("function")
        arguments = node.child_by_field_name("arguments")
        if (
            function is None
            or arguments is None
            or function.type != "member_expression"
        ):
            return False
        prop = function.child_by_field_name("property")
        if prop is None or tree.text(prop) != "catch":
            return False
        handler = next((c for c in arguments.named_children), None)
        if handler is None or handler.type not in (
            "arrow_function",
            "function_expression",
            "function",
        ):
            return False
        body = handler.child_by_field_name("body")
        return (
            body is not None
            and body.type == "statement_block"
            and body.named_child_count == 0
        )


class LooseEquality(Rule):
    """`==` and `!=` convert types silently; `===` and `!==` do not."""

    languages = LANGUAGES
    id = "ROB-LOOSE-EQUALITY"
    title = "Loose equality (== or !=)"
    analyzer = "robustness"
    severity = SeverityLevel.LOW
    remediation = (
        "Use === or !==. Comparing with null on purpose (`x == null`) is accepted."
    )
    tags = ("type_safety",)
    aggregate = True

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        tree = ctx.tree
        for node in tree.walk():
            if node.type != "binary_expression" or ECMASCRIPT.operator_of(node) not in (
                "==",
                "!=",
            ):
                continue
            sides = (
                node.child_by_field_name("left"),
                node.child_by_field_name("right"),
            )
            if any(s is not None and s.type in ("null", "undefined") for s in sides):
                continue  # `x == null` is the usual way to test null and undefined together
            yield RuleHit(
                tree.line(node),
                f"`{ECMASCRIPT.operator_of(node)}` compares with type conversion",
            )


class UnsafeEval(Rule):
    """`eval` and `new Function` run text as code."""

    languages = LANGUAGES
    id = "ROB-UNSAFE-EVAL"
    title = "Dynamic code execution (eval or new Function)"
    analyzer = "robustness"
    severity = SeverityLevel.HIGH
    category = FindingCategory.SECURITY
    remediation = "Avoid evaluating strings as code. Parse data with JSON.parse or use a lookup table."
    tags = ("security", "injection")
    skip_tests = True

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        tree = ctx.tree
        for node in tree.walk():
            if node.type == "call_expression":
                function = node.child_by_field_name("function")
                if (
                    function is not None
                    and function.type == "identifier"
                    and tree.text(function) == "eval"
                ):
                    yield RuleHit(tree.line(node), "`eval()` runs a string as code")
            elif node.type == "new_expression":
                constructor = node.child_by_field_name("constructor")
                if constructor is not None and tree.text(constructor) == "Function":
                    yield RuleHit(
                        tree.line(node), "`new Function()` builds code from a string"
                    )


class UnsafeHtml(Rule):
    """Writing a non-literal value into innerHTML or dangerouslySetInnerHTML allows script injection."""

    languages = LANGUAGES
    id = "ROB-UNSAFE-HTML"
    title = "Unescaped HTML assignment"
    analyzer = "robustness"
    severity = SeverityLevel.HIGH
    category = FindingCategory.SECURITY
    remediation = "Set textContent instead, or sanitize the HTML first (for example with DOMPurify)."
    tags = ("security", "xss")
    skip_tests = True
    LITERALS = ("string", "template_string")

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        tree = ctx.tree
        for node in tree.walk():
            if node.type == "assignment_expression":
                left = node.child_by_field_name("left")
                right = node.child_by_field_name("right")
                prop = (
                    left.child_by_field_name("property")
                    if left is not None and left.type == "member_expression"
                    else None
                )
                if (
                    prop is not None
                    and tree.text(prop) in ("innerHTML", "outerHTML")
                    and not self._literal(tree, right)
                ):
                    yield RuleHit(
                        tree.line(node),
                        f"`{tree.text(prop)}` is set from a value that is not a literal",
                    )
            elif (
                node.type == "jsx_attribute"
                and self._attribute_name(tree, node) == "dangerouslySetInnerHTML"
            ):
                if not self._literal_html(tree, node):
                    yield RuleHit(
                        tree.line(node),
                        "`dangerouslySetInnerHTML` is set from a value that is not a literal",
                    )

    def _literal(self, tree: SourceTree, node: Any) -> bool:
        if node is None or node.type not in self.LITERALS:
            return False
        return all(c.type != "template_substitution" for c in node.children)

    @staticmethod
    def _attribute_name(tree: SourceTree, node: Any) -> str:
        first = node.children[0] if node.children else None
        return tree.text(first) if first is not None else ""

    def _literal_html(self, tree: SourceTree, node: Any) -> bool:
        for pair in (n for n in _descendants(node) if n.type == "pair"):
            key = pair.child_by_field_name("key")
            if key is not None and tree.text(key) == "__html":
                return self._literal(tree, pair.child_by_field_name("value"))
        return False


class UntypedAny(Rule):
    """An explicit `any` switches off type checking for that value."""

    id = "ROB-UNTYPED-ANY"
    title = "Explicit any type"
    analyzer = "robustness"
    severity = SeverityLevel.LOW
    remediation = "Use a precise type, `unknown` with a check, or a generic."
    tags = ("type_safety",)
    languages = ("typescript",)
    aggregate = True

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        if ctx.path.endswith(".d.ts"):
            return
        tree = ctx.tree
        for node in tree.walk():
            if node.type == "predefined_type" and tree.text(node) == "any":
                yield RuleHit(tree.line(node), "A value is typed as `any`")


class TsSuppress(Rule):
    """`@ts-ignore` and `@ts-nocheck` hide type errors instead of fixing them."""

    id = "ROB-TS-SUPPRESS"
    title = "Type errors suppressed with a comment"
    analyzer = "robustness"
    severity = SeverityLevel.LOW
    remediation = "Fix the type error. If it must stay, prefer `@ts-expect-error` with the reason."
    tags = ("type_safety",)
    languages = ("typescript",)
    aggregate = True
    PATTERN = re.compile(r"@ts-(ignore|nocheck)\b")

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        tree = ctx.tree
        for node in tree.walk():
            if node.type == "comment":
                match = self.PATTERN.search(tree.text(node))
                if match:
                    yield RuleHit(
                        tree.line(node), f"`@ts-{match.group(1)}` hides type errors"
                    )


def _descendants(node: Any) -> Iterator[Any]:
    stack = list(node.children)
    while stack:
        current = stack.pop()
        yield current
        stack.extend(current.children)
