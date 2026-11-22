"""The source languages `gnost analyze` understands and the file extensions of each.

`AnalysisLanguages` is the one place that says which files are analyzed, so file discovery, the
analyzers and `--language` agree. Python is checked with its own tools (mypy, bandit, radon, ruff);
the other languages are checked by the rule engine in `gnost.analysis.rules`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class AnalysisLanguage:
    """A language and the extensions of its files."""

    name: str
    extensions: Tuple[str, ...]


class AnalysisLanguages:
    """The registry of analyzable languages (add one here to make `analyze` read its files)."""

    ALL: Tuple[AnalysisLanguage, ...] = (
        AnalysisLanguage("python", (".py",)),
        AnalysisLanguage("javascript", (".js", ".jsx", ".mjs", ".cjs")),
        AnalysisLanguage("typescript", (".ts", ".tsx", ".mts", ".cts")),
        AnalysisLanguage("java", (".java",)),
    )

    def __init__(self, enabled: Optional[Iterable[str]] = None) -> None:
        """`enabled` limits the languages (names, case-insensitive); None means all."""
        wanted = {n.lower() for n in enabled} if enabled else None
        self.languages = [
            lang for lang in self.ALL if wanted is None or lang.name in wanted
        ]
        self._by_extension: Dict[str, str] = {
            ext: lang.name for lang in self.languages for ext in lang.extensions
        }

    @classmethod
    def names(cls) -> List[str]:
        """Every language name, for help text and validation."""
        return [lang.name for lang in cls.ALL]

    def extensions(self) -> Set[str]:
        """The extensions of the enabled languages."""
        return set(self._by_extension)

    # Build output and caches of the JavaScript world; their files are not hand-written code.
    GENERATED_DIRS = frozenset(
        {
            "dist",
            "build",
            "out",
            "coverage",
            ".next",
            ".nuxt",
            ".turbo",
            ".cache",
            "storybook-static",
            "target",  # Maven
            ".gradle",
        }
    )

    def is_generated(self, path: str, root: str) -> bool:
        """True for a non-Python file inside a build-output folder (below `root`)."""
        if self.language_of(path) in (None, "python"):
            return False
        parts = os.path.relpath(path, root).replace(os.sep, "/").split("/")[:-1]
        return any(part in self.GENERATED_DIRS for part in parts)

    def language_of(self, path: str) -> Optional[str]:
        """The language of a file path, or None for an unsupported or disabled one."""
        return self._by_extension.get(os.path.splitext(path)[1].lower())
