"""The rule fixture contract: every rule has a bad and a good file per language, and fires exactly there.

`tests/fixtures/rules/<language>/<RULE-ID>.bad.<ext>` marks the expected lines with `// expect: ID` (or `/* expect: ID */`, for
rules about comments) on the line above (`// expect-file: ID` means line 1). The `.good.` file must produce no hit for the rule. A
language is supported only when every rule id registered for it has such a pair, so equivalent rules in
different languages are held to the same standard.
"""

from __future__ import annotations

import glob
import re
from pathlib import Path
from typing import List, Tuple

import pytest

from gnost.analysis.rules import RuleRegistry, RuleRunner, default_registry
from gnost.parsing import default_factory

FIXTURES = Path(__file__).parent / "fixtures" / "rules"
REGISTRY = default_registry()
EXPECT = re.compile(r"(?://|/\*)\s*expect:\s*([A-Z-]+)")
EXPECT_FILE = re.compile(r"//\s*expect-file:\s*([A-Z-]+)")
needs_grammars = pytest.mark.skipif(
    not default_factory().available("javascript"),
    reason="tree-sitter grammars are not installed",
)


def cases() -> List[Tuple[str, str]]:
    return [
        (language, rule_id)
        for language, ids in REGISTRY.ids_by_language().items()
        for rule_id in ids
    ]


def fixture(language: str, rule_id: str, kind: str) -> Path:
    found = sorted(glob.glob(str(FIXTURES / language / f"{rule_id}.{kind}.*")))
    assert found, f"missing {kind} fixture for {rule_id} in {language}"
    return Path(found[0])


def expected_lines(path: Path, rule_id: str) -> List[int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    wanted: List[int] = []
    for number, text in enumerate(lines, start=1):
        if EXPECT_FILE.search(text) and EXPECT_FILE.search(text).group(1) == rule_id:
            wanted.append(1)
        match = EXPECT.search(text)
        if match and match.group(1) == rule_id:
            wanted.append(number + 1)
    return sorted(wanted)


def hit_lines(path: Path, rule_id: str, analyzer: str) -> List[int]:
    run = RuleRunner(registry=REGISTRY).run([str(path)], analyzer, str(path.parent))
    return sorted(f.location.line_number for f in run.findings if f.rule_id == rule_id)


@needs_grammars
@pytest.mark.parametrize("language, rule_id", cases())
def test_the_bad_file_fires_on_the_marked_lines(language: str, rule_id: str) -> None:
    rule = next(r for r in REGISTRY.rules_for(language) if r.id == rule_id)
    bad = fixture(language, rule_id, "bad")
    expected = expected_lines(bad, rule_id)
    assert expected, f"{bad.name} has no expect marker"
    assert hit_lines(bad, rule_id, rule.analyzer) == expected


@needs_grammars
@pytest.mark.parametrize("language, rule_id", cases())
def test_the_good_file_stays_quiet(language: str, rule_id: str) -> None:
    rule = next(r for r in REGISTRY.rules_for(language) if r.id == rule_id)
    good = fixture(language, rule_id, "good")
    assert hit_lines(good, rule_id, rule.analyzer) == []


def test_every_language_has_a_fixture_pair_for_every_rule() -> None:
    for language, ids in REGISTRY.ids_by_language().items():
        for rule_id in ids:
            for kind in ("bad", "good"):
                fixture(language, rule_id, kind)


def test_typescript_has_every_javascript_rule_and_more() -> None:
    ids = REGISTRY.ids_by_language()
    assert set(ids["javascript"]) <= set(ids["typescript"])
    assert {"ROB-UNTYPED-ANY", "ROB-TS-SUPPRESS"} <= set(ids["typescript"]) - set(
        ids["javascript"]
    )


def test_rule_ids_are_unique_per_language_and_well_formed() -> None:
    for language, ids in REGISTRY.ids_by_language().items():
        assert len(ids) == len(set(ids)), language
        assert all(re.fullmatch(r"[A-Z]{3}-[A-Z-]+", i) for i in ids), language


def test_a_duplicate_rule_id_is_refused() -> None:
    registry = RuleRegistry()
    rule_class = type(REGISTRY.rules_for("javascript")[0])
    registry.register(rule_class())
    with pytest.raises(ValueError, match="duplicate rule id"):
        registry.register(rule_class())


def test_every_rule_says_what_to_do_about_it() -> None:
    for language in REGISTRY.languages():
        for rule in REGISTRY.rules_for(language):
            assert rule.title and rule.remediation and rule.analyzer, rule.id
            assert rule.analyzer in {
                "robustness",
                "maintainability",
                "observability",
                "readability",
            }, rule.id


# ------------------------------------------------------------- the parity contract

# The checks that mean the same thing in every language. A language is supported by `analyze` only when it
# has all of them (each with its own fixture pair, enforced above), so a score means the same everywhere.
CORE_IDS = {
    "ROB-EMPTY-CATCH",
    "MNT-COMPLEXITY",
    "MNT-LONG-FUNCTION",
    "MNT-LONG-FILE",
    "MNT-DEEP-NESTING",
    "MNT-MANY-PARAMS",
    "OBS-SWALLOWED-ERROR",
    "OBS-PRINT-LOGGING",
    "RDB-NAMING",
    "RDB-LONG-LINE",
    "RDB-COMMENTED-CODE",
    "RDB-TODO",
}


@pytest.mark.parametrize("language", ["javascript", "typescript", "java"])
def test_every_supported_language_has_every_core_rule(language: str) -> None:
    ids = set(REGISTRY.ids_by_language()[language])
    assert CORE_IDS <= ids, f"{language} is missing {sorted(CORE_IDS - ids)}"


def test_core_rules_use_the_same_severity_and_analyzer_in_every_language() -> None:
    """The same id must score the same, whatever language it is found in."""
    for rule_id in sorted(CORE_IDS):
        seen = {
            (r.analyzer, r.severity, r.category)
            for language in ("javascript", "typescript", "java")
            for r in REGISTRY.rules_for(language)
            if r.id == rule_id
        }
        assert len(seen) == 1, f"{rule_id} differs between languages: {seen}"


def test_every_analyzable_language_has_rules() -> None:
    from gnost.analysis.languages import AnalysisLanguages

    for name in AnalysisLanguages.names():
        if name != "python":  # Python is checked by mypy, bandit, radon and ruff
            assert name in REGISTRY.languages(), name
