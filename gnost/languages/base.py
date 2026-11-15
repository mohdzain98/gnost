# gnost/languages/base.py

from abc import ABC, abstractmethod
from typing import List, Optional


class EntryPoint:
    """
    Represents a detected entry point in the codebase.
    """

    PRIMARY = 0
    SECONDARY = 1

    def __init__(self, file: str, reason: str, priority: int = 0):
        self.file = file
        self.reason = reason
        # PRIMARY: where the application starts. SECONDARY: helper scripts.
        self.priority = priority

    def __repr__(self):
        return f"EntryPoint(file={self.file}, reason={self.reason})"


class ImportEdge:
    """
    Represents an import dependency: file -> imported module/file.

    `names` holds the names imported from `target` (``from target import a, b``)
    so a resolver can tell submodules from symbols. `level` is the number of
    leading dots of a relative import (0 for absolute imports). `deferred` marks
    imports that do not run when the module loads: inside a function, under
    ``TYPE_CHECKING``, a dynamic ``import()`` or a type-only import.
    """

    def __init__(
        self,
        source: str,
        target: str,
        names: Optional[List[str]] = None,
        level: int = 0,
        deferred: bool = False,
    ):
        self.source = source
        self.target = target
        self.names = names or []
        self.level = level
        self.deferred = deferred


class LanguageAdapter(ABC):
    """
    Base interface for all language adapters.

    GNOST core must rely ONLY on this interface.
    """

    name: str = "unknown"
    extensions: List[str] = []

    # -------------------------
    # Detection
    # -------------------------

    @abstractmethod
    def detect_entry_points(self, files: List[str]) -> List[EntryPoint]:
        """
        Detect probable entry points in the project.
        """
        raise NotImplementedError

    @abstractmethod
    def detect_imports(self, file_path: str, content: str) -> List[ImportEdge]:
        """
        Detect imports in a file.
        """
        raise NotImplementedError

    @abstractmethod
    def detect_framework(self, files: List[str]) -> Optional[str]:
        """
        Detect framework (FastAPI, Express, Spring, etc.)
        """
        raise NotImplementedError

    # -------------------------
    # Optional Enhancements
    # -------------------------

    def detect_framework_from_manifest(self, root: str) -> Optional[str]:
        """
        Detect a framework from project manifests (package.json, ...).
        Optional — more reliable than scanning source when a manifest exists.
        """
        return None

    def detect_calls(self, content: str) -> List[str]:
        """
        Detect function / method calls.
        Optional — heuristic based.
        """
        return []

    def is_entry_file_name(self, file_path: str) -> bool:
        """
        Heuristic based on file naming conventions.
        """
        return False
