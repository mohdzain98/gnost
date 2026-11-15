from __future__ import annotations

import os
from typing import Dict, List, Optional

from gnost.languages.base import EntryPoint, LanguageAdapter
from gnost.scanner.filters import (
    is_excluded,
    is_gitignored,
    is_noise_file,
    is_test_file,
    is_virtualenv_dir,
    load_gitignore,
    should_ignore,
)
from gnost.scanner.models import FileInfo, ScanResult


class ScannerEngine:
    """
    Orchestrates repo scanning using language adapters.
    """

    def __init__(
        self, adapters: List[LanguageAdapter], exclude: Optional[List[str]] = None
    ):
        self.adapters = adapters
        self.exclude = list(exclude or [])
        self.extension_map = self._build_extension_map()

    # -------------------------
    # Public API
    # -------------------------

    def scan(self, root: str) -> ScanResult:
        gitignore = load_gitignore(root)
        files = [
            f
            for f in self._discover_files(root, gitignore)
            if not is_noise_file(f, root)
            and not is_test_file(f, root)
            and not is_excluded(f, root, self.exclude)
        ]

        detected_files: List[FileInfo] = []
        entry_points = []
        languages_count: Dict[str, int] = {}
        frameworks: List[str] = []

        for adapter in self.adapters:
            lang_files = [f for f in files if self._matches_language(f, adapter)]

            if not lang_files:
                continue

            languages_count[adapter.name] = len(lang_files)

            # Detect entry points
            for ep in adapter.detect_entry_points(lang_files):
                if not self._plausible_entry(ep, root):
                    continue
                ep.priority = self._entry_priority(ep, adapter)
                entry_points.append(ep)

            # Detect framework: manifest first, then source; keep every distinct
            # one (a repo can hold a FastAPI backend and a React frontend).
            detected = adapter.detect_framework_from_manifest(root)
            if detected is None:  # no manifest at all: guess from source
                detected = adapter.detect_framework(lang_files)
            for name in (detected or "").split(", "):
                if name and name not in frameworks:
                    frameworks.append(name)

            # Detect imports per file
            for file_path in lang_files:
                content = self._read_file(file_path)
                if content is None:
                    continue

                imports = adapter.detect_imports(file_path, content)

                detected_files.append(
                    FileInfo(
                        path=file_path,
                        language=adapter.name,
                        imports=imports,
                    )
                )

        entry_points.sort(key=lambda e: (e.priority, e.file, e.reason))

        return ScanResult(
            root=root,
            languages=languages_count,
            files=detected_files,
            entry_points=entry_points,
            framework=", ".join(self._drop_fallbacks(frameworks)) or None,
        )

    # -------------------------
    # Internal Helpers
    # -------------------------

    def _discover_files(self, root: str, gitignore: list[str]) -> List[str]:
        collected = []

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d
                for d in dirnames
                if not is_virtualenv_dir(os.path.join(dirpath, d))
                and not is_gitignored(os.path.join(dirpath, d), root, gitignore)
            ]
            if should_ignore(dirpath) or is_gitignored(dirpath, root, gitignore):
                continue

            for file in filenames:
                full_path = os.path.join(dirpath, file)
                if should_ignore(full_path) or is_gitignored(
                    full_path, root, gitignore
                ):
                    continue
                collected.append(full_path)

        return collected

    @staticmethod
    def _drop_fallbacks(frameworks: List[str]) -> List[str]:
        """ "Plain Java" only means nothing else was found."""
        real = [f for f in frameworks if f != "Plain Java"]
        return real or frameworks

    ENTRY_DIRS = {"", "src", "server", "app", "bin"}

    @classmethod
    def _plausible_entry(cls, ep: EntryPoint, root: str) -> bool:
        """A file called index/main/app is an entry point only near the top.

        `src/lib/index.ts` is a barrel file, not where the program starts.
        """
        if ep.reason != "Common JS entry filename":
            return True
        rel_dir = os.path.relpath(os.path.dirname(ep.file), root)
        last = "" if rel_dir == "." else os.path.basename(rel_dir)
        return last in cls.ENTRY_DIRS

    @staticmethod
    def _entry_priority(ep: EntryPoint, adapter: LanguageAdapter) -> int:
        """A bare `__main__` guard in a helper script is secondary; app starts are primary."""
        if ep.reason == "__main__ guard" and not adapter.is_entry_file_name(ep.file):
            return EntryPoint.SECONDARY
        return EntryPoint.PRIMARY

    def _matches_language(self, file_path: str, adapter: LanguageAdapter) -> bool:
        return any(file_path.endswith(ext) for ext in adapter.extensions)

    def _build_extension_map(self) -> Dict[str, LanguageAdapter]:
        mapping = {}
        for adapter in self.adapters:
            for ext in adapter.extensions:
                mapping[ext] = adapter
        return mapping

    def _read_file(self, file_path: str) -> Optional[str]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return None
