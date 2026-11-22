"""The rules that mean the same thing in every language, written once against a `Syntax`.

Complexity, length, nesting, empty and swallowed catch blocks, long lines, commented-out code and TODO
comments are not language-specific ideas. Each class here is abstract about the language (it has no
`languages` or `syntax`); a language package subclasses it with those two attributes, and may override
a small hook. Findings keep one id across languages, so equal problems score equally.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, List, Optional, Pattern

from gnost.analysis.core.models import FindingCategory, SeverityLevel
from gnost.analysis.rules.base import Rule, RuleContext, RuleHit
from gnost.analysis.rules.syntax import Syntax
from gnost.parsing import SourceTree


class SyntaxRule(Rule):
    """A rule that reads the tree through a language's `Syntax`."""

    syntax: Syntax


# ---------------------------------------------------------------- maintainability


class Complexity(SyntaxRule):
    """Cyclomatic complexity: the number of independent paths through a function."""

    id = "MNT-COMPLEXITY"
    title = "Function is too complex"
    analyzer = "maintainability"
    severity = SeverityLevel.LOW
    remediation = "Split the function into smaller ones, or replace long if/else chains with a lookup."
    tags = ("complexity",)

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        limit = ctx.settings.max_complexity
        for node in self.syntax.iter_functions(ctx.tree):
            score = 1 + self.syntax.decision_points(node)
            if score > limit:
                name = self.syntax.function_name(ctx.tree, node)
                yield RuleHit(
                    ctx.tree.line(node),
                    f"`{name}` has a cyclomatic complexity of {score} (limit {limit})",
                    function=name,
                    severity=self._severity(score, limit),
                )

    @staticmethod
    def _severity(score: int, limit: int) -> SeverityLevel:
        if score > 2 * limit:
            return SeverityLevel.HIGH
        if score > limit + limit // 2:
            return SeverityLevel.MEDIUM
        return SeverityLevel.LOW


class LongFunction(SyntaxRule):
    """A function that does not fit on a screen is hard to read and to test."""

    id = "MNT-LONG-FUNCTION"
    title = "Function is too long"
    analyzer = "maintainability"
    severity = SeverityLevel.LOW
    remediation = "Extract the steps into named functions."
    tags = ("size",)
    skip_tests = True  # test callbacks (describe/it) are long by nature

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        limit = ctx.settings.max_function_lines
        for node in self.syntax.iter_functions(ctx.tree):
            lines = self.syntax.line_span(node)
            if lines > limit:
                name = self.syntax.function_name(ctx.tree, node)
                yield RuleHit(
                    ctx.tree.line(node),
                    f"`{name}` is {lines} lines long (limit {limit})",
                    function=name,
                    severity=SeverityLevel.MEDIUM
                    if lines > 2 * limit
                    else SeverityLevel.LOW,
                )


class LongFile(Rule):
    """A very long file usually holds more than one idea."""

    id = "MNT-LONG-FILE"
    title = "File is too long"
    analyzer = "maintainability"
    severity = SeverityLevel.LOW
    remediation = "Split the file by responsibility."
    tags = ("size",)
    skip_tests = True  # test classes grow with every case

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        limit = ctx.settings.max_file_lines
        total = len(ctx.lines)
        if total > limit:
            yield RuleHit(
                1,
                f"The file has {total} lines (limit {limit})",
                severity=SeverityLevel.MEDIUM
                if total > 2 * limit
                else SeverityLevel.LOW,
            )


class DeepNesting(SyntaxRule):
    """Blocks inside blocks inside blocks: hard to follow."""

    id = "MNT-DEEP-NESTING"
    title = "Code is nested too deeply"
    analyzer = "maintainability"
    severity = SeverityLevel.LOW
    remediation = "Return early, extract the inner part into a function, or flatten the conditions."
    tags = ("complexity",)

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        limit = ctx.settings.max_nesting
        for node in self.syntax.iter_functions(ctx.tree):
            depth = self.syntax.max_nesting(node)
            if depth > limit:
                name = self.syntax.function_name(ctx.tree, node)
                yield RuleHit(
                    ctx.tree.line(node),
                    f"`{name}` nests blocks {depth} levels deep (limit {limit})",
                    function=name,
                )


class ManyParameters(SyntaxRule):
    """Many parameters usually mean a missing object or a function doing too much."""

    id = "MNT-MANY-PARAMS"
    title = "Function takes too many parameters"
    analyzer = "maintainability"
    severity = SeverityLevel.LOW
    remediation = "Group related parameters into one object."
    tags = ("design",)

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        limit = ctx.settings.max_parameters
        for node in self.syntax.iter_functions(ctx.tree):
            count = self.syntax.parameter_count(node)
            if count > limit:
                name = self.syntax.function_name(ctx.tree, node)
                yield RuleHit(
                    ctx.tree.line(node),
                    f"`{name}` takes {count} parameters (limit {limit})",
                    function=name,
                )


# ---------------------------------------------------------- robustness, observability


class EmptyCatch(SyntaxRule):
    """A catch block with nothing in it throws the error away."""

    id = "ROB-EMPTY-CATCH"
    title = "Empty catch block"
    analyzer = "robustness"
    severity = SeverityLevel.MEDIUM
    remediation = "Handle the error, log it, or rethrow it. If ignoring it is deliberate, say why in a comment."
    tags = ("error_handling",)
    skip_tests = True  # tests catch exceptions on purpose, to assert that they happen

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        tree = ctx.tree
        for node in tree.walk():
            if node.type == self.syntax.catch_clause:
                body = node.child_by_field_name("body")
                # a comment inside the block counts as a stated reason
                if body is not None and body.named_child_count == 0:
                    yield RuleHit(tree.line(node), "The catch block is empty")
            else:
                hit = self.extra(tree, node)
                if hit:
                    yield hit

    def extra(self, tree: SourceTree, node: Any) -> Optional[RuleHit]:
        """Hook for language-specific forms of an empty handler (JavaScript's `.catch(() => {})`)."""
        return None


class SwallowedError(SyntaxRule):
    """A catch block that neither logs, rethrows, reports nor uses the error hides the failure."""

    id = "OBS-SWALLOWED-ERROR"
    title = "Error is caught and neither logged nor rethrown"
    analyzer = "observability"
    severity = (
        SeverityLevel.LOW
    )  # a judgement call: "return null" after a failed lookup is often deliberate
    skip_tests = True
    category = FindingCategory.OBSERVABILITY
    remediation = (
        "Log the error (with context), rethrow it, show it to the user, or pass it on."
    )
    tags = ("error_handling", "logging")
    # A catch block that mentions one of these is reporting the failure somehow.
    handling_words: Pattern[str] = re.compile(
        r"error|fail|toast|notify|alert|report|capture|warn|log", re.IGNORECASE
    )
    logger_names: Pattern[str] = re.compile(r"^(console|logger|log)\b", re.IGNORECASE)

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        tree = ctx.tree
        for node in tree.walk():
            if node.type != self.syntax.catch_clause:
                continue
            body = node.child_by_field_name("body")
            if body is None or not any(
                c.type not in self.syntax.comments for c in body.named_children
            ):
                continue  # empty (or comment-only) blocks are covered by ROB-EMPTY-CATCH
            if not self._handled(tree, node, body):
                yield RuleHit(
                    tree.line(node),
                    "The error is caught but not logged, rethrown or used",
                )

    def _handled(self, tree: SourceTree, catch: Any, body: Any) -> bool:
        name = self.syntax.catch_parameter(tree, catch)
        statements = " ".join(
            tree.text(c)
            for c in body.named_children
            if c.type not in self.syntax.comments
        )
        if self.handling_words.search(statements):
            return True
        for node in self.syntax.own_nodes(body):
            if node.type == "throw_statement":
                return True
            target = self.syntax.call_target(tree, node)
            if target is not None and self.logger_names.match(target):
                return True
            if name and node.type == "identifier" and tree.text(node) == name:
                return True  # the error is passed on or inspected
        return False


class PrintLogging(SyntaxRule):
    """Writing to the console instead of a logger."""

    id = "OBS-PRINT-LOGGING"
    title = "Console output instead of a logger"
    analyzer = "observability"
    severity = SeverityLevel.INFO
    category = FindingCategory.OBSERVABILITY
    remediation = "Use a logger with levels and remove debug output."
    tags = ("logging",)
    skip_tests = True
    aggregate = True

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        tree = ctx.tree
        for node in tree.walk():
            target = self.syntax.call_target(tree, node)
            if target is not None and self.is_console(target):
                yield RuleHit(tree.line(node), f"`{target}` is used for output")

    def is_console(self, target: str) -> bool:
        """True when a call target writes to the console (language-specific)."""
        raise NotImplementedError


# ------------------------------------------------------------------- readability


class LongLine(Rule):
    """Very long lines are hard to read and to review."""

    id = "RDB-LONG-LINE"
    title = "Line is too long"
    analyzer = "readability"
    severity = SeverityLevel.INFO
    category = FindingCategory.READABILITY
    remediation = "Break the line, or let a formatter do it."
    tags = ("formatting",)
    aggregate = True
    exempt: Pattern[str] = re.compile(r"https?://")

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        limit = ctx.settings.max_line_length
        for number, line in enumerate(ctx.lines, start=1):
            if len(line) > limit and not self.exempt.search(line):
                yield RuleHit(
                    number, f"The line is {len(line)} characters (limit {limit})"
                )


class CommentedCode(SyntaxRule):
    """Code left in comments is noise; version control already remembers it."""

    id = "RDB-COMMENTED-CODE"
    title = "Commented-out code"
    analyzer = "readability"
    severity = SeverityLevel.INFO
    category = FindingCategory.READABILITY
    remediation = "Delete it; it is in version control if it is needed again."
    tags = ("dead_code",)
    aggregate = True
    code: Pattern[str] = re.compile(
        r"[;{}]\s*$|^\s*(const|let|var|function|if|else|for|while|return|import|export|await)\b|\)\s*\{?\s*$|=>"
    )
    min_lines = 2

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        tree = ctx.tree
        for group in self._groups(tree):
            if tree.text(group[0]).startswith("/**"):
                continue  # documentation comments are full of `{@code ...}` and `;`
            text = "\n".join(tree.text(node) for node in group)
            lines = [ln.strip().lstrip("/*").strip() for ln in text.splitlines()]
            lines = [ln for ln in lines if ln]
            hits = sum(1 for ln in lines if self.code.search(ln))
            if hits >= self.min_lines and hits * 2 >= len(lines):
                yield RuleHit(tree.line(group[0]), "A comment contains code")

    def _groups(self, tree: SourceTree) -> List[List[Any]]:
        """Comments in source order, with consecutive `//` lines joined into one group."""
        groups: List[List[Any]] = []
        for node in tree.walk():
            if node.type not in self.syntax.comments:
                continue
            previous = groups[-1][-1] if groups else None
            joins = (
                previous is not None
                and tree.text(previous).startswith("//")
                and tree.text(node).startswith("//")
                and node.start_point[0] == previous.end_point[0] + 1
            )
            if joins:
                groups[-1].append(node)
            else:
                groups.append([node])
        return groups


class TodoComment(SyntaxRule):
    """TODO and FIXME comments mark unfinished work."""

    id = "RDB-TODO"
    title = "TODO or FIXME comment"
    analyzer = "readability"
    severity = SeverityLevel.INFO
    category = FindingCategory.READABILITY
    remediation = "Finish the work, or move it to the issue tracker."
    tags = ("todo",)
    aggregate = True
    pattern: Pattern[str] = re.compile(r"(?<![\w-])(TODO|FIXME|XXX|HACK)\b")

    def check(self, ctx: RuleContext) -> Iterable[RuleHit]:
        tree = ctx.tree
        for node in tree.walk():
            if node.type in self.syntax.comments:
                match = self.pattern.search(tree.text(node))
                if match:
                    yield RuleHit(
                        tree.line(node),
                        f"A `{match.group(1)}` comment is left in the code",
                    )
