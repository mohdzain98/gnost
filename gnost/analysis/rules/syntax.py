"""How a language's syntax tree is shaped, for the rules that work the same in every language.

A `Syntax` names the node types for functions, branches and comments, and knows how to read a
function's name, its parameter count and the target of a call. Shared rules (complexity, nesting,
swallowed errors, ...) ask the syntax instead of hard-coding node names, so a new language adds a
`Syntax` subclass and a few thin rule subclasses, not a copy of every rule.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterator, List, Optional, Tuple

from gnost.parsing import SourceTree


class Syntax(ABC):
    """Node-type tables and small readers for one language's tree-sitter grammar."""

    functions: Tuple[str, ...] = ()
    callbacks: Tuple[str, ...] = ()  # function nodes that count nesting on their own
    nesting: Tuple[str, ...] = ()
    decisions: Tuple[str, ...] = ()
    short_circuit: Tuple[str, ...] = ("&&", "||")
    comments: Tuple[str, ...] = ("comment",)
    catch_clause: str = "catch_clause"

    def iter_functions(self, tree: SourceTree) -> Iterator[Any]:
        """Every function, method and lambda in the file."""
        for node in tree.walk():
            if node.type in self.functions:
                yield node

    def own_nodes(self, node: Any) -> Iterator[Any]:
        """The nodes of a function's own body: nested functions are not entered."""
        stack: List[Any] = list(reversed(node.children))
        while stack:
            current = stack.pop()
            yield current
            if current.type in self.functions:
                continue
            stack.extend(reversed(current.children))

    @staticmethod
    def line_span(node: Any) -> int:
        """How many lines a node covers."""
        return int(node.end_point[0]) - int(node.start_point[0]) + 1

    @staticmethod
    def operator_of(node: Any) -> Optional[str]:
        """The operator token of a binary expression."""
        operator = node.child_by_field_name("operator")
        return operator.type if operator is not None else None

    @abstractmethod
    def function_name(self, tree: SourceTree, node: Any) -> str:
        """The name of a function, or a placeholder for an anonymous one."""

    @abstractmethod
    def parameter_count(self, node: Any) -> int:
        """The number of declared parameters."""

    @abstractmethod
    def call_target(self, tree: SourceTree, node: Any) -> Optional[str]:
        """For a call node, the text of what is called (`console.log`, `logger.error`); else None."""

    @abstractmethod
    def catch_parameter(self, tree: SourceTree, clause: Any) -> Optional[str]:
        """The name bound by a catch clause, if it has one."""

    def decision_points(self, function: Any) -> int:
        """Branches, loops, cases, catches, ternaries and short-circuits in the function's own body."""
        count = 0
        for node in self.own_nodes(function):
            if node.type in self.decisions and self.counts_as_decision(node):
                count += 1
            elif (
                node.type == "binary_expression"
                and self.operator_of(node) in self.short_circuit
            ):
                count += 1
        return count

    def counts_as_decision(self, node: Any) -> bool:
        """Hook for nodes that only sometimes add a path (a `default` label does not)."""
        return True

    def max_nesting(self, function: Any) -> int:
        """The deepest chain of nested control statements in the function's own body."""
        deepest = 0
        stack = [(child, 0) for child in function.children]
        while stack:
            node, level = stack.pop()
            if node.type in self.nesting:
                level += 1
                deepest = max(deepest, level)
            if node.type in self.callbacks:
                continue  # a callback starts its own count
            stack.extend((child, level) for child in node.children)
        return deepest
