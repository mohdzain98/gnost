import json
from pathlib import Path

import pytest

from gnost.core.cycles import (
    DEFERRED,
    IMPORT_TIME,
    example_cycle,
    find_cycles,
    strongly_connected_components,
)
from gnost.core.graph import DependencyGraph
from gnost.languages.javascript import JavaScriptAdapter
from gnost.languages.python import PythonAdapter
from gnost.languages.typescript import TypeScriptAdapter
from gnost.scanner.engine import ScannerEngine


def _graph(edges, deferred=()):
    g = DependencyGraph()
    for src, dst in edges:
        g._ensure_node(src)
        g._ensure_node(dst)
        g.add_edge(src, dst, deferred=(src, dst) in deferred)
    return g


# ---- algorithm ----


def test_acyclic_graph_has_no_cycles():
    assert find_cycles(_graph([("a", "b"), ("b", "c"), ("a", "c")])) == []


def test_two_cycle_three_cycle_and_self_loop():
    g = _graph(
        [
            ("a", "b"),
            ("b", "a"),
            ("x", "y"),
            ("y", "z"),
            ("z", "x"),
            ("s", "s"),
            ("a", "x"),
        ]
    )
    cycles = find_cycles(g)
    assert [c.files for c in cycles] == [["x", "y", "z"], ["a", "b"], ["s"]]
    assert example_cycle(["s"], g.dependencies_of) == ["s", "s"]


def test_example_cycle_is_a_real_loop():
    g = _graph([("a", "b"), ("b", "c"), ("c", "a"), ("a", "c")])
    loop = find_cycles(g)[0].example
    assert loop[0] == loop[-1] and len(loop) >= 3
    assert all(dst in g.dependencies_of(src) for src, dst in zip(loop, loop[1:]))


def test_scc_handles_very_deep_graphs_without_recursion_errors():
    n = 20000
    chain = [(f"n{i:05d}", f"n{i + 1:05d}") for i in range(n)]
    g = _graph(chain + [(f"n{n:05d}", "n00000")])
    comps = strongly_connected_components(list(g.all_nodes()), g.dependencies_of)
    assert len(comps) == 1 and len(comps[0]) == n + 1


def test_results_are_deterministic_regardless_of_insertion_order():
    edges = [("b", "a"), ("a", "b"), ("d", "c"), ("c", "d")]
    assert [c.files for c in find_cycles(_graph(edges))] == [
        c.files for c in find_cycles(_graph(list(reversed(edges))))
    ]


def test_deferred_only_cycle_is_classified_deferred():
    g = _graph([("a", "b"), ("b", "a")], deferred={("b", "a")})
    cycle = find_cycles(g)[0]
    assert cycle.kind == DEFERRED
    assert cycle.example == ["a", "b", "a"]


def test_eager_loop_inside_a_larger_deferred_group_is_import_time():
    g = _graph(
        [("a", "b"), ("b", "a"), ("b", "c"), ("c", "b")],
        deferred={("b", "c"), ("c", "b")},
    )
    (cycle,) = find_cycles(g)
    assert cycle.kind == IMPORT_TIME and cycle.files == ["a", "b", "c"]
    # the example uses eager edges only
    assert set(cycle.example) == {"a", "b"}


def test_import_time_cycles_sort_before_deferred():
    g = _graph(
        [("a", "b"), ("b", "a"), ("x", "y"), ("y", "x"), ("y", "z"), ("z", "y")],
        deferred={("a", "b"), ("b", "a")},
    )
    assert [c.kind for c in find_cycles(g)] == [IMPORT_TIME, DEFERRED]


# ---- deferred import detection ----


def test_python_marks_function_and_type_checking_imports_deferred():
    src = (
        "import eager_mod\n"
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    import only_types\nelse:\n    import runtime_fallback\n"
        "class K:\n    import in_class\n"
        "def f():\n    import in_func\n"
        "g = lambda: __import__('x')\n"
        "async def h():\n    from pkg import in_async\n"
    )
    flags = {e.target: e.deferred for e in PythonAdapter().detect_imports("f.py", src)}
    assert flags == {
        "eager_mod": False,
        "typing": False,
        "only_types": True,
        "runtime_fallback": False,
        "in_class": False,  # a class body runs at import time
        "in_func": True,
        "pkg": True,
    }


def test_js_marks_dynamic_and_type_only_imports_deferred():
    src = (
        "import a from './a';\n"
        "import type { T } from './types';\n"
        "const L = lazy(() => import('./lazy'));\n"
        "import { x } from './both';\n"
        "import type { Y } from './both';\n"
    )
    for adapter in (JavaScriptAdapter(), TypeScriptAdapter()):
        flags = {e.target: e.deferred for e in adapter.detect_imports("f.ts", src)}
        assert flags == {
            "./a": False,
            "./types": True,
            "./lazy": True,
            "./both": False,  # one eager import makes the edge eager
        }


# ---- end to end on fixtures ----


def _scan_graph(root: Path) -> DependencyGraph:
    scan = ScannerEngine([PythonAdapter()]).scan(str(root))
    return DependencyGraph.from_scan(scan)


def test_fixture_cycle_kinds(fixture_repo):
    root = fixture_repo("deferred_cycle")
    cycles = find_cycles(_scan_graph(root))
    assert [(c.kind, [Path(f).name for f in c.files]) for c in cycles] == [
        (DEFERRED, ["a.py", "b.py"]),
        (DEFERRED, ["c.py", "d.py"]),
    ]


def test_fixture_import_time_cycle(fixture_repo):
    root = fixture_repo("cyclic_py")
    (cycle,) = find_cycles(_scan_graph(root))
    assert cycle.kind == IMPORT_TIME
    assert [Path(f).name for f in cycle.example] == ["a.py", "b.py", "a.py"]


def test_deferred_edges_are_recorded_on_the_graph(fixture_repo):
    root = fixture_repo("deferred_cycle")
    graph = _scan_graph(root)
    a, b = f"{root}/svc/a.py", f"{root}/svc/b.py"
    assert (b, a) in graph.deferred_edges
    assert (a, b) not in graph.deferred_edges
    assert graph.eager_dependencies_of(b) == set()


# ---- insights JSON ----


def _payload(root: Path):
    from gnost.cli.commands.onboard import run

    out = root / "insights.json"
    run(path=str(root), json_out=str(out), insights_only=True)
    return json.loads(out.read_text(encoding="utf-8"))


PROJECTS = [
    "python_app",
    "js_app",
    "ts_app",
    "java_app",
    "cyclic_py",
    "package_app",
    "react_app",
    "deferred_cycle",
]


@pytest.mark.parametrize("project", PROJECTS)
def test_insights_json_matches_schema(project, fixture_repo):
    jsonschema = pytest.importorskip("jsonschema")
    from gnost.reporters.insights_json import load_schema

    payload = _payload(fixture_repo(project))
    jsonschema.validate(payload, load_schema())


def test_insights_json_is_portable_and_deterministic(fixture_repo):
    root = fixture_repo("package_app")
    first = _payload(root)
    second = _payload(root)
    assert first == second

    text = json.dumps(first)
    assert str(root) not in text and "\\" not in text
    assert "app/main.py" in first["layers"]["entry"]
    assert first["project"]["framework"] == "FastAPI"
    assert first["stats"]["files"] == first["project"]["files"]


def test_insights_json_reports_cycles(fixture_repo):
    payload = _payload(fixture_repo("cyclic_py"))
    assert payload["stats"]["cycles_import_time"] == 1
    assert payload["cycles"] == [
        {
            "kind": "import-time",
            "files": ["pkg/a.py", "pkg/b.py"],
            "example": ["pkg/a.py", "pkg/b.py", "pkg/a.py"],
        }
    ]
    assert any(c["category"] == "circular_dependency" for c in payload["caution_areas"])
    deferred = _payload(fixture_repo("deferred_cycle"))
    assert deferred["stats"]["cycles_deferred"] == 2
    assert deferred["caution_areas"] == [] or all(
        c["category"] != "circular_dependency" for c in deferred["caution_areas"]
    )
    flagged = {
        (e["source"], e["target"]): e["deferred"] for e in deferred["graph"]["edges"]
    }
    assert flagged[("svc/b.py", "svc/a.py")] is True


# ---- CLI behaviour ----


def test_insights_only_writes_only_the_json(fixture_repo):
    from gnost.cli.commands.onboard import run

    root = fixture_repo("python_app")
    run(path=str(root), insights_only=True)
    assert (root / "docs/insights/gnost_insights.json").is_file()
    assert not (root / "ONBOARD.md").exists()
    assert not (root / "docs/flow").exists()


def test_json_flag_writes_json_next_to_the_normal_output(fixture_repo):
    from gnost.cli.commands.onboard import run

    root = fixture_repo("python_app")
    run(path=str(root), json_out="")
    assert (root / "docs/insights/gnost_insights.json").is_file()
    assert (root / "ONBOARD.md").is_file()
    assert (root / "docs/flow/FLOW-full.mmd").is_file()


def test_json_flag_accepts_a_custom_path(fixture_repo, tmp_path):
    from gnost.cli.commands.onboard import run

    root = fixture_repo("python_app")
    target = tmp_path / "out" / "x.json"
    run(path=str(root), json_out=str(target), insights_only=True)
    assert target.is_file()
    assert not (root / "docs").exists()


def test_cli_parses_json_and_insights_only(fixture_repo, monkeypatch):
    from gnost.cli import main

    root = fixture_repo("python_app")
    monkeypatch.setattr("sys.argv", ["gnost", "onboard", str(root), "--insights-only"])
    main()
    assert (root / "docs/insights/gnost_insights.json").is_file()
    assert not (root / "ONBOARD.md").exists()
