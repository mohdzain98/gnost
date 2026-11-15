# gnost/languages/python.py

import ast
import os
import re
from typing import List, Optional

from gnost.languages.base import LanguageAdapter, EntryPoint, ImportEdge
from gnost.languages.manifests import find_manifests, read_text


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

            for reason in self._entry_reasons(content):
                entry_points.append(EntryPoint(file=file, reason=reason))

        return entry_points

    _MAIN_GUARD_RE = re.compile(r"""if\s+__name__\s*==\s*['"]__main__['"]""")

    def _entry_reasons(self, content: str) -> List[str]:
        """Why a file starts the app. Real syntax only: a string or regex that
        merely mentions `Flask(` or `uvicorn.run` does not count."""
        try:
            tree = ast.parse(content)
        except (SyntaxError, ValueError):
            return self._entry_reasons_regex(content)

        guard = fastapi = flask = uvicorn = False
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and self._is_main_guard(node.test):
                guard = True
            elif isinstance(node, ast.Call):
                name = self._call_name(node)
                if name == "FastAPI":
                    fastapi = True
                elif name == "Flask":
                    flask = True
                elif name == "uvicorn.run":
                    uvicorn = True

        reasons = []
        if guard:
            reasons.append("__main__ guard")
        if fastapi:
            reasons.append("FastAPI app initialization")
        if flask:
            reasons.append("Flask app initialization")
        if uvicorn:
            reasons.append("uvicorn.run")
        return reasons

    def _entry_reasons_regex(self, content: str) -> List[str]:
        reasons = []
        if self._MAIN_GUARD_RE.search(content):
            reasons.append("__main__ guard")
        if re.search(r"FastAPI\s*\(", content):
            reasons.append("FastAPI app initialization")
        if re.search(r"Flask\s*\(", content):
            reasons.append("Flask app initialization")
        if re.search(r"uvicorn\.run", content):
            reasons.append("uvicorn.run")
        return reasons

    @staticmethod
    def _is_main_guard(test: ast.expr) -> bool:
        """`__name__ == "__main__"` in either order."""
        if not (
            isinstance(test, ast.Compare)
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
        ):
            return False
        sides = [test.left, test.comparators[0]]
        has_name = any(isinstance(n, ast.Name) and n.id == "__name__" for n in sides)
        has_main = any(
            isinstance(n, ast.Constant) and n.value == "__main__" for n in sides
        )
        return has_name and has_main

    @staticmethod
    def _call_name(call: ast.Call) -> str:
        """`FastAPI(...)` -> "FastAPI", `fastapi.FastAPI()` -> "FastAPI",
        `uvicorn.run()` -> "uvicorn.run"."""
        func = call.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name) and func.value.id == "uvicorn":
                return f"uvicorn.{func.attr}"
            return func.attr
        return ""

    # -------------------------
    # Import Detection
    # -------------------------

    def detect_imports(self, file_path: str, content: str) -> List[ImportEdge]:
        try:
            tree = ast.parse(content)
        except (SyntaxError, ValueError):
            return self._detect_imports_regex(file_path, content)

        imports: List[ImportEdge] = []
        self._collect_imports(tree, file_path, False, imports)

        imports.sort(key=lambda e: e.target)
        return imports

    def _collect_imports(
        self,
        node: ast.AST,
        file_path: str,
        deferred: bool,
        out: List[ImportEdge],
    ) -> None:
        """Walk the tree, remembering whether an import runs at module load."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Import):
                for alias in child.names:
                    out.append(ImportEdge(file_path, alias.name, deferred=deferred))
            elif isinstance(child, ast.ImportFrom):
                out.append(
                    ImportEdge(
                        file_path,
                        child.module or "",
                        names=[a.name for a in child.names if a.name != "*"],
                        level=child.level,
                        deferred=deferred,
                    )
                )
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                self._collect_imports(child, file_path, True, out)
            elif isinstance(child, ast.If) and self._is_type_checking(child.test):
                for stmt in child.body:
                    self._collect_imports(ast.Module([stmt], []), file_path, True, out)
                for stmt in child.orelse:
                    self._collect_imports(
                        ast.Module([stmt], []), file_path, deferred, out
                    )
            else:
                self._collect_imports(child, file_path, deferred, out)

    @staticmethod
    def _is_type_checking(test: ast.expr) -> bool:
        return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
            isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
        )

    def _detect_imports_regex(self, file_path: str, content: str) -> List[ImportEdge]:
        """Fallback for files that do not parse (syntax errors, Python 2)."""
        imports: List[ImportEdge] = []

        for match in re.findall(
            r"^\s*import\s+([a-zA-Z0-9_\.]+)", content, re.MULTILINE
        ):
            imports.append(ImportEdge(source=file_path, target=match))

        for dots, module in re.findall(
            r"^\s*from\s+(\.*)([a-zA-Z0-9_\.]*)\s+import", content, re.MULTILINE
        ):
            imports.append(ImportEdge(source=file_path, target=module, level=len(dots)))

        return imports

    # -------------------------
    # Framework Detection
    # -------------------------

    # (package name, label), most specific first.
    FRAMEWORK_PACKAGES = [
        ("django", "Django"),
        ("fastapi", "FastAPI"),
        ("flask", "Flask"),
        ("litestar", "Litestar"),
        ("sanic", "Sanic"),
        ("tornado", "Tornado"),
        ("aiohttp", "aiohttp"),
        ("starlette", "Starlette"),
        ("streamlit", "Streamlit"),
        ("gradio", "Gradio"),
    ]

    def detect_framework_from_manifest(self, root: str) -> Optional[str]:
        """Read dependencies from pyproject.toml, requirements*.txt and Pipfile.

        Returns "" when manifests declare dependencies but none is a known framework, so the
        source-based guess does not override what the project declares.
        """
        labels: List[str] = []
        found_manifest = False
        for path in find_manifests(root, self._is_python_manifest):
            deps = self._dependencies(path)
            found_manifest = found_manifest or bool(deps)
            for package, label in self.FRAMEWORK_PACKAGES:
                if package in deps:
                    if label not in labels:
                        labels.append(label)
                    break
        if labels:
            return ", ".join(labels)
        return "" if found_manifest else None

    @staticmethod
    def _is_python_manifest(name: str) -> bool:
        return name in {"pyproject.toml", "Pipfile"} or (
            name.startswith("requirements") and name.endswith(".txt")
        )

    def _dependencies(self, path: str) -> set:
        text = read_text(path)
        name = os.path.basename(path)
        if name == "pyproject.toml":
            raw = self._pyproject_dependencies(text)
        elif name == "Pipfile":
            raw = re.findall(r"^\s*([A-Za-z0-9_.\-]+)\s*=", text, re.MULTILINE)
        else:
            raw = re.findall(r"^\s*([A-Za-z0-9][A-Za-z0-9_.\-]*)", text, re.MULTILINE)
        return {re.sub(r"[-_.]+", "-", d).lower() for d in raw}

    _REQUIREMENT_RE = re.compile(r"""["']([A-Za-z0-9][A-Za-z0-9_.\-]*)""")

    def _pyproject_dependencies(self, text: str) -> List[str]:
        """Names from [project] dependencies, optional/group tables and Poetry."""
        names: List[str] = []
        m = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.MULTILINE | re.DOTALL)
        if m:
            names += self._REQUIREMENT_RE.findall(m.group(1))

        sections = re.split(r"^\[([^\]]+)\]\s*$", text, flags=re.MULTILINE)
        for header, body in zip(sections[1::2], sections[2::2]):
            header = header.strip()
            if header in ("project.optional-dependencies", "dependency-groups"):
                names += self._REQUIREMENT_RE.findall(body)
            elif header.startswith("tool.poetry") and header.endswith("dependencies"):
                names += re.findall(
                    r"^\s*([A-Za-z0-9][A-Za-z0-9_.\-]*)\s*=", body, re.MULTILINE
                )
        return names

    def detect_framework(self, files: List[str]) -> Optional[str]:
        for file in files:
            if not file.endswith(".py"):
                continue

            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            found = self._framework_in_source(content)
            if found:
                return found

        return None

    def _framework_in_source(self, content: str) -> Optional[str]:
        """Framework from real imports or app construction, not from text."""
        try:
            tree = ast.parse(content)
        except (SyntaxError, ValueError):
            return None

        imported: set = set()
        called: set = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                called.add(self._call_name(node))

        for module, call, label in (
            ("fastapi", "FastAPI", "FastAPI"),
            ("flask", "Flask", "Flask"),
            ("django", "", "Django"),
        ):
            if module in imported or (call and call in called):
                return label
        return None

    # -------------------------
    # Naming Heuristics
    # -------------------------

    def is_entry_file_name(self, file_path: str) -> bool:
        file_name = file_path.split("/")[-1].lower()
        return file_name in {
            "app.py",
            "main.py",
            "server.py",
            "manage.py",
            "wsgi.py",
            "asgi.py",
            "__main__.py",
        }
