# gnost/languages/javascript.py

import json
import os
import re
from typing import List, Optional

from gnost.languages.base import LanguageAdapter, EntryPoint, ImportEdge
from gnost.languages.manifests import find_manifests


class JavaScriptAdapter(LanguageAdapter):
    name = "javascript"
    extensions = [".js", ".jsx", ".mjs", ".cjs"]
    entry_stems = {"index", "main", "server", "app"}

    # -------------------------
    # Entry Points
    # -------------------------

    def detect_entry_points(self, files: List[str]) -> List[EntryPoint]:
        entry_points: List[EntryPoint] = []

        for file in files:
            stem, ext = os.path.splitext(os.path.basename(file).lower())

            if stem in self.entry_stems and ext in self.extensions:
                entry_points.append(
                    EntryPoint(file=file, reason="Common JS entry filename")
                )

            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            if re.search(
                r"\b(?:app|server|srv|fastify|koa|http\w*)\.listen\s*\(", content
            ) or re.search(r"\bcreateServer\s*\(", content):
                entry_points.append(
                    EntryPoint(file=file, reason="Server listen() call")
                )

        return entry_points

    # -------------------------
    # Imports
    # -------------------------

    # `from` clause of import/export, possibly spanning lines:
    #   import a from 'x'  |  import { a,\n b } from 'x'  |  export * from 'x'
    _FROM_RE = re.compile(
        r"""\b(?:import|export)\s+(?:type\s+)?[^'";]*?\bfrom\s*['"]([^'"\n]+)['"]"""
    )
    _SIDE_EFFECT_RE = re.compile(r"""\bimport\s*['"]([^'"\n]+)['"]""")
    _DYNAMIC_RE = re.compile(r"""\bimport\s*\(\s*['"]([^'"\n]+)['"]\s*\)""")
    _REQUIRE_RE = re.compile(r"""\brequire\s*\(\s*['"]([^'"\n]+)['"]\s*\)""")

    _TYPE_PREFIX_RE = re.compile(r"(?:import|export)\s+type\b")

    def detect_imports(self, file_path: str, content: str) -> List[ImportEdge]:
        """Imports with a flag for those that do not run when the module loads
        (dynamic `import()` and `import type`), so they cannot cause an
        import-time cycle. One eager import of a target makes its edge eager."""
        found: List[tuple] = []  # (target, deferred)
        for m in self._FROM_RE.finditer(content):
            found.append((m.group(1), bool(self._TYPE_PREFIX_RE.match(m.group(0)))))
        for regex in (self._SIDE_EFFECT_RE, self._REQUIRE_RE):
            found.extend((t, False) for t in regex.findall(content))
        found.extend((t, True) for t in self._DYNAMIC_RE.findall(content))

        deferred: dict = {}
        for target, is_deferred in found:
            deferred[target] = deferred.get(target, True) and is_deferred

        return [
            ImportEdge(source=file_path, target=t, deferred=d)
            for t, d in deferred.items()
        ]

    # -------------------------
    # Framework Detection
    # -------------------------

    # (dependency, label), strongest first. A meta-framework wins over the
    # library it is built on (Next.js over React).
    FRAMEWORK_DEPENDENCIES = [
        ("next", "Next.js"),
        ("nuxt", "Nuxt"),
        ("@sveltejs/kit", "SvelteKit"),
        ("@nestjs/core", "NestJS"),
        ("@angular/core", "Angular"),
        ("@remix-run/react", "Remix"),
        ("astro", "Astro"),
        ("react-native", "React Native"),
        ("react", "React"),
        ("vue", "Vue"),
        ("svelte", "Svelte"),
        ("solid-js", "Solid"),
        ("express", "Express"),
        ("fastify", "Fastify"),
        ("koa", "Koa"),
    ]
    # Build tools worth naming next to a UI library, e.g. "React (Vite)".
    BUNDLERS = [("vite", "Vite")]

    def detect_framework_from_manifest(self, root: str) -> Optional[str]:
        """Read package.json files near the root (monorepos keep them in subfolders)."""
        labels: List[str] = []
        for path in find_manifests(root, lambda name: name == "package.json"):
            label = self._framework_from_package_json(path)
            if label and label not in labels:
                labels.append(label)
        return ", ".join(labels) or None

    def _framework_from_package_json(self, path: str) -> Optional[str]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict):
            return None

        deps: set = set()
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            section = data.get(key)
            if isinstance(section, dict):
                deps.update(section)

        for dependency, label in self.FRAMEWORK_DEPENDENCIES:
            if dependency in deps:
                bundlers = [name for dep, name in self.BUNDLERS if dep in deps]
                if bundlers and label in {"React", "Vue", "Svelte", "Solid"}:
                    return f"{label} ({', '.join(bundlers)})"
                return label
        return None

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
