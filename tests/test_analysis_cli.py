from pathlib import Path

import gnost.cli.app as app
from gnost.analysis.core.models import (
    ConsolidatedReport,
    AnalysisMetrics,
    SeverityLevel,
    UnifiedFinding,
)


def test_analysis_output_paths_are_under_docs_analysis(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    target = repo_root / "src" / "module.py"
    target.parent.mkdir()
    target.write_text("x = 1\n", encoding="utf-8")

    assert app._analysis_output_path(str(target)) == str(
        repo_root / "docs" / "analysis" / "gnost_analysis.json"
    )
    assert app._analysis_html_output_path(str(target)) == str(
        repo_root / "docs" / "analysis" / "gnost_analysis.html"
    )


def test_analyze_list_analyzers(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    class DummyRegistry:
        def list_analyzer_names(self):
            return ["robustness", "readability"]

    monkeypatch.setattr(app.analysis, "initialize_analyzers", lambda: None)
    monkeypatch.setattr(
        app.analysis, "get_analyzer_registry", lambda: DummyRegistry()
    )
    monkeypatch.setattr("sys.argv", ["gnost", "analyze", "--list-analyzers"])

    result = app.main()
    captured = capsys.readouterr()
    assert result == 0
    assert "robustness" in captured.out
    assert "readability" in captured.out


def test_analyze_with_no_python_files_returns_zero(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app.analysis, "initialize_analyzers", lambda: None)

    def empty_collect(_target_path: str, *, exts=None):
        return [], 0

    monkeypatch.setattr(app.analysis, "collect_code_files", empty_collect)
    monkeypatch.setattr("sys.argv", ["gnost", "analyze", "."])

    result = app.main()
    assert result == 0


def test_analyze_out_writes_json_and_html_files(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (repo_root / "sample.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.chdir(repo_root)

    captured = {}

    monkeypatch.setattr(app.analysis, "initialize_analyzers", lambda: None)

    def collect(_, *, exts=None):
        return [str(repo_root / "sample.py")], 1

    monkeypatch.setattr(app.analysis, "collect_code_files", collect)

    async def fake_run_async(cfg, show_progress: bool):
        metrics = AnalysisMetrics(
            analyzer_name="robustness",
            execution_time_seconds=0.01,
            files_analyzed=1,
            findings_count=0,
        )
        report = ConsolidatedReport(
            target_path=str(repo_root),
            findings=[
                UnifiedFinding(
                    title="test",
                    description="test finding",
                    severity=SeverityLevel.HIGH,
                    source_analyzer="robustness",
                )
            ],
            analysis_metrics=[metrics],
            summary={"risk_score": 30.0},
        )
        return report

    monkeypatch.setattr(app.analysis, "run_async", fake_run_async)

    def fake_write_json_file(path: str, data: dict, compact: bool):
        captured["json"] = path
        captured["compact"] = compact
        captured["payload"] = data

    def fake_render_html(payload: dict, output_path: str):
        captured["html"] = output_path
        captured["render_payload"] = payload

    monkeypatch.setattr(app.analysis, "write_json_file", fake_write_json_file)
    monkeypatch.setattr(app, "render_analysis_html", fake_render_html)

    monkeypatch.setattr("sys.argv", ["gnost", "analyze", ".", "-o", "--compact"])

    result = app.main()
    assert result == 0
    assert captured["json"] == str(repo_root / "docs" / "analysis" / "gnost_analysis.json")
    assert captured["html"] == str(repo_root / "docs" / "analysis" / "gnost_analysis.html")
    assert captured["compact"] is True
    assert "findings" in captured["payload"]
