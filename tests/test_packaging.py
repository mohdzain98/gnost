import asyncio
import shutil
from pathlib import Path

import pytest

from gnost.analysis.analyzers.robustness_analyzer import MYPY_CONFIG, RobustnessAnalyzer
from gnost.reporters import analysis_html


def test_bundled_mypy_config_exists():
    assert MYPY_CONFIG.is_file()
    assert "strict = True" in MYPY_CONFIG.read_text(encoding="utf-8")


def test_report_templates_exist():
    templates = Path(analysis_html.__file__).parent / "templates"
    assert (templates / "analyzer_guides.json").is_file()
    assert (templates / "analyzer_guides_layout.html").is_file()


@pytest.mark.skipif(shutil.which("mypy") is None, reason="mypy not installed")
def test_mypy_findings_work_outside_repo_cwd(tmp_path, monkeypatch):
    """Regression: mypy used to fail silently when ./mypy.ini was missing."""
    target = tmp_path / "mod.py"
    target.write_text("def f(x):\n    return x\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    findings = asyncio.run(RobustnessAnalyzer()._run_mypy_check([str(target)]))
    assert findings, "expected strict-mode mypy findings for an untyped function"
