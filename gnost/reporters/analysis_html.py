from __future__ import annotations

import json
import html
import os
from typing import Any, Dict, List


def _escape(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _risk_to_score(risk_score: float) -> float:
    clamped = max(0.0, min(100.0, float(risk_score)))
    return round(10.0 * (1.0 - clamped / 100.0), 2)


def _analyzer_risk(findings: List[Dict[str, Any]]) -> float:
    if not findings:
        return 0.0

    severity_weights = {
        "critical": 1.0,
        "high": 0.6,
        "medium": 0.3,
        "low": 0.1,
        "info": 0.05,
    }
    scored_findings = [
        finding for finding in findings if isinstance(finding, dict)
    ]
    if not scored_findings:
        return 0.0

    total_weight = sum(
        severity_weights.get(
            str(finding.get("severity", "info")).split(".")[-1].lower(),
            0.05,
        )
        for finding in scored_findings
    )
    max_weight = max(severity_weights.values())
    return round((total_weight / (len(scored_findings) * max_weight)) * 100.0, 2)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _analyzer_glossary_html(by_analyzer: Dict[str, List[Dict[str, Any]]]) -> str:
    template_path = os.path.join(
        os.path.dirname(__file__),
        "templates",
        "analyzer_guides_layout.html",
    )
    data_path = os.path.join(
        os.path.dirname(__file__),
        "templates",
        "analyzer_guides.json",
    )

    try:
        with open(data_path, "r", encoding="utf-8") as fp:
            guide_payload = json.load(fp)
            static_guides = guide_payload.get("analyzers", {})
    except Exception:
        static_guides = {}

    if not by_analyzer:
        return "<p class=\"muted\">No analyzer guidance is available for this report.</p>"

    def _list_html(items: List[str]) -> str:
        list_items = "".join(f"<li>{_escape(item)}</li>" for item in items)
        return f"<ul class='guide-list'>{list_items}</ul>"

    def _table_html(headers: List[str], rows: List[List[str]]) -> str:
        head = "".join(f"<th>{_escape(h)}</th>" for h in headers)
        body = "".join(
            "<tr>" + "".join(f"<td>{_escape(cell)}</td>" for cell in row) + "</tr>"
            for row in rows
        )
        return (
            "<div class='table-shell'><table><thead><tr>"
            f"{head}"
            "</tr></thead><tbody>"
            f"{body}"
            "</tbody></table></div>"
        )

    def _severity_table(rows: List[Dict[str, Any]]) -> str:
        severity_rows = []
        for row in rows:
            severity = row.get("severity", "")
            severity_class = str(severity).lower()
            severity_rows.append(
                f"<tr>"
                f"<td><span class=\"badge badge-{severity_class}\">{_escape(severity)}</span></td>"
                f"<td>{_escape(row.get('description', ''))}</td>"
                f"<td>{_escape(row.get('example', ''))}</td>"
                f"</tr>"
            )
        return (
            "<div class='guide-subtitle'>Severity Focus</div>"
            "<div class='table-shell'><table><thead><tr><th>Severity</th><th>Description</th><th>Example Code</th></tr></thead>"
            f"<tbody>{''.join(severity_rows)}</tbody></table></div>"
        )

    rendered_buttons = []
    rendered_panels = []
    first = True

    for analyzer_name in sorted(by_analyzer.keys()):
        guide = static_guides.get(str(analyzer_name).lower())
        if not guide:
            continue
        panel_id = f"guide-{str(analyzer_name).replace(' ', '-').lower()}"
        quality_categories = _list_html([str(i) for i in guide.get("quality_categories", [])])
        tools = _list_html([str(i) for i in guide.get("tools_used", [])])
        findings = _list_html([str(i) for i in guide.get("what_it_finds", [])])
        card = [
            f"<section class=\"guide-card\" data-analyzer=\"{_escape(analyzer_name)}\">",
            f"<h3>{_escape(str(guide.get('title', analyzer_name)).replace('_', ' ').title())}</h3>",
            "<div class='guide-meta'>",
            "<div class='guide-block'><h4>Quality Categories</h4>" + quality_categories + "</div>",
            "<div class='guide-block'><h4>Description</h4><p>"
            + _escape(str(guide.get('description', '')))
            + "</p></div>",
            "<div class='guide-block'><h4>What it finds</h4>" + findings + "</div>",
            "<div class='guide-block'><h4>Tools used</h4>" + tools + "</div>",
            "</div>",
            _severity_table(guide.get("severity_focus", [])),
            "</section>",
        ]

        for section in guide.get("extra_sections", []):
            title = _escape(section.get("title", ""))
            section_table = _table_html(
                [str(h) for h in section.get("headers", [])],
                [[str(cell) for cell in row] for row in section.get("rows", [])],
            )
            card.append(f"<div class='guide-subtitle'>{title}</div>{section_table}")

        rendered_buttons.append(
            f"<button type=\"button\" class=\"tab-btn glossary-tab-btn {'active' if first else ''}\" "
            f"data-guide-tab=\"{_escape(panel_id)}\" data-guide-analyzer=\"{_escape(analyzer_name)}\" "
            f"aria-selected=\"{'true' if first else 'false'}\">{_escape(str(guide.get('title', analyzer_name)).title())}</button>"
        )
        rendered_panels.append(
            f"<div class=\"analyzer-guide-panel {'active' if first else ''}\" id=\"{_escape(panel_id)}\">"
            + "".join(card)
            + "</div>"
        )
        first = False

    if not rendered_buttons:
        return "<p class=\"muted\">No analyzer guidance is available for this report.</p>"

    body = "".join(rendered_panels)
    buttons = "".join(rendered_buttons)

    try:
        with open(template_path, "r", encoding="utf-8") as fp:
            layout_template = fp.read()
    except Exception:
        return (
            "<p class=\"muted\">Analyzer guide template is missing or unreadable.</p>"
        )

    return (
        layout_template.replace("{{TAB_BUTTONS}}", buttons)
        .replace("{{TAB_PANELS}}", body)
    )


def render_analysis_html(report: Dict[str, Any], output_file: str) -> None:
    """
    Render an interactive, browser-friendly HTML report from consolidated report data.
    """
    findings = report.get("findings", []) if isinstance(report, dict) else []
    summary = report.get("summary", {}) if isinstance(report, dict) else {}
    metrics = report.get("analysis_metrics", []) if isinstance(report, dict) else []

    risk_score = summary.get("risk_score", 0.0)
    final_score_source = (
        report.get("final_score")
        if isinstance(report, dict)
        else None
    )
    if not isinstance(final_score_source, (int, float)):
        final_score_source = summary.get("final_score") if isinstance(summary, dict) else None
    final_score = _safe_float(
        final_score_source, _risk_to_score(_safe_float(risk_score))
    )
    final_score_class = "good" if final_score >= 8 else ("okay" if final_score >= 6 else "bad")

    total_findings = _safe_int(summary.get("total_findings", len(findings)))
    files_with_issues = _safe_int(summary.get("files_with_issues", 0))
    total_analyzers = _safe_int(summary.get("total_analyzers", 0))
    severity_breakdown = summary.get("severity_breakdown", {}) or {}
    high_count = _safe_int(severity_breakdown.get("high"))
    medium_count = _safe_int(severity_breakdown.get("medium"))
    low_count = _safe_int(severity_breakdown.get("low"))
    overall_executed = _safe_float(report.get("total_execution_time", 0.0))

    by_analyzer: Dict[str, List[Dict[str, Any]]] = {}
    by_severity = {"high": 0, "medium": 0, "low": 0, "critical": 0, "info": 0}
    by_title = set()
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        analyzer = finding.get("source_analyzer") or "unknown"
        by_analyzer.setdefault(analyzer, []).append(finding)

        severity = str(finding.get("severity", "info")).lower()
        if severity not in by_severity:
            by_severity["info"] += 1
        else:
            by_severity[severity] += 1

        title = finding.get("title")
        if isinstance(title, str):
            cleaned_title = title.strip()
            if cleaned_title:
                by_title.add(cleaned_title)

    title_filter_options = "".join(
        f'<option value="{_escape(title)}">{_escape(title)}</option>'
        for title in sorted(by_title)
    )

    analyzer_rows = []
    for metric in metrics:
        analyzer_name = metric.get("analyzer_name", "unknown")
        analyzer_findings = by_analyzer.get(analyzer_name, [])
        metric_risk_score = metric.get("risk_score")
        if not isinstance(metric_risk_score, (int, float)):
            metric_risk_score = _analyzer_risk(analyzer_findings)
        analyzer_rows.append(
            {
                "analyzer": analyzer_name,
                "score": _risk_to_score(_safe_float(metric_risk_score, 0.0)),
                "findings": len(analyzer_findings),
                "high": sum(
                    1 for f in analyzer_findings if str(f.get("severity", "")).lower() == "high"
                )
                + sum(
                    1
                    for f in analyzer_findings
                    if str(f.get("severity", "")).lower() == "critical"
                ),
                "medium": sum(
                    1 for f in analyzer_findings if str(f.get("severity", "")).lower() == "medium"
                ),
                "low": sum(
                    1 for f in analyzer_findings if str(f.get("severity", "")).lower() == "low"
                ),
            }
        )

    # Fallback for analyzers that may not appear in analysis metrics
    analyzer_rows += [
        {
            "analyzer": name,
            "score": 10.0,
            "findings": len(items),
            "high": sum(
                1 for f in items if str(f.get("severity", "")).lower() in {"high", "critical"}
            ),
            "medium": sum(1 for f in items if str(f.get("severity", "")).lower() == "medium"),
            "low": sum(1 for f in items if str(f.get("severity", "")).lower() == "low"),
        }
        for name, items in by_analyzer.items()
        if not any(row["analyzer"] == name for row in analyzer_rows)
    ]

    analyzer_rows = sorted(analyzer_rows, key=lambda row: row["analyzer"].lower())

    analyzer_summary_rows = "".join(
        (
            "<tr>"
            f"<td>{_escape(row['analyzer'])}</td>"
            f"<td>{row['score']:.2f}</td>"
            f"<td>{row['findings']}</td>"
            f"<td>{row['high']}</td>"
            f"<td>{row['medium']}</td>"
            f"<td>{row['low']}</td>"
            "</tr>"
        )
        for row in analyzer_rows
    )

    analyzer_filter_options = "".join(
        f'<option value="{_escape(name)}">{_escape(name)}</option>'
        for name in sorted(by_analyzer.keys())
    )
    analyzer_guides_html = _analyzer_glossary_html(by_analyzer)

    payload_json = json.dumps(
        json.dumps(report, ensure_ascii=False).replace("</script>", "<\\/script>"),
        ensure_ascii=False,
    )
    out_dir = os.path.dirname(os.path.abspath(output_file)) or "."
    os.makedirs(out_dir, exist_ok=True)

    html_content = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>GNOST Analysis Report</title>
  <style>
    :root {{
      --bg: #0f172a;
      --panel: #111827;
      --panel-soft: #1f2937;
      --text: #f8fafc;
      --muted: #94a3b8;
      --border: #334155;
      --good: #22c55e;
      --warn: #f59e0b;
      --bad: #ef4444;
      --neutral: #64748b;
      --accent: #60a5fa;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, "Segoe UI", Arial, sans-serif;
      background: radial-gradient(circle at top, #111827, #0f172a 45%);
      color: var(--text);
      padding: 22px;
    }}
    .container {{ max-width: 1400px; margin: 0 auto; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .subtitle {{ margin: 0 0 18px; color: var(--muted); }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
    }}
    .card h3 {{ margin: 0 0 8px; font-size: 14px; color: var(--muted); font-weight: 500; letter-spacing: 0.2px; }}
    .card p {{ margin: 0; font-size: 22px; font-weight: 700; }}
    .row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 18px;
      flex-wrap: wrap;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
      margin-bottom: 14px;
    }}
    .filters {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }}
    .filters input, .filters select {{
      background: var(--panel-soft);
      color: var(--text);
      border: 1px solid var(--border);
      padding: 8px 10px;
      border-radius: 8px;
      min-width: 180px;
      font-size: 14px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      border-right: 1px solid rgba(148, 163, 184, 0.12);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{ background: #0b1220; color: var(--muted); position: sticky; top: 0; cursor: pointer; user-select: none; }}
    tr:hover td {{ background: rgba(96, 165, 250, 0.08); }}
    .badge {{
      display: inline-block;
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .badge-high {{ background: rgba(239, 68, 68, 0.2); color: #fecaca; }}
    .badge-medium {{ background: rgba(245, 158, 11, 0.2); color: #fde68a; }}
    .badge-low {{ background: rgba(34, 197, 94, 0.2); color: #bbf7d0; }}
    .badge-info {{ background: rgba(14, 165, 233, 0.2); color: #bae6fd; }}
    .badge-critical {{ background: rgba(236, 72, 153, 0.2); color: #fbcfe8; }}
    .muted {{ color: var(--muted); }}
    .small {{ font-size: 12px; color: var(--muted); }}
    .pager {{
      margin-top: 10px;
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      align-items: center;
    }}
    .pager button {{
      border: 1px solid var(--border);
      color: var(--text);
      background: var(--panel-soft);
      border-radius: 8px;
      padding: 6px 10px;
      cursor: pointer;
    }}
    .pager button:disabled {{ opacity: 0.45; cursor: not-allowed; }}
    .score {{
      display: inline-block;
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 4px 10px;
      font-weight: 700;
      color: var(--text);
    }}
    .score.good {{ border-color: rgba(34,197,94,0.5); color: #86efac; }}
    .score.okay {{ border-color: rgba(245,158,11,0.5); color: #fcd34d; }}
    .score.bad {{ border-color: rgba(239,68,68,0.5); color: #fca5a5; }}
    .severity-col {{ width: 90px; }}
    .details {{ max-width: 360px; white-space: pre-wrap; }}
    .analysis-grid {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 10px;
      margin-bottom: 18px;
    }}
    .kpi-subtitle {{
      font-size: 11px;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      opacity: 0.75;
      margin-top: 6px;
    }}
    .stats .card p {{
      display: flex;
      align-items: baseline;
      gap: 6px;
    }}
    .table-shell {{
      overflow-x: auto;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: transparent;
    }}
    table thead th {{
      position: sticky;
      top: 0;
      z-index: 1;
    }}
    tbody tr:nth-child(even) td {{
      background: rgba(15, 23, 42, 0.28);
    }}
    .badge-unknown {{
      background: rgba(148, 163, 184, 0.25);
      color: #e2e8f0;
    }}
    .muted-note {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 8px;
    }}
    .scorebar {{
      height: 8px;
      width: 100%;
      border-radius: 999px;
      background: rgba(148, 163, 184, 0.18);
      overflow: hidden;
      margin-top: 8px;
    }}
    .scorebar > span {{
      display: block;
      height: 100%;
      background: linear-gradient(90deg, #0ea5e9, #22c55e);
      width: 0;
    }}
    .score-note {{
      margin-top: 6px;
      padding-top: 6px;
      font-size: 10px;
      opacity: 0.8;
    }}
    .glossary-layout {{
      display: grid;
      gap: 12px;
    }}
    .glossary-tabs {{
      margin-bottom: 12px;
    }}
    .analyzer-guide-panels {{
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 4px;
      background: var(--panel);
    }}
    .analyzer-guide-panel {{
      display: none;
    }}
    .analyzer-guide-panel.active {{
      display: block;
    }}
    .glossary-panel {{
      display: grid;
      gap: 14px;
    }}
    .guide-card {{
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
      background: var(--panel);
    }}
    .guide-card h3 {{
      margin: 0 0 12px;
      font-size: 18px;
      color: var(--text);
    }}
    .guide-meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
      margin-bottom: 12px;
    }}
    .guide-block {{
      border: 1px solid rgba(148, 163, 184, 0.15);
      border-radius: 10px;
      padding: 10px;
      background: var(--panel-soft);
      min-width: 0;
    }}
    .guide-block h4 {{
      margin: 0 0 8px;
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.35px;
    }}
    .guide-block p {{
      margin: 0;
      color: var(--text);
      font-size: 13px;
      line-height: 1.45;
    }}
    .guide-list {{
      margin: 0;
      padding-left: 18px;
      color: var(--text);
      line-height: 1.5;
      font-size: 13px;
    }}
    .guide-list li {{
      margin-bottom: 6px;
      word-break: break-word;
    }}
    .guide-subtitle {{
      margin: 8px 0 8px;
      font-size: 13px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.35px;
    }}
    .guide-card th,
    .guide-card td {{
      font-size: 13px;
    }}
    .finding-details {{
      margin-top: 6px;
      border-top: 1px dashed rgba(148, 163, 184, 0.28);
      padding-top: 6px;
    }}
    .finding-details summary {{
      cursor: pointer;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 4px;
    }}
    .finding-details ul {{
      margin: 0;
      padding-left: 18px;
      font-size: 12px;
      line-height: 1.5;
    }}
    .finding-details li {{
      margin: 0 0 4px;
      word-break: break-word;
    }}
    .clubbed-line-indicator {{
      display: inline-flex;
      margin-left: 4px;
      font-size: 11px;
      color: var(--muted);
      border: 1px dashed rgba(148, 163, 184, 0.45);
      padding: 1px 6px;
      border-radius: 999px;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .severity-breakdown {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }}
    .severity-item {{
      background: var(--panel-soft);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px;
      text-align: center;
    }}
    .severity-item h4 {{
      margin: 0;
      font-size: 13px;
      color: var(--muted);
      font-weight: 600;
      letter-spacing: 0.3px;
      text-transform: uppercase;
    }}
    .severity-item p {{
      margin: 6px 0 0;
      font-size: 20px;
      font-weight: 700;
      line-height: 1;
    }}
    .small-pill {{
      display: inline-block;
      border: 1px solid rgba(148, 163, 184, 0.3);
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 11px;
      text-transform: uppercase;
      color: var(--muted);
      margin-right: 6px;
    }}
    .tabs {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 12px;
      flex-wrap: wrap;
    }}
    .tab-btn {{
      border: 1px solid var(--border);
      background: var(--panel);
      color: var(--text);
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }}
    .tab-btn:hover {{
      border-color: rgba(96, 165, 250, 0.6);
      color: #bfdbfe;
    }}
    .tab-btn.active {{
      border-color: rgba(96, 165, 250, 0.85);
      background: rgba(96, 165, 250, 0.12);
      color: #bfdbfe;
    }}
    .tab-panel {{
      display: none;
    }}
    .tab-panel.active {{
      display: block;
    }}
    .pager button:hover:not(:disabled) {{
      border-color: rgba(96, 165, 250, 0.6);
      color: #dbeafe;
    }}
    @media (max-width: 1024px) {{
      body {{ padding: 12px; }}
    }}
    @media (max-width: 900px) {{
      h1 {{ font-size: 24px; }}
      .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .severity-breakdown {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class=\"container\">
    <h1>GNOST Analysis Report</h1>
    <p class=\"subtitle\">Target: TARGET_PATH</p>
    <div class=\"row\">
      <div class=\"stats\">
        <div class=\"card\">
          <h3>Final Score</h3>
          <p><span id=\"finalScore\" class=\"score FINAL_SCORE_CLASS\">FINAL_SCORE / 10.00</span></p>
          <div class=\"scorebar\"><span id=\"scoreBar\"></span></div>
          <p class=\"small score-note\" style=\"font-size: small\">Higher is better</p>
        </div>
        <div class=\"card\">
          <h3>Total Findings</h3>
          <p>TOTAL_FINDINGS</p>
        </div>
        <div class=\"card\">
          <h3>Analyzers</h3>
          <p>TOTAL_ANALYZERS</p>
        </div>
        <div class=\"card\">
          <h3>Files with findings</h3>
          <p>FILES_WITH_ISSUES</p>
        </div>
        <div class=\"card\">
          <h3>Execution Time</h3>
          <p>OVERALL_EXECUTEDs</p>
        </div>
      </div>
    </div>

    <div class=\"panel\">
      <h3>Severity Breakdown</h3>
      <div class=\"severity-breakdown\">
        <div class=\"severity-item\">
          <h4>High</h4>
          <p>HIGH_COUNT</p>
        </div>
        <div class=\"severity-item\">
          <h4>Medium</h4>
          <p>MEDIUM_COUNT</p>
        </div>
        <div class=\"severity-item\">
          <h4>Low</h4>
          <p>LOW_COUNT</p>
        </div>
      </div>
    </div>

    <div class=\"panel\">
      <h3>Analyzer Summary</h3>
      <div class=\"table-shell\">
        <table id=\"analyzerTable\">
          <thead>
            <tr>
              <th>Analyzer</th>
              <th>Score</th>
              <th>Findings</th>
              <th>High</th>
              <th>Medium</th>
              <th>Low</th>
            </tr>
          </thead>
          <tbody>
            ANALYZER_SUMMARY_ROWS
          </tbody>
        </table>
      </div>
    </div>

    <div class=\"tabs\" role=\"tablist\" aria-label=\"Report tabs\">
      <button type=\"button\" class=\"tab-btn active\" data-main-tab=\"true\" data-tab=\"findingsTab\" aria-selected=\"true\">Findings</button>
      <button type=\"button\" class=\"tab-btn\" data-main-tab=\"true\" data-tab=\"glossaryTab\" aria-selected=\"false\">Glossary</button>
    </div>

    <div class=\"tab-panel active\" id=\"findingsTab\">
      <div class=\"panel\">
        <h3>Findings</h3>
        <div class=\"filters\">
          <input id=\"searchInput\" type=\"text\" placeholder=\"Search title, message, file, analyzer\" />
          <select id=\"severityFilter\">
            <option value=\"\">All severities</option>
            <option value=\"high\">High</option>
            <option value=\"medium\">Medium</option>
            <option value=\"low\">Low</option>
            <option value=\"critical\">Critical</option>
            <option value=\"info\">Info</option>
          </select>
          <select id=\"analyzerFilter\">
            <option value=\"\">All analyzers</option>
            ANALYZER_FILTER_OPTIONS
          </select>
          <select id=\"titleFilter\">
            <option value=\"\">All error titles</option>
            TITLE_FILTER_OPTIONS
          </select>
        </div>
        <div class=\"table-shell\">
          <table id=\"findingsTable\">
            <thead>
              <tr>
                <th data-sort=\"severity\" class=\"severity-col\">Severity</th>
                <th data-sort=\"source_analyzer\">Analyzer</th>
                <th data-sort=\"file\">File</th>
                <th data-sort=\"line\">Line</th>
                <th data-sort=\"title\">Title</th>
                <th data-sort=\"description\">Description</th>
                <th data-sort=\"remediation\">Remediation</th>
              </tr>
            </thead>
            <tbody id=\"findingsBody\"></tbody>
          </table>
        </div>
        <div class=\"pager\">
          <label for=\"pageSize\" class=\"small\">Rows / page</label>
          <select id=\"pageSize\">
            <option value=\"25\">25</option>
            <option value=\"50\" selected>50</option>
            <option value=\"100\">100</option>
            <option value=\"200\">200</option>
          </select>
          <span id=\"pagerInfo\" class=\"small\"></span>
          <button id=\"prevPage\">Prev</button>
          <button id=\"nextPage\">Next</button>
        </div>
      </div>
    </div>
    <div class=\"tab-panel\" id=\"glossaryTab\">
      <div class=\"panel\">
        <h3>Glossary</h3>
        <div class=\"glossary-panel\">
          ANALYZER_GUIDES_HTML
        </div>
      </div>
    </div>
  </div>

  <script>
    const REPORT_DATA = JSON.parse(REPORT_DATA_JSON);
    const findings = Array.isArray(REPORT_DATA.findings) ? REPORT_DATA.findings : [];

    const severityOrder = {{
      critical: 4,
      high: 3,
      medium: 2,
      low: 1,
      info: 0,
    }};

    const severityFilter = document.getElementById("severityFilter");
    const analyzerFilter = document.getElementById("analyzerFilter");
    const titleFilter = document.getElementById("titleFilter");
    const searchInput = document.getElementById("searchInput");
    const tableBody = document.getElementById("findingsBody");
    const pageSizeEl = document.getElementById("pageSize");
    const pagerInfo = document.getElementById("pagerInfo");
    const prevBtn = document.getElementById("prevPage");
    const nextBtn = document.getElementById("nextPage");
    const scoreBar = document.getElementById("scoreBar");
    const tabButtons = document.querySelectorAll(".tab-btn[data-main-tab='true']");
    const glossaryTabButtons = document.querySelectorAll(".glossary-tab-btn");
    const tabPanels = document.querySelectorAll(".tab-panel");
    const glossaryTabPanels = document.querySelectorAll(".analyzer-guide-panel");

    let currentPage = 1;
    let filtered = [...findings];
    let sortState = {{ key: "severity", direction: "desc" }};

    if (scoreBar) {{
      const scoreValue = parseFloat(FINAL_SCORE);
      scoreBar.style.width = `${{Math.max(0, Math.min(100, scoreValue * 10)).toFixed(0)}}%`;
    }}

    function badgeClass(value) {{
      const severity = String(value || "info").toLowerCase();
      if (severity === "critical") return "badge-critical";
      if (severity === "high") return "badge-high";
      if (severity === "medium") return "badge-medium";
      return "badge-low";
    }}

    function getText(value) {{
      return (value === null || value === undefined) ? "" : String(value);
    }}

    function createTextCell(value, className) {{
      const td = document.createElement("td");
      if (className) {{
        td.className = className;
      }}
      td.textContent = value;
      return td;
    }}

    function createTableSpacer(columns = 7, message = "No findings found for the selected filters.") {{
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = columns;
      cell.className = "muted small";
      cell.textContent = message;
      row.appendChild(cell);
      return row;
    }}

    function formatClubbedValue(value) {{
      if (value === null || value === undefined) {{
        return "";
      }}
      if (Array.isArray(value)) {{
        return value
          .map((item) => String(item))
          .filter((item) => item.length > 0)
          .join(", ");
      }}
      if (typeof value === "object") {{
        try {{
          return JSON.stringify(value);
        }} catch (_) {{
          return "";
        }}
      }}
      return String(value);
    }}

    function isClubbedFinding(clubbed) {{
      return Boolean(clubbed) && typeof clubbed === "object" && !Array.isArray(clubbed);
    }}

    function extractClubbedLines(clubbed) {{
      if (!isClubbedFinding(clubbed)) {{
        return [];
      }}
      const lines = [];
      const rawLines = clubbed.lines;
      if (Array.isArray(rawLines)) {{
        rawLines.forEach((line) => {{
          if (line === 0 || Number.isInteger(line)) {{
            lines.push(line);
          }} else {{
            const parsed = parseInt(line, 10);
            if (!Number.isNaN(parsed)) {{
              lines.push(parsed);
            }}
          }}
        }});
      }}
      return lines;
    }}

    function buildClubbedList(clubbed) {{
      if (!isClubbedFinding(clubbed)) {{
        return [];
      }}
      const details = [];
      const lines = extractClubbedLines(clubbed);
      const messages = Array.isArray(clubbed.messages) ? clubbed.messages : [];
      if (Array.isArray(clubbed.lines) && lines.length > 0 && Array.isArray(clubbed.messages) && messages.length > 0) {{
        const maxLen = Math.max(lines.length, messages.length);
        for (let i = 0; i < maxLen; i += 1) {{
          const line = i < lines.length && lines[i] !== 0 ? String(lines[i]) : "-";
          const message = messages[i] || "";
          if (message) {{
            details.push(`Line ${line}: ${message}`);
          }} else {{
            details.push(`Line ${line}`.trim());
          }}
        }}
        return details;
      }}

      const entries = Object.entries(clubbed);
      const arrayEntries = entries.filter((entry) => Array.isArray(entry[1]));
      if (arrayEntries.length >= 2 && arrayEntries.every((entry) => Array.isArray(entry[1]) && entry[1].length === arrayEntries[0][1].length)) {{
        const length = arrayEntries[0][1].length;
        for (let i = 0; i < length; i += 1) {{
          const row = arrayEntries
            .map(([key, values]) => `${{key}}: ${{formatClubbedValue(values[i])}}`)
            .join(" | ");
          details.push(row);
        }}
        return details;
      }}

      entries.forEach(([key, value]) => {{
        const formatted = formatClubbedValue(value);
        if (formatted) {{
          details.push(`${{key}}: ${{formatted}}`);
        }}
      }});
      return details;
    }}

    function createDescriptionCell(description, f) {{
      const td = document.createElement("td");
      td.className = "details";
      td.textContent = description;

      const clubbed = f.clubbed;
      if (isClubbedFinding(clubbed)) {{
        const clubbedItems = buildClubbedList(clubbed);
        if (clubbedItems.length > 0) {{
          const details = document.createElement("details");
          details.className = "finding-details";
          const summary = document.createElement("summary");
          summary.textContent = `Grouped: ${clubbedItems.length} item(s)`;
          const list = document.createElement("ul");
          clubbedItems.forEach((entry) => {{
            const li = document.createElement("li");
            li.textContent = entry;
            list.appendChild(li);
          }});
          details.appendChild(summary);
          details.appendChild(list);
          td.appendChild(details);
        }}
      }}
      return td;
    }}

    function clubbedLineText(clubbed) {{
      const lines = extractClubbedLines(clubbed);
      if (lines.length === 0) {{
        return "";
      }}
      const sortedLines = [...new Set(lines)].sort((a, b) => a - b);
      if (lines.length === 1) {{
        return String(sortedLines[0]);
      }}
      if (sortedLines.length <= 5) {{
        return sortedLines.join(", ");
      }}
      return `${{sortedLines[0]}}...${{sortedLines[sortedLines.length - 1]}}`;
    }}

    function clubbedSearchText(clubbed) {{
      if (!isClubbedFinding(clubbed)) {{
        return "";
      }}
      return Object.entries(clubbed)
        .map(([key, value]) => `${{key}}:${{formatClubbedValue(value)}}`)
        .join(" ")
        .toLowerCase();
    }}

    function cellForFinding(f) {{
      const filePath = getText(f.location && f.location.file_path);
      const clubbed = f.clubbed;
      const line = f.location ? (f.location.line_number || clubbedLineText(clubbed)) : clubbedLineText(clubbed);
      const rule = getText(f.rule_id);
      const analyzer = getText(f.source_analyzer || "unknown");
      const severity = getText(f.severity || "info").toLowerCase();
      const title = getText(f.title);
      const desc = getText(f.description);
      const remediation = getText(f.remediation_guidance);

      const row = document.createElement("tr");

      const severityCell = document.createElement("td");
      const severityBadge = document.createElement("span");
      severityBadge.className = `badge ${badgeClass(severity)}`;
      severityBadge.textContent = severity;
      severityCell.appendChild(severityBadge);
      row.appendChild(severityCell);

      row.appendChild(createTextCell(analyzer));
      row.appendChild(createTextCell(filePath));
      const lineCell = createTextCell(line);
      if (f.location && !f.location.line_number && isClubbedFinding(clubbed) && extractClubbedLines(clubbed).length > 1) {{
        const indicator = document.createElement("span");
        indicator.className = "clubbed-line-indicator";
        indicator.textContent = "multiple";
        lineCell.appendChild(indicator);
      }}
      row.appendChild(lineCell);
      row.appendChild(createTextCell(title, "details"));
      row.appendChild(createDescriptionCell(desc, f));
      row.appendChild(createTextCell(remediation, "details"));

      row.dataset.severity = severity;
      row.dataset.analyzer = analyzer.toLowerCase();
      row.dataset.search = `${severity} ${analyzer} ${rule} ${filePath} ${line} ${title} ${desc} ${remediation} ${clubbedSearchText(clubbed)}`.toLowerCase();
      return row;
    }}

    function normalizeCell(value) {{
      return getText(value).toLowerCase().trim();
    }}

    function switchTab(activeTabId) {{
      tabButtons.forEach((button) => {{
        const isActive = button.dataset.tab === activeTabId;
        button.classList.toggle("active", isActive);
        button.setAttribute("aria-selected", isActive ? "true" : "false");
      }});
      tabPanels.forEach((panel) => {{
        panel.classList.toggle("active", panel.id === activeTabId);
      }});
    }}

    function switchGuideTab(activeTabId) {{
      glossaryTabButtons.forEach((button) => {{
        const isActive = button.dataset.guideTab === activeTabId;
        button.classList.toggle("active", isActive);
        button.setAttribute("aria-selected", isActive ? "true" : "false");
      }});
      glossaryTabPanels.forEach((panel) => {{
        panel.classList.toggle("active", panel.id === activeTabId);
      }});
    }}

    function applyFilters() {{
      const text = (searchInput.value || "").toLowerCase().trim();
      const severity = (severityFilter.value || "").toLowerCase();
      const analyzer = (analyzerFilter.value || "").toLowerCase();
      const title = (titleFilter.value || "").toLowerCase();

      filtered = findings.filter((f) => {{
        const loc = f.location || {};
        const matchesText = !text || ((f.title || "") + (f.description || "") + (loc.file_path || "") + (f.rule_id || "") + (f.source_analyzer || "") + (f.category || "") + clubbedSearchText(f.clubbed)).toLowerCase().includes(text);
        const s = (f.severity || "info").toLowerCase();
        const a = (f.source_analyzer || "unknown").toLowerCase();
        const t = (f.title || "").toLowerCase();
        const passesSeverity = !severity || s === severity;
        const passesAnalyzer = !analyzer || a === analyzer;
        const passesTitle = !title || t === title;
        return matchesText && passesSeverity && passesAnalyzer && passesTitle;
      }});

      currentPage = 1;
      applySort();
      renderTable();
    }}

    function getComparable(f, key) {{
      const loc = f.location || {{}};
      const sev = (f.severity || "info").toLowerCase();
      const analyzer = getText(f.source_analyzer || "unknown");
      const title = getText(f.title);
      const line = loc.line_number || 0;
      const clubbedLine = clubbedLineText(f.clubbed);
      const parsedLine = parseInt(line || clubbedLine, 10);
      const rule = getText(f.rule_id);
      const desc = getText(f.description);
      const filePath = getText(loc.file_path);
      const remediation = getText(f.remediation_guidance);
      switch (key) {{
        case "severity":
          return severityOrder[sev] || 0;
        case "source_analyzer":
          return analyzer.toLowerCase();
        case "rule_id":
          return rule.toLowerCase();
        case "file":
          return filePath.toLowerCase();
        case "title":
          return title.toLowerCase();
        case "description":
          return desc.toLowerCase();
        case "line":
          return Number.isFinite(parsedLine) ? parsedLine : 0;
        case "remediation":
          return remediation.toLowerCase();
        default:
          return "";
      }}
    }}

    function applySort() {{
      const direction = sortState.direction === "asc" ? 1 : -1;
      const key = sortState.key;
      filtered.sort((a, b) => {{
        const aVal = getComparable(a, key);
        const bVal = getComparable(b, key);
        if (aVal === bVal) return 0;
        return aVal > bVal ? direction : -direction;
      }});
    }}

    function renderTable() {{
      tableBody.innerHTML = "";
      const pageSize = parseInt(pageSizeEl.value || "50", 10);
      const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
      const safePage = Math.min(Math.max(1, currentPage), totalPages);
      currentPage = safePage;
      const start = (currentPage - 1) * pageSize;
      const end = Math.min(start + pageSize, filtered.length);

      if (filtered.length === 0) {{
        tableBody.appendChild(createTableSpacer());
      }} else {{
        for (let i = start; i < end; i += 1) {{
          tableBody.appendChild(cellForFinding(filtered[i]));
        }}
      }}

      if (filtered.length === 0) {{
        pagerInfo.textContent = "No findings match your filters.";
      }} else {{
        pagerInfo.textContent = `Showing ${{start + 1}}-${{end}} of ${{filtered.length}} findings`;
      }}
      prevBtn.disabled = currentPage === 1;
      nextBtn.disabled = currentPage === totalPages;
    }}

    document.querySelectorAll("th[data-sort]").forEach((header) => {{
      header.addEventListener("click", () => {{
        const key = header.dataset.sort;
        if (sortState.key === key) {{
          sortState.direction = sortState.direction === "asc" ? "desc" : "asc";
        }} else {{
          sortState.key = key;
          sortState.direction = "asc";
        }}
        applySort();
        currentPage = 1;
        renderTable();
      }});
    }});

    searchInput.addEventListener("input", applyFilters);
    severityFilter.addEventListener("change", applyFilters);
    analyzerFilter.addEventListener("change", applyFilters);
    titleFilter.addEventListener("change", applyFilters);
    pageSizeEl.addEventListener("change", () => {{
      currentPage = 1;
      renderTable();
    }});
    prevBtn.addEventListener("click", () => {{
      if (currentPage > 1) {{
        currentPage -= 1;
        renderTable();
      }}
    }});
    nextBtn.addEventListener("click", () => {{
      currentPage += 1;
      renderTable();
    }});

    tabButtons.forEach((button) => {{
      button.addEventListener("click", () => {{
        switchTab(button.dataset.tab);
      }});
    }});

    glossaryTabButtons.forEach((button) => {{
      button.addEventListener("click", () => {{
        switchGuideTab(button.dataset.guideTab);
      }});
    }});

    applyFilters();
  </script>
</body>
</html>
"""

    html_content = html_content.replace("{{", "{").replace("}}", "}")
    html_content = (
        html_content.replace("TARGET_PATH", _escape(report.get("target_path", "")))
        .replace("FINAL_SCORE", f"{final_score:.2f}")
        .replace("FINAL_SCORE_CLASS", final_score_class)
        .replace("TOTAL_FINDINGS", str(total_findings))
        .replace("TOTAL_ANALYZERS", str(total_analyzers))
        .replace("FILES_WITH_ISSUES", str(files_with_issues))
        .replace("OVERALL_EXECUTEDs", f"{overall_executed:.2f}s")
        .replace("HIGH_COUNT", str(high_count))
        .replace("MEDIUM_COUNT", str(medium_count))
        .replace("LOW_COUNT", str(low_count))
        .replace("ANALYZER_SUMMARY_ROWS", analyzer_summary_rows)
        .replace("ANALYZER_FILTER_OPTIONS", analyzer_filter_options)
        .replace("TITLE_FILTER_OPTIONS", title_filter_options)
        .replace("ANALYZER_GUIDES_HTML", analyzer_guides_html)
        .replace("REPORT_DATA_JSON", payload_json)
    )

    with open(output_file, "w", encoding="utf-8") as file:
        file.write(html_content)
