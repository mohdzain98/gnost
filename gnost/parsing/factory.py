"""Creates tree-sitter parsers on demand and says when one is not available.

`ParserFactory` loads each grammar the first time it is needed and keeps one parser per language.
If a grammar cannot be loaded (no wheel for the platform) or `GNOST_PARSER=regex` is set, `parse`
returns None and callers use their older text-based code, so a missing grammar never stops a scan.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, Iterable, Mapping, Optional

from gnost.parsing.tree import SourceTree

SWITCH = "GNOST_PARSER"  # set to "regex" to skip tree-sitter

# file extension -> grammar key
LANGUAGE_BY_EXTENSION = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
}
# GNOST language name -> grammar keys it uses
GRAMMARS_OF = {
    "javascript": ("javascript",),
    "typescript": ("typescript", "tsx"),
    "java": ("java",),
}


def _load_javascript() -> Any:
    import tree_sitter_javascript

    return tree_sitter_javascript.language()


def _load_typescript() -> Any:
    import tree_sitter_typescript

    return tree_sitter_typescript.language_typescript()


def _load_tsx() -> Any:
    import tree_sitter_typescript

    return tree_sitter_typescript.language_tsx()


def _load_java() -> Any:
    import tree_sitter_java

    return tree_sitter_java.language()


LOADERS: Dict[str, Callable[[], Any]] = {
    "javascript": _load_javascript,
    "typescript": _load_typescript,
    "tsx": _load_tsx,
    "java": _load_java,
}


class ParserFactory:
    """One lazily created parser per grammar; unavailable grammars are remembered."""

    def __init__(
        self,
        environ: Optional[Mapping[str, str]] = None,
        loaders: Optional[Mapping[str, Callable[[], Any]]] = None,
    ) -> None:
        self.environ = environ if environ is not None else os.environ
        self.loaders = dict(loaders if loaders is not None else LOADERS)
        self._parsers: Dict[str, Any] = {}
        self._missing: Dict[str, str] = {}

    @property
    def enabled(self) -> bool:
        """False when the user switched tree-sitter off."""
        return self.environ.get(SWITCH, "").lower() != "regex"

    def grammar_for(self, extension: str) -> Optional[str]:
        """The grammar key for a file extension, or None for an unknown one."""
        return LANGUAGE_BY_EXTENSION.get(extension.lower())

    def available(self, grammar: str) -> bool:
        """True when this grammar can be loaded here."""
        return self.enabled and self._parser(grammar) is not None

    def parse(self, grammar: str, source: bytes) -> Optional[SourceTree]:
        """Parse source with a grammar; None when it is unavailable or parsing fails."""
        if not self.enabled:
            return None
        parser = self._parser(grammar)
        if parser is None:
            return None
        try:
            tree = parser.parse(source)
        except Exception as exc:  # a parser bug must not stop the scan
            self._missing[grammar] = f"parse failed: {exc}"
            return None
        return SourceTree(source, tree.root_node, grammar)

    def reason(self, grammar: str) -> Optional[str]:
        """Why a grammar is unavailable, or None when it is fine."""
        if not self.enabled:
            return f"switched off by {SWITCH}=regex"
        self._parser(grammar)
        return self._missing.get(grammar)

    def status(self, languages: Iterable[str]) -> Dict[str, str]:
        """For each GNOST language, how its files are read: ast, tree-sitter or regex."""
        out: Dict[str, str] = {}
        for language in sorted(set(languages)):
            if language == "python":
                out[language] = "ast"
            elif language in GRAMMARS_OF:
                ok = all(self.available(g) for g in GRAMMARS_OF[language])
                out[language] = "tree-sitter" if ok else "regex"
        return out

    # ------------------------------------------------------------ internals

    def _parser(self, grammar: str) -> Optional[Any]:
        if grammar in self._parsers:
            return self._parsers[grammar]
        if grammar in self._missing or grammar not in self.loaders:
            return None
        try:
            from tree_sitter import Language, Parser

            parser = Parser(Language(self.loaders[grammar]()))
        except Exception as exc:  # no wheel, wrong ABI, import error
            self._missing[grammar] = str(exc)
            return None
        self._parsers[grammar] = parser
        return parser


_default: Optional[ParserFactory] = None


def default_factory() -> ParserFactory:
    """The shared factory (created on first use)."""
    global _default
    if _default is None:
        _default = ParserFactory()
    return _default
