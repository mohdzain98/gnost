"""The tree-sitter node names of JavaScript, TypeScript and TSX, for the shared rules."""

from __future__ import annotations

from typing import Any, Optional

from gnost.analysis.rules.syntax import Syntax
from gnost.parsing import SourceTree


class EcmaScriptSyntax(Syntax):
    """JavaScript and TypeScript."""

    functions = (
        "function_declaration",
        "function_expression",
        "function",
        "arrow_function",
        "method_definition",
        "generator_function_declaration",
        "generator_function",
    )
    callbacks = ("arrow_function", "function_expression", "function")
    nesting = (
        "if_statement",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
        "try_statement",
        "switch_statement",
    )
    short_circuit = ("&&", "||", "??")
    decisions = (
        "if_statement",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
        "switch_case",
        "catch_clause",
        "ternary_expression",
    )

    def function_name(self, tree: SourceTree, node: Any) -> str:
        """From the declaration, or the variable, property or assignment the function is given to."""
        name = node.child_by_field_name("name")
        if name is not None:
            return tree.text(name)
        parent = node.parent
        if parent is None:
            return "<anonymous>"
        if parent.type == "variable_declarator":
            target = parent.child_by_field_name("name")
        elif parent.type == "pair":
            target = parent.child_by_field_name("key")
        elif parent.type == "assignment_expression":
            target = parent.child_by_field_name("left")
        else:
            target = None
        return tree.text(target) if target is not None else "<anonymous>"

    def parameter_count(self, node: Any) -> int:
        """Declared parameters (a TypeScript `this` parameter is not counted)."""
        params = node.child_by_field_name("parameters")
        if params is None:
            return 1 if node.child_by_field_name("parameter") is not None else 0
        count = 0
        for child in params.named_children:
            if child.type == "comment":
                continue
            if child.type in ("required_parameter", "optional_parameter"):
                first = child.children[0] if child.children else None
                if first is not None and first.type == "this":
                    continue
            count += 1
        return count

    def call_target(self, tree: SourceTree, node: Any) -> Optional[str]:
        """The callee of a `call_expression`."""
        if node.type != "call_expression":
            return None
        function = node.child_by_field_name("function")
        return tree.text(function) if function is not None else None

    def catch_parameter(self, tree: SourceTree, clause: Any) -> Optional[str]:
        """The identifier in `catch (err)`; None for `catch {` and destructuring."""
        parameter = clause.child_by_field_name("parameter")
        if parameter is not None and parameter.type == "identifier":
            return tree.text(parameter)
        return None


ECMASCRIPT = EcmaScriptSyntax()
