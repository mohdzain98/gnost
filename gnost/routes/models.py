"""Route model shared by the per-language extractors."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Route:
    """An HTTP (or websocket) endpoint and the code that handles it."""

    method: str  # GET, POST, ..., "ANY", "WS"
    path: str  # always starts with "/"
    handler: str  # function or method name, "<inline>" for anonymous handlers
    file: str  # absolute path of the file that defines the handler
    line: int
    framework: str


def join_paths(*parts: str) -> str:
    """Join URL fragments with single slashes: ("/api/", "users", "/{id}")
    -> "/api/users/{id}". A trailing slash on the last part is kept."""
    pieces = [p for p in parts if p and p != "/"]
    joined = "/".join(p.strip("/") for p in pieces if p.strip("/"))
    result = "/" + joined
    if pieces and pieces[-1].endswith("/") and result != "/":
        result += "/"
    return result


def methods_of(values: Iterable[str]) -> list:
    found = [v.upper() for v in values if re.fullmatch(r"[A-Za-z]+", v)]
    return found or ["GET"]


MAX_CHAINS = 4  # a router mounted in several places yields at most this many routes


def resolve_prefixes(key, own, parents, seen=frozenset()) -> list:
    """Every URL prefix a router ends up under, outermost first.

    `own(key)` is the router's own prefix and `parents(key)` lists
    `(parent_key, mount_prefix)` pairs for each place it is mounted. Mount
    cycles are cut instead of followed.
    """
    mine = own(key)
    if key in seen:
        return [mine]
    mounted = parents(key)
    if not mounted:
        return [mine]
    found: list = []
    for parent_key, mount_prefix in mounted:
        for outer in resolve_prefixes(parent_key, own, parents, seen | {key}):
            found.append(join_paths(outer, mount_prefix, mine))
    return found[:MAX_CHAINS] or [mine]
