"""Function-level call graph for Python projects.

The file graph says which files depend on which; this one says which *functions*
call which, so a request can be followed from its handler down through the code.

Calls are resolved through the syntax tree and the project's imports:

    helper()                a function or class in the same file
    helper()                a name imported with `from x import helper`
    store.save()            a module imported as `store`
    Store.load()            a class (local or imported)
    self.step()             a method of the same class (or a base class in the file)

Calls through other objects (`self.client.send()`, `request.json()`) are not
followed: without types there is no way to know what they point at.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from gnost.core.resolver import ImportResolver
from gnost.scanner.models import ScanResult

Node = Tuple[str, str]  # (file, qualified name)
TASK_DISPATCH = {"delay", "apply_async", "s", "si", "signature", "apply"}
MODULE = "<module>"  # code that runs when the file is imported
MAIN = "<main>"  # the body of `if __name__ == "__main__":`


@dataclass
class CallRef:
    kind: str  # "name", "attr" or "self"
    base: Optional[str]
    name: str
    line: int


@dataclass
class FuncInfo:
    file: str
    qualname: str
    line: int
    calls: List[CallRef] = field(default_factory=list)


@dataclass
class FileSymbols:
    path: str
    functions: Dict[str, FuncInfo] = field(default_factory=dict)
    classes: Dict[str, List[str]] = field(default_factory=dict)  # class -> base names
    imports: Dict[str, Tuple[str, Optional[str], int]] = field(default_factory=dict)


@dataclass
class CallGraph:
    functions: Dict[Node, FuncInfo] = field(default_factory=dict)
    edges: Dict[Node, List[Node]] = field(default_factory=dict)  # in call order
    unparsed: List[str] = field(default_factory=list)

    def calls_of(self, node: Node) -> List[Node]:
        return self.edges.get(node, [])

    @property
    def edge_count(self) -> int:
        return sum(len(v) for v in self.edges.values())


# -------------------------
# Reading one file
# -------------------------


def _call_ref(call: ast.Call) -> Optional[CallRef]:
    func = call.func
    if isinstance(func, ast.Name):
        return CallRef("name", None, func.id, call.lineno)
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        base = func.value.id
        kind = "self" if base in ("self", "cls") else "attr"
        return CallRef(kind, base, func.attr, call.lineno)
    return None


def _calls_in(nodes) -> List[CallRef]:
    refs: List[CallRef] = []
    for top in nodes:
        for node in ast.walk(top):
            if isinstance(node, ast.Call):
                ref = _call_ref(node)
                if ref:
                    refs.append(ref)
    refs.sort(key=lambda r: r.line)
    return refs


def _is_main_guard(node: ast.AST) -> bool:
    if not isinstance(node, ast.If):
        return False
    test = node.test
    if not (
        isinstance(test, ast.Compare)
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Eq)
    ):
        return False
    sides = [test.left, test.comparators[0]]
    return any(isinstance(s, ast.Name) and s.id == "__name__" for s in sides) and any(
        isinstance(s, ast.Constant) and s.value == "__main__" for s in sides
    )


def read_file(path: str, content: str) -> Optional[FileSymbols]:
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError):
        return None

    symbols = FileSymbols(path=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                module = alias.name if alias.asname else alias.name.split(".")[0]
                symbols.imports[local] = (module, None, 0)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                symbols.imports[alias.asname or alias.name] = (
                    node.module or "",
                    alias.name,
                    node.level,
                )

    module_level: List[ast.AST] = []
    main_level: List[ast.AST] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.functions[node.name] = FuncInfo(
                path, node.name, node.lineno, _calls_in(node.body)
            )
        elif isinstance(node, ast.ClassDef):
            symbols.classes[node.name] = [
                b.id for b in node.bases if isinstance(b, ast.Name)
            ]
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qual = f"{node.name}.{item.name}"
                    symbols.functions[qual] = FuncInfo(
                        path, qual, item.lineno, _calls_in(item.body)
                    )
        elif _is_main_guard(node):
            main_level += node.body  # type: ignore[attr-defined]
        elif not isinstance(node, (ast.Import, ast.ImportFrom)):
            module_level.append(node)

    if main_level:
        symbols.functions[MAIN] = FuncInfo(
            path, MAIN, main_level[0].lineno, _calls_in(main_level)
        )
    module_calls = _calls_in(module_level)
    if module_calls:
        symbols.functions[MODULE] = FuncInfo(path, MODULE, 1, module_calls)
    return symbols


# -------------------------
# Resolving calls
# -------------------------


class _Resolver:
    def __init__(self, files: Dict[str, FileSymbols], imports: ImportResolver):
        self.files = files
        self.imports = imports

    def target(self, symbols: FileSymbols, owner: str, ref: CallRef) -> Optional[Node]:
        if ref.kind == "self":
            cls = owner.split(".")[0] if "." in owner else None
            return self._method(symbols, cls, ref.name) if cls else None
        if ref.kind == "name":
            return self._named(symbols, ref.name)
        return self._attribute(symbols, ref.base or "", ref.name)

    def _method(
        self,
        symbols: FileSymbols,
        cls: Optional[str],
        name: str,
        seen: Optional[Set[str]] = None,
    ) -> Optional[Node]:
        seen = seen or set()
        if cls is None or cls in seen:
            return None
        qual = f"{cls}.{name}"
        if qual in symbols.functions:
            return (symbols.path, qual)
        for base in symbols.classes.get(cls, []):
            found = self._method(symbols, base, name, seen | {cls})
            if found:
                return found
        return None

    def _symbol(self, symbols: FileSymbols, name: str) -> Optional[Node]:
        """A function, or a class (its __init__), defined in `symbols`."""
        if name in symbols.functions:
            return (symbols.path, name)
        if name in symbols.classes:
            init = self._method(symbols, name, "__init__")
            return init
        return None

    def _named(self, symbols: FileSymbols, name: str) -> Optional[Node]:
        local = self._symbol(symbols, name)
        if local:
            return local
        imported = symbols.imports.get(name)
        if not imported or not imported[1]:
            return None
        module, attr, level = imported
        file = self.imports.module_file(symbols.path, module, level, None)
        target = self.files.get(file) if file else None
        return self._symbol(target, attr) if target and attr else None

    def _attribute(self, symbols: FileSymbols, base: str, name: str) -> Optional[Node]:
        # task.delay(...) / task.apply_async(...): dispatching a Celery-style task
        # runs the task function itself.
        if name in TASK_DISPATCH:
            task = self._named(symbols, base)
            if task:
                return task

        # Class.method() on a class defined here
        if base in symbols.classes:
            return self._method(symbols, base, name)

        imported = symbols.imports.get(base)
        if not imported:
            return None
        module, attr, level = imported

        # `from pkg.mod import Class` then Class.method()
        if attr is not None:
            owner_file = self.imports.module_file(symbols.path, module, level, None)
            owner = self.files.get(owner_file) if owner_file else None
            if owner and attr in owner.classes:
                return self._method(owner, attr, name)

        # `import pkg.mod as base`, or `from pkg import base` where base is a module
        file = self.imports.module_file(symbols.path, module, level, attr)
        target = self.files.get(file) if file else None
        return self._symbol(target, name) if target else None


def build_call_graph(scan: ScanResult, resolver: ImportResolver) -> CallGraph:
    graph = CallGraph()
    files: Dict[str, FileSymbols] = {}

    for info in scan.files:
        if info.language != "python":
            continue
        try:
            with open(info.path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            continue
        symbols = read_file(info.path, content)
        if symbols is None:
            graph.unparsed.append(info.path)
        else:
            files[info.path] = symbols

    linker = _Resolver(files, resolver)
    for path, symbols in sorted(files.items()):
        for qual, func in symbols.functions.items():
            node = (path, qual)
            graph.functions[node] = func
            targets: List[Node] = []
            for ref in func.calls:
                target = linker.target(symbols, qual, ref)
                if target and target != node and target not in targets:
                    targets.append(target)
            if targets:
                graph.edges[node] = targets

    graph.unparsed.sort()
    return graph


# -------------------------
# Flows: the call tree below an entry point
# -------------------------

MAX_FLOWS = 25  # entries kept in the output
TREE_DEPTH = 5  # levels of calls followed
TREE_NODES = 60  # most functions listed under one entry


@dataclass
class CallNode:
    function: str
    file: str
    line: int
    calls: List["CallNode"] = field(default_factory=list)
    repeat: bool = False  # already shown earlier in this tree


@dataclass
class FunctionFlow:
    kind: str  # "route" or "main"
    label: str  # "POST /v1/ingest" or "app/main.py"
    entry: CallNode
    size: int  # functions in the tree, entry included
    truncated: bool = False  # depth or size limit cut the tree short


def build_tree(
    graph: CallGraph, start: Node, depth: int = TREE_DEPTH, limit: int = TREE_NODES
) -> Tuple[CallNode, int, bool]:
    """Call tree below `start`: (root, number of functions, was it cut short)."""
    seen: Set[Node] = {start}
    count = 1
    cut = False

    def make(node: Node, remaining: int) -> CallNode:
        nonlocal count, cut
        info = graph.functions.get(node)
        result = CallNode(node[1], node[0], info.line if info else 0)
        if remaining == 0:
            cut = cut or bool(graph.calls_of(node))
            return result
        for child in graph.calls_of(node):
            if child in seen:
                again = graph.functions.get(child)
                result.calls.append(
                    CallNode(
                        child[1], child[0], again.line if again else 0, repeat=True
                    )
                )
                continue
            if count >= limit:
                cut = True
                break
            seen.add(child)
            count += 1
            result.calls.append(make(child, remaining - 1))
        return result

    return make(start, depth), count, cut


def find_flows(
    scan: ScanResult,
    graph: CallGraph,
    depth: int = TREE_DEPTH,
    limit: int = MAX_FLOWS,
) -> List[FunctionFlow]:
    """Flows for the program's main entry points and its routes.

    Entries that call nothing the graph can resolve are left out. Main entries
    come first, then routes with the biggest call trees.
    """
    flows: List[FunctionFlow] = []

    for ep in scan.entry_points:
        node = (ep.file, MAIN)
        if (
            ep.priority == ep.PRIMARY
            and node in graph.functions
            and graph.calls_of(node)
        ):
            tree, size, cut = build_tree(graph, node, depth)
            label = os.path.relpath(ep.file, scan.root).replace(os.sep, "/")
            flows.append(FunctionFlow("main", label, tree, size, cut))

    routed: List[FunctionFlow] = []
    done: Set[Tuple[str, str]] = set()
    for route in scan.routes:
        name = route.handler.split(".")[-1]
        node = (
            route.file,
            route.handler if route.handler in {q for (_, q) in ()} else name,
        )
        node = (route.file, name)
        if node not in graph.functions or not graph.calls_of(node):
            continue
        key = (f"{route.method} {route.path}", name)
        if key in done:
            continue
        done.add(key)
        tree, size, cut = build_tree(graph, node, depth)
        routed.append(
            FunctionFlow("route", f"{route.method} {route.path}", tree, size, cut)
        )

    routed.sort(key=lambda f: (-f.size, f.label))
    return (flows + routed)[:limit]
