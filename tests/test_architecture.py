"""Architecture rules: path patterns, the two rule kinds, config parsing, onboard and `gnost changes`."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import jsonschema
import pytest

from gitrepo import make_repo
from gnost.changes.analyzer import ChangeAnalyzer
from gnost.changes.refs import RefRange
from gnost.changes.snapshot import ProjectSnapshot
from gnost.cli.commands.changes import ChangesCommand
from gnost.cli.commands.onboard import run
from gnost.config.settings import ConfigError, GnostConfig, _validate
from gnost.core.architecture import (
    ArchitectureChecker,
    ArchitectureSettings,
    ForbiddenImportRule,
    LayerOrderRule,
    PathPatterns,
    Violation,
    relative_to,
)
from gnost.reporters.insights_json import SCHEMA_PATH
from gnost.vcs.git import GitRepository

needs_git = pytest.mark.skipif(
    shutil.which("git") is None, reason="git is not installed"
)
D1, D2 = "2026-01-01T10:00:00+00:00", "2026-01-02T10:00:00+00:00"


# ------------------------------------------------------------------- patterns


@pytest.mark.parametrize(
    "pattern, path, expected",
    [
        ("db", "src/db/user.py", True),  # a folder name matches anywhere
        ("db", "src/dbx/user.py", False),
        ("db", "db.py", False),  # the file's own name is not a folder
        ("src/api/**", "src/api/routes/a.py", True),
        ("src/api/**", "src/apix/a.py", False),
        ("src/api", "src/api/a.py", True),  # a path prefix
        ("**/models/*.py", "src/app/models/user.py", True),
        ("*.generated.ts", "src/a.generated.ts", True),
    ],
)
def test_path_patterns(pattern: str, path: str, expected: bool) -> None:
    assert PathPatterns([pattern]).matches(path) is expected


# ---------------------------------------------------------------------- rules


def test_forbidden_import_with_an_exception() -> None:
    rule = ForbiddenImportRule(
        "no db in api", ["src/api/**"], ["src/db/**"], allow=["src/db/models/**"]
    )
    assert rule.violation("src/api/a.py", "src/db/conn.py")
    assert not rule.violation("src/api/a.py", "src/db/models/user.py")  # allowed
    assert not rule.violation("src/service/a.py", "src/db/conn.py")  # not a source
    assert not rule.violation("src/api/a.py", "src/api/b.py")


def test_layer_order_flags_only_upward_imports() -> None:
    rule = LayerOrderRule(["api", "service", "db"])
    assert rule.violation(
        "src/db/a.py", "src/service/b.py"
    )  # a lower layer imports a higher one
    assert rule.violation("src/service/a.py", "src/api/b.py")
    assert not rule.violation("src/api/a.py", "src/db/b.py")  # downward is fine
    assert not rule.violation("src/service/a.py", "src/service/b.py")  # same layer
    assert not rule.violation("src/util/a.py", "src/api/b.py")  # not in a layer
    assert "which is a layer above it" in rule.violation("src/db/a.py", "src/api/b.py")


def test_compare_uses_renames_so_a_move_is_not_new_and_fixed() -> None:
    old = [Violation("r", "a.py", "b.py")]
    moved = [Violation("r", "c.py", "b.py")]
    new, fixed = ArchitectureChecker.compare(old, moved, renamed={"a.py": "c.py"})
    assert new == [] and fixed == []
    new, fixed = ArchitectureChecker.compare(old, moved, renamed={})
    assert len(new) == 1 and len(fixed) == 1


def test_a_new_kind_of_rule_needs_no_change_to_the_checker(tmp_path: Path) -> None:
    from gnost.core.architecture import ArchitectureRule

    class NoFixtures(ArchitectureRule):
        name = "no fixtures in production"

        def violation(self, source: str, target: str) -> str:
            return (
                "imports a fixture"
                if "fixtures/" in target and "fixtures/" not in source
                else ""
            )

    (tmp_path / "app.py").write_text("import fixtures.helper\n")
    (tmp_path / "fixtures").mkdir()
    (tmp_path / "fixtures" / "helper.py").write_text("X = 1\n")
    snap = ProjectSnapshot.scan_folder(str(tmp_path))
    found = ArchitectureChecker([NoFixtures()]).check(
        snap.graph, relative_to(str(tmp_path))
    )
    assert [(v.source, v.target) for v in found] == [("app.py", "fixtures/helper.py")]


# --------------------------------------------------------------------- config


def settings(raw: dict) -> ArchitectureSettings:
    config = GnostConfig()
    _validate({"architecture": raw}, config)
    return config.architecture_settings()


def test_the_architecture_table_becomes_rule_objects() -> None:
    built = settings(
        {
            "layers": ["api", "service", "db"],
            "fail": True,
            "rules": [
                {"name": "x", "from": "src/api/**", "must_not_import": ["src/db/**"]},
                {"from": ["a/**", "b/**"], "must_not_import": ["c"], "allow": ["c/ok"]},
            ],
        }
    )
    assert built.configured and built.fail and built.layers == ("api", "service", "db")
    assert [r.name for r in built.forbidden] == ["x", "rule 2"]
    assert built.forbidden[1].sources == ("a/**", "b/**")
    assert len(built.rules()) == 3  # two explicit rules and the layer order


def test_no_architecture_table_means_nothing_is_checked() -> None:
    assert not ArchitectureSettings().configured
    assert ArchitectureSettings().rules() == []


@pytest.mark.parametrize(
    "raw, message",
    [
        ({"layers": ["api", "api"]}, "lists a layer twice"),
        ({"layers": [""]}, "must be a list of folder names"),
        ({"rules": [{"must_not_import": ["x"]}]}, "needs 'from'"),
        ({"rules": [{"from": "a"}]}, "needs 'must_not_import'"),
        ({"rules": [{"from": "a", "must_not_import": "x"}]}, "must be a list of paths"),
        ({"rules": ["not a table"]}, "must be a table"),
        ({"fail": "yes"}, "must be true or false"),
    ],
)
def test_bad_architecture_config_names_the_problem(raw: dict, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        settings(raw)


def test_an_unknown_key_in_a_rule_is_a_warning() -> None:
    config = GnostConfig()
    _validate(
        {
            "architecture": {
                "rules": [{"from": "a", "must_not_import": ["b"], "frm": "x"}]
            }
        },
        config,
    )
    assert any("frm" in w for w in config.warnings)


# --------------------------------------------------------------------- onboard


def project(root: Path, files: dict) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root


LAYERED = {
    "app/api/routes.py": "from app.service import logic\n",
    "app/service/logic.py": "from app.db import repo\n",
    "app/db/repo.py": "from app.api import routes\n",  # a lower layer imports the top one
}


def test_onboard_reports_violations_in_the_guide_and_the_json(tmp_path: Path) -> None:
    root = project(tmp_path / "p", LAYERED)
    run(
        path=str(root),
        architecture=ArchitectureSettings(layers=("api", "service", "db")),
    )
    guide = (root / ".gnost" / "ONBOARD.md").read_text(encoding="utf-8")
    assert "## Architecture rules" in guide and "1 imports break the rules" in guide
    assert "`app/db/repo.py` | `app/api/routes.py`" in guide
    payload = json.loads(
        (root / ".gnost" / "insights.json").read_text(encoding="utf-8")
    )
    assert payload["architecture"]["configured"] is True
    assert payload["architecture"]["violations"][0]["rule"] == "layers"
    jsonschema.validate(payload, json.load(open(SCHEMA_PATH)))


def test_onboard_says_when_all_rules_pass_and_stays_silent_without_rules(
    tmp_path: Path,
) -> None:
    clean = project(
        tmp_path / "clean",
        {"app/api/a.py": "from app.db import b\n", "app/db/b.py": "X = 1\n"},
    )
    run(path=str(clean), architecture=ArchitectureSettings(layers=("api", "db")))
    assert "All 1 rules pass" in (clean / ".gnost" / "ONBOARD.md").read_text(
        encoding="utf-8"
    )
    none = project(tmp_path / "none", LAYERED)
    run(path=str(none))
    assert "Architecture rules" not in (none / ".gnost" / "ONBOARD.md").read_text(
        encoding="utf-8"
    )
    payload = json.loads(
        (none / ".gnost" / "insights.json").read_text(encoding="utf-8")
    )
    assert payload["architecture"]["configured"] is False


# --------------------------------------------------------------------- changes

CONFIG = (
    'layers = ["api", "db"]\n'.join(["[architecture]\n", ""])
    if False
    else ('[architecture]\nlayers = ["api", "db"]\n')
)


def build(tmp_path: Path, extra: str = "") -> Path:
    base = {
        ".gnost.toml": CONFIG + extra,
        "app/api/a.py": "from app.db import b\n",
        "app/db/b.py": "X = 1\n",
    }
    return make_repo(
        tmp_path / "r",
        [
            ("Ada", base, D1),
            (
                "Ada",
                {"app/db/b.py": "from app.api import a\nX = 1\n"},
                D2,
            ),  # db now imports api
        ],
    )


def analyze_changes(root: Path, **kwargs) -> object:
    repo = GitRepository.containing(str(root))
    arch = ArchitectureSettings(layers=("api", "db"))
    return ChangeAnalyzer(repo, str(root), architecture=arch, **kwargs).analyze(
        RefRange.parse("HEAD~1", repo)
    )


@needs_git
def test_changes_lists_the_violation_the_change_adds(tmp_path: Path) -> None:
    report = analyze_changes(build(tmp_path))
    change = report.architecture
    assert change.configured and change.compared
    assert [(v["source"], v["target"]) for v in change.new] == [
        ("app/db/b.py", "app/api/a.py")
    ]
    assert change.fixed == [] and change.total == 1
    from gnost.changes.render import MarkdownRenderer, TextRenderer

    assert (
        "Breaks `layers`: `app/db/b.py` imports `app/api/a.py`"
        in MarkdownRenderer().render(report)
    )
    assert "Architecture rules broken by this change" in TextRenderer().render(report)
    assert report.to_dict()["architecture"]["new"][0]["rule"] == "layers"


@needs_git
def test_changes_without_the_base_scan_lists_violations_in_changed_files(
    tmp_path: Path,
) -> None:
    report = analyze_changes(build(tmp_path), compare_base=False)
    assert report.architecture.compared is False
    assert len(report.architecture.new) == 1


@needs_git
def test_a_fixed_violation_is_reported_as_fixed(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path / "r",
        [
            (
                "Ada",
                {
                    "app/api/a.py": "X = 1\n",
                    "app/db/b.py": "from app.api import a\n",  # already broken
                },
                D1,
            ),
            ("Ada", {"app/db/b.py": "Y = 2\n"}, D2),
        ],
    )
    report = analyze_changes(root)
    assert report.architecture.new == []
    assert [(v["source"], v["target"]) for v in report.architecture.fixed] == [
        ("app/db/b.py", "app/api/a.py")
    ]


@needs_git
def test_the_gate_exits_3_with_the_flag_or_the_config_and_0_without(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    root = build(tmp_path)
    assert ChangesCommand(str(root), "HEAD~1", output_format="json").run() == 0
    assert ChangesCommand(str(root), "HEAD~1", fail_on_violations=True).run() == 3
    assert "architecture" in capsys.readouterr().err
    configured = build(tmp_path / "c", extra="fail = true\n")
    assert ChangesCommand(str(configured), "HEAD~1").run() == 3


@needs_git
def test_a_change_that_adds_nothing_passes_the_gate(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path / "r",
        [
            (
                "Ada",
                {
                    ".gnost.toml": CONFIG,
                    "app/api/a.py": "X = 1\n",
                    "app/db/b.py": "Y = 1\n",
                },
                D1,
            ),
            (
                "Ada",
                {"app/api/a.py": "from app.db import b\n"},
                D2,
            ),  # downward: allowed
        ],
    )
    assert ChangesCommand(str(root), "HEAD~1", fail_on_violations=True).run() == 0
    assert os.path.isfile(root / ".gnost" / "changes" / "changes.md")
