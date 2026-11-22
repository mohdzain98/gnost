"""A parsed source file with the few helpers GNOST needs on top of a tree-sitter tree.

`SourceTree` keeps the bytes the tree was built from, so node text can be read back, and walks
the tree without recursion (deep expressions cannot hit the recursion limit). Grammar-specific node
names do not appear here; they live in `gnost.parsing.queries`.
"""

from __future__ import annotations

from typing import Any, Iterator, Optional

# Children of a string node that mean it is not a plain literal.
NOT_LITERAL = {"template_substitution", "escape_sequence"}


class SourceTree:
    """A tree-sitter tree plus the source it was parsed from."""

    def __init__(self, source: bytes, root: Any, language: str) -> None:
        self.source = source
        self.root = root
        self.language = language

    @property
    def has_error(self) -> bool:
        """True when the parser had to recover from a syntax error somewhere."""
        return bool(self.root.has_error)

    def walk(self) -> Iterator[Any]:
        """Every node, parents before children, in source order."""
        stack = [self.root]
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.children))

    def text(self, node: Any) -> str:
        """The source text of a node."""
        return self.source[node.start_byte : node.end_byte].decode("utf-8", "replace")

    def line(self, node: Any) -> int:
        """The 1-based line a node starts on."""
        return int(node.start_point[0]) + 1

    def string_value(self, node: Optional[Any]) -> Optional[str]:
        """The value of a plain string literal node, or None for anything else.

        A string with an escape or a `${}` substitution is not a plain literal, so None.
        """
        if node is None or node.type not in ("string", "template_string"):
            return None
        if any(child.type in NOT_LITERAL for child in node.children):
            return None
        return "".join(
            self.text(child)
            for child in node.children
            if child.type == "string_fragment"
        ) or ("" if node.child_count <= 2 else None)
