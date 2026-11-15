"""Routes of Express/Fastify/Hono apps and NestJS controllers (JS and TS).

Detection is text based: receivers are the variables created with `express()`,
`express.Router()`, `fastify()` ..., route calls are `receiver.get('/x', ...)`,
and mounts are `app.use('/api', usersRouter)`. Prefixes follow the import of the
mounted router when it is a relative module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from gnost.core.resolver import ImportResolver
from gnost.languages.base import ImportEdge
from gnost.routes.models import Route, join_paths, resolve_prefixes

METHODS = ("get", "post", "put", "delete", "patch", "all", "options", "head")
COMMON_NAMES = {"app", "router", "routes", "server", "api", "route"}

_RECEIVER_RE = re.compile(
    r"""(?:const|let|var)\s+(\w+)\s*(?::[^=]+)?=\s*
        (?P<ctor>express\s*\(\s*\)
          |(?:express\.)?Router\s*\([^)]*\)
          |require\(\s*['"]express['"]\s*\)\.Router\s*\([^)]*\)
          |fastify\s*\([^)]*\)
          |new\s+Hono\s*\([^)]*\))""",
    re.X,
)
_ROUTE_CALL_RE = re.compile(r"\b(\w+)\.(%s)\s*\(" % "|".join(METHODS))
_USE_CALL_RE = re.compile(r"\b(\w+)\.use\s*\(")
_ES_IMPORT_RE = re.compile(
    r"""import\s+(?:(\w+)\s*,?\s*)?(?:\{([^}]*)\})?\s*from\s*['"]([^'"]+)['"]"""
)
_REQUIRE_RE = re.compile(
    r"""(?:const|let|var)\s+(?:(\w+)|\{([^}]*)\})\s*=\s*require\(\s*['"]([^'"]+)['"]\s*\)(?:\.(\w+))?"""
)
_CONTROLLER_RE = re.compile(
    r"""@Controller\(\s*(?:['"`]([^'"`]*)['"`])?\s*\)\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)"""
)
_NEST_METHOD_RE = re.compile(
    r"""@(Get|Post|Put|Delete|Patch|Options|Head|All)\(\s*(?:['"`]([^'"`]*)['"`])?[^)]*\)\s*(?:@\w+\([^)]*\)\s*)*(?:public\s+|async\s+|private\s+)*(\w+)\s*\("""
)
_STRING_RE = re.compile(r"""^\s*(['"`])(.*?)\1\s*$""", re.S)


@dataclass
class JsDecl:
    receiver: str
    method: str
    path: str
    handler: str
    line: int


@dataclass
class JsMount:
    receiver: str
    prefix: str
    ident: Optional[str]  # imported variable being mounted
    spec: Optional[str]  # or a require('./x') mounted inline


@dataclass
class JsFacts:
    path: str
    receivers: Dict[str, str] = field(default_factory=dict)  # name -> framework
    imports: Dict[str, Tuple[str, Optional[str]]] = field(default_factory=dict)
    decls: List[JsDecl] = field(default_factory=list)
    mounts: List[JsMount] = field(default_factory=list)
    nest: List[Route] = field(default_factory=list)


def _line(content: str, index: int) -> int:
    return content.count("\n", 0, index) + 1


def _split_args(content: str, open_index: int) -> Tuple[List[str], int]:
    """Top-level arguments of the call whose `(` is at `open_index`."""
    args: List[str] = []
    depth, start, i = 0, open_index + 1, open_index
    quote: Optional[str] = None
    while i < len(content):
        ch = content[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "'\"`":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                tail = content[start:i].strip()
                if tail:
                    args.append(tail)
                return args, i
        elif ch == "," and depth == 1:
            args.append(content[start:i].strip())
            start = i + 1
        i += 1
    return args, len(content)


def _literal(arg: str) -> Optional[str]:
    m = _STRING_RE.match(arg)
    return m.group(2) if m else None


def _handler_name(arg: str) -> str:
    arg = arg.strip()
    return arg if re.fullmatch(r"[\w$.]+", arg) else "<inline>"


def extract(path: str, content: str) -> Optional[JsFacts]:
    facts = JsFacts(path=path)

    for m in _RECEIVER_RE.finditer(content):
        ctor = m.group("ctor")
        facts.receivers[m.group(1)] = (
            "Fastify"
            if ctor.startswith("fastify")
            else "Hono"
            if "Hono" in ctor
            else "Express"
        )

    for m in _ES_IMPORT_RE.finditer(content):
        default, named, module = m.groups()
        if default:
            facts.imports[default] = (module, None)
        for item in (named or "").split(","):
            parts = [x.strip() for x in re.split(r"\bas\b", item.replace("type ", ""))]
            if parts and parts[0]:
                facts.imports[parts[-1]] = (module, parts[0])
    for m in _REQUIRE_RE.finditer(content):
        single, destructured, module, prop = m.groups()
        if single:
            facts.imports[single] = (module, prop)
        for item in (destructured or "").split(","):
            parts = [x.strip() for x in item.split(":")]
            if parts and parts[0]:
                facts.imports[parts[-1]] = (module, parts[0])

    mentions_framework = bool(re.search(r"express|fastify|Router|hono", content, re.I))

    def acceptable(name: str) -> bool:
        return name in facts.receivers or (mentions_framework and name in COMMON_NAMES)

    for m in _ROUTE_CALL_RE.finditer(content):
        receiver, method = m.group(1), m.group(2)
        if not acceptable(receiver):
            continue
        args, _ = _split_args(content, m.end() - 1)
        if len(args) < 2:
            continue  # app.get('setting') is Express's settings getter
        literal = _literal(args[0])
        if literal is None and not args[0].startswith("["):
            continue
        facts.decls.append(
            JsDecl(
                receiver,
                "ANY" if method == "all" else method.upper(),
                literal if literal is not None else "<dynamic>",
                _handler_name(args[-1]),
                _line(content, m.start()),
            )
        )

    for m in _USE_CALL_RE.finditer(content):
        receiver = m.group(1)
        if not acceptable(receiver):
            continue
        args, _ = _split_args(content, m.end() - 1)
        if not args:
            continue
        prefix = _literal(args[0]) if len(args) > 1 else ""
        if prefix is None:
            prefix = ""
        target = args[-1]
        spec = re.match(r"""require\(\s*['"]([^'"]+)['"]\s*\)""", target)
        ident = target if re.fullmatch(r"\w+", target) else None
        if spec or ident:
            facts.mounts.append(
                JsMount(receiver, prefix, ident, spec.group(1) if spec else None)
            )

    _extract_nest(facts, content)

    if not (facts.decls or facts.mounts or facts.nest or facts.receivers):
        return None
    return facts


def _extract_nest(facts: JsFacts, content: str) -> None:
    controllers = list(_CONTROLLER_RE.finditer(content))
    for index, ctl in enumerate(controllers):
        end = (
            controllers[index + 1].start()
            if index + 1 < len(controllers)
            else len(content)
        )
        body = content[ctl.end() : end]
        base = ctl.group(1) or ""
        for m in _NEST_METHOD_RE.finditer(body):
            verb, sub, handler = m.group(1), m.group(2) or "", m.group(3)
            facts.nest.append(
                Route(
                    "ANY" if verb == "All" else verb.upper(),
                    join_paths(base, sub),
                    f"{ctl.group(2)}.{handler}",
                    facts.path,
                    _line(content, ctl.end() + m.start()),
                    "NestJS",
                )
            )


def link(facts: Dict[str, JsFacts], resolver: ImportResolver) -> List[Route]:
    def target_of(f: JsFacts, mount: JsMount) -> Optional[Tuple[str, str]]:
        spec, name = mount.spec, None
        if mount.ident and mount.ident in f.imports:
            spec, name = f.imports[mount.ident]
        elif mount.ident and mount.ident in f.receivers:
            return (f.path, mount.ident)
        if not spec:
            return None
        found = resolver.resolve(ImportEdge(f.path, spec), "javascript")
        if not found or found[0] not in facts:
            return None
        target = facts[found[0]]
        for candidate in (name, mount.ident, "router"):
            if candidate in target.receivers:
                return (target.path, candidate)
        if len(target.receivers) == 1:
            return (target.path, next(iter(target.receivers)))
        return None

    mounts_into: Dict[Tuple[str, str], List[Tuple[Tuple[str, str], str]]] = {}
    for f in facts.values():
        for mount in f.mounts:
            target = target_of(f, mount)
            if target and target != (f.path, mount.receiver):
                mounts_into.setdefault(target, []).append(
                    ((f.path, mount.receiver), mount.prefix)
                )

    routes: List[Route] = []
    for path, f in sorted(facts.items()):
        routes += f.nest
        for decl in f.decls:
            framework = f.receivers.get(decl.receiver, "Express")
            prefixes = resolve_prefixes(
                (path, decl.receiver),
                own=lambda k: "",
                parents=lambda k: mounts_into.get(k, []),
            )
            for prefix in prefixes:
                routes.append(
                    Route(
                        decl.method,
                        join_paths(prefix, decl.path),
                        decl.handler,
                        path,
                        decl.line,
                        framework,
                    )
                )

    unique = {(r.method, r.path, r.handler, r.file, r.line): r for r in routes}
    return sorted(unique.values(), key=lambda r: (r.path, r.method, r.file, r.line))
