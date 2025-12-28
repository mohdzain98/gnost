# gnost/languages/python.py

import re
from typing import List, Optional

from gnost.languages.base import LanguageAdapter, EntryPoint, ImportEdge


class PythonAdapter(LanguageAdapter):
    name = "python"
    extensions = [".py"]

    # -------------------------
    # Entry Point Detection
    # -------------------------

    def detect_entry_points(self, files: List[str]) -> List[EntryPoint]:
        entry_points: List[EntryPoint] = []

        for file in files:
            if not file.endswith(".py"):
                continue

            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            # 1. if __name__ == "__main__"
            if "__name__" in content and "__main__" in content:
                entry_points.append(EntryPoint(file=file, reason="__main__ guard"))

            # 2. FastAPI / Flask app initialization
            if re.search(r"FastAPI\s*\(", content):
                entry_points.append(
                    EntryPoint(file=file, reason="FastAPI app initialization")
                )

            if re.search(r"Flask\s*\(", content):
                entry_points.append(
                    EntryPoint(file=file, reason="Flask app initialization")
                )

            # 3. Uvicorn / Gunicorn run
            if re.search(r"uvicorn\.run", content):
                entry_points.append(EntryPoint(file=file, reason="uvicorn.run"))

        return entry_points

    # -------------------------
    # Import Detection
    # -------------------------

    def detect_imports(self, file_path: str, content: str) -> List[ImportEdge]:
        imports: List[ImportEdge] = []

        # import x
        for match in re.findall(
            r"^\s*import\s+([a-zA-Z0-9_\.]+)", content, re.MULTILINE
        ):
            imports.append(ImportEdge(source=file_path, target=match))

        # from x import y
        for match in re.findall(
            r"^\s*from\s+([a-zA-Z0-9_\.]+)\s+import", content, re.MULTILINE
        ):
            imports.append(ImportEdge(source=file_path, target=match))

        return imports

    # -------------------------
    # Framework Detection
    # -------------------------

    def detect_framework(self, files: List[str]) -> Optional[str]:
        framework_signals = {
            "FastAPI": r"FastAPI\s*\(",
            "Flask": r"Flask\s*\(",
            "Django": r"django\.setup|manage\.py",
        }

        for file in files:
            if not file.endswith(".py"):
                continue

            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            for framework, pattern in framework_signals.items():
                if re.search(pattern, content):
                    return framework

        return None

    # -------------------------
    # Naming Heuristics
    # -------------------------

    def is_entry_file_name(self, file_path: str) -> bool:
        file_name = file_path.split("/")[-1].lower()
        return file_name in {"app.py", "main.py", "server.py"}
