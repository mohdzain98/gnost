"""Change hotspots: parsing git log, ranking, collecting from real repositories, and the report."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

from typing import Callable, Dict, Tuple

import pytest

from gitrepo import make_repo
from gnost.cli.commands.onboard import run
from gnost.config.settings import ConfigError, GnostConfig, _validate
from gnost.vcs.git import GitRunner
from gnost.vcs.history import (
    FIELD,
    RECORD,
    ChangeHistory,
    ChangeRanker,
    FileChange,
    HistoryReader,
    HistorySettings,
    LogParser,
    Reason,
    Signal,
)

needs_git = pytest.mark.skipif(
    not GitRunner().available(), reason="git is not installed"
)

NOW = 1_800_000_000  # a fixed "today" for parsing tests
DAY = 86400


def record(author: str, when: int, *lines: str) -> str:
    return f"{RECORD}abc{FIELD}{author}{FIELD}{when}\n\n" + "\n".join(lines) + "\n"


# ------------------------------------------------------------------ parsing


def test_counts_authors_recent_changes_and_lines() -> None:
    log = record("Ada", NOW - DAY, "10\t2\ta.py", "1\t0\tb.py") + record(
        "Grace", NOW - 200 * DAY, "5\t5\ta.py"
    )
    h = LogParser(HistorySettings(), NOW).parse(log)
    a = h.files["a.py"]
    assert (a.commits, a.author_count, a.recent_commits, a.added, a.removed) == (
        2,
        2,
        1,
        15,
        7,
    )
    assert h.files["b.py"].commits == 1 and h.commits == 2
    assert a.last_changed == NOW - DAY


def test_binary_files_count_as_changes_with_no_lines() -> None:
    h = LogParser(HistorySettings(), NOW).parse(record("Ada", NOW, "-\t-\timage.png"))
    assert h.files["image.png"].commits == 1 and h.files["image.png"].added == 0


def test_a_renamed_file_keeps_its_history_under_the_new_name() -> None:
    # Newest commit first: the rename happened in the middle of the history.
    log = (
        record("Ada", NOW - 1 * DAY, "3\t1\tsrc/new_name.py")
        + record("Grace", NOW - 2 * DAY, "0\t0\tsrc/{old_name.py => new_name.py}")
        + record("Linus", NOW - 3 * DAY, "9\t0\tsrc/old_name.py")
    )
    h = LogParser(HistorySettings(), NOW).parse(log)
    assert list(h.files) == ["src/new_name.py"]
    assert h.files["src/new_name.py"].commits == 3
    assert h.files["src/new_name.py"].author_count == 3


def test_both_rename_forms_are_understood() -> None:
    log = record("Ada", NOW, "0\t0\tx.py => y.py") + record(
        "Ada", NOW - DAY, "1\t0\tx.py"
    )
    h = LogParser(HistorySettings(), NOW).parse(log)
    assert list(h.files) == ["y.py"] and h.files["y.py"].commits == 2
    log = record("Ada", NOW, "0\t0\t{a => b}/f.py") + record(
        "Ada", NOW - DAY, "1\t0\ta/f.py"
    )
    h = LogParser(HistorySettings(), NOW).parse(log)
    assert list(h.files) == ["b/f.py"] and h.files["b/f.py"].commits == 2


def test_bots_and_giant_commits_are_left_out() -> None:
    many = [f"1\t0\tf{i}.py" for i in range(10)]
    log = (
        record("dependabot[bot]", NOW, "1\t1\tpom.xml")
        + record("renovate-bot", NOW, "1\t1\tpackage.json")
        + record("Ada", NOW, *many)  # a "mass reformat"
        + record("Ada", NOW, "2\t0\treal.py")
    )
    h = LogParser(HistorySettings(max_files_per_commit=5), NOW).parse(log)
    assert list(h.files) == ["real.py"]
    assert h.commits == 1 and h.skipped_commits == 3


def test_junk_records_are_ignored() -> None:
    log = (
        "garbage\n" + RECORD + "not enough fields\n" + record("Ada", NOW, "1\t0\ta.py")
    )
    assert list(LogParser(HistorySettings(), NOW).parse(log).files) == ["a.py"]


# ------------------------------------------------------------------ ranking


def _history(spec: Dict[str, Tuple[int, int, int]]) -> ChangeHistory:
    """spec: {path: (commits, recent, authors)}"""
    text = ""
    for path, (commits, recent, authors) in spec.items():
        for i in range(commits):
            who = f"author{i % authors}"
            when = NOW - (i * 3 * DAY if i < recent else 300 * DAY + i)
            text += record(who, when, f"1\t0\t{path}")
    return LogParser(HistorySettings(), NOW).parse(text)


def test_ranking_prefers_frequent_recent_and_shared_files() -> None:
    h = _history(
        {
            "hot.py": (10, 8, 4),
            "warm.py": (5, 2, 2),
            "cold.py": (2, 0, 1),
            "once.py": (1, 1, 1),
        }
    )
    ranked = ChangeRanker(HistorySettings()).rank(h)
    assert [r.change.path for r in ranked] == [
        "hot.py",
        "warm.py",
        "cold.py",
    ]  # once.py needs 2 changes
    assert ranked[0].score > ranked[1].score > ranked[2].score
    assert all(0 <= r.score <= 100 for r in ranked)


def test_a_new_signal_is_added_without_touching_the_ranker() -> None:
    class LinesSignal(Signal):
        weight = 100.0  # dominates the others

        def value(self, change: FileChange) -> int:
            return change.added

    spec = {"many_commits.py": (6, 3, 2), "big_edit.py": (3, 1, 1)}
    h = _history(spec)
    h.files["big_edit.py"].added = 5000
    default = [r.change.path for r in ChangeRanker(HistorySettings()).rank(h)]
    custom = ChangeRanker(
        HistorySettings(), signals=(*ChangeRanker.DEFAULT_SIGNALS, LinesSignal())
    ).rank(h)
    assert default[0] == "many_commits.py"
    assert custom[0].change.path == "big_edit.py"


def test_the_reader_works_from_a_fake_git_with_no_repository(tmp_path: Path) -> None:
    log = record("Ada", NOW - DAY, "4\t1\ta.py") + record(
        "Grace", NOW - 2 * DAY, "2\t0\ta.py"
    )

    class FakeGit(GitRunner):
        def available(self) -> bool:
            return True

        def run(self, args, cwd, timeout=None, env=None) -> str:
            if args[0] == "rev-parse" and "--show-toplevel" in args:
                return str(tmp_path) + "\n"
            if args[0] == "rev-parse":
                return "false\n"
            if args[0] == "rev-list":
                return "2\n"
            return log

    reader = HistoryReader(
        HistorySettings(), runner=FakeGit(), clock=lambda: float(NOW)
    )
    insights = reader.analyze(str(tmp_path), {"a.py"})
    assert insights.history.available and insights.hotspots[0].change.commits == 2


def test_ties_are_broken_the_same_way_every_time() -> None:
    h = _history({"b.py": (3, 1, 1), "a.py": (3, 1, 1), "c.py": (3, 1, 1)})
    first = [r.change.path for r in ChangeRanker(HistorySettings()).rank(h)]
    assert first == ["a.py", "b.py", "c.py"]
    assert first == [r.change.path for r in ChangeRanker(HistorySettings()).rank(h)]


def test_ranking_can_be_limited_to_files_that_still_exist() -> None:
    h = _history({"gone.py": (9, 9, 3), "here.py": (3, 1, 1)})
    ranked = ChangeRanker(HistorySettings()).rank(h, {"here.py"})
    assert [r.change.path for r in ranked] == ["here.py"]


# ------------------------------------------------------------ real repositories

T = lambda d: f"2026-{d}T10:00:00+00:00"  # noqa: E731
TODAY = time.mktime(time.strptime("2026-06-30", "%Y-%m-%d"))


@needs_git
def test_a_real_repository_is_read_with_authors_and_a_window(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "r",
        [
            (
                "Old Timer",
                {"old.py": "1\n"},
                "2024-01-01T10:00:00+00:00",
            ),  # outside the window
            ("Ada", {"a.py": "1\n", "b.py": "1\n"}, T("03-01")),
            ("Grace", {"a.py": "2\n"}, T("03-15")),
            ("Ada", {"a.py": "3\n", "b.py": "2\n"}, T("06-20")),
        ],
    )
    h = HistoryReader(HistorySettings(), clock=lambda: TODAY).read(str(repo))
    assert h.available and h.commits == 3
    assert "old.py" not in h.files
    a = h.files["a.py"]
    assert (a.commits, a.author_count, a.recent_commits) == (3, 2, 1)
    assert h.files["b.py"].commits == 2


@needs_git
def test_a_moved_file_and_a_deleted_file(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "r",
        [
            ("Ada", {"keep.py": "x = 1\n" * 20, "gone.py": "y = 1\n"}, T("01-10")),
            ("Ada", {"keep.py": "x = 2\n" * 20}, T("02-10")),
        ],
    )
    subprocess.run(["git", "mv", "keep.py", "moved.py"], cwd=repo, check=True)
    subprocess.run(["git", "rm", "-q", "gone.py"], cwd=repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Ada",
            "-c",
            "user.email=a@example.com",
            "commit",
            "-q",
            "-m",
            "move",
        ],
        cwd=repo,
        check=True,
        env={
            **__import__("os").environ,
            "GIT_AUTHOR_DATE": T("03-10"),
            "GIT_COMMITTER_DATE": T("03-10"),
        },
    )
    changes = HistoryReader(HistorySettings(), clock=lambda: TODAY).analyze(
        str(repo), {"moved.py"}
    )
    assert [h.change.path for h in changes.hotspots] == ["moved.py"]
    assert changes.hotspots[0].change.commits == 3  # created, edited, moved


@needs_git
def test_mailmap_merges_one_person_with_two_names(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "r",
        [
            ("Ada L", {"a.py": "1\n"}, T("03-01")),
            ("Ada Lovelace", {"a.py": "2\n"}, T("04-01")),
        ],
    )
    (repo / ".mailmap").write_text(
        "Ada Lovelace <ada.lovelace@example.com> Ada L <ada.l@example.com>\n"
    )
    h = HistoryReader(HistorySettings(), clock=lambda: TODAY).read(str(repo))
    assert h.files["a.py"].author_count == 1


@needs_git
def test_a_subfolder_is_read_with_paths_relative_to_it(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "r",
        [
            ("Ada", {"service/a.py": "1\n", "other/z.py": "1\n"}, T("03-01")),
            ("Ada", {"service/a.py": "2\n", "other/z.py": "2\n"}, T("04-01")),
        ],
    )
    h = HistoryReader(HistorySettings(), clock=lambda: TODAY).read(
        str(repo / "service")
    )
    assert list(h.files) == ["a.py"] and h.files["a.py"].commits == 2


@needs_git
def test_every_reason_history_is_missing_is_reported(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    h = HistoryReader(HistorySettings()).read(str(plain))
    assert not h.available and h.reason_kind == Reason.NOT_A_REPO

    empty = tmp_path / "empty"
    empty.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=empty, check=True)
    assert HistoryReader(HistorySettings()).read(str(empty)).reason_kind == Reason.EMPTY

    origin = make_repo(
        tmp_path / "origin",
        [("Ada", {"a.py": "1\n"}, T("03-01")), ("Ada", {"a.py": "2\n"}, T("04-01"))],
    )
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", origin.resolve().as_uri(), str(clone)],
        check=True,
        capture_output=True,
    )
    h = HistoryReader(HistorySettings(), clock=lambda: TODAY).read(str(clone))
    assert h.reason_kind == Reason.SHALLOW and "fetch-depth: 0" in h.reason

    off = HistoryReader(HistorySettings(enabled=False)).read(str(origin))
    assert not off.available and off.reason_kind == "disabled"


def test_missing_git_is_silent_for_plain_folders_and_loud_for_repositories(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    plain = tmp_path / "plain"
    plain.mkdir()
    changes = HistoryReader(HistorySettings()).analyze(str(plain), set())
    assert not changes.history.available and not changes.note_worth_showing
    (tmp_path / ".git").mkdir()
    changes = HistoryReader(HistorySettings()).analyze(str(tmp_path), set())
    assert changes.note_worth_showing and "Install git" in changes.history.reason


# --------------------------------------------------------------- the reports

APP = {
    "main.py": "from app import service\n\nif __name__ == '__main__':\n    service.run()\n",
    "app/__init__.py": "",
    "app/service.py": "def run():\n    return 1\n",
    "app/util.py": "def helper():\n    return 2\n",
}


def _app_repo(tmp_path: Path) -> Path:
    commits = [("Ada", APP, T("01-05"))]
    for i, (who, when) in enumerate(
        [("Grace", T("02-05")), ("Linus", T("03-05")), ("Ada", T("06-25"))]
    ):
        commits.append(
            (who, {"app/service.py": f"def run():\n    return {i + 10}\n"}, when)
        )
    commits.append(
        ("Ada", {"app/util.py": "def helper():\n    return 3\n"}, T("06-26"))
    )
    return make_repo(tmp_path / "proj", commits)


@needs_git
def test_onboard_reports_change_hotspots_in_markdown_json_and_terminal(
    tmp_path, capsys
):
    repo = _app_repo(tmp_path)
    run(
        path=str(repo), history=HistorySettings(days=36500)
    )  # the fixed dates are old, so look back far
    out = capsys.readouterr().out
    md = (repo / ".gnost" / "ONBOARD.md").read_text(encoding="utf-8")
    assert "## Change Hotspots" in md
    row = next(
        line for line in md.splitlines() if line.startswith("| `app/service.py`")
    )
    assert "| 4 | 3 |" in row  # 4 commits by 3 people
    assert md.index("`app/service.py`", md.index("## Change Hotspots")) < md.index(
        "`app/util.py`", md.index("## Change Hotspots")
    )
    assert "Change Hotspots" in out and "app/service.py" in out

    data = json.loads((repo / ".gnost" / "insights.json").read_text())
    assert data["schema_version"] == "1.5"
    ch = data["change_history"]
    assert ch["available"] is True and ch["files"][0]["path"] == "app/service.py"
    assert ch["files"][0]["commits"] == 4 and ch["files"][0]["authors"] == 3

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(Path("gnost/schemas/insights.schema.json").read_text())
    jsonschema.validate(data, schema)


@needs_git
def test_a_shallow_clone_says_why_there_are_no_hotspots(tmp_path: Path) -> None:
    origin = _app_repo(tmp_path)
    clone = tmp_path / "ci-checkout"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", origin.resolve().as_uri(), str(clone)],
        check=True,
        capture_output=True,
    )
    run(path=str(clone))
    md = (clone / ".gnost" / "ONBOARD.md").read_text(encoding="utf-8")
    assert (
        "## Change Hotspots" in md
        and "_Not available:" in md
        and "fetch-depth: 0" in md
    )
    data = json.loads((clone / ".gnost" / "insights.json").read_text())
    assert data["change_history"]["available"] is False
    assert "shallow" in data["change_history"]["reason"]


def test_a_folder_that_is_not_a_repository_has_no_section_and_valid_json(
    fixture_repo: Callable[[str], Path],
) -> None:
    root = fixture_repo("python_app")
    run(path=str(root))
    md = (root / ".gnost" / "ONBOARD.md").read_text(encoding="utf-8")
    assert "Change Hotspots" not in md
    data = json.loads((root / ".gnost" / "insights.json").read_text())
    assert data["change_history"]["available"] is False


# ------------------------------------------------------------------- config


def test_history_settings_come_from_the_config_over_the_defaults() -> None:
    config = GnostConfig()
    _validate({"history": {"days": 30, "exclude_authors": ["ci-*"], "top": 5}}, config)
    s = config.history_settings()
    assert (s.days, s.top, s.exclude_authors) == (30, 5, ("ci-*",))
    assert s.max_commits == HistorySettings().max_commits  # untouched


@pytest.mark.parametrize(
    "bad",
    [{"days": 0}, {"top": -1}, {"exclude_authors": [1, 2]}, {"days": "many"}],
)
def test_bad_history_settings_are_refused(bad: object) -> None:
    with pytest.raises(ConfigError):
        _validate({"history": bad}, GnostConfig())


def test_the_window_start_is_an_exact_timestamp_and_absent_for_a_huge_window() -> None:
    reader = HistoryReader(HistorySettings(days=10))
    assert f"--max-age={NOW - 10 * DAY}" in reader._log_command(float(NOW))
    forever = HistoryReader(HistorySettings(days=36500))._log_command(float(NOW))
    assert not any(a.startswith(("--max-age", "--since")) for a in forever)
