"""`gnost analyze` on JavaScript and TypeScript through the real command line."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pytest

import gnost.cli.app as app
from gnost.ci.exit_codes import ExitCode
from gnost.parsing import default_factory

needs_grammars = pytest.mark.skipif(
    not default_factory().available("javascript"),
    reason="tree-sitter grammars are not installed",
)

PROBLEM_JS = (
    "function load(input) {\n"
    "  try {\n"
    "    eval(input);\n"
    "  } catch (err) {}\n"
    "  if (input == 1) { console.log('one'); }\n"
    "  return input;\n"
    "}\n"
)
PROBLEM_TS = "export function read(value: any): any {\n  return value;\n}\n"
PROBLEM_PY = (
    "def f(a, b, c, d, e, f2):\n    try:\n        pass\n    except:\n        pass\n"
)


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".git").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.js").write_text(PROBLEM_JS)
    (tmp_path / "src" / "reader.ts").write_text(PROBLEM_TS)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def analyze(monkeypatch: pytest.MonkeyPatch, *flags: str) -> int:
    monkeypatch.setattr(
        "sys.argv", ["gnost", "analyze", ".", "--no-progress", "--quiet", *flags]
    )
    return int(app.main())


def findings(project: Path) -> List[dict]:
    report = json.loads(
        (project / ".gnost" / "analysis" / "analysis.json").read_text(encoding="utf-8")
    )
    return report["findings"]


@needs_grammars
def test_javascript_and_typescript_files_are_analyzed(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert analyze(monkeypatch, "-o") == ExitCode.OK
    rules = {(f["rule_id"], f["source_analyzer"]) for f in findings(project)}
    assert ("ROB-UNSAFE-EVAL", "robustness") in rules
    assert ("ROB-EMPTY-CATCH", "robustness") in rules
    assert ("ROB-UNTYPED-ANY", "robustness") in rules
    assert ("OBS-PRINT-LOGGING", "observability") in rules
    paths = {f["location"]["file_path"] for f in findings(project)}
    assert {"src/app.js", "src/reader.ts"} <= paths  # relative to the analyzed folder


@needs_grammars
def test_sarif_has_locations_for_javascript_findings(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert analyze(monkeypatch, "--sarif") == ExitCode.OK
    sarif = json.loads(
        (project / ".gnost" / "analysis" / "analysis.sarif").read_text(encoding="utf-8")
    )
    results = sarif["runs"][0]["results"]
    uris = {
        r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
        for r in results
        if r.get("locations")
    }
    assert "src/app.js" in uris and "src/reader.ts" in uris
    assert all("partialFingerprints" in r for r in results)


@needs_grammars
def test_a_baseline_hides_known_javascript_findings_and_shows_new_ones(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert analyze(monkeypatch, "--write-baseline") == ExitCode.OK
    assert analyze(monkeypatch, "--baseline", "--fail-on-new") == ExitCode.OK
    (project / "src" / "extra.js").write_text("function f() { eval('x'); }\n")
    assert analyze(monkeypatch, "--baseline", "--fail-on-new") == ExitCode.GATE_FAILED


@needs_grammars
def test_the_language_option_limits_the_files(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project / "tool.py").write_text(PROBLEM_PY)
    assert analyze(monkeypatch, "-o", "--language", "typescript") == ExitCode.OK
    paths = {f["location"]["file_path"] for f in findings(project)}
    assert paths == {"src/reader.ts"}


def test_an_unknown_language_is_a_usage_error(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert analyze(monkeypatch, "--language", "cobol") == ExitCode.USAGE


@needs_grammars
def test_generated_minified_vendored_and_test_files_are_handled(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for folder, name in (
        ("dist", "bundle.js"),
        ("node_modules/lib", "index.js"),
        ("src", "app.min.js"),
        ("src", "types.d.ts"),
    ):
        target = project / folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(PROBLEM_JS)
    (project / "src" / "app.test.js").write_text(
        "describe('x', () => { it('logs', () => { console.log('ok'); }); });\n"
    )
    assert analyze(monkeypatch, "-o") == ExitCode.OK
    paths = {f["location"]["file_path"] for f in findings(project)}
    assert paths == {
        "src/app.js",
        "src/reader.ts",
    }  # none of the skipped ones, no console.log in a test


@needs_grammars
def test_python_and_javascript_are_scored_together(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    (project / "tool.py").write_text(PROBLEM_PY)
    assert analyze(monkeypatch, "-o", "-a", "robustness") == ExitCode.OK
    paths = {f["location"]["file_path"] for f in findings(project)}
    assert any(p.endswith("tool.py") for p in paths)
    assert "src/app.js" in paths


@needs_grammars
def test_a_javascript_only_project_gets_every_analyzer_score(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    assert analyze(monkeypatch, "-o") == ExitCode.OK
    out = capsys.readouterr().out
    for name in ("robustness", "maintainability", "observability", "readability"):
        assert name in out
    assert "final score" in out


# ----------------------------------------------------------------------- Java

PROBLEM_JAVA = (
    "package demo;\n\n"
    "class Service {\n"
    "  boolean same(String a) {\n"
    "    try {\n"
    "      Runtime.getRuntime().exec(a);\n"
    "    } catch (Exception e) {}\n"
    '    System.out.println("done");\n'
    '    return a == "yes";\n'
    "  }\n"
    "}\n"
)


@needs_grammars
def test_java_files_are_analyzed_with_the_same_analyzers(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    java = project / "src" / "main" / "java" / "demo"
    java.mkdir(parents=True)
    (java / "Service.java").write_text(PROBLEM_JAVA)
    (project / "target" / "classes").mkdir(parents=True)
    (project / "target" / "classes" / "Generated.java").write_text(PROBLEM_JAVA)
    assert analyze(monkeypatch, "-o", "--language", "java") == ExitCode.OK
    found = findings(project)
    rules = {(f["rule_id"], f["source_analyzer"]) for f in found}
    assert ("ROB-UNSAFE-EXEC", "robustness") in rules
    assert ("ROB-EMPTY-CATCH", "robustness") in rules
    assert ("ROB-CATCH-GENERIC", "robustness") in rules
    assert ("ROB-STRING-EQUALITY", "robustness") in rules
    assert ("OBS-PRINT-LOGGING", "observability") in rules
    paths = {f["location"]["file_path"] for f in found}
    assert paths == {"src/main/java/demo/Service.java"}  # nothing from target/


@needs_grammars
def test_java_test_classes_are_exempt_from_the_noisy_rules(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tests = project / "src" / "test" / "java" / "demo"
    tests.mkdir(parents=True)
    (tests / "ServiceTest.java").write_text(
        'class ServiceTest {\n  void t() { System.out.println("x"); e.printStackTrace(); }\n}\n'
    )
    assert analyze(monkeypatch, "-o", "--language", "java") == ExitCode.OK
    assert not any(
        f["rule_id"] in ("OBS-PRINT-LOGGING", "OBS-PRINT-STACKTRACE")
        for f in findings(project)
    )


@needs_grammars
def test_paths_stay_relative_when_the_folder_is_reached_through_a_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """macOS /tmp is a symlink to /private/tmp; the names in findings must not become ../../../private/..."""
    real = tmp_path / "real"
    (real / "src").mkdir(parents=True)
    (real / ".git").mkdir()
    (real / "src" / "app.js").write_text(PROBLEM_JS)
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv", ["gnost", "analyze", str(link), "--no-progress", "--quiet", "-o"]
    )
    assert int(app.main()) == ExitCode.OK
    report = json.loads(
        (real / ".gnost" / "analysis" / "analysis.json").read_text(encoding="utf-8")
    )
    paths = {f["location"]["file_path"] for f in report["findings"]}
    assert paths == {"src/app.js"}
