# gnost/languages/javascript.py

import json
import os
import re
from typing import List, Optional

from gnost.languages.base import LanguageAdapter, EntryPoint, ImportEdge


class JavaScriptAdapter(LanguageAdapter):
    name = "javascript"
    extensions = [".js"]

    # -------------------------
    # Entry Points
    # -------------------------

    def detect_entry_points(self, files: List[str]) -> List[EntryPoint]:
        entry_points: List[EntryPoint] = []

        for file in files:
            fname = os.path.basename(file).lower()

            if fname in {"index.js", "main.js", "server.js", "app.js"}:
                entry_points.append(
                    EntryPoint(file=file, reason="Common JS entry filename")
                )

            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            if re.search(r"\.listen\s*\(", content):
                entry_points.append(
                    EntryPoint(file=file, reason="Server listen() call")
                )

        return entry_points

    # -------------------------
    # Imports
    # -------------------------

    def detect_imports(self, file_path: str, content: str) -> List[ImportEdge]:
        imports: List[ImportEdge] = []

        # ES imports: import x from './x'
        for match in re.findall(
            r'import\s+.*?\s+from\s+[\'"](.+?)[\'"]',
            content,
        ):
            imports.append(ImportEdge(source=file_path, target=match))

        # require(): const x = require('./x')
        for match in re.findall(
            r'require\(\s*[\'"](.+?)[\'"]\s*\)',
            content,
        ):
            imports.append(ImportEdge(source=file_path, target=match))

        return imports

    # -------------------------
    # Framework Detection
    # -------------------------

    def detect_framework(self, files: List[str]) -> Optional[str]:
        for file in files:
            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            if "express(" in content:
                return "Express"
            if "@nestjs" in content:
                return "NestJS"

        return None
