"""Resolve import statements to files inside the scanned project."""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional, Set, Tuple

from gnost.languages.base import ImportEdge
from gnost.scanner.models import FileInfo

JS_EXTENSIONS = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")
# TypeScript ESM code imports "./x.js" while the file on disk is x.ts / x.tsx.
JS_EXT_SWAPS = {".js": (".ts", ".tsx"), ".jsx": (".tsx",), ".mjs": (".mts",)}


class ImportResolver:
    """Maps import edges to project files.

    Python imports are matched by exact dotted module name (packages resolve to
    their ``__init__.py``), relative imports by directory, JS/TS imports by
    relative path and Java imports by package path. Anything not found in the
    project (standard library, third-party) resolves to nothing.
    """

    def __init__(self, root: str, files: List[FileInfo]):
        self.root = root
        self.paths: Set[str] = {f.path for f in files}
        self.python_modules = self._index_python(files)
        self.java_classes = self._index_java(files)
        self.js_aliases, self.js_base_urls = self._load_js_config()

    # -------------------------
    # Public API
    # -------------------------

    def resolve(self, edge: ImportEdge, language: str) -> List[str]:
        if language == "python":
            found = self._resolve_python(edge)
        elif language in ("javascript", "typescript"):
            found = self._resolve_js(edge)
        elif language == "java":
            found = self._resolve_java(edge)
        else:
            found = []

        seen: List[str] = []
        for path in found:
            if path != edge.source and path not in seen:
                seen.append(path)
        return seen

    def module_file(
        self, source: str, module: str, level: int = 0, name: Optional[str] = None
    ) -> Optional[str]:
        """File of Python `module` (or of its submodule `name`) as seen from `source`.

        `from app.api import chat` passes module="app.api", name="chat" and finds
        chat.py (or chat/__init__.py) rather than the package's __init__.py.
        """
        for names in ([[name]] if name else []) + [[]]:
            edge = ImportEdge(source, module, names=list(names), level=level)
            found = self.resolve(edge, "python")
            if names:
                for path in found:
                    stem = os.path.basename(path)
                    folder = os.path.basename(os.path.dirname(path))
                    if stem == f"{names[0]}.py" or (
                        stem == "__init__.py" and folder == names[0]
                    ):
                        return path
            elif found:
                return found[0]
        return None

    # -------------------------
    # Python
    # -------------------------

    def _index_python(self, files: List[FileInfo]) -> Dict[str, str]:
        index: Dict[str, str] = {}
        py_files = sorted(
            (f.path for f in files if f.path.endswith(".py")),
            key=lambda p: (p.count(os.sep), p),
        )
        for path in py_files:
            for name in self._python_module_names(path):
                index.setdefault(name, path)
        return index

    def _python_module_names(self, path: str) -> List[str]:
        """Dotted names a file can be imported as.

        One relative to the scan root, and one relative to the nearest ancestor
        directory that is not a package (a ``src/`` layout).
        """
        names: List[str] = []
        rel = os.path.relpath(path, self.root)
        parts = rel[: -len(".py")].replace(os.sep, "/").split("/")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if parts:
            names.append(".".join(parts))

        is_init = os.path.basename(path) == "__init__.py"
        directory = os.path.dirname(path)
        depth = 0
        while directory != self.root and os.path.isfile(
            os.path.join(directory, "__init__.py")
        ):
            directory = os.path.dirname(directory)
            depth += 1
        keep = depth if is_init else depth + 1
        if depth and keep < len(parts):
            alt = ".".join(parts[-keep:])
            if alt not in names:
                names.append(alt)
        return names

    def _resolve_python(self, edge: ImportEdge) -> List[str]:
        if edge.level:
            return self._resolve_python_relative(edge)

        found: List[str] = []
        base = self.python_modules.get(edge.target)
        if base:
            found.append(base)
        for name in edge.names:
            sub = self.python_modules.get(f"{edge.target}.{name}")
            if sub:
                found.append(sub)
        return found

    def _resolve_python_relative(self, edge: ImportEdge) -> List[str]:
        directory = os.path.dirname(edge.source)
        for _ in range(edge.level - 1):
            directory = os.path.dirname(directory)

        module_dir = (
            os.path.join(directory, *edge.target.split("."))
            if edge.target
            else directory
        )
        found: List[str] = []
        if edge.target:
            for candidate in (
                module_dir + ".py",
                os.path.join(module_dir, "__init__.py"),
            ):
                if candidate in self.paths:
                    found.append(candidate)
                    break
        else:
            init = os.path.join(directory, "__init__.py")
            if init in self.paths:
                found.append(init)

        for name in edge.names:
            for candidate in (
                os.path.join(module_dir, name + ".py"),
                os.path.join(module_dir, name, "__init__.py"),
            ):
                if candidate in self.paths:
                    found.append(candidate)
                    break
        return found

    # -------------------------
    # JavaScript / TypeScript
    # -------------------------

    def _resolve_js(self, edge: ImportEdge) -> List[str]:
        target = re.split(r"[?#]", edge.target, maxsplit=1)[0]
        if not target:
            return []

        if target.startswith("."):
            base = os.path.normpath(os.path.join(os.path.dirname(edge.source), target))
            found = self._probe_js(base)
            return [found] if found else []

        for base in self._alias_bases(target):
            found = self._probe_js(base)
            if found:
                return [found]
        return []  # bare package specifier (react, lodash, ...)

    def _probe_js(self, base: str) -> Optional[str]:
        """Find the file a module path points at (extensions, index files)."""
        candidates = [base]
        stem, ext = os.path.splitext(base)
        for swap in JS_EXT_SWAPS.get(ext, ()):
            candidates.append(stem + swap)
        candidates += [base + e for e in JS_EXTENSIONS]
        candidates += [os.path.join(base, "index" + e) for e in JS_EXTENSIONS]
        for candidate in candidates:
            if candidate in self.paths:
                return candidate
        return None

    def _alias_bases(self, target: str) -> List[str]:
        """Absolute paths a non-relative import may refer to (aliases, baseUrl)."""
        bases: List[str] = []
        for pattern, directories in self.js_aliases:
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if not target.startswith(prefix):
                    continue
                rest = target[len(prefix) :]
                bases += [os.path.normpath(d.replace("*", rest)) for d in directories]
            elif target == pattern:
                bases += [os.path.normpath(d) for d in directories]
        bases += [os.path.normpath(os.path.join(b, target)) for b in self.js_base_urls]
        return bases

    # tsconfig/jsconfig `paths` and `baseUrl`; bundler-only aliases (vite.config)
    # are not read, so `@/` falls back to `src/` by convention.
    _CONFIG_NAMES = ("tsconfig.json", "jsconfig.json", "tsconfig.app.json")

    def _load_js_config(self) -> Tuple[List[Tuple[str, List[str]]], List[str]]:
        aliases: List[Tuple[str, List[str]]] = []
        base_urls: List[str] = []
        pending = [os.path.join(self.root, n) for n in self._CONFIG_NAMES]
        seen: Set[str] = set()

        while pending:
            path = pending.pop(0)
            if path in seen or not os.path.isfile(path):
                continue
            seen.add(path)
            config = self._read_jsonc(path)
            here = os.path.dirname(path)

            options = config.get("compilerOptions") or {}
            base = os.path.normpath(os.path.join(here, options.get("baseUrl", ".")))
            if "baseUrl" in options:
                base_urls.append(base)
            for pattern, targets in (options.get("paths") or {}).items():
                dirs = [os.path.normpath(os.path.join(base, t)) for t in targets]
                aliases.append((pattern, dirs))

            for ref in config.get("references") or []:
                ref_path = os.path.normpath(os.path.join(here, ref.get("path", "")))
                pending.append(
                    ref_path
                    if ref_path.endswith(".json")
                    else os.path.join(ref_path, "tsconfig.json")
                )
            extends = config.get("extends")
            if isinstance(extends, str) and extends.startswith("."):
                ext_path = os.path.normpath(os.path.join(here, extends))
                pending.append(
                    ext_path if ext_path.endswith(".json") else ext_path + ".json"
                )

        if not any(p.startswith("@/") for p, _ in aliases):
            src = os.path.join(self.root, "src")
            if any(path.startswith(src + os.sep) for path in self.paths):
                aliases.append(("@/*", [os.path.join(src, "*")]))
        return aliases, base_urls

    @staticmethod
    def _read_jsonc(path: str) -> dict:
        """Parse JSON with comments and trailing commas (tsconfig style)."""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            return {}
        text = re.sub(
            r'("(?:\\.|[^"\\])*")|//[^\n]*|/\*.*?\*/',
            lambda m: m.group(1) or "",
            text,
            flags=re.S,
        )
        text = re.sub(r",(\s*[}\]])", r"\1", text)
        try:
            data = json.loads(text)
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    # -------------------------
    # Java
    # -------------------------

    def _index_java(self, files: List[FileInfo]) -> Dict[str, str]:
        """Index every dotted suffix of a source path (``a.b.C``, ``b.C``, ``C``)."""
        index: Dict[str, str] = {}
        java_files = sorted(
            (f.path for f in files if f.path.endswith(".java")),
            key=lambda p: (p.count(os.sep), p),
        )
        for path in java_files:
            rel = os.path.relpath(path, self.root)[: -len(".java")]
            parts = rel.replace(os.sep, "/").split("/")
            for start in range(len(parts)):
                index.setdefault(".".join(parts[start:]), path)
        return index

    NESTED_CLASS_DEPTH = 2  # `a.b.Outer.Inner` imports the file of `a.b.Outer`

    def _resolve_java(self, edge: ImportEdge) -> List[str]:
        target = edge.target
        for _ in range(self.NESTED_CLASS_DEPTH + 1):
            path = self.java_classes.get(target)
            if path:
                return [path]
            if "." not in target:
                break
            target = target.rsplit(".", 1)[0]
        return []
