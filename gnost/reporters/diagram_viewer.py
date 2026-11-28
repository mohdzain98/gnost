"""Standalone HTML viewer for Mermaid (.mmd) and Markdown files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Literal, Optional

VENDOR_DIR = Path(__file__).parent / "vendor"
TEMPLATES_DIR = str(Path(__file__).parent / "templates")

Kind = Literal["mermaid", "markdown", "graph"]

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { --bg:#0d1117; --fg:#e6edf3; --muted:#8b949e; --line:#30363d; --code:#161b22; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
  header { padding:10px 16px; border-bottom:1px solid var(--line); color:var(--muted);
           display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
  header b { color:var(--fg); }
  button { background:var(--code); color:var(--fg); border:1px solid var(--line);
           border-radius:6px; padding:3px 10px; cursor:pointer; }
  main { padding:16px; max-width:1100px; margin:0 auto; }
  main.wide { max-width:none; padding:0; }
  .diagram { border:1px solid var(--line); border-radius:8px; margin:16px 0;
             overflow:hidden; background:var(--bg); }
  main.wide .diagram { border:0; border-radius:0; margin:0; }
  .diagram svg { width:100%; height:calc(100vh - 56px); display:block; }
  main:not(.wide) .diagram svg { height:70vh; }
  pre,code { background:var(--code); border-radius:6px; }
  pre { padding:12px; overflow:auto; } code { padding:1px 5px; }
  pre code { padding:0; }
  table { border-collapse:collapse; } td,th { border:1px solid var(--line); padding:4px 10px; }
  blockquote { border-left:4px solid var(--line); margin:0; padding:0 14px; color:var(--muted); }
  #err { color:#d1242f; padding:16px; white-space:pre-wrap; }
</style>
</head>
<body>
<header><b>__TITLE__</b><span>scroll to zoom, drag to pan</span>
<button onclick="fit()">Fit</button></header>
<main id="out" class="__WIDE__"></main>
<div id="err"></div>
__LIBS__
<script>
const KIND = __KIND__;
const SOURCE = __SOURCE__;
const zoomers = [];
function fit() { zoomers.forEach(z => { z.resetZoom(); z.fit(); z.center(); }); }

async function drawAll(nodes) {
  for (const el of nodes) {
    const src = el.dataset.src;
    try {
      const { svg } = await mermaid.render("d" + Math.random().toString(36).slice(2), src);
      el.innerHTML = svg;
      const s = el.querySelector("svg");
      s.removeAttribute("style");
      zoomers.push(svgPanZoom(s, { zoomScaleSensitivity: 0.3, minZoom: 0.05,
                                   maxZoom: 40, fit: true, center: true }));
    } catch (e) {
      el.innerHTML = '<pre>' + String(e.message || e).replace(/</g, "&lt;") + '</pre>';
    }
  }
}

async function main() {
  if (typeof mermaid === "undefined") {
    document.getElementById("err").textContent =
      "Mermaid is missing from this page.";
    return;
  }
  mermaid.initialize({ startOnLoad: false, theme: "dark", securityLevel: "loose",
                       maxEdges: 20000, maxTextSize: 5000000,
                       flowchart: { useMaxWidth: false, htmlLabels: true } });
  const out = document.getElementById("out");
  if (KIND === "mermaid") {
    out.innerHTML = '<div class="diagram"></div>';
    const el = out.firstChild; el.dataset.src = SOURCE;
    await drawAll([el]);
    return;
  }
  out.innerHTML = marked.parse(SOURCE);
  const blocks = [...out.querySelectorAll("pre > code.language-mermaid")];
  const holders = blocks.map(code => {
    const div = document.createElement("div");
    div.className = "diagram"; div.dataset.src = code.textContent;
    code.parentElement.replaceWith(div); return div;
  });
  await drawAll(holders);
}
main();
</script>
</body>
</html>
"""


def _js_string(text: str) -> str:
    return json.dumps(text).replace("</", "<\\/")


def _fill(template: str, values: dict) -> str:
    """Replace every placeholder in one pass, so inserted text is never re-scanned."""
    pattern = re.compile("|".join(re.escape(k) for k in values))
    return pattern.sub(lambda m: values[m.group(0)], template)


def _inline(*files: str) -> str:
    """Return the named vendored libraries as inline <script> blocks."""
    parts = []
    for name in files:
        code = (VENDOR_DIR / name).read_text(encoding="utf-8")
        parts.append("<script>" + code.replace("</script", "<\\/script") + "</script>")
    return "\n".join(parts)


def _js_json(value: Any) -> str:
    return json.dumps(value).replace("</", "<\\/")


def render_viewer_html(
    source: str, title: str, kind: Kind, meta: Optional[Dict[str, Any]] = None
) -> str:
    """Self-contained HTML page that draws `source`; it needs no network.

    `meta` (graph pages only) adds what the Mermaid source lacks, such as the project name
    and the entry points, which the mind map highlights.
    """
    safe_title = title.replace("<", "&lt;")
    if kind == "graph":
        html = (Path(__file__).parent / "templates" / "graph_viewer.html").read_text(
            encoding="utf-8"
        )
        libs = _inline(
            "cytoscape.min.js", "layout-base.js", "cose-base.js", "cytoscape-fcose.js"
        )
        return _fill(
            html,
            {
                "__TITLE__": safe_title,
                "__LIBS__": libs,
                "__SOURCE__": _js_string(source),
                "__META__": _js_json(meta or {}),
            },
        )
    files = ["mermaid.min.js", "svg-pan-zoom.min.js"]
    if kind == "markdown":
        files.insert(1, "marked.min.js")
    return _fill(
        _TEMPLATE,
        {
            "__TITLE__": safe_title,
            "__WIDE__": "wide" if kind == "mermaid" else "",
            "__KIND__": _js_string(kind),
            "__LIBS__": _inline(*files),
            "__SOURCE__": _js_string(source),
        },
    )
