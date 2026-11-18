"""Pages written by `gnost open` must work with no network."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from gnost.cli.commands.show import run
from gnost.reporters import analysis_html

EXTERNAL = re.compile(r"""(?:src|href)\s*=\s*["']https?://""", re.I)
CHROME_CANDIDATES = [
    os.environ.get("CHROME_BIN", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("google-chrome") or "",
    shutil.which("google-chrome-stable") or "",
    shutil.which("chromium") or "",
    shutil.which("chromium-browser") or "",
    shutil.which("chrome") or "",
]
CHROME = next((c for c in CHROME_CANDIDATES if c and Path(c).exists()), None)


@pytest.fixture()
def pages(tmp_path: Path) -> dict:
    mmd = tmp_path / "small.mmd"
    mmd.write_text("flowchart TD\n  a --> b\n", encoding="utf-8")
    big = tmp_path / "big.mmd"
    big.write_text(
        "\n".join(["flowchart TD"] + [f"  n{i} --> n{i + 1}" for i in range(200)]),
        encoding="utf-8",
    )
    md = tmp_path / "doc.md"
    md.write_text(
        "# Title\n\n```mermaid\nflowchart TD\n  a --> b\n```\n", encoding="utf-8"
    )
    out = {}
    for name, src, mode in [
        ("mermaid", mmd, "mermaid"),
        ("graph", big, "graph"),
        ("markdown", md, "auto"),
    ]:
        dest = tmp_path / f"{name}.html"
        assert run(str(src), str(dest), open_browser=False, mode=mode) == 0
        out[name] = dest
    return out


def test_generated_pages_have_no_external_resources(pages):
    for name, page in pages.items():
        html = page.read_text(encoding="utf-8")
        assert not EXTERNAL.search(html), f"{name} page loads an external resource"


def test_pages_only_carry_the_libraries_they_use(pages):
    graph = pages["graph"].read_text(encoding="utf-8")
    mermaid = pages["mermaid"].read_text(encoding="utf-8")
    assert "cytoscape" in graph.lower() and "mermaid.initialize" not in graph
    assert "mermaid.initialize" in mermaid and "The Cytoscape Consortium" not in mermaid
    assert len(graph) < 1_500_000


def test_analysis_report_templates_have_no_cdn():
    templates = Path(analysis_html.__file__).parent / "templates"
    for f in templates.glob("*.html"):
        assert not EXTERNAL.search(f.read_text(encoding="utf-8")), f.name


def _dump(page: Path) -> str:
    cmd = [
        CHROME,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--host-resolver-rules=MAP * ~NOTFOUND",
        "--virtual-time-budget=8000",
        "--dump-dom",
        page.resolve().as_uri(),
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=90).stdout


@pytest.mark.skipif(CHROME is None, reason="Chrome/Chromium not found")
def test_pages_render_with_network_blocked(pages):
    mermaid = _dump(pages["mermaid"])
    assert "<svg" in mermaid and 'id="err"></div>' in mermaid
    markdown = _dump(pages["markdown"])
    assert "<h1" in markdown and "<svg" in markdown
    graph = _dump(pages["graph"])
    assert "<canvas" in graph and 'id="err"></div>' in graph
