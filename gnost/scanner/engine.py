import os
from typing import Dict, List

from gnost.languages.base import LanguageAdapter
from gnost.scanner.filters import (
    is_gitignored,
    is_virtualenv_dir,
    load_gitignore,
    should_ignore,
)
from gnost.scanner.loc import scan
from gnost.scanner.models import FileInfo, ScanResult


class ScannerEngine:
    """
    Orchestrates repo scanning using language adapters.
    """

    def __init__(self, adapters: List[LanguageAdapter]):
        self.adapters = adapters
        self.extension_map = self._build_extension_map()

    # -------------------------
    # Public API
    # -------------------------

    def scan(self, root: str) -> ScanResult:
        gitignore = load_gitignore(root)
        files = self._discover_files(root, gitignore)

        detected_files: List[FileInfo] = []
        entry_points = []
        languages_count: Dict[str, int] = {}
        framework = None

        for adapter in self.adapters:
            lang_files = [f for f in files if self._matches_language(f, adapter)]

            if not lang_files:
                continue

            languages_count[adapter.name] = len(lang_files)

            # Detect entry points
            entry_points.extend(adapter.detect_entry_points(lang_files))

            # Detect framework (first hit wins)
            if framework is None:
                framework = adapter.detect_framework(lang_files)

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

        return ScanResult(
            root=root,
            languages=languages_count,
            files=detected_files,
            entry_points=entry_points,
            framework=framework,
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

    def _matches_language(self, file_path: str, adapter: LanguageAdapter) -> bool:
        return any(file_path.endswith(ext) for ext in adapter.extensions)

    def _build_extension_map(self) -> Dict[str, LanguageAdapter]:
        mapping = {}
        for adapter in self.adapters:
            for ext in adapter.extensions:
                mapping[ext] = adapter
        return mapping

    def _read_file(self, file_path: str) -> str | None:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return None
