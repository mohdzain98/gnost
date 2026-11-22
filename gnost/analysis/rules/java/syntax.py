"""The tree-sitter node names of Java, for the shared rules."""

from __future__ import annotations

from typing import Any, Optional

from gnost.analysis.rules.syntax import Syntax
from gnost.parsing import SourceTree


class JavaSyntax(Syntax):
    """Java methods, constructors and lambdas."""

    functions = (
        "method_declaration",
        "constructor_declaration",
        "compact_constructor_declaration",
        "lambda_expression",
    )
    callbacks = ("lambda_expression",)
    nesting = (
        "if_statement",
        "for_statement",
        "enhanced_for_statement",
        "while_statement",
        "do_statement",
        "try_statement",
        "try_with_resources_statement",
        "switch_expression",
        "switch_statement",
        "synchronized_statement",
    )
    decisions = (
        "if_statement",
        "for_statement",
        "enhanced_for_statement",
        "while_statement",
        "do_statement",
        "switch_block_statement_group",
        "switch_rule",
        "catch_clause",
        "ternary_expression",
    )
    comments = ("line_comment", "block_comment")

    def counts_as_decision(self, node: Any) -> bool:
        """A `default` label adds no path of its own."""
        if node.type in ("switch_block_statement_group", "switch_rule"):
            label = next((c for c in node.children if c.type == "switch_label"), None)
            return not (
                label is not None
                and label.children
                and label.children[0].type == "default"
            )
        return True

    def function_name(self, tree: SourceTree, node: Any) -> str:
        """The method or constructor name; a lambda takes the name of its variable."""
        name = node.child_by_field_name("name")
        if name is not None:
            return tree.text(name)
        parent = node.parent
        if parent is not None and parent.type == "variable_declarator":
            target = parent.child_by_field_name("name")
            if target is not None:
                return tree.text(target)
        return "<lambda>"

    def parameter_count(self, node: Any) -> int:
        """Declared parameters of a method, constructor or lambda."""
        params = node.child_by_field_name("parameters")
        if params is None:
            return 0
        if params.type == "identifier":
            return 1  # `x -> ...`
        return sum(
            1
            for child in params.named_children
            if child.type not in ("line_comment", "block_comment", "receiver_parameter")
        )

    def call_target(self, tree: SourceTree, node: Any) -> Optional[str]:
        """The text before the argument list of a method call, for example `log.error`."""
        if node.type != "method_invocation":
            return None
        arguments = node.child_by_field_name("arguments")
        end = arguments.start_byte if arguments is not None else node.end_byte
        return tree.source[node.start_byte : end].decode("utf-8", "replace").strip()

    def catch_parameter(self, tree: SourceTree, clause: Any) -> Optional[str]:
        """The name bound by `catch (IOException e)`."""
        for child in clause.children:
            if child.type == "catch_formal_parameter":
                name = child.child_by_field_name("name")
                return tree.text(name) if name is not None else None
        return None


JAVA = JavaSyntax()
