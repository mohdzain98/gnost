"""`gnost analyze` CI flags through the real command line: exit codes, SARIF, baseline, gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import gnost.cli.app as app
from gnost.ci.exit_codes import ExitCode

PROBLEM = (
    "import os, sys\n\n"
    "def run(cmd, a, b, c, d, e, f):\n"
    "    try:\n"
    "        x = eval(cmd)\n"
    "        return os.system(cmd)\n"
    "    except:\n"
    "        pass\n"
)
ANOTHER = (
    "def helper(a, b, c, d, e, f, g, h):\n"
    "    try:\n"
    "        return int(a)\n"
    "    except:\n"
    "        pass\n"
)


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A one-file project with a few findings, as the current directory."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "app.py").write_text(PROBLEM)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def analyze(monkeypatch: pytest.MonkeyPatch, *flags: str) -> int:
    monkeypatch.setattr(
        "sys.argv",
        [
            "gnost",
            "analyze",
            ".",
            "--no-progress",
            "--quiet",
            "-a",
            "readability",
            *flags,
        ],
    )
    return int(app.main())


def test_sarif_and_baseline_files_go_in_the_gnost_folder(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert analyze(monkeypatch, "--sarif", "--write-baseline") == ExitCode.OK
    sarif = json.loads((project / ".gnost" / "analysis" / "analysis.sarif").read_text())
    results = sarif["runs"][0]["results"]
    located = [
        r for r in results if "locations" in r
    ]  # project-wide findings have none
    assert located and all(
        r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "app.py"
        for r in located
    )
    baseline = json.loads((project / ".gnost" / "baseline.json").read_text())
    assert baseline["total"] == len(results)


def test_a_custom_sarif_path_is_used(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert analyze(monkeypatch, "--sarif", "out/report.sarif") == ExitCode.OK
    assert (project / "out" / "report.sarif").is_file()


def test_unchanged_code_passes_and_a_new_problem_fails_the_gate(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert analyze(monkeypatch, "--write-baseline") == ExitCode.OK
    assert analyze(monkeypatch, "--baseline", "--fail-on-new") == ExitCode.OK

    (project / "other.py").write_text(ANOTHER)
    assert analyze(monkeypatch, "--baseline", "--fail-on-new") == ExitCode.GATE_FAILED
    assert (
        analyze(monkeypatch, "--baseline") == ExitCode.OK
    )  # without --fail-on-new it only reports


def test_only_new_findings_reach_the_json_report(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    analyze(monkeypatch, "--write-baseline")
    (project / "other.py").write_text(ANOTHER)
    assert analyze(monkeypatch, "--baseline", "-o") == ExitCode.OK
    data = json.loads((project / ".gnost" / "analysis" / "analysis.json").read_text())
    assert data["baseline"]["new_findings"] == len(data["findings"]) > 0
    assert data["baseline"]["known_findings_hidden"] > 0
    assert all("other.py" in f["location"]["file_path"] for f in data["findings"])


def test_fail_under_compares_the_final_score(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert analyze(monkeypatch, "--fail-under", "0") == ExitCode.OK
    assert analyze(monkeypatch, "--fail-under", "10.01") == ExitCode.GATE_FAILED


def test_fail_under_can_come_from_the_config(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project / ".gnost.toml").write_text("[analyze]\nfail_under = 10\n")
    assert (
        analyze(monkeypatch) == ExitCode.GATE_FAILED
    )  # a file with findings cannot score 10


def test_mistakes_exit_with_the_usage_code(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert analyze(monkeypatch, "--fail-on-new") == ExitCode.USAGE  # needs a baseline
    assert analyze(monkeypatch, "--baseline", "missing.json") == ExitCode.USAGE
    monkeypatch.setattr("sys.argv", ["gnost", "analyze", "/no/such/folder", "--quiet"])
    assert app.main() == ExitCode.USAGE
