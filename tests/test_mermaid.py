import re
from typing import Dict, Tuple

import pytest

from gnost.core.cycles import Cycle
from gnost.core.flow import FlowResult
from gnost.reporters.mermaid import (
    COMBINED_MAX_EDGES,
    MAX_CHARS,
    MermaidFlowReporter,
)
from gnost.reporters.mermaid_graph import (
    CYCLE,
    CYCLE_DEFERRED,
    CYCLE_SOFT,
    DEFERRED,
    NORMAL,
    build_diagram,
    common_prefix,
    edge_styles,
)

ROOT = "/proj"
EDGE_RE = re.compile(r"^\s+(\w+) (-->|-\.->|==>)(?:\|[^|]+\|)? (\w+)$")
NODE_RE = re.compile(r'^\s+(\w+)\["[^"\n]*"\]$')


def check_mermaid(text: str) -> None:
    """Cheap structural validation of every Mermaid block in `text`."""
    blocks = re.findall(r"```mermaid\n(.*?)```", text, re.S) or [text]
    for block in blocks:
        assert len(block) <= MAX_CHARS, "diagram too large for GitHub"
        lines = block.strip("\n").split("\n")
        assert lines[0].startswith("flowchart "), lines[0]
        defined, edges, link_indexes = set(), 0, []
        subgraphs = 0
        for line in lines[1:]:
            stripped = line.strip()
            if not stripped or stripped.startswith(("classDef", "class ")):
                continue
            if stripped.startswith("subgraph"):
                subgraphs += 1
            elif stripped == "end":
                subgraphs -= 1
            elif stripped.startswith("linkStyle"):
                link_indexes += [int(i) for i in stripped.split()[1].split(",")]
            elif m := NODE_RE.match(line):
                defined.add(m.group(1))
            elif m := EDGE_RE.match(line):
                edges += 1
                assert m.group(1) in defined and m.group(3) in defined, line
            else:
                pytest.fail(f"unrecognised Mermaid line: {line!r}")
        assert subgraphs == 0
        assert edges <= 500, "GitHub refuses more than 500 edges"
        assert all(i < edges for i in link_indexes)


def f(name: str) -> str:
    return f"{ROOT}/{name}"


def star(folders: int, per_folder: int) -> Dict[Tuple[str, str], str]:
    """Every file of every folder imports the first file of the next folder."""
    edges = {}
    for a in range(folders):
        for i in range(per_folder):
            b = (a + 1) % folders
            edges[(f(f"src/pkg{a}/m{i}.py"), f(f"src/pkg{b}/m0.py"))] = NORMAL
    return edges


# ---- diagram model ----


def test_small_graph_stays_file_level_with_relative_labels():
    d = build_diagram({(f("a/x.py"), f("a/y.py")): NORMAL}, ROOT, 50)
    assert not d.collapsed
    assert {n.label for n in d.nodes.values()} == {"a/x.py", "a/y.py"}


def test_big_graph_is_grouped_by_folder_and_weighted():
    edges = star(8, 12)  # 96 file edges between 8 folders
    d = build_diagram(edges, ROOT, 50)
    assert d.collapsed and d.level == 1
    assert len(d.edges) == 8 and all(e.weight == 12 for e in d.edges)
    assert d.total_edges == 96
    assert all(n.files == 12 or n.files == 12 for n in d.nodes.values() if n.folder)


def test_grouping_starts_below_the_common_prefix():
    files = [f("src/a/x.py"), f("src/b/y.py")]
    assert common_prefix(files, ROOT) == ["src"]
    d = build_diagram(star(8, 12), ROOT, 50)
    assert {n.label for n in d.nodes.values()} == {f"src/pkg{i}" for i in range(8)}


def test_explicit_collapse_level_is_honoured():
    edges = {
        (f("src/a/b/x.py"), f("src/a/c/y.py")): NORMAL,
        (f("src/d/z.py"), f("src/a/b/x.py")): NORMAL,
    }
    assert {
        n.label for n in build_diagram(edges, ROOT, 50, level=1).nodes.values()
    } == {"src/a", "src/d"}
    two = {n.label for n in build_diagram(edges, ROOT, 50, level=2).nodes.values()}
    assert "src/a/b" in two and "src/a/c" in two


def test_prunes_least_important_edges_but_keeps_cycles():
    edges = {(f(f"a/f{i}.py"), f(f"b/g{i}.py")): NORMAL for i in range(30)}
    edges[(f("a/c1.py"), f("b/c2.py"))] = CYCLE
    d = build_diagram(edges, ROOT, 1)  # 2 folders, 1 grouped edge
    assert len(d.edges) == 1 and d.edges[0].style == CYCLE
    cycle_node_keys = [k for k, n in d.nodes.items() if n.in_cycle]
    assert len(cycle_node_keys) == 2


def test_too_coarse_level_prefers_a_detailed_pruned_one():
    # 2 top-level folders, but 30 sub-folders: do not collapse to two boxes.
    edges = {}
    for i in range(30):
        edges[(f(f"app/s{i}/x.py"), f(f"app/s{(i + 1) % 30}/x.py"))] = NORMAL
        edges[(f(f"app/s{i}/x.py"), f(f"lib/y{i}.py"))] = NORMAL
    d = build_diagram(edges, ROOT, 40)
    assert len(d.nodes) >= 6


# ---- edge styles ----


def test_edge_styles_classify_cycles_and_deferred_edges():
    a, b, c, d = f("a.py"), f("b.py"), f("c.py"), f("d.py")
    edges = [(a, b), (b, a), (b, c), (c, b), (a, d), (d, c)]
    deferred = {(c, b), (d, c)}
    cycles = [Cycle(files=[a, b, c], example=[a, b, a], kind="import-time")]
    styles = edge_styles(edges, deferred, cycles)
    assert styles[(a, b)] == CYCLE and styles[(b, a)] == CYCLE
    # b -> c is eager but its loop only closes through the deferred c -> b
    assert styles[(b, c)] == CYCLE_SOFT
    assert styles[(c, b)] == CYCLE_DEFERRED
    assert styles[(a, d)] == NORMAL
    assert styles[(d, c)] == DEFERRED


# ---- rendering ----


def flow_for(
    edges: Dict[Tuple[str, str], str], entry: str, cycles=(), deferred=()
) -> FlowResult:
    pairs = sorted(edges)
    nodes = {n for e in pairs for n in e}
    return FlowResult(
        entry_points=[],
        paths=[],
        layers={"entry": {entry}, "core": nodes - {entry}, "leaf": set()},
        edges=pairs,
        depths={n: 0 if n == entry else 1 for n in nodes},
        cycles=list(cycles),
        deferred_edges=set(deferred),
    )


def test_cycle_edges_are_red_deferred_are_dotted_and_legend_is_noted():
    a, b, c = f("a.py"), f("b.py"), f("c.py")
    edges = {(a, b): NORMAL, (b, a): NORMAL, (b, c): NORMAL, (c, b): NORMAL}
    flow = flow_for(
        edges,
        a,
        cycles=[Cycle([a, b, c], [a, b, a], "import-time")],
        deferred={(c, b)},
    )
    reporter = MermaidFlowReporter(flow, ROOT)
    text = reporter.render(markdown=False)
    check_mermaid(text)
    assert "a_py ==> b_py" in text and "linkStyle" in text
    assert "-.->" in text and "classDef cycle" in text
    assert any("red" in n for n in reporter.notes)
    assert any("dotted" in n.lower() for n in reporter.notes)


def test_oversized_flow_is_grouped_and_stays_within_limits():
    edges = star(40, 40)  # 1600 file edges
    flow = flow_for(edges, f("src/pkg0/m0.py"))
    reporter = MermaidFlowReporter(flow, ROOT)
    text = reporter.render(markdown=True)
    check_mermaid(text)
    assert 'dir_src_pkg0["src/pkg0<br/>40 files"]' in text
    assert any("Grouped by folder" in n for n in reporter.notes)


def test_character_limit_forces_further_trimming():
    edges = {
        (
            f(f"{'x' * 60}/{'y' * 60}/pkg{i}/{'z' * 60}{j}.py"),
            f(f"{'x' * 60}/{'y' * 60}/pkg{(i + 1) % 150}/{'w' * 60}.py"),
        ): NORMAL
        for i in range(150)
        for j in range(3)
    }
    flow = flow_for(edges, f("a.py"))
    text = MermaidFlowReporter(flow, ROOT, max_edges=400).render(markdown=False)
    assert len(text) <= MAX_CHARS
    check_mermaid(text)


def test_digit_led_and_reserved_ids_are_made_safe():
    edges = {(f("2fast.py"), f("graph.py")): NORMAL}
    reporter = MermaidFlowReporter(flow_for(edges, f("2fast.py")), ROOT)
    text = reporter.render(markdown=False)
    check_mermaid(text)
    assert re.search(r"^\s+n_2fast_py\[", text, re.M)

    from gnost.reporters.mermaid_graph import Diagram, DiagramNode

    odd = Diagram(
        nodes={k: DiagramNode(key=k, label=k) for k in ("end", "class", "ok")}
    )
    ids = reporter._node_ids(odd)
    assert ids == {"end": "n_end", "class": "n_class", "ok": "ok"}


def test_overview_uses_a_smaller_budget():
    edges = star(8, 12)
    flow = flow_for(edges, f("src/pkg0/m0.py"))
    full = MermaidFlowReporter(flow, ROOT, max_edges=200).render(markdown=False)
    assert "dir_" not in full  # 96 edges fit at file level
    overview = MermaidFlowReporter(flow, ROOT, overview=True).render(markdown=False)
    assert "dir_" in overview  # 96 > 60: grouped by folder


def test_forced_collapse_and_depth_limit():
    edges = {
        (f("src/a/x.py"), f("src/b/y.py")): NORMAL,
        (f("src/b/y.py"), f("src/c/z.py")): NORMAL,
    }
    flow = flow_for(edges, f("src/a/x.py"))
    flow.depths = {f("src/a/x.py"): 0, f("src/b/y.py"): 1, f("src/c/z.py"): 2}
    grouped = MermaidFlowReporter(flow, ROOT, collapse=1).render(markdown=False)
    assert "dir_src_a" in grouped
    limited = MermaidFlowReporter(flow, ROOT, depth=1).render(markdown=False)
    assert "src_c_z_py" not in limited and "src_b_y_py" in limited


def test_combined_paths_respect_their_own_smaller_budget():
    edges = star(8, 12)
    flow = flow_for(edges, f("src/pkg0/m0.py"))
    paths = [[a, b] for a, b in edges]
    text = MermaidFlowReporter(flow, ROOT, max_edges=200).render_combined_paths(paths)
    check_mermaid(text)
    assert COMBINED_MAX_EDGES < len(edges) and "dir_" in text


def test_document_adds_folder_drilldown_only_when_grouped():
    small = flow_for({(f("a.py"), f("b.py")): NORMAL}, f("a.py"))
    assert "Detail by folder" not in MermaidFlowReporter(small, ROOT).render_document()

    big = flow_for(star(8, 40), f("src/pkg0/m0.py"))
    # give each folder an internal edge so it has something to drill into
    internal = {
        (f(f"src/pkg{i}/m1.py"), f(f"src/pkg{i}/m2.py")): NORMAL for i in range(8)
    }
    big.edges = sorted(set(big.edges) | set(internal))
    for n in {x for e in internal for x in e}:
        big.depths.setdefault(n, 1)
    doc = MermaidFlowReporter(big, ROOT, max_edges=50).render_document()
    check_mermaid(doc)
    assert "# Detail by folder" in doc and "## `src/pkg0`" in doc


# ---- generated output on the fixture projects ----


@pytest.mark.parametrize(
    "project",
    [
        "python_app",
        "js_app",
        "ts_app",
        "java_app",
        "cyclic_py",
        "package_app",
        "react_app",
        "deferred_cycle",
    ],
)
def test_onboard_diagrams_are_valid_mermaid(project, fixture_repo):
    from gnost.cli.commands.onboard import run

    root = fixture_repo(project)
    run(path=str(root))
    for rel in [
        "ONBOARD.md",
        "docs/flow/FLOW-full.md",
        "docs/flow/FLOW-full.mmd",
        "docs/flow/FLOW-overview.mmd",
        "docs/flow/entry-paths.md",
        "docs/flow/folder-paths.md",
    ]:
        text = (root / rel).read_text(encoding="utf-8")
        if "mermaid" in text or rel.endswith(".mmd"):
            check_mermaid(text)


def test_cli_collapse_and_max_edges_options(fixture_repo):
    from gnost.cli.commands.onboard import run

    root = fixture_repo("package_app")
    run(path=str(root), collapse=1)
    assert "dir_" in (root / "docs/flow/FLOW-full.mmd").read_text(encoding="utf-8")


def test_cli_passes_diagram_options_through(fixture_repo, monkeypatch):
    from gnost.cli import main

    root = fixture_repo("package_app")
    monkeypatch.setattr(
        "sys.argv", ["gnost", "onboard", str(root), "--collapse", "--max-edges", "5"]
    )
    main()
    assert "dir_" in (root / "docs/flow/FLOW-full.mmd").read_text(encoding="utf-8")
