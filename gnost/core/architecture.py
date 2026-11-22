"""Architecture rules: which parts of the code may import which, checked on the import graph.

`ForbiddenImportRule` ("code under api/ must not import db/") and `LayerOrderRule` ("a lower layer must
not import a higher one") are `ArchitectureRule` classes; adding a kind of rule is adding a class.
`ArchitectureChecker` runs them on the dependency graph, so it works for every language `onboard` reads.
Used by `gnost onboard` (the Architecture section) and `gnost changes` (violations the change adds).
"""

from __future__ import annotations

import fnmatch
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Sequence, Set, Tuple

from gnost.core.graph import DependencyGraph


@dataclass(frozen=True, order=True)
class Violation:
    """One import that breaks one rule."""

    rule: str
    source: str  # path relative to the scanned folder
    target: str
    message: str = field(default="", compare=False)

    @property
    def key(self) -> Tuple[str, str, str]:
        """What identifies a violation across two versions of the code."""
        return (self.rule, self.source, self.target)

    def to_dict(self) -> Dict[str, str]:
        """The JSON form."""
        return {
            "rule": self.rule,
            "source": self.source,
            "target": self.target,
            "message": self.message,
        }


class PathPatterns:
    """Matches relative paths against globs; a bare folder name matches any folder of that name."""

    def __init__(self, patterns: Iterable[str]) -> None:
        self.patterns = [
            p.strip().replace("\\", "/").strip("/") for p in patterns if p.strip()
        ]

    def matches(self, path: str) -> bool:
        """True when the path matches any pattern."""
        return any(self._one(path, pattern) for pattern in self.patterns)

    @staticmethod
    def _one(path: str, pattern: str) -> bool:
        if not any(c in pattern for c in "*?[") and "/" not in pattern:
            return pattern in path.split("/")[:-1]  # a folder name anywhere in the path
        if pattern.endswith("/**"):
            prefix = pattern[:-3]
            return (
                path == prefix
                or path.startswith(prefix + "/")
                or fnmatch.fnmatchcase(path, pattern)
            )
        return fnmatch.fnmatchcase(path, pattern) or path.startswith(pattern + "/")


class ArchitectureRule(ABC):
    """One rule: looks at one import (an edge of the graph) and says whether it is allowed."""

    name: str

    @abstractmethod
    def violation(self, source: str, target: str) -> str:
        """An explanation if importing `target` from `source` breaks the rule, else an empty string."""


@dataclass
class ForbiddenImportRule(ArchitectureRule):
    """Files matching `sources` must not import files matching `forbidden` (except those in `allow`)."""

    name: str
    sources: Sequence[str]
    forbidden: Sequence[str]
    allow: Sequence[str] = ()

    def __post_init__(self) -> None:
        self._sources = PathPatterns(self.sources)
        self._forbidden = PathPatterns(self.forbidden)
        self._allow = PathPatterns(self.allow)

    def violation(self, source: str, target: str) -> str:
        if not self._sources.matches(source) or not self._forbidden.matches(target):
            return ""
        if self._allow.matches(target) or self._allow.matches(source):
            return ""
        return f"{source} imports {target}, which this rule forbids"


@dataclass
class LayerOrderRule(ArchitectureRule):
    """Layers are listed top to bottom; a file must not import a layer above its own."""

    layers: Sequence[str]
    name: str = "layers"

    def __post_init__(self) -> None:
        self._layers = [PathPatterns([layer]) for layer in self.layers]

    def layer_of(self, path: str) -> int:
        """The index of the first layer whose pattern matches the path, or -1."""
        for index, patterns in enumerate(self._layers):
            if patterns.matches(path):
                return index
        return -1

    def violation(self, source: str, target: str) -> str:
        mine, theirs = self.layer_of(source), self.layer_of(target)
        if mine < 0 or theirs < 0 or theirs >= mine:
            return ""
        return (
            f"`{self.layers[mine]}` imports `{self.layers[theirs]}`, "
            f"which is a layer above it ({' > '.join(self.layers)})"
        )


@dataclass(frozen=True)
class ArchitectureSettings:
    """The `[architecture]` table: explicit rules, an optional layer order, and the CI gate."""

    forbidden: Tuple[ForbiddenImportRule, ...] = ()
    layers: Tuple[str, ...] = ()
    fail: bool = False

    @property
    def configured(self) -> bool:
        """True when at least one rule is set."""
        return bool(self.forbidden or self.layers)

    def rules(self) -> List[ArchitectureRule]:
        """Every rule as an object the checker can run."""
        rules: List[ArchitectureRule] = list(self.forbidden)
        if self.layers:
            rules.append(LayerOrderRule(self.layers))
        return rules


@dataclass
class ArchitectureReport:
    """What the check found, ready for the guide, the JSON and the terminal."""

    configured: bool
    rules: int
    edges_checked: int
    violations: List[Violation] = field(default_factory=list)
    fail: bool = False

    def to_dict(self) -> Dict[str, object]:
        """The JSON form (`architecture` in insights.json)."""
        return {
            "configured": self.configured,
            "rules": self.rules,
            "edges_checked": self.edges_checked,
            "fail": self.fail,
            "violations": [v.to_dict() for v in self.violations],
        }


class ArchitectureChecker:
    """Runs the rules on every import of a dependency graph."""

    def __init__(self, rules: Sequence[ArchitectureRule]) -> None:
        self.rules = list(rules)

    @classmethod
    def for_settings(cls, settings: ArchitectureSettings) -> "ArchitectureChecker":
        """A checker for the rules of an `[architecture]` table."""
        return cls(settings.rules())

    def report(
        self,
        graph: DependencyGraph,
        relative: Callable[[str], str],
        settings: ArchitectureSettings,
    ) -> ArchitectureReport:
        """The violations plus how many rules and imports were checked."""
        if not self.rules:
            return ArchitectureReport(False, 0, 0, fail=settings.fail)
        edges = sum(len(graph.dependencies_of(n)) for n in graph.all_nodes())
        return ArchitectureReport(
            True, len(self.rules), edges, self.check(graph, relative), settings.fail
        )

    def check(
        self, graph: DependencyGraph, relative: Callable[[str], str]
    ) -> List[Violation]:
        """Violations in the graph, sorted. `relative` turns a graph node into a project path."""
        found: Set[Violation] = set()
        for source in graph.all_nodes():
            rel_source = relative(source)
            for target in graph.dependencies_of(source):
                rel_target = relative(target)
                for rule in self.rules:
                    message = rule.violation(rel_source, rel_target)
                    if message:
                        found.add(Violation(rule.name, rel_source, rel_target, message))
        return sorted(found)

    @staticmethod
    def compare(
        before: Sequence[Violation],
        after: Sequence[Violation],
        renamed: Dict[str, str],
    ) -> Tuple[List[Violation], List[Violation]]:
        """(new, fixed): violations only in `after`, and only in `before`.

        `renamed` maps old paths to new ones, so a moved file's old violations are not "fixed" and
        "new" at the same time.
        """

        def moved(v: Violation) -> Violation:
            return Violation(
                v.rule,
                renamed.get(v.source, v.source),
                renamed.get(v.target, v.target),
                v.message,
            )

        old = {moved(v).key for v in before}
        new_keys = {v.key for v in after}
        return (
            [v for v in after if v.key not in old],
            [v for v in before if moved(v).key not in new_keys],
        )


def relative_to(root: str) -> Callable[[str], str]:
    """A function that turns an absolute path into a forward-slash path relative to root."""
    return lambda path: os.path.relpath(path, root).replace(os.sep, "/")
