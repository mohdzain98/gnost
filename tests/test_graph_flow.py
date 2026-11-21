import os
from pathlib import Path
from gnost.core.flow import FlowBuilder
from gnost.core.graph import DependencyGraph
from gnost.languages.java import JavaAdapter
from gnost.languages.javascript import JavaScriptAdapter
from gnost.languages.python import PythonAdapter
from gnost.languages.typescript import TypeScriptAdapter
from gnost.scanner.engine import ScannerEngine


def _scan(root):
    engine = ScannerEngine(
        [PythonAdapter(), JavaScriptAdapter(), TypeScriptAdapter(), JavaAdapter()]
    )
    return engine.scan(str(root))


def _rel(root, paths):
    return {p[len(str(root)) + 1 :].replace("\\", "/") for p in paths}


def test_graph_python_edges(fixture_repo):
    root = fixture_repo("python_app")
    graph = DependencyGraph.from_scan(_scan(root))

    main = str(Path(root, "main.py"))
    assert _rel(root, graph.dependencies_of(main)) == {
        "app/api.py",
        "app/services/users.py",
    }
    users = str(Path(root, "app/services/users.py"))
    assert _rel(root, graph.dependencies_of(users)) == {"app/services/db.py"}
    assert _rel(root, graph.dependents_of(users)) == {"main.py", "app/api.py"}
    assert graph.fan_in(users) == 2 and graph.fan_out(main) == 2


def test_graph_roots_and_leaves(fixture_repo):
    root = fixture_repo("python_app")
    graph = DependencyGraph.from_scan(_scan(root))
    assert str(Path(root, "main.py")) in graph.roots()
    assert str(Path(root, "app/services/db.py")) in graph.leaves()
    assert graph.all_nodes() >= {
        str(Path(root, "main.py")),
        str(Path(root, "app/api.py")),
    }


def test_graph_js_relative_imports(fixture_repo):
    root = fixture_repo("js_app")
    graph = DependencyGraph.from_scan(_scan(root))
    index = str(Path(root, "src/index.js"))
    assert _rel(root, graph.dependencies_of(index)) == {
        "src/lib/greet.js",
        "src/routes/users.js",
    }


def test_graph_java_imports_resolve_by_package_path(fixture_repo):
    root = fixture_repo("java_app")
    graph = DependencyGraph.from_scan(_scan(root))
    app = str(Path(root, "src/main/java/demo/App.java"))
    assert _rel(root, graph.dependencies_of(app)) == {"src/main/java/demo/Greeter.java"}


def test_graph_ts_imports_resolve_tsx(fixture_repo):
    root = fixture_repo("ts_app")
    graph = DependencyGraph.from_scan(_scan(root))
    index = str(Path(root, "src/index.ts"))
    assert _rel(root, graph.dependencies_of(index)) == {"src/math.ts", "src/view.tsx"}


def test_graph_cyclic_fixture_has_cycle_edges(fixture_repo):
    root = fixture_repo("cyclic_py")
    graph = DependencyGraph.from_scan(_scan(root))
    a, b = str(Path(root, "pkg/a.py")), str(Path(root, "pkg/b.py"))
    assert graph.dependencies_of(a) == {b}
    assert graph.dependencies_of(b) == {a}


def test_flow_paths_edges_and_layers(fixture_repo):
    root = fixture_repo("python_app")
    scan = _scan(root)
    flow = FlowBuilder(DependencyGraph.from_scan(scan), scan).build()

    paths = {tuple(_rel(root, [n]).pop() for n in p.path) for p in flow.paths}
    assert ("main.py", "app/services/users.py", "app/services/db.py") in paths
    # Every dependency edge is kept even when a path does not walk it.
    edges = {tuple(_rel(root, [n]).pop() for n in e) for e in flow.edges}
    assert ("app/api.py", "app/services/users.py") in edges
    assert flow.depths[str(Path(root, "main.py"))] == 0
    assert flow.depths[str(Path(root, "app/services/db.py"))] == 2
    # api.py is also an entry point, but main.py imports it, so only main.py
    # starts the flow.
    assert _rel(root, flow.layers["entry"]) == {"main.py"}
    assert _rel(root, flow.layers["leaf"]) == {"app/services/db.py"}
    assert flow.overview_nodes() >= flow.layers["core"]


def test_flow_falls_back_to_graph_roots_without_entry_points(tmp_path):
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("x = 1\n")
    scan = _scan(tmp_path)
    assert scan.entry_points == []
    flow = FlowBuilder(DependencyGraph.from_scan(scan), scan).build()
    assert [p.path for p in flow.paths] == [
        [str(Path(tmp_path, "a.py")), str(Path(tmp_path, "b.py"))]
    ]


def test_flow_uses_secondary_entry_points_when_nothing_else(tmp_path):
    (tmp_path / "tool.py").write_text(
        'import b\nif __name__ == "__main__":\n    pass\n'
    )
    (tmp_path / "b.py").write_text("x = 1\n")
    scan = _scan(tmp_path)
    assert [e.priority for e in scan.entry_points] == [1]
    flow = FlowBuilder(DependencyGraph.from_scan(scan), scan).build()
    assert flow.paths and flow.paths[0].start == str(Path(tmp_path, "tool.py"))


def test_flow_terminates_on_cycle(fixture_repo):
    root = fixture_repo("cyclic_py")
    scan = _scan(root)
    flow = FlowBuilder(DependencyGraph.from_scan(scan), scan).build()
    chains = {tuple(_rel(root, [n]).pop() for n in p.path) for p in flow.paths}
    assert chains == {("main.py", "pkg/a.py", "pkg/b.py")}
    # The edge that closes the cycle is still reported.
    edges = {tuple(_rel(root, [n]).pop() for n in e) for e in flow.edges}
    assert ("pkg/b.py", "pkg/a.py") in edges
    # The file where the branch stopped is not mislabelled as a leaf.
    assert flow.layers["leaf"] == set()


def test_flow_path_count_stays_bounded_on_dense_graphs(tmp_path):
    """A layered graph has 3**8 routes; the flow must not enumerate them."""
    layers, width = 8, 3
    names = [[f"l{i}_{j}.py" for j in range(width)] for i in range(layers)]
    for i, layer in enumerate(names):
        for name in layer:
            body = ""
            if i + 1 < layers:
                body = "".join(f"import {n[:-3]}\n" for n in names[i + 1])
            (tmp_path / name).write_text(body)
    (tmp_path / "main.py").write_text(
        "".join(f"import {n[:-3]}\n" for n in names[0])
        + 'if __name__ == "__main__":\n    pass\n'
    )
    scan = _scan(tmp_path)
    flow = FlowBuilder(DependencyGraph.from_scan(scan), scan).build()
    assert len(flow.paths) <= len(scan.files)


def test_flow_starts_from_primary_entry_points_only(fixture_repo):
    root = fixture_repo("package_app")
    scan = _scan(root)
    starts = {
        p.start
        for p in FlowBuilder(DependencyGraph.from_scan(scan), scan).build().paths
    }
    assert starts == {str(Path(root, "app/main.py"))}


def test_graph_resolves_from_package_import_to_submodule_and_init(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "mod.py").write_text("x = 1\n")
    (tmp_path / "main.py").write_text("from pkg import mod\n")
    graph = DependencyGraph.from_scan(_scan(tmp_path))
    assert graph.dependencies_of(str(Path(tmp_path, "main.py"))) == {
        str(Path(tmp_path, "pkg/__init__.py")),
        str(Path(tmp_path, "pkg/mod.py")),
    }


def test_entry_reachable_from_another_entry_is_not_a_root(fixture_repo):
    """main.tsx imports App.tsx; only main.tsx should start the flow."""
    root = fixture_repo("react_app")
    scan = _scan(root)
    assert {Path(e.file).name for e in scan.entry_points} == {
        "main.tsx",
        "App.tsx",
    }
    flow = FlowBuilder(DependencyGraph.from_scan(scan), scan).build()
    assert {p.start for p in flow.paths} == {str(Path(root, "src/main.tsx"))}
    assert _rel(root, flow.layers["entry"]) == {"src/main.tsx"}


def test_unreachable_files_do_not_get_negative_hotspot_scores(tmp_path):
    from gnost.core.ranker import HotspotRanker

    (tmp_path / "main.py").write_text(
        'import a\nif __name__ == "__main__":\n    pass\n'
    )
    (tmp_path / "a.py").write_text("")
    (tmp_path / "island.py").write_text("import hub\n")
    (tmp_path / "hub.py").write_text("")
    scan = _scan(tmp_path)
    flow = FlowBuilder(DependencyGraph.from_scan(scan), scan).build()
    ranked = HotspotRanker(DependencyGraph.from_scan(scan), flow).rank()
    assert all(h.score >= 0 for h in ranked)


def test_flow_still_shows_the_project_when_the_entry_point_imports_nothing(
    tmp_path,
) -> None:
    """Frameworks that wire code by scanning (Spring Boot) leave the entry class import-free."""
    from gnost.changes.snapshot import ProjectSnapshot

    (tmp_path / "app.py").write_text('if __name__ == "__main__":\n    print("hi")\n')
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("import c\n")
    (tmp_path / "c.py").write_text("X = 1\n")
    flow = ProjectSnapshot.scan_folder(str(tmp_path)).flow
    names = {(os.path.basename(s), os.path.basename(d)) for s, d in flow.edges}
    assert names == {("a.py", "b.py"), ("b.py", "c.py")}
