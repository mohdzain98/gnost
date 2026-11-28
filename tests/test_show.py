from pathlib import Path

from gnost.cli.commands.show import run
from gnost.reporters.diagram_viewer import render_viewer_html


def test_viewer_embeds_source_safely():
    html = render_viewer_html("flowchart TD\n  a --> b</script>", "x.mmd", "mermaid")
    assert "a --> b<\\/script>" in html
    assert "__SOURCE__" not in html and "__KIND__" not in html


def test_show_writes_html_for_mmd_and_md(tmp_path: Path):
    mmd = tmp_path / "f.mmd"
    mmd.write_text("flowchart TD\n  a --> b\n", encoding="utf-8")
    out = tmp_path / "f.html"
    assert run(str(mmd), str(out), open_browser=False) == 0
    assert "cytoscape" in out.read_text(
        encoding="utf-8"
    )  # interactive, even when small

    md = tmp_path / "f.md"
    md.write_text("# t\n", encoding="utf-8")
    assert run(str(md), str(out), open_browser=False) == 0


def test_show_rejects_missing_and_unknown(tmp_path: Path):
    assert run(str(tmp_path / "nope.mmd"), open_browser=False) == 2
    other = tmp_path / "a.txt"
    other.write_text("x", encoding="utf-8")
    assert run(str(other), open_browser=False) == 2


def test_every_diagram_is_interactive_unless_mermaid_is_asked_for(tmp_path: Path):
    lines = ["flowchart TD"] + [f"  n{i} --> n{i + 1}" for i in range(200)]
    mmd = tmp_path / "big.mmd"
    mmd.write_text("\n".join(lines), encoding="utf-8")
    out = tmp_path / "big.html"
    assert run(str(mmd), str(out), open_browser=False) == 0
    assert "cytoscape" in out.read_text(encoding="utf-8")
    assert run(str(mmd), str(out), open_browser=False, mode="mermaid") == 0
    assert "cytoscape(" not in out.read_text(encoding="utf-8")


def test_show_opens_html_as_is(tmp_path: Path, monkeypatch):
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    page = tmp_path / "report.html"
    page.write_text("<html></html>", encoding="utf-8")
    assert run(str(page)) == 0
    assert opened and opened[0].startswith("file://") and "report.html" in opened[0]


def test_open_command_handles_flow_files_and_bad_targets(tmp_path: Path, monkeypatch):
    import gnost.cli.app as app

    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr("sys.argv", ["gnost", "open", "flow"])
    assert app.main() == 1  # nothing generated yet

    flow = tmp_path / "docs" / "flow"
    flow.mkdir(parents=True)
    (flow / "flow-complete.mmd").write_text(
        "flowchart TD\n  a --> b\n", encoding="utf-8"
    )
    monkeypatch.setattr("sys.argv", ["gnost", "open", "flow"])
    assert app.main() == 0 and opened

    monkeypatch.setattr("sys.argv", ["gnost", "open", "nonsense"])
    assert app.main() == 2
    monkeypatch.setattr("sys.argv", ["gnost", "show", str(flow / "flow-complete.mmd")])
    assert app.main() == 0


def test_the_explorer_has_a_png_download_button(tmp_path: Path):
    mmd = tmp_path / "f.mmd"
    mmd.write_text("flowchart TD\n  a --> b\n", encoding="utf-8")
    out = tmp_path / "f.html"
    assert run(str(mmd), str(out), open_browser=False) == 0
    page = out.read_text(encoding="utf-8")
    assert 'id="png"' in page and "cy.png(" in page


def test_the_explorer_has_a_mind_map_with_the_entry_points(tmp_path: Path):
    meta = {"project": "demo</script>", "entry": ["src/app.py"]}
    page = render_viewer_html(
        'flowchart TD\n  a["src/app.py"]\n', "f.mmd", "graph", meta
    )
    assert 'id="mind"' in page and "function mindView()" in page
    assert '"entry": ["src/app.py"]' in page
    assert "demo<\\/script>" in page and "__META__" not in page


def test_an_explorer_built_from_a_mmd_file_has_empty_meta(tmp_path: Path):
    mmd = tmp_path / "f.mmd"
    mmd.write_text("flowchart TD\n  a --> b\n", encoding="utf-8")
    out = tmp_path / "f.html"
    assert run(str(mmd), str(out), open_browser=False) == 0
    assert "const META = {};" in out.read_text(encoding="utf-8")


def test_onboard_passes_the_project_and_entry_points_to_the_explorer(
    tmp_path: Path,
) -> None:
    from gnost.cli.commands.onboard import _page_meta
    from gnost.languages.base import EntryPoint

    class Scan:
        entry_points = [
            EntryPoint(file=str(tmp_path / "cli" / "app.py"), reason="__main__ guard")
        ]

    meta = _page_meta(Scan(), str(tmp_path), None)
    assert meta["project"] == tmp_path.name and meta["entry"] == ["cli/app.py"]
    assert meta["mind"]["depth"] == 2  # the explorer reads the shared settings
    remote = _page_meta(Scan(), str(tmp_path), "https://github.com/pallets/flask.git")
    assert remote["project"] == "flask"
