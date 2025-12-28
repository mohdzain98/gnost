# gnost/languages/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class EntryPoint:
    """
    Represents a detected entry point in the codebase.
    """

    def __init__(self, file: str, reason: str):
        self.file = file
        self.reason = reason

    def __repr__(self):
        return f"EntryPoint(file={self.file}, reason={self.reason})"


class ImportEdge:
    """
    Represents an import dependency: file -> imported module/file
    """

    def __init__(self, source: str, target: str):
        self.source = source
        self.target = target


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
