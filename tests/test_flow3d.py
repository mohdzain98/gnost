"""Tests for the 3D flow page: its data, the page itself and how onboard and open write it.

The page is checked for escaping (file names from remote repositories can be hostile), for
the inlined library and its notice, and for staying out of the default flow.html.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from gnost.reporters.flow3d import LIBRARY, Flow3dData, Flow3dPage

VENDOR = Path(__file__).resolve().parents[1] / "gnost" / "reporters" / "vendor"


def _payload() -> Dict[str, Any]:
    return {
        "project": {"name": "demo"},
        "entry_points": [{"file": "app/main.py"}],
        "graph": {
            "nodes": ["app/main.py", "app/a.py", "app/b.py", "lib/util.py"],
            "edges": [
                {"source": "app/main.py", "target": "app/a.py", "deferred": False},
                {"source": "app/a.py", "target": "app/b.py", "deferred": False},
                {"source": "app/b.py", "target": "app/a.py", "deferred": True},
                {"source": "app/b.py", "target": "lib/util.py", "deferred": False},
                {"source": "app/b.py", "target": "gone.py", "deferred": False},
            ],
        },
        "cycles": [{"kind": "deferred", "files": ["app/a.py", "app/b.py"]}],
    }


def test_the_data_has_folders_counts_entry_points_and_cycles() -> None:
    data = Flow3dData(_payload()).build()
    nodes = {n["id"]: n for n in data["nodes"]}
    assert data["project"] == "demo" and len(data["links"]) == 4  # gone.py dropped
    assert nodes["app/main.py"]["entry"] and not nodes["app/a.py"]["entry"]
    assert nodes["app/b.py"] == {
        "id": "app/b.py",
        "name": "b.py",
        "folder": "app",
        "inn": 1,
        "out": 2,
        "entry": False,
        "cyc": "deferred",
    }
    links = {(link["source"], link["target"]): link for link in data["links"]}
    assert links[("app/b.py", "app/a.py")]["cycle"] == "deferred"
    assert links[("app/b.py", "app/a.py")]["deferred"]
    assert links[("app/main.py", "app/a.py")]["cycle"] == ""  # main.py is not in it
    assert links[("app/b.py", "lib/util.py")]["cross"]


def test_an_import_time_cycle_wins_over_a_deferred_one() -> None:
    payload = _payload()
    payload["cycles"].append({"kind": "import_time", "files": ["app/a.py", "x.py"]})
    nodes = {n["id"]: n for n in Flow3dData(payload).build()["nodes"]}
    assert nodes["app/a.py"]["cyc"] == "import_time"


def test_the_page_inlines_the_library_and_escapes_names() -> None:
    payload = _payload()
    payload["project"]["name"] = "<b>demo</b>"
    payload["graph"]["nodes"].append("app/</script><script>alert(1)</script>.py")
    page = Flow3dPage(payload).render()
    assert "__DATA__" not in page and "__LIBS__" not in page
    assert "ForceGraph3D" in page and len(page) > 1_000_000  # the 1.4 MB library
    assert "</script><script>alert(1)" not in page  # `</` is escaped in the data
    assert "<title>&lt;b>demo&lt;/b> · 3D flow</title>" in page
    assert "esc(mid(n.name, 40))" in page  # the hover card escapes names


def test_the_library_is_pinned_with_its_notice() -> None:
    manifest = json.loads((VENDOR / "vendor.json").read_text(encoding="utf-8"))
    assert manifest["3d-force-graph"]["file"] == LIBRARY
    assert manifest["3d-force-graph"]["version"] == "1.80.2"
    notices = (VENDOR / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "## 3d-force-graph 1.80.2 (MIT)" in notices


def _project(root: Path) -> None:
    (root / ".git").mkdir()
    (root / "app").mkdir()
    (root / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "app" / "main.py").write_text(
        "from app import util\n\nif __name__ == '__main__':\n    util.go()\n",
        encoding="utf-8",
    )
    (root / "app" / "util.py").write_text("def go():\n    pass\n", encoding="utf-8")


def test_onboard_writes_the_3d_page_only_when_asked(tmp_path: Path) -> None:
    from gnost.cli.commands.onboard import run

    _project(tmp_path)
    run(path=str(tmp_path), footer=False)
    gnost = tmp_path / ".gnost"
    assert not (gnost / "flow-3d.html").exists()
    assert '"has3d": false' in (gnost / "flow.html").read_text(encoding="utf-8")
    assert "ForceGraph3D" not in (gnost / "flow.html").read_text(encoding="utf-8")

    run(path=str(tmp_path), footer=False, three_d=True)
    assert "app/main.py" in (gnost / "flow-3d.html").read_text(encoding="utf-8")
    flow = (gnost / "flow.html").read_text(encoding="utf-8")
    assert '"has3d": true' in flow and 'id="to3d"' in flow


def test_open_flow_3d_builds_the_page_from_insights(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import gnost.cli.app as app

    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["gnost", "open", "flow", "--3d"])
    assert app.main() == 1  # no insights.json yet

    (tmp_path / ".git").mkdir()
    gnost = tmp_path / ".gnost"
    gnost.mkdir()
    (gnost / "insights.json").write_text(json.dumps(_payload()), encoding="utf-8")
    assert app.main() == 0
    assert opened and opened[0].endswith("flow-3d.html")
    assert "app/main.py" in (gnost / "flow-3d.html").read_text(encoding="utf-8")


def test_the_3d_view_rotates_by_default() -> None:
    page = Flow3dPage(_payload()).render()
    assert '<input type="checkbox" id="optRotate" checked>' in page
    assert '$("optRotate").onchange.call($("optRotate"))' in page
