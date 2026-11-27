"""CI features: exit codes, score card, path resolver, fingerprints, baseline, SARIF and the gate."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List, Optional

import pytest

from gnost.analysis.core.models import (
    AnalysisMetrics,
    CodeLocation,
    ConsolidatedReport,
    SeverityLevel,
    UnifiedFinding,
)
from gnost.ci.baseline import Baseline, BaselineError
from gnost.ci.exit_codes import ExitCode
from gnost.ci.fingerprint import FindingFingerprint
from gnost.ci.gate import QualityGate
from gnost.ci.paths import PathResolver
from gnost.ci.run import CiOptions, CiRun
from gnost.ci.sarif import SarifWriter
from gnost.ci.scorecard import ScoreCard
from gnost.config.settings import GnostConfig, _validate
from gnost.utils.layout import OutputLayout

ROOT = os.path.abspath("/repo")
FILES = [
    os.path.join(ROOT, p)
    for p in ("src/a.py", "src/b.py", "pkg/core/util.py", "other/core/util.py")
]


def finding(
    title: str = "Long function",
    path: str = "src/a.py",
    line: int = 10,
    analyzer: str = "readability",
    rule: Optional[str] = "long-function",
    severity: SeverityLevel = SeverityLevel.MEDIUM,
    function: Optional[str] = None,
) -> UnifiedFinding:
    return UnifiedFinding(
        title=title,
        description=f"{title} here",
        severity=severity,
        source_analyzer=analyzer,
        rule_id=rule,
        location=CodeLocation(path, line_number=line, function_name=function),
    )


def resolver() -> PathResolver:
    return PathResolver(FILES, ROOT)


def fingerprint() -> FindingFingerprint:
    return FindingFingerprint(resolver())


# ---------------------------------------------------------------- exit codes


def test_exit_codes_are_documented_numbers() -> None:
    assert [
        int(c)
        for c in (
            ExitCode.OK,
            ExitCode.ERROR,
            ExitCode.USAGE,
            ExitCode.GATE_FAILED,
            ExitCode.INTERRUPTED,
        )
    ] == [0, 1, 2, 3, 130]


# ---------------------------------------------------------------- score card


def test_risk_converts_to_a_score_out_of_ten() -> None:
    assert ScoreCard.risk_to_score(0) == 10.0
    assert ScoreCard.risk_to_score(100) == 0.0
    assert ScoreCard.risk_to_score(25) == 7.5
    assert ScoreCard.risk_to_score(-5) == 10.0 and ScoreCard.risk_to_score(500) == 0.0


def test_critical_findings_count_as_high() -> None:
    found = [
        finding(severity=SeverityLevel.CRITICAL),
        finding(severity=SeverityLevel.HIGH),
        finding(severity=SeverityLevel.LOW),
    ]
    assert ScoreCard.severity_counts(found) == {
        "high": 2,
        "medium": 0,
        "low": 1,
        "info": 0,
    }


def test_the_score_card_reads_a_report() -> None:
    report = ConsolidatedReport(
        findings=[
            finding(analyzer="readability"),
            finding(analyzer="readability", severity=SeverityLevel.HIGH),
        ],
        analysis_metrics=[
            AnalysisMetrics("robustness", 1.0, 3, 0),
            AnalysisMetrics("readability", 1.0, 3, 2),
        ],
        summary={"risk_score": 30.0},
    )
    card = ScoreCard.from_report(report)
    assert [a.name for a in card.analyzers] == ["readability", "robustness"]  # sorted
    assert card.method == "density" and card.lines is None
    assert (
        card.final_score == 8.72
    )  # weight 0.9 in fewer than 1,000 lines: 10 - 2 ln 1.9
    assert ScoreCard.from_report(report, "average").final_score == 7.0  # risk_score 30
    clean = next(a for a in card.analyzers if a.name == "robustness")
    assert clean.score == 10.0 and clean.findings == 0
    assert (
        ScoreCard.style(8.0) == "green"
        and ScoreCard.style(6.5) == "yellow"
        and ScoreCard.style(3) == "red"
    )


def _scored(findings: List[UnifiedFinding], lines: Optional[int]) -> ScoreCard:
    return ScoreCard.from_report(
        ConsolidatedReport(
            findings=findings,
            analysis_metrics=[AnalysisMetrics("readability", 1.0, 3, len(findings))],
            summary={"analyzed_lines": lines, "risk_score": 30.0},
        )
    )


def test_the_density_curve() -> None:
    assert ScoreCard.density_to_score(0) == 10.0
    assert ScoreCard.density_to_score(1) == 8.61
    assert ScoreCard.density_to_score(4) == 6.78
    assert ScoreCard.density_to_score(10_000) == 0.0  # floored, never negative
    assert ScoreCard.density_to_score(-1) == 10.0


def test_the_number_of_findings_counts() -> None:
    one = _scored([finding(severity=SeverityLevel.INFO)], 5000)
    many = _scored(
        [finding(severity=SeverityLevel.INFO, line=i) for i in range(200)], 5000
    )
    assert (
        many.final_score < one.final_score
    )  # the "average" formula scored them the same
    critical = _scored([finding(severity=SeverityLevel.CRITICAL)], 5000)
    assert (
        many.final_score < critical.final_score
    )  # 200 info findings weigh more than one critical


def test_the_project_size_counts() -> None:
    found = [finding(line=i) for i in range(20)]
    assert _scored(found, 50_000).final_score > _scored(found, 5_000).final_score
    assert _scored(found, 50_000).density == 0.12  # 20 x 0.3 per 50 KLOC


def test_a_small_project_counts_as_a_thousand_lines() -> None:
    found = [finding()]
    assert _scored(found, 20).final_score == _scored(found, 1000).final_score
    assert _scored(found, None).final_score == _scored(found, 1000).final_score


def test_the_analyzer_and_final_scores_use_the_same_lines() -> None:
    card = _scored([finding(), finding(analyzer="robustness", line=2)], 2000)
    readability = next(a for a in card.analyzers if a.name == "readability")
    assert readability.score == ScoreCard.density_to_score(0.15)
    assert card.final_score == ScoreCard.density_to_score(0.3)
    assert card.to_dict() == {
        "method": "density",
        "final_score": card.final_score,
        "analyzed_lines": 2000,
        "density": 0.3,
        "analyzers": {"readability": readability.score},
    }


def test_count_lines_skips_blank_lines_and_missing_files(tmp_path: Path) -> None:
    source = tmp_path / "a.py"
    source.write_text("x = 1\n\n   \ny = 2\n", encoding="utf-8")
    assert ScoreCard.count_lines([str(source), str(tmp_path / "gone.py")]) == 2


def test_the_score_method_comes_from_the_config(tmp_path: Path) -> None:
    from gnost.config.settings import ConfigError

    config = GnostConfig()
    _validate({"analyze": {"score": "average"}}, config)
    options = CiOptions.from_args(
        argparse.Namespace(), config, OutputLayout(str(tmp_path))
    )
    assert options.score_method == "average"
    assert CiOptions().score_method == "density"
    with pytest.raises(ConfigError):
        _validate({"analyze": {"score": "median"}}, GnostConfig())


# ------------------------------------------------------------ path resolving


def test_reported_paths_resolve_to_repository_relative_ones() -> None:
    r = resolver()
    assert r.resolve(os.path.join(ROOT, "src/a.py")) == "src/a.py"  # absolute
    assert r.resolve("src/a.py") == "src/a.py"  # already right
    assert r.resolve("./src/b.py") == "src/b.py"
    assert r.resolve("b.py") == "src/b.py"  # a unique ending
    assert r.resolve("pkg/core/util.py") == "pkg/core/util.py"


def test_a_project_folder_name_in_front_of_the_path_is_dropped() -> None:
    r = resolver()
    assert (
        r.resolve("repo/src/a.py") == "src/a.py"
    )  # analyzers may keep the folder name
    assert r.resolve("whatever/src/a.py") == "src/a.py"
    assert r.resolve("repo/pkg/core/util.py") == "pkg/core/util.py"


def test_an_ambiguous_ending_is_left_as_reported() -> None:
    r = resolver()
    assert r.resolve("core/util.py") == "core/util.py"  # matches two files
    assert not r.exists("core/util.py")
    assert r.exists("src/a.py")


# --------------------------------------------------------------- fingerprints


def test_a_fingerprint_ignores_lines_and_numbers_but_not_files_or_rules() -> None:
    fp = fingerprint()
    base = fp.of(finding(line=10))
    assert fp.of(finding(line=250)) == base  # code above moved
    assert fp.of(finding(title="Long  function", line=3)) == base
    assert fp.of(finding(title="Function with 12 branches")) == fp.of(
        finding(title="Function with 15 branches")
    )
    assert fp.of(finding(path="src/b.py")) != base
    assert fp.of(finding(rule="other-rule")) != base
    assert fp.of(finding(function="run")) != base
    assert fp.of(finding(path="b.py", analyzer="readability")) == fp.of(
        finding(path="src/b.py")
    )  # same file, other spelling


# ------------------------------------------------------------------ baseline


def test_a_baseline_hides_known_findings_and_shows_new_ones(tmp_path: Path) -> None:
    fp = fingerprint()
    today = [finding(line=10), finding(line=20), finding(path="src/b.py")]
    baseline = Baseline.from_findings(today, fp)
    path = tmp_path / "baseline.json"
    baseline.save(str(path))
    loaded = Baseline.load(str(path))
    assert loaded.counts == baseline.counts and sum(loaded.counts.values()) == 3

    # Nothing changed, lines moved: nothing is new.
    moved = [finding(line=15), finding(line=99), finding(path="src/b.py", line=4)]
    new, known = loaded.split(moved, fp)
    assert new == [] and len(known) == 3

    # A third problem of the same kind in the same file is new, a fixed one never hides it.
    more = moved + [finding(line=200)]
    new, known = loaded.split(more, fp)
    assert len(new) == 1 and len(known) == 3
    new, _ = loaded.split([finding(line=1), finding(line=2), finding(line=3)], fp)
    assert len(new) == 1  # baseline knew two of this kind


def test_the_baseline_file_is_stable_and_readable(tmp_path: Path) -> None:
    fp = fingerprint()
    findings = [finding(path="src/b.py"), finding(), finding(line=2)]
    first, second = tmp_path / "1.json", tmp_path / "2.json"
    Baseline.from_findings(findings, fp).save(str(first))
    Baseline.from_findings(list(reversed(findings)), fp).save(str(second))
    assert first.read_text() == second.read_text()  # order does not matter
    data = json.loads(first.read_text())
    assert (
        data["total"] == 3
        and data["version"] == 1
        and data["generator"].startswith("gnost ")
    )


@pytest.mark.parametrize(
    "content",
    ["not json", "[1, 2]", '{"fingerprints": "x"}', '{"fingerprints": {"a": "b"}}'],
)
def test_a_broken_baseline_is_refused_with_a_message(
    tmp_path: Path, content: str
) -> None:
    path = tmp_path / "b.json"
    path.write_text(content)
    with pytest.raises(BaselineError):
        Baseline.load(str(path))


def test_a_missing_baseline_says_how_to_create_it(tmp_path: Path) -> None:
    with pytest.raises(BaselineError) as err:
        Baseline.load(str(tmp_path / "none.json"))
    assert "--write-baseline" in str(err.value)


# --------------------------------------------------------------------- SARIF


def test_sarif_has_rules_results_locations_and_fingerprints() -> None:
    writer = SarifWriter(resolver(), fingerprint())
    findings = [
        finding(line=10, severity=SeverityLevel.HIGH),
        finding(
            title="Bare except",
            rule=None,
            analyzer="robustness",
            path="pkg/core/util.py",
            line=7,
            severity=SeverityLevel.LOW,
        ),
        finding(title="Project level", path="repo", rule="project"),  # not a file
    ]
    log = writer.build(findings)
    assert log["version"] == "2.1.0" and log["$schema"].endswith("sarif-2.1.0.json")
    run = log["runs"][0]
    assert run["tool"]["driver"]["name"] == "GNOST"
    rule_ids = [r["id"] for r in run["tool"]["driver"]["rules"]]
    assert rule_ids == sorted(set(rule_ids), key=rule_ids.index)  # unique
    assert (
        "readability/long-function" in rule_ids and "robustness/bare-except" in rule_ids
    )

    by_rule = {r["ruleId"]: r for r in run["results"]}
    high = by_rule["readability/long-function"]
    assert high["level"] == "error"
    loc = high["locations"][0]["physicalLocation"]
    assert loc["artifactLocation"] == {"uri": "src/a.py", "uriBaseId": "%SRCROOT%"}
    assert loc["region"]["startLine"] == 10
    assert by_rule["robustness/bare-except"]["level"] == "note"
    assert (
        "locations" not in by_rule["readability/project"]
    )  # no real file, no location
    for result in run["results"]:
        assert len(result["partialFingerprints"]["gnostFingerprint/v1"]) == 32
        assert (
            run["tool"]["driver"]["rules"][result["ruleIndex"]]["id"]
            == result["ruleId"]
        )


def test_sarif_output_is_ordered_and_can_be_written(tmp_path: Path) -> None:
    writer = SarifWriter(resolver(), fingerprint())
    findings = [
        finding(path="src/b.py", line=5),
        finding(path="src/a.py", line=30),
        finding(path="src/a.py", line=2),
    ]
    out = tmp_path / "deep" / "out.sarif"
    writer.write(str(out), findings)
    results = json.loads(out.read_text())["runs"][0]["results"]
    places = [
        (
            r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"],
            r["locations"][0]["physicalLocation"]["region"]["startLine"],
        )
        for r in results
    ]
    assert places == [("src/a.py", 2), ("src/a.py", 30), ("src/b.py", 5)]


def test_an_empty_sarif_is_valid() -> None:
    log = SarifWriter(resolver(), fingerprint()).build([])
    assert (
        log["runs"][0]["results"] == []
        and log["runs"][0]["tool"]["driver"]["rules"] == []
    )


# ---------------------------------------------------------------------- gate


@pytest.mark.parametrize(
    "fail_under,fail_on_new,score,new,passed",
    [
        (None, False, 1.0, None, True),
        (8.0, False, 7.99, None, False),
        (8.0, False, 8.0, None, True),
        (None, True, 9.0, 0, True),
        (None, True, 9.0, 2, False),
        (8.0, True, 5.0, 3, False),
    ],
)
def test_the_gate_checks_each_rule(
    fail_under: Optional[float],
    fail_on_new: bool,
    score: float,
    new: Optional[int],
    passed: bool,
) -> None:
    result = QualityGate(fail_under, fail_on_new).evaluate(score, new)
    assert result.passed is passed and bool(result.messages) is (not passed)


def test_the_gate_names_every_broken_rule() -> None:
    result = QualityGate(8.0, True).evaluate(5.0, 1)
    assert len(result.messages) == 2
    assert "5.00" in result.messages[0] and "8.00" in result.messages[0]
    assert "1 new finding " in result.messages[1]


# --------------------------------------------------------------- the options


def _args(**given: object) -> argparse.Namespace:
    base = dict(
        fail_under=None,
        fail_on_new=False,
        baseline=None,
        write_baseline=None,
        sarif=None,
    )
    base.update(given)
    return argparse.Namespace(**base)


def test_options_use_default_files_for_bare_flags(tmp_path: Path) -> None:
    layout = OutputLayout(str(tmp_path))
    opts = CiOptions.from_args(
        _args(sarif="", write_baseline="", baseline="mine.json"), GnostConfig(), layout
    )
    assert opts.sarif == layout.analysis_sarif
    assert opts.write_baseline == layout.baseline_json
    assert opts.baseline == "mine.json"
    nothing = CiOptions.from_args(_args(), GnostConfig(), layout)
    assert (
        nothing.sarif,
        nothing.baseline,
        nothing.write_baseline,
        nothing.fail_under,
    ) == (None, None, None, None)


def test_options_read_the_config_and_flags_win(tmp_path: Path) -> None:
    config = GnostConfig()
    _validate({"analyze": {"fail_under": 7.5, "baseline": "ci/base.json"}}, config)
    layout = OutputLayout(str(tmp_path))
    opts = CiOptions.from_args(_args(), config, layout)
    assert opts.fail_under == 7.5 and opts.baseline == str(
        tmp_path / "ci" / "base.json"
    )
    assert CiOptions.from_args(_args(fail_under=9.0), config, layout).fail_under == 9.0


def test_fail_on_new_without_a_baseline_is_a_mistake() -> None:
    assert CiOptions(fail_on_new=True).problem() is not None
    assert CiOptions(fail_on_new=True, baseline="b.json").problem() is None
    assert CiOptions().problem() is None


def test_bad_fail_under_in_the_config_is_refused() -> None:
    from gnost.config.settings import ConfigError

    with pytest.raises(ConfigError):
        _validate({"analyze": {"fail_under": 11}}, GnostConfig())


# ----------------------------------------------------------------- the run


def _report(findings: List[UnifiedFinding]) -> ConsolidatedReport:
    return ConsolidatedReport(
        findings=findings,
        analysis_metrics=[AnalysisMetrics("readability", 1.0, 3, len(findings))],
        summary={"risk_score": 30.0},
    )


def test_a_full_run_writes_the_baseline_then_gates_on_new_findings(
    tmp_path: Path,
) -> None:
    base, sarif = str(tmp_path / "b.json"), str(tmp_path / "out.sarif")
    today = _report([finding(line=1), finding(path="src/b.py")])

    first = CiRun(CiOptions(write_baseline=base, sarif=sarif), ROOT, FILES).process(
        today
    )
    assert first.gate.passed and first.new_findings is None
    assert len(first.report.findings) == 2  # no baseline yet, everything shows
    assert os.path.isfile(base) and os.path.isfile(sarif)

    options = CiOptions(baseline=base, fail_on_new=True, fail_under=9.5)
    same = CiRun(options, ROOT, FILES).process(_report(list(today.findings)))
    assert same.new_findings == 0 and same.known_findings == 2
    assert (
        same.report.findings == [] and same.card.final_score == 9.06
    )  # the score covers everything: two medium findings, 10 - 2 ln 1.6
    assert same.gate.messages == [
        "score 9.06 is below the required 9.50 (--fail-under)"
    ]

    grown = CiRun(options, ROOT, FILES).process(
        _report(today.findings + [finding(path="src/b.py", rule="new-rule")])
    )
    assert grown.new_findings == 1 and len(grown.report.findings) == 1
    assert grown.baseline_summary() == {"new_findings": 1, "known_findings_hidden": 2}
    assert any("1 new" in note for note in grown.notes)


def test_paths_behind_a_symlinked_folder_still_resolve(tmp_path: Path) -> None:
    real = tmp_path / "real"
    (real / "src").mkdir(parents=True)
    (real / "src" / "a.py").write_text("x = 1\n")
    link = tmp_path / "link"
    link.symlink_to(real)
    # The analyzers saw the real path; the command line named the symlink.
    resolver_ = PathResolver([str(real / "src" / "a.py")], str(link))
    assert resolver_.resolve(str(link / "src" / "a.py")) == "src/a.py"
    assert resolver_.resolve(str(real / "src" / "a.py")) == "src/a.py"


def test_the_html_report_shows_the_card_scores(tmp_path: Path) -> None:
    from gnost.reporters.analysis_html import render_analysis_html

    out = tmp_path / "report.html"
    summary = {
        "final_score": 6.78,
        "score": {
            "method": "density",
            "final_score": 6.78,
            "analyzed_lines": 12345,
            "density": 4.0,
            "analyzers": {"readability": 7.25},
        },
    }
    render_analysis_html(
        {
            "findings": [],
            "summary": summary,
            "analysis_metrics": [{"analyzer_name": "readability"}],
        },
        str(out),
    )
    page = out.read_text(encoding="utf-8")
    assert "6.78 / 10.00" in page and 'class="score bad"' not in page
    assert (
        'class="score okay"' in page
    )  # the colour class is filled in, not "6.78_CLASS"
    assert "<td>7.25</td>" in page
    assert "<h3>Finding Density</h3>\n          <p>4.00</p>" in page
    assert "Weighted findings per 1,000 lines (12,345 lines analyzed)" in page


def test_the_html_report_has_a_light_theme(tmp_path: Path) -> None:
    from gnost.reporters.analysis_html import render_analysis_html

    out = tmp_path / "report.html"
    render_analysis_html({"findings": [], "summary": {}}, str(out))
    page = out.read_text(encoding="utf-8")
    assert '<html lang="en" data-theme="dark">' in page
    assert ':root[data-theme="light"] {' in page  # braces unescaped
    assert 'id="themeBtn"' in page
    assert "Not computed with score = average" in page  # no density in this report
    assert 'localStorage.getItem("gnost-theme")' in page  # shared with flow.html


def test_findings_left_out_by_max_findings_still_count() -> None:
    metrics = AnalysisMetrics("readability", 1.0, 3, 1)
    metrics.capped_by_severity = {"low": 30}
    report = ConsolidatedReport(
        findings=[finding()],
        analysis_metrics=[metrics],
        summary={"analyzed_lines": 1000},
    )
    card = ScoreCard.from_report(report)
    assert card.density == 3.3  # 0.3 listed + 30 x 0.1 left out
    assert (
        card.analyzers[0].score == card.final_score == ScoreCard.density_to_score(3.3)
    )


def test_the_engine_reports_what_the_cap_left_out() -> None:
    from gnost.analysis.core.engine import UnifiedAnalysisEngine
    from gnost.analysis.core.models import AnalysisConfiguration

    found = [finding(severity=SeverityLevel.LOW, line=i) for i in range(5)]
    found.append(finding(severity=SeverityLevel.HIGH, line=99))
    kept, left_out = UnifiedAnalysisEngine._cap(
        found, AnalysisConfiguration(max_findings_per_analyzer=2)
    )
    assert [f.severity for f in kept] == [SeverityLevel.HIGH, SeverityLevel.LOW]
    assert len(left_out) == 4 and {f.severity for f in left_out} == {SeverityLevel.LOW}
    assert UnifiedAnalysisEngine._cap(
        found, AnalysisConfiguration(max_findings_per_analyzer=0)
    ) == (found, [])
