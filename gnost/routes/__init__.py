"""Find the HTTP routes of a scanned project and the handlers behind them."""

from __future__ import annotations

from typing import Dict, List

from gnost.core.resolver import ImportResolver
from gnost.routes import java, javascript, python
from gnost.routes.models import Route
from gnost.scanner.models import ScanResult

__all__ = ["Route", "find_routes"]


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def find_routes(scan: ScanResult) -> List[Route]:
    """Routes from every supported framework, sorted by path then method."""
    resolver = ImportResolver(scan.root, scan.files)

    py_facts: Dict[str, python.FileFacts] = {}
    js_facts: Dict[str, javascript.JsFacts] = {}
    routes: List[Route] = []

    for info in scan.files:
        if info.language == "python":
            facts = python.extract(info.path, _read(info.path))
            if facts:
                py_facts[info.path] = facts
        elif info.language in ("javascript", "typescript"):
            facts = javascript.extract(info.path, _read(info.path))
            if facts:
                js_facts[info.path] = facts
        elif info.language == "java":
            routes += java.extract(info.path, _read(info.path))

    routes += python.link(py_facts, resolver)
    routes += javascript.link(js_facts, resolver)
    return sorted(set(routes), key=lambda r: (r.path, r.method, r.file, r.line))
