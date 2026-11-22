"""What GNOST asks of a parsed file, per language: imports, Java packages and type references.

Grammar node names (`import_statement`, `type_identifier`, ...) are confined to these classes, so
a grammar change touches one place. `EcmaScriptQueries` serves JavaScript, TypeScript and TSX;
`JavaQueries` serves Java. Syntax errors are tolerated: broken parts are skipped, the rest is read.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Set

from gnost.parsing.tree import SourceTree


@dataclass(frozen=True)
class ImportRef:
    """One imported module and whether the import runs when the file loads."""

    target: str
    deferred: bool = False  # dynamic import() and type-only imports


class EcmaScriptQueries:
    """Imports of JavaScript and TypeScript files (ES modules, require, import())."""

    def imports(self, tree: SourceTree) -> List[ImportRef]:
        """Every literal import in the file, in source order (duplicates included)."""
        found: List[ImportRef] = []
        for node in tree.walk():
            if node.type in ("import_statement", "export_statement"):
                ref = self._statement(tree, node)
                if ref:
                    found.append(ref)
            elif node.type == "call_expression":
                ref = self._call(tree, node)
                if ref:
                    found.append(ref)
        return found

    def _statement(self, tree: SourceTree, node: Any) -> Optional[ImportRef]:
        """`import ... from 'x'`, `export ... from 'x'`, `import 'x'`, `import a = require('x')`."""
        source = node.child_by_field_name("source")
        if source is None:
            for child in node.children:  # import x = require('y')
                if child.type == "import_require_clause":
                    source = next(
                        (c for c in child.children if c.type == "string"), None
                    )
        value = tree.string_value(source)
        if not value:
            return None
        return ImportRef(value, self._type_only(node))

    @staticmethod
    def _type_only(node: Any) -> bool:
        """`import type`, `export type`, or an import whose every name is marked `type`."""
        if any(child.type == "type" and not child.is_named for child in node.children):
            return True
        specifiers = [
            spec
            for child in node.children
            for named in child.children
            for spec in named.children
            if spec.type in ("import_specifier", "export_specifier")
        ]
        return bool(specifiers) and all(
            any(part.type == "type" and not part.is_named for part in spec.children)
            for spec in specifiers
        )

    @staticmethod
    def _call(tree: SourceTree, node: Any) -> Optional[ImportRef]:
        """`require('x')` (eager) and `import('x')` (deferred)."""
        function = node.child_by_field_name("function")
        arguments = node.child_by_field_name("arguments")
        if function is None or arguments is None:
            return None
        is_require = function.type == "identifier" and tree.text(function) == "require"
        if function.type != "import" and not is_require:
            return None
        first = next((c for c in arguments.children if c.is_named), None)
        value = tree.string_value(first)
        return ImportRef(value, deferred=not is_require) if value else None


class JavaQueries:
    """Package, imports, declared types and referenced type names of a Java file."""

    DECLARATIONS = (
        "class_declaration",
        "interface_declaration",
        "enum_declaration",
        "record_declaration",
        "annotation_type_declaration",
    )
    # An uppercase identifier here is a class name (`Utils.run()`, `Config.X`, `@Service`).
    CLASS_NAME_PARENTS = ("method_invocation", "field_access")
    ANNOTATIONS = ("marker_annotation", "annotation")
    NAME_NODES = ("scoped_identifier", "identifier")

    def package(self, tree: SourceTree) -> str:
        """The dotted package name, or an empty string for the default package."""
        for node in tree.root.children:
            if node.type == "package_declaration":
                name = next(
                    (c for c in node.children if c.type in self.NAME_NODES), None
                )
                return tree.text(name) if name is not None else ""
        return ""

    def imports(self, tree: SourceTree) -> List[str]:
        """Imported class names. A static import names its class; a wildcard import is skipped."""
        found: List[str] = []
        for node in tree.root.children:
            if node.type != "import_declaration":
                continue
            name = next((c for c in node.children if c.type in self.NAME_NODES), None)
            if name is None:
                continue
            text = tree.text(name)
            has_star = any(c.type == "asterisk" for c in node.children)
            is_static = any(c.type == "static" for c in node.children)
            if has_star and not is_static:
                continue  # a package, not a class
            if is_static and not has_star and "." in text:
                text = text.rsplit(".", 1)[0]  # drop the imported member
            found.append(text)
        return found

    def declared_types(self, tree: SourceTree) -> Set[str]:
        """Names of every type declared in the file, nested ones included."""
        names: Set[str] = set()
        for node in tree.walk():
            if node.type in self.DECLARATIONS:
                name = node.child_by_field_name("name")
                if name is not None:
                    names.add(tree.text(name))
        return names

    def referenced_types(self, tree: SourceTree) -> Set[str]:
        """Simple names of the types the file uses, in declarations, expressions and annotations."""
        names: Set[str] = set()
        for node in tree.walk():
            if node.type == "type_identifier":
                names.add(tree.text(node))
            elif node.type == "identifier":
                text = tree.text(node)
                if text[:1].isupper() and self._is_class_name(node):
                    names.add(text)
        return names

    def _is_class_name(self, node: Any) -> bool:
        parent = node.parent
        if parent is None:
            return False
        if parent.type in self.ANNOTATIONS:
            return True
        if parent.type in self.CLASS_NAME_PARENTS:
            return parent.child_by_field_name("object") == node
        return False
