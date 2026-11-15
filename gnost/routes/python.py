"""Routes of Flask, FastAPI/Starlette and Django projects.

Decorators and urlpatterns are read from the syntax tree. Router prefixes are
resolved across files: `app.include_router(chat.router, prefix="/chat")`,
`app.register_blueprint(bp, url_prefix="/x")` and Django `include("app.urls")`.
Anything that is not a literal string is shown as `<dynamic>`.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from gnost.core.resolver import ImportResolver
from gnost.routes.models import Route, join_paths, resolve_prefixes

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head", "trace"}
ROUTER_FACTORIES = {
    "FastAPI": "FastAPI",
    "APIRouter": "FastAPI",
    "Flask": "Flask",
    "Blueprint": "Flask",
    "Router": "FastAPI",
    "DefaultRouter": "Django",
    "SimpleRouter": "Django",
}
PREFIX_KEYWORDS = ("prefix", "url_prefix")

Ref = Tuple[str, Optional[str]]  # ("chat", "router") for chat.router, ("router", None)


@dataclass
class RouteDecl:
    receiver: str
    methods: List[str]
    path: str
    handler: str
    line: int


@dataclass
class Mount:
    receiver: str
    target: Ref
    prefix: str


@dataclass
class UrlEntry:
    pattern: str
    view: str  # handler text, or "" for includes
    include: Optional[str]  # dotted module of include("pkg.urls")
    include_router: Optional[str]  # router variable of include(router.urls)
    line: int


@dataclass
class FileFacts:
    path: str
    framework_hint: Dict[str, str] = field(
        default_factory=dict
    )  # receiver -> framework
    own_prefix: Dict[str, str] = field(default_factory=dict)  # receiver -> prefix
    imports: Dict[str, Tuple[str, Optional[str], int]] = field(default_factory=dict)
    decls: List[RouteDecl] = field(default_factory=list)
    mounts: List[Mount] = field(default_factory=list)
    urlpatterns: List[UrlEntry] = field(default_factory=list)
    registered: List[RouteDecl] = field(default_factory=list)  # DRF router.register


def _const_str(node: Optional[ast.AST]) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _kw(call: ast.Call, *names: str) -> Optional[ast.AST]:
    for kw in call.keywords:
        if kw.arg in names:
            return kw.value
    return None


def _call_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _ref(node: ast.AST) -> Optional[Ref]:
    if isinstance(node, ast.Name):
        return (node.id, None)
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return (node.value.id, node.attr)
    return None


def _string_list(node: Optional[ast.AST]) -> List[str]:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [s for s in (_const_str(e) for e in node.elts) if s]
    single = _const_str(node)
    return [single] if single else []


def extract(path: str, content: str) -> Optional[FileFacts]:
    """Route facts of one file, or None when it cannot be parsed."""
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError):
        return None

    facts = FileFacts(path=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                module = alias.name if alias.asname else alias.name.split(".")[0]
                facts.imports[local] = (module, None, 0)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                facts.imports[alias.asname or alias.name] = (
                    node.module or "",
                    alias.name,
                    node.level,
                )
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            _read_router_assignment(facts, node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _read_decorators(facts, node)
        elif isinstance(node, ast.Call):
            _read_call(facts, node)

    for node in ast.walk(tree):  # urlpatterns = [...] holds a list, not a call
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, (ast.List, ast.Tuple))
            and any(
                isinstance(t, ast.Name) and t.id == "urlpatterns" for t in node.targets
            )
        ):
            facts.urlpatterns += _url_entries(node.value)
        elif (
            isinstance(node, ast.AugAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "urlpatterns"
            and isinstance(node.value, (ast.List, ast.Tuple))
        ):
            facts.urlpatterns += _url_entries(node.value)

    facts.urlpatterns.sort(key=lambda e: e.line)
    return facts


def _read_router_assignment(facts: FileFacts, node: ast.Assign) -> None:
    name = _call_name(node.value)  # type: ignore[arg-type]
    framework = ROUTER_FACTORIES.get(name)
    if not framework:
        return
    for target in node.targets:
        if isinstance(target, ast.Name):
            facts.framework_hint[target.id] = framework
            prefix = _const_str(_kw(node.value, *PREFIX_KEYWORDS))  # type: ignore[arg-type]
            if prefix:
                facts.own_prefix[target.id] = prefix


def _read_decorators(facts: FileFacts, func: ast.AST) -> None:
    assert isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef))
    for dec in func.decorator_list:
        if not (
            isinstance(dec, ast.Call)
            and isinstance(dec.func, ast.Attribute)
            and isinstance(dec.func.value, ast.Name)
        ):
            continue
        receiver, attr = dec.func.value.id, dec.func.attr
        first = dec.args[0] if dec.args else _kw(dec, "path", "rule")
        path = _const_str(first)
        if attr in HTTP_METHODS:
            methods = [attr.upper()]
        elif attr in ("route", "api_route"):
            listed = _string_list(_kw(dec, "methods"))
            methods = [m.upper() for m in listed] or ["GET"]
        elif attr == "websocket":
            methods = ["WS"]
        else:
            continue
        facts.decls.append(
            RouteDecl(
                receiver,
                methods,
                path if path is not None else "<dynamic>",
                func.name,
                func.lineno,
            )
        )


def _read_call(facts: FileFacts, call: ast.Call) -> None:
    if not (
        isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name)
    ):
        return
    receiver, attr = call.func.value.id, call.func.attr

    if attr in ("include_router", "register_blueprint") and call.args:
        target = _ref(call.args[0])
        if target:
            prefix = _const_str(_kw(call, *PREFIX_KEYWORDS)) or ""
            facts.mounts.append(Mount(receiver, target, prefix))
    elif (
        attr == "register" and len(call.args) >= 2
    ):  # DRF: router.register("users", UserViewSet)
        prefix = _const_str(call.args[0])
        view = _ref(call.args[1])
        if prefix is not None and view:
            facts.registered.append(
                RouteDecl(receiver, ["ANY"], prefix, view[1] or view[0], call.lineno)
            )


def _url_entries(container: ast.AST) -> List[UrlEntry]:
    entries: List[UrlEntry] = []
    for item in getattr(container, "elts", []):
        if not (
            isinstance(item, ast.Call)
            and _call_name(item) in ("path", "re_path", "url")
        ):
            continue
        if len(item.args) < 2:
            continue
        pattern = _const_str(item.args[0])
        target = item.args[1]
        include: Optional[str] = None
        include_router: Optional[str] = None
        view = ""
        if (
            isinstance(target, ast.Call)
            and _call_name(target) == "include"
            and target.args
        ):
            arg = target.args[0]
            include = _const_str(arg)
            if (
                isinstance(arg, ast.Attribute)
                and arg.attr == "urls"
                and isinstance(arg.value, ast.Name)
            ):
                include_router = arg.value.id
        elif isinstance(target, ast.Call):
            view = _expr_text(target.func)  # Foo.as_view()
        else:
            view = _expr_text(target)
        entries.append(
            UrlEntry(
                pattern if pattern is not None else "<dynamic>",
                view,
                include,
                include_router,
                item.lineno,
            )
        )
    return entries


def _expr_text(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _expr_text(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return _expr_text(node.func)
    return "<dynamic>"


# -------------------------
# Linking across files
# -------------------------


class _Linker:
    def __init__(self, facts: Dict[str, FileFacts], resolver: ImportResolver):
        self.facts = facts
        self.resolver = resolver
        self.mounts_into: Dict[Tuple[str, str], List[Tuple[str, str, str]]] = {}
        for facts_ in facts.values():
            for mount in facts_.mounts:
                target = self._resolve_ref(facts_, mount.target)
                if target:
                    self.mounts_into.setdefault(target, []).append(
                        (facts_.path, mount.receiver, mount.prefix)
                    )

    def _module_file(
        self, source: str, module: str, level: int, name: Optional[str]
    ) -> Optional[str]:
        return self.resolver.module_file(source, module, level, name)

    def _resolve_ref(self, facts: FileFacts, ref: Ref) -> Optional[Tuple[str, str]]:
        """(file, variable) a reference such as `chat.router` points at."""
        base, attr = ref
        if attr is None:
            if base in facts.framework_hint:
                return (facts.path, base)
            imported = facts.imports.get(base)
            if imported and imported[1]:
                module, name, level = imported
                target = self._module_file(facts.path, module, level, None)
                if target:
                    return (target, name)
            return None
        imported = facts.imports.get(base)
        if imported:
            module, name, level = imported
            target = self._module_file(facts.path, module, level, name)
            if target:
                return (target, attr)
        return None

    def prefixes(self, file: str, var: str) -> List[str]:
        """Every URL prefix `var` ends up under, outermost first."""
        return resolve_prefixes(
            (file, var),
            own=lambda k: (
                self.facts[k[0]].own_prefix.get(k[1], "") if k[0] in self.facts else ""
            ),
            parents=lambda k: [
                ((f, v), prefix) for f, v, prefix in self.mounts_into.get(k, [])
            ],
        )


def link(facts: Dict[str, FileFacts], resolver: ImportResolver) -> List[Route]:
    linker = _Linker(facts, resolver)
    routes: List[Route] = []

    for path, file_facts in sorted(facts.items()):
        for decl in file_facts.decls + file_facts.registered:
            owner_file, owner_var = path, decl.receiver
            framework = file_facts.framework_hint.get(decl.receiver)
            if framework is None:  # a router imported from another module
                target = linker._resolve_ref(file_facts, (decl.receiver, None))
                if target and target[0] in facts:
                    owner_file, owner_var = target
                    framework = facts[owner_file].framework_hint.get(owner_var)
            if framework is None:
                continue  # `@something.get(...)` on an unknown object: not a router
            for prefix in linker.prefixes(owner_file, owner_var):
                full = join_paths(prefix, decl.path)
                for method in decl.methods:
                    routes.append(
                        Route(method, full, decl.handler, path, decl.line, framework)
                    )

    routes += _django_routes(facts, linker)
    unique = {(r.method, r.path, r.handler, r.file, r.line): r for r in routes}
    return sorted(unique.values(), key=lambda r: (r.path, r.method, r.file, r.line))


# -------------------------
# Django urlconfs
# -------------------------


def _django_routes(facts: Dict[str, FileFacts], linker: _Linker) -> List[Route]:
    """Flatten urlpatterns, following include() from the urlconfs nobody includes."""
    urlconfs = {p: f for p, f in facts.items() if f.urlpatterns}
    if not urlconfs:
        return []

    included: Set[str] = set()
    targets: Dict[Tuple[str, int], str] = {}
    for path, f in urlconfs.items():
        for entry in f.urlpatterns:
            if entry.include:
                target = linker._module_file(path, entry.include, 0, None)
                if target in urlconfs:
                    targets[(path, entry.line)] = target
                    included.add(target)

    routes: List[Route] = []

    def walk(path: str, prefix: str, trail: Tuple[str, ...]) -> None:
        f = urlconfs[path]
        for entry in f.urlpatterns:
            pattern = _clean_pattern(entry.pattern)
            if entry.include and (path, entry.line) in targets:
                target = targets[(path, entry.line)]
                if target not in trail:
                    walk(target, join_paths(prefix, pattern), trail + (path,))
            elif entry.include_router and entry.include_router in f.framework_hint:
                for reg in f.registered:
                    if reg.receiver == entry.include_router:
                        routes.append(
                            Route(
                                "ANY",
                                join_paths(prefix, pattern, reg.path),
                                reg.handler,
                                path,
                                reg.line,
                                "Django",
                            )
                        )
            elif entry.view:
                routes.append(
                    Route(
                        "ANY",
                        join_paths(prefix, pattern),
                        entry.view,
                        path,
                        entry.line,
                        "Django",
                    )
                )

    roots = sorted(set(urlconfs) - included) or sorted(urlconfs)
    for root in roots:
        walk(root, "", ())
    return routes


def _clean_pattern(pattern: str) -> str:
    """Drop regex anchors from `re_path` patterns: ^api/users/$ -> api/users/."""
    return pattern.lstrip("^").rstrip("$")
