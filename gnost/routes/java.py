"""Routes of Spring MVC / Spring Boot controllers."""

from __future__ import annotations

import re
from typing import List

from gnost.routes.models import Route, join_paths

_CLASS_RE = re.compile(r"\b(?:public\s+)?(?:abstract\s+)?class\s+(\w+)")
_MAPPING_RE = re.compile(
    r"@(Get|Post|Put|Delete|Patch|Request)Mapping\s*(\((?:[^()]|\([^()]*\))*\))?"
)
_STRING_RE = re.compile(r'"([^"]*)"')
_REQUEST_METHOD_RE = re.compile(r"RequestMethod\.(\w+)")
_SIGNATURE_RE = re.compile(
    r"\s*(?:@\w+(?:\((?:[^()]|\([^()]*\))*\))?\s*)*"
    r"(?:public\s+|protected\s+|private\s+|static\s+|final\s+)*"
    r"[\w<>\[\],.?\s]+?\s+(\w+)\s*\("
)


def _paths(args: str) -> List[str]:
    """Paths from a mapping's arguments: ("/x"), (value = {"/a", "/b"}), (path = "/x")."""
    head = re.split(
        r"\bmethod\s*=|\bproduces\s*=|\bconsumes\s*=|\bparams\s*=|\bheaders\s*=", args
    )[0]
    return _STRING_RE.findall(head) or [""]


def extract(path: str, content: str) -> List[Route]:
    if "Mapping" not in content or not re.search(
        r"@(Rest)?Controller|@RequestMapping", content
    ):
        return []

    cls = _CLASS_RE.search(content)
    if not cls:
        return []

    base = [""]
    for m in _MAPPING_RE.finditer(content[: cls.start()]):
        if m.group(1) == "Request":
            base = _paths(m.group(2) or "")

    routes: List[Route] = []
    body_start = content.find("{", cls.end())
    if body_start == -1:
        return []
    for m in _MAPPING_RE.finditer(content, body_start):
        verb, args = m.group(1), m.group(2) or ""
        if verb == "Request":
            methods = [x.upper() for x in _REQUEST_METHOD_RE.findall(args)] or ["ANY"]
        else:
            methods = [verb.upper()]
        signature = _SIGNATURE_RE.match(content, m.end())
        handler = f"{cls.group(1)}.{signature.group(1)}" if signature else cls.group(1)
        line = content.count("\n", 0, m.start()) + 1
        for prefix in base:
            for sub in _paths(args):
                for method in methods:
                    routes.append(
                        Route(
                            method,
                            join_paths(prefix, sub),
                            handler,
                            path,
                            line,
                            "Spring",
                        )
                    )
    return routes
