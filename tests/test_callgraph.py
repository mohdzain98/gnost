import json
from pathlib import Path
from typing import Dict, List

import pytest

from gnost.core.callgraph import (
    MAIN,
    MODULE,
    TREE_NODES,
    build_call_graph,
    build_tree,
    find_flows,
    read_file,
)
from gnost.core.resolver import ImportResolver
from gnost.languages.python import PythonAdapter
from gnost.routes import find_routes
from gnost.scanner.engine import ScannerEngine
from tests.test_mermaid import check_mermaid


def graph_of(root: Path):
    scan = ScannerEngine([PythonAdapter()]).scan(str(root))
    scan.routes = find_routes(scan)
    return scan, build_call_graph(scan, ImportResolver(str(root), scan.files))


def project(tmp_path: Path, files: Dict[str, str]) -> Path:
    for name, text in files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return tmp_path


def edges(root: Path, graph) -> Dict[str, List[str]]:
    def name(node):
        return f"{Path(node[0]).relative_to(root).as_posix()}:{node[1]}"

    return {name(n): [name(c) for c in cs] for n, cs in sorted(graph.edges.items())}


# ---- resolving calls ----


def test_local_imported_module_and_class_calls(tmp_path):
    root = project(
        tmp_path,
        {
            "app.py": (
                "from util import helper, Thing\n"
                "import store\n"
                "def main():\n"
                "    helper()\n"
                "    store.save()\n"
                "    Thing().run()\n"
                "    local()\n"
                "    print(len([]))\n"
                "def local(): ...\n"
            ),
            "util.py": "def helper(): ...\nclass Thing:\n    def __init__(self): ...\n    def run(self): ...\n",
            "store.py": "def save(): ...\n",
        },
    )
    _, graph = graph_of(root)
    assert edges(root, graph)["app.py:main"] == [
        "util.py:helper",
        "store.py:save",
        "util.py:Thing.__init__",  # Thing() -> its constructor
        "app.py:local",
    ]


def test_package_submodule_and_class_method_calls(tmp_path):
    root = project(
        tmp_path,
        {
            "pkg/__init__.py": "",
            "pkg/store.py": "def save(): ...\nclass Repo:\n    @staticmethod\n    def make(): ...\n",
            "main.py": (
                "from pkg import store\nfrom pkg.store import Repo\n"
                "def go():\n    store.save()\n    Repo.make()\n"
            ),
        },
    )
    _, graph = graph_of(root)
    assert edges(root, graph)["main.py:go"] == [
        "pkg/store.py:save",
        "pkg/store.py:Repo.make",
    ]


def test_self_calls_follow_methods_and_base_classes(tmp_path):
    root = project(
        tmp_path,
        {
            "m.py": (
                "class Base:\n    def shared(self): ...\n"
                "class Child(Base):\n"
                "    def run(self):\n        self.step()\n        self.shared()\n        self.client.send()\n"
                "    def step(self): ...\n"
            )
        },
    )
    _, graph = graph_of(root)
    assert edges(root, graph)["m.py:Child.run"] == [
        "m.py:Child.step",
        "m.py:Base.shared",
    ]


def test_celery_style_dispatch_follows_the_task(tmp_path):
    root = project(
        tmp_path,
        {
            "tasks.py": "@app.task\ndef process(doc): ...\n",
            "api.py": (
                "from tasks import process\n"
                "def handler(doc):\n    process.delay(doc)\n    process.apply_async(args=[doc])\n"
            ),
        },
    )
    _, graph = graph_of(root)
    assert edges(root, graph)["api.py:handler"] == ["tasks.py:process"]


def test_relative_and_aliased_imports(tmp_path):
    root = project(
        tmp_path,
        {
            "pkg/__init__.py": "",
            "pkg/a.py": "from .b import work as do\nfrom . import c\ndef run():\n    do()\n    c.go()\n",
            "pkg/b.py": "def work(): ...\n",
            "pkg/c.py": "def go(): ...\n",
        },
    )
    _, graph = graph_of(root)
    assert edges(root, graph)["pkg/a.py:run"] == ["pkg/b.py:work", "pkg/c.py:go"]


def test_module_level_and_main_guard_code_become_pseudo_functions(tmp_path):
    root = project(
        tmp_path,
        {
            "run.py": (
                "from lib import setup, go\n"
                "setup()\n"
                "def main(): go()\n"
                'if __name__ == "__main__":\n    main()\n'
            ),
            "lib.py": "def setup(): ...\ndef go(): ...\n",
        },
    )
    _, graph = graph_of(root)
    e = edges(root, graph)
    assert e["run.py:<module>"] == ["lib.py:setup"]
    assert e["run.py:<main>"] == ["run.py:main"]
    assert MAIN == "<main>" and MODULE == "<module>"


def test_unparsable_files_are_listed_not_fatal(tmp_path):
    root = project(tmp_path, {"ok.py": "def f(): ...\n", "bad.py": "def broken(:\n"})
    scan, graph = graph_of(root)
    assert [Path(p).name for p in graph.unparsed] == ["bad.py"]
    assert read_file("x.py", "def f(:") is None


# ---- flows ----


def test_tree_marks_repeats_and_terminates_on_recursion(tmp_path):
    root = project(
        tmp_path,
        {
            "m.py": "def a():\n    b()\n    c()\ndef b():\n    c()\n    a()\ndef c():\n    a()\n"
        },
    )
    _, graph = graph_of(root)
    tree, size, cut = build_tree(graph, (str(root / "m.py"), "a"))
    assert size == 3 and not cut
    b = tree.calls[0]
    assert [(n.function, n.repeat) for n in b.calls] == [("c", False), ("a", True)] or [
        (n.function, n.repeat) for n in b.calls
    ] == [("a", True), ("c", False)]
    assert any(n.repeat for n in tree.calls) or any(n.repeat for n in b.calls)


def test_tree_limits_depth_and_size(tmp_path):
    chain = (
        "".join(f"def f{i}():\n    f{i + 1}()\n" for i in range(30))
        + "def f30(): ...\n"
    )
    root = project(tmp_path, {"m.py": chain})
    _, graph = graph_of(root)
    _, size, cut = build_tree(graph, (str(root / "m.py"), "f0"), depth=4)
    assert size == 5 and cut

    wide = (
        "def top():\n"
        + "".join(f"    g{i}()\n" for i in range(200))
        + "".join(f"def g{i}(): ...\n" for i in range(200))
    )
    root2 = project(tmp_path / "w", {"m.py": wide})
    _, graph2 = graph_of(root2)
    _, size2, cut2 = build_tree(graph2, (str(root2 / "m.py"), "top"))
    assert size2 == TREE_NODES and cut2


def test_flows_for_routes_and_main_biggest_first(fixture_repo):
    root = fixture_repo("package_app")
    scan, graph = graph_of(root)
    flows = find_flows(scan, graph)
    labels = [f.label for f in flows]
    assert "POST /chat/api/v1/messages" in labels
    send = next(f for f in flows if f.label == "POST /chat/api/v1/messages")
    assert send.kind == "route" and send.entry.function == "send"
    assert [c.function for c in send.entry.calls] == ["save", "helper"] or {
        c.function for c in send.entry.calls
    } == {"save", "helper"}
    sizes = [f.size for f in flows if f.kind == "route"]
    assert sizes == sorted(sizes, reverse=True)


def test_entries_without_resolvable_calls_are_left_out(tmp_path):
    root = project(
        tmp_path,
        {
            "a.py": "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/x')\ndef x():\n    return len('a')\n"
        },
    )
    scan, graph = graph_of(root)
    assert find_flows(scan, graph) == []


# ---- reports ----


def test_markdown_json_and_diagram_output(fixture_repo):
    jsonschema = pytest.importorskip("jsonschema")
    from gnost.cli.commands.onboard import run
    from gnost.reporters.insights_json import load_schema

    root = fixture_repo("package_app")
    run(path=str(root), json_out="")

    md = (root / ".gnost/ONBOARD.md").read_text(encoding="utf-8")
    assert "## Function-level Flow" in md
    assert "### `POST /chat/api/v1/messages` → `send`" in md
    assert "- `save` (`app/services/store.py:" in md

    payload = json.loads((root / ".gnost/insights.json").read_text())
    jsonschema.validate(payload, load_schema())
    assert (
        payload["callgraph"]["functions"] > 0
        and payload["callgraph"]["unparsed_files"] == []
    )
    flow = next(
        f for f in payload["flows"] if f["label"] == "POST /chat/api/v1/messages"
    )
    assert flow["entry"]["file"] == "app/api/v1/chat.py"
    assert not flow["entry"]["file"].startswith("/")

    doc = (root / ".gnost/flow/function-flow.md").read_text(encoding="utf-8")
    check_mermaid(doc)
    assert "send<br/>app/api/v1/chat.py" in doc


def test_no_function_flow_section_without_python_entries(fixture_repo):
    from gnost.cli.commands.onboard import run

    root = fixture_repo("js_app")
    run(path=str(root))
    assert "## Function-level Flow" not in (root / ".gnost/ONBOARD.md").read_text(
        encoding="utf-8"
    )
    assert not (root / ".gnost/flow/function-flow.md").exists()
