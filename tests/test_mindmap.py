"""Tests for the mind map: the model, the radial layout and its parity with the explorer.

The parity test runs the explorer's own layout code (between the mind-layout markers in
graph_viewer.html) under Node and compares every position with the Python layout.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from gnost.reporters.mindmap.layout import RadialLayout
from gnost.reporters.mindmap.model import MindMap, MindMapSettings

TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "gnost"
    / "reporters"
    / "templates"
    / "graph_viewer.html"
)


def _project() -> Tuple[List[str], List[Tuple[str, str]], List[str]]:
    """A small project under src/app/ with a deep folder, a big folder and shared files."""
    files = ["src/app/main.py", "src/app/Zeta.py", "src/app/_private.py"]
    files += [f"src/app/core/m{i}.py" for i in range(5)]
    files += [f"src/app/core/deep/inner/x{i}.py" for i in range(3)]
    files += [f"src/app/plugins/p{i:02d}.py" for i in range(45)]
    edges = [("src/app/main.py", f"src/app/core/m{i}.py") for i in range(5)]
    edges += [(f"src/app/plugins/p{i:02d}.py", "src/app/core/m0.py") for i in range(9)]
    edges += [(f"src/app/plugins/p{i:02d}.py", "src/app/core/m1.py") for i in range(3)]
    edges += [("src/app/core/m2.py", "src/app/_private.py")]
    edges += [("src/app/core/m3.py", "src/app/_private.py")]
    return files, edges, ["src/app/main.py"]


def test_the_tree_skips_the_shared_prefix_and_counts_files() -> None:
    files, edges, entry = _project()
    mind = MindMap(files, edges, entry, project="demo")
    assert mind.tree.path == "src/app" and mind.tree.label == "demo\nsrc/app"
    assert mind.tree.n == len(files)
    assert mind.fan_in["src/app/core/m0.py"] == 10  # main.py and 9 plugins
    assert "src/app/main.py" not in mind.top  # entry points are not "most imported"
    assert {"src/app/core/m0.py", "src/app/core/m1.py"} <= mind.top


def test_deep_and_big_folders_start_closed() -> None:
    files, edges, entry = _project()
    placed = RadialLayout(MindMap(files, edges, entry)).place()
    by_id = {item.id: item for item in placed.items}
    assert by_id["m:src/app/core"].open
    assert by_id["m:src/app/core/deep"].open  # depth 2
    assert not by_id["m:src/app/core/deep/inner"].open  # depth 3
    assert not by_id["m:src/app/plugins"].open  # 45 files
    assert by_id["m:src/app/plugins"].label == "plugins (45)"
    assert placed.at["src/app/plugins/p07.py"] == "m:src/app/plugins"
    assert placed.at["src/app/core/m0.py"] == "src/app/core/m0.py"


def test_fit_closes_the_deepest_folders_first() -> None:
    files, edges, entry = _project()
    layout = RadialLayout(MindMap(files, edges, entry))
    choices = layout.fit(max_leaves=8)
    assert choices["src/app/core/deep"] is False
    assert choices.get("src/app/core") is False  # still too many: the next level up
    assert len([i for i in layout.place(choices).items if i.kind != "root"]) <= 8 + 2


def test_settings_reach_the_explorer_by_name() -> None:
    assert MindMapSettings().to_meta() == {
        "depth": 2,
        "big": 40,
        "gap": 15.0,
        "ring": 150.0,
        "topShare": 0.03,
        "topMin": 5,
    }


def _js_layout(
    nodes: Dict[str, str],
    edges: List[Tuple[str, str]],
    meta: dict,
    open_: Dict[str, bool],
) -> dict:
    page = TEMPLATE.read_text(encoding="utf-8")
    start = page.index("// mind-layout:start")
    end = page.index("// mind-layout:end")
    script = (
        f"const META = {json.dumps(meta)};\n"
        + page[start:end]
        + f"""
const model = mindModel({json.dumps(nodes)},
  {json.dumps([{"source": s, "target": t} for s, t in edges])}, META);
const out = mindLayout(model, {json.dumps(open_)});
process.stdout.write(JSON.stringify({{ items: out.items, at: out.at,
  top: [...model.top].sort() }}));
"""
    )
    done = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, check=True
    )
    return json.loads(done.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node")
@pytest.mark.parametrize(
    "open_", [{}, {"src/app/plugins": True}, {"src/app/core": False}]
)
def test_the_python_layout_matches_the_explorer(open_: Dict[str, bool]) -> None:
    files, edges, entry = _project()
    settings = MindMapSettings()
    meta = {"project": "demo", "entry": entry, "mind": settings.to_meta()}
    js = _js_layout({f: f for f in files}, edges, meta, open_)
    mind = MindMap(files, edges, entry, project="demo", settings=settings)
    py = RadialLayout(mind).place(open_)
    assert sorted(mind.top) == js["top"]
    assert py.at == js["at"]
    assert [i.id for i in py.items] == [i["id"] for i in js["items"]]
    for mine, theirs in zip(py.items, js["items"]):
        assert mine.kind == theirs["kind"] and mine.label == theirs["label"]
        assert mine.parent == theirs["parent"]
        for key in ("x", "y", "angle", "size"):
            assert getattr(mine, key) == pytest.approx(theirs[key], abs=1e-6), (
                mine.id,
                key,
            )


# ---- README image and Mermaid block ----


def test_the_svg_marks_entry_points_and_escapes_names() -> None:
    from gnost.reporters.mindmap.svg import MindMapSvg

    files = ["app/main.py", "app/<img src=x onerror=alert(1)>.py", "app/util.py"]
    edges = [("app/main.py", "app/util.py")]
    svg = MindMapSvg(MindMap(files, edges, ["app/main.py"], project="demo")).render()
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert "<script" not in svg and "&lt;img src=x onerror=alert(1)&gt;.py" in svg
    assert 'class="e"' in svg and 'class="el"' in svg  # the entry point is green
    assert '<path class="l"' in svg  # with a line to what it imports
    assert "prefers-color-scheme: dark" in svg
    assert "<title" in svg and "demo: 3 files" in svg


def test_the_svg_keeps_big_projects_under_the_leaf_cap() -> None:
    from gnost.reporters.mindmap.svg import MindMapSvg

    files = [
        f"pkg/m{a}/s{b}/f{c}.py" for a in range(8) for b in range(8) for c in range(8)
    ]
    svg = MindMapSvg(MindMap(files, []), max_leaves=100).render()
    assert (
        svg.count("<circle") + svg.count("<rect") <= 100 + 10
    )  # leaves, open folders, root
    assert len(svg) < 200_000


def test_the_mermaid_block_is_safe_and_follows_the_closed_folders() -> None:
    from gnost.reporters.mindmap.mermaid import MindMapMermaid

    files, edges, entry = _project()
    files += ["src/app/odd (copy)[1].py", "src/app/__init__.py"]
    text = MindMapMermaid(MindMap(files, edges, entry, project="demo")).render()
    lines = text.splitlines()
    assert lines[0] == "mindmap" and lines[1] == "  root((demo src/app))"
    assert "    plugins, 45 files" in lines  # closed: too many files
    assert "        inner, 3 files" in lines  # closed: too deep (core > deep > inner)
    assert "    main.py ★" in lines
    assert "    odd  copy  1 .py" in lines
    assert "    \\_\\_init\\_\\_.py" in lines  # not bold "init" in Mermaid's Markdown


def test_the_mindmap_block_goes_at_the_end_and_is_replaced(tmp_path: Path) -> None:
    from gnost.reporters.readme import MINDMAP_START, MindMapInjector, ReadmeInjector

    readme = tmp_path / "README.md"
    readme.write_text("# Demo\n\nIntro.\n\n## Usage\n\nRun it.\n", encoding="utf-8")
    assert MindMapInjector(str(tmp_path), image="./.gnost/mindmap.svg").inject()
    first = readme.read_text(encoding="utf-8")
    assert first.index("## Usage") < first.index(MINDMAP_START)  # at the end
    assert "![Project map" in first and "(./.gnost/mindmap.svg)" in first
    assert MindMapInjector(str(tmp_path), image="./.gnost/mindmap.svg").inject()
    assert readme.read_text(encoding="utf-8") == first  # re-running changes nothing
    assert ReadmeInjector(str(tmp_path)).inject()  # the onboarding block is separate
    assert ReadmeInjector(str(tmp_path)).inject()
    both = readme.read_text(encoding="utf-8")
    assert both.count(MINDMAP_START) == 1 and both.count("## Onboarding") == 1
    assert MindMapInjector(str(tmp_path), mermaid="mindmap\n  root((x))\n").inject()
    text = readme.read_text(encoding="utf-8")
    assert "```mermaid\nmindmap" in text and "![Project map" not in text
    assert not MindMapInjector(str(tmp_path / "nowhere"), image="x.svg").inject()


def test_onboard_writes_the_map_and_injects_it(tmp_path: Path) -> None:
    from gnost.cli.commands.onboard import run

    (tmp_path / ".git").mkdir()
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text(
        "from app import util\n\nif __name__ == '__main__':\n    util.go()\n",
        encoding="utf-8",
    )
    (tmp_path / "app" / "util.py").write_text("def go():\n    pass\n", encoding="utf-8")
    (tmp_path / "app" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    run(path=str(tmp_path), mindmap="svg", footer=False)
    svg = (tmp_path / ".gnost" / "mindmap.svg").read_text(encoding="utf-8")
    assert "main.py" in svg and 'class="e"' in svg
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "(./.gnost/mindmap.svg)" in readme
    run(path=str(tmp_path), mindmap="mermaid", footer=False)
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "```mermaid\nmindmap" in readme and readme.count("## Project map") == 1


# ---- rotating GIF ----


def test_the_scene_is_centred_and_keeps_closed_folders_as_one_node() -> None:
    from gnost.reporters.mindmap.gif import MindMapScene

    files, edges, entry = _project()
    points = MindMapScene(MindMap(files, edges, entry, project="demo")).build()
    assert points[0].label == "demo" and points[0].parent == -1
    for axis in ("x", "y", "z"):
        assert abs(sum(getattr(p, axis) for p in points)) < 1e-6  # turns in place
    labels = [p.label for p in points]
    assert "plugins" in labels  # closed: one node, not 45
    # project; core, plugins and 3 files; core's deep and 5 files; deep's inner (closed)
    assert len(points) == 1 + 5 + 6 + 1
    assert all(0 <= p.parent < len(points) for p in points[1:])


def test_the_scene_is_the_same_every_time() -> None:
    from gnost.reporters.mindmap.gif import MindMapScene

    files, edges, entry = _project()
    first = MindMapScene(MindMap(files, edges, entry)).build()
    again = MindMapScene(MindMap(list(reversed(files)), edges, entry)).build()
    assert first == again  # input order does not matter


def test_the_gif_turns_and_is_deterministic() -> None:
    pytest.importorskip("PIL")
    from PIL import Image
    import io

    from gnost.reporters.mindmap.gif import MindMapGif

    files, edges, entry = _project()
    mind = MindMap(files, edges, entry, project="demo")
    data = MindMapGif(mind, size=200, frames=6).render()
    assert data[:6] == b"GIF89a"
    image = Image.open(io.BytesIO(data))
    assert image.size == (200, 200) and image.n_frames == 6
    assert image.info.get("loop") == 0  # loops forever
    assert MindMapGif(mind, size=200, frames=6).render() == data


def test_onboard_falls_back_to_the_svg_without_pillow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    from gnost.cli.commands.onboard import run
    from gnost.reporters.mindmap.gif import MindMapGif

    monkeypatch.setattr(MindMapGif, "available", staticmethod(lambda: False))
    (tmp_path / ".git").mkdir()
    (tmp_path / "main.py").write_text("print(1)\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    run(path=str(tmp_path), mindmap="gif", footer=False)
    assert "gnost[media]" in capsys.readouterr().err
    assert (tmp_path / ".gnost" / "mindmap.svg").exists()
    assert not (tmp_path / ".gnost" / "mindmap.gif").exists()
    assert "mindmap.svg" in (tmp_path / "README.md").read_text(encoding="utf-8")


def test_onboard_writes_and_injects_the_gif(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    from gnost.cli.commands.onboard import run

    (tmp_path / ".git").mkdir()
    (tmp_path / "main.py").write_text("print(1)\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    run(path=str(tmp_path), mindmap="gif", footer=False)
    gif = (tmp_path / ".gnost" / "mindmap.gif").read_bytes()
    assert gif[:6] == b"GIF89a"
    assert "(./.gnost/mindmap.gif)" in (tmp_path / "README.md").read_text(
        encoding="utf-8"
    )
