"""Language shares the way GitHub's language bar counts them (`gnost summary --git`).

GitHub uses Linguist: bytes of committed files, only programming and markup languages, and no
vendored, documentation or generated files. `.gitattributes` overrides (linguist-vendored,
linguist-generated, linguist-documentation, linguist-detectable, linguist-language) apply too.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

PROGRAMMING, MARKUP = "programming", "markup"

# extension (or exact file name) -> (Linguist language, type); only the types GitHub shows
LANGUAGES: Dict[str, Tuple[str, str]] = {
    ".py": ("Python", PROGRAMMING),
    ".pyi": ("Python", PROGRAMMING),
    ".pyx": ("Cython", PROGRAMMING),
    ".js": ("JavaScript", PROGRAMMING),
    ".mjs": ("JavaScript", PROGRAMMING),
    ".cjs": ("JavaScript", PROGRAMMING),
    ".jsx": ("JavaScript", PROGRAMMING),
    ".ts": ("TypeScript", PROGRAMMING),
    ".mts": ("TypeScript", PROGRAMMING),
    ".cts": ("TypeScript", PROGRAMMING),
    ".tsx": ("TSX", PROGRAMMING),
    ".java": ("Java", PROGRAMMING),
    ".kt": ("Kotlin", PROGRAMMING),
    ".kts": ("Kotlin", PROGRAMMING),
    ".scala": ("Scala", PROGRAMMING),
    ".groovy": ("Groovy", PROGRAMMING),
    ".gradle": ("Groovy", PROGRAMMING),
    ".go": ("Go", PROGRAMMING),
    ".rs": ("Rust", PROGRAMMING),
    ".c": ("C", PROGRAMMING),
    ".h": ("C", PROGRAMMING),
    ".cc": ("C++", PROGRAMMING),
    ".cpp": ("C++", PROGRAMMING),
    ".cxx": ("C++", PROGRAMMING),
    ".hpp": ("C++", PROGRAMMING),
    ".cs": ("C#", PROGRAMMING),
    ".fs": ("F#", PROGRAMMING),
    ".swift": ("Swift", PROGRAMMING),
    ".m": ("Objective-C", PROGRAMMING),
    ".mm": ("Objective-C++", PROGRAMMING),
    ".rb": ("Ruby", PROGRAMMING),
    ".php": ("PHP", PROGRAMMING),
    ".pl": ("Perl", PROGRAMMING),
    ".lua": ("Lua", PROGRAMMING),
    ".r": ("R", PROGRAMMING),
    ".dart": ("Dart", PROGRAMMING),
    ".ex": ("Elixir", PROGRAMMING),
    ".exs": ("Elixir", PROGRAMMING),
    ".erl": ("Erlang", PROGRAMMING),
    ".hs": ("Haskell", PROGRAMMING),
    ".clj": ("Clojure", PROGRAMMING),
    ".jl": ("Julia", PROGRAMMING),
    ".zig": ("Zig", PROGRAMMING),
    ".sh": ("Shell", PROGRAMMING),
    ".bash": ("Shell", PROGRAMMING),
    ".zsh": ("Shell", PROGRAMMING),
    ".ps1": ("PowerShell", PROGRAMMING),
    ".bat": ("Batchfile", PROGRAMMING),
    ".cmd": ("Batchfile", PROGRAMMING),
    ".vue": ("Vue", MARKUP),
    ".svelte": ("Svelte", MARKUP),
    ".html": ("HTML", MARKUP),
    ".htm": ("HTML", MARKUP),
    ".css": ("CSS", MARKUP),
    ".scss": ("SCSS", MARKUP),
    ".sass": ("Sass", MARKUP),
    ".less": ("Less", MARKUP),
    ".ipynb": ("Jupyter Notebook", MARKUP),
    ".tex": ("TeX", MARKUP),
    ".mmd": ("Mermaid", MARKUP),
    ".mermaid": ("Mermaid", MARKUP),
    "Dockerfile": ("Dockerfile", PROGRAMMING),
    "Makefile": ("Makefile", PROGRAMMING),
    "makefile": ("Makefile", PROGRAMMING),
    "GNUmakefile": ("Makefile", PROGRAMMING),
    ".mk": ("Makefile", PROGRAMMING),
    "CMakeLists.txt": ("CMake", PROGRAMMING),
    ".cmake": ("CMake", PROGRAMMING),
}

# GitHub's colours for the bar (from Linguist's languages.yml)
COLORS: Dict[str, str] = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "TSX": "#3178c6",
    "Java": "#b07219",
    "Kotlin": "#A97BFF",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "C": "#555555",
    "C++": "#f34b7d",
    "C#": "#178600",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Swift": "#F05138",
    "Shell": "#89e051",
    "HTML": "#e34c26",
    "CSS": "#663399",
    "SCSS": "#c6538c",
    "Vue": "#41b883",
    "Svelte": "#ff3e00",
    "Dockerfile": "#384d54",
    "Makefile": "#427819",
    "Batchfile": "#C1F12E",
    "PowerShell": "#012456",
    "Jupyter Notebook": "#DA5B0B",
    "Groovy": "#4298b8",
    "Scala": "#c22d40",
    "Dart": "#00B4AB",
    "Mermaid": "#ff3670",
}

# Linguist's vendor.yml, documentation.yml and generated heuristics: the common patterns
VENDORED = [
    r"(^|/)vendors?/",
    r"(^|/)node_modules/",
    r"(^|/)bower_components/",
    r"(^|/)third[-_]?party/",
    r"(^|/)extern(al)?/",
    r"(^|/)deps/",
    r"(^|/)dist/",
    r"(^|/)cache/",
    r"(^|/)\.yarn/",
    r"(^|/)[Ff]ixtures/",  # test fixtures
    r"(^|/)Pods/",
    r"(^|/)Carthage/",
    r"(^|/)\.?venv/",
    r"(^|/)\.github/",
    r"(^|/)\.vscode/",
    r"(^|/)\.idea/",
    r"(^|/)gradlew(\.bat)?$",
    r"(^|/)mvnw(\.cmd)?$",
    r"(^|/)\.mvn/wrapper/",
    r"(^|/)gradle/wrapper/",
    r"[.-]min\.(js|css)$",
    r"(^|/)jquery[^/]*\.js$",
    r"(^|/)bootstrap[^/]*\.(js|css)$",
]
DOCUMENTATION = [
    r"^[Dd]ocs?/",
    r"(^|/)[Dd]ocumentation/",
    r"(^|/)[Jj]avadoc/",
    r"^[Mm]an/",
    r"^[Ee]xamples?/",
    r"^[Dd]emos?/",
    r"(^|/)inst/doc/",
    r"^[Ss]amples?/",
    r"(^|/)CITATION(\.cff|(S)?(\.(bib|md))?)$",
    r"(^|/)(CHANGE(S|LOG)?|CONTRIBUTING|COPYING|INSTALL)(\.|$)",
    # README and LICENSE in any capitalisation: GitHub skips gnost/reporters/readme.py too
    r"(^|/)(LICEN[CS]E|[Ll]icen[cs]e|README|[Rr]eadme)(\.|$)",
]
GENERATED = [
    r"_pb2(_grpc)?\.py$",
    r"\.pb\.go$",
    r"\.(js|css)\.map$",
    r"(^|/)package-lock\.json$",
]

ATTRIBUTES = (
    "linguist-vendored",
    "linguist-generated",
    "linguist-documentation",
    "linguist-detectable",
    "linguist-language",
)


class GitError(RuntimeError):
    """The folder is not in a git repository, or git failed."""


@dataclass
class LanguageShare:
    """One language on the bar: its files, bytes and share of the counted bytes."""

    name: str
    files: int = 0
    bytes: int = 0
    share: float = 0.0
    color: str = "#8b949e"


@dataclass
class GitLanguages:
    """The result: languages by bytes (largest first) and what was left out, by reason."""

    languages: List[LanguageShare] = field(default_factory=list)
    skipped: Dict[str, int] = field(default_factory=dict)
    total: int = 0


class LinguistCounter:
    """Counts the committed files under a folder the way GitHub's language bar does.

    Paths are matched from the repository root (Linguist anchors `^docs/` there), and git
    itself evaluates `.gitattributes`, so overrides follow git's own rules.
    """

    def __init__(self, path: str) -> None:
        self.path = os.path.abspath(path)
        self._vendored = re.compile("|".join(VENDORED))
        self._docs = re.compile("|".join(DOCUMENTATION))
        self._generated = re.compile("|".join(GENERATED))

    def count(self) -> GitLanguages:
        """Language shares of the files in the last commit (HEAD) under the folder."""
        root = self._git("rev-parse", "--show-toplevel", cwd=self.path).strip()
        prefix = os.path.relpath(self.path, root).replace(os.sep, "/")
        prefix = "" if prefix == "." else prefix + "/"
        blobs = [b for b in self._blobs(root) if b[0].startswith(prefix)]
        attributes = self._attributes(root, [path for path, _ in blobs])
        result = GitLanguages()
        by_name: Dict[str, LanguageShare] = {}
        for path, size in blobs:
            reason, language = self._classify(path, attributes.get(path, {}))
            if language is None:
                result.skipped[reason] = result.skipped.get(reason, 0) + 1
                continue
            share = by_name.setdefault(
                language, LanguageShare(language, color=COLORS.get(language, "#8b949e"))
            )
            share.files += 1
            share.bytes += size
        result.total = sum(s.bytes for s in by_name.values())
        for share in by_name.values():
            share.share = 100.0 * share.bytes / result.total if result.total else 0.0
        result.languages = sorted(by_name.values(), key=lambda s: (-s.bytes, s.name))
        return result

    def _classify(self, path: str, attrs: Dict[str, str]) -> Tuple[str, Optional[str]]:
        """(why it is left out, or "" ; its language, or None when it is not counted)."""
        language = self.language_of(path)
        override = attrs.get("linguist-language", "unspecified")
        if override not in ("unspecified", "set", "unset"):
            language = (override, PROGRAMMING)
        if language is None:
            return "not a language GitHub shows", None
        for attribute, pattern, reason in (
            ("linguist-vendored", self._vendored, "vendored"),
            ("linguist-documentation", self._docs, "documentation"),
            ("linguist-generated", self._generated, "generated"),
        ):
            value = attrs.get(attribute, "unspecified")
            if value == "set" or (value == "unspecified" and pattern.search(path)):
                return reason, None
        detectable = attrs.get("linguist-detectable", "unspecified")
        if detectable == "unset":
            return "linguist-detectable=false", None
        if language[1] not in (PROGRAMMING, MARKUP) and detectable != "set":
            return "not a language GitHub shows", None
        return "", language[0]

    @staticmethod
    def language_of(path: str) -> Optional[Tuple[str, str]]:
        """The Linguist language and type of a path, from its file name or extension."""
        name = path.rsplit("/", 1)[-1]
        if name in LANGUAGES:
            return LANGUAGES[name]
        if name.startswith("Dockerfile"):
            return LANGUAGES["Dockerfile"]
        ext = os.path.splitext(name)[1]
        return LANGUAGES.get(ext.lower()) or LANGUAGES.get(ext)

    def _blobs(self, root: str) -> List[Tuple[str, int]]:
        """(path, size) of every regular file in HEAD; symlinks and submodules are skipped."""
        out = self._git("ls-tree", "-r", "-l", "-z", "HEAD", cwd=root)
        blobs = []
        for entry in out.split("\0"):
            if not entry:
                continue
            meta, path = entry.split("\t", 1)
            mode, kind, _, size = meta.split()
            if kind == "blob" and mode in ("100644", "100755"):
                blobs.append((path, int(size)))
        return blobs

    def _attributes(self, root: str, paths: List[str]) -> Dict[str, Dict[str, str]]:
        """The linguist-* attributes of each path, as git reports them (set/unset/value)."""
        if not paths:
            return {}
        out = self._git(
            "check-attr", "-z", "--stdin", *ATTRIBUTES, cwd=root, stdin="\0".join(paths)
        )
        found: Dict[str, Dict[str, str]] = {}
        parts = out.split("\0")
        for k in range(0, len(parts) - 2, 3):
            path, attribute, value = parts[k], parts[k + 1], parts[k + 2]
            if value != "unspecified":
                found.setdefault(path, {})[attribute] = value
        return found

    @staticmethod
    def _git(*args: str, cwd: str, stdin: Optional[str] = None) -> str:
        try:
            done = subprocess.run(
                ["git", *args],
                cwd=cwd,
                input=stdin,
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as exc:
            raise GitError("git is not installed") from exc
        except subprocess.CalledProcessError as exc:
            message = (exc.stderr or "").strip().splitlines()
            raise GitError(message[-1] if message else "git failed") from exc
        return done.stdout
