"""Tests for `gnost changes`: ref parsing, the diff, blast radius, cycles, routes and output."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from gitrepo import make_repo
from gnost.changes.analyzer import ChangeAnalyzer
from gnost.changes.refs import DiffReader, RefError, RefRange
from gnost.changes.render import COMMENT_MARKER, MarkdownRenderer, TextRenderer
from gnost.cli.commands.changes import ChangesCommand
from gnost.vcs.git import GitRepository

needs_git = pytest.mark.skipif(
    shutil.which("git") is None, reason="git is not installed"
)
D1, D2, D3 = (
    "2026-01-01T10:00:00+00:00",
    "2026-01-02T10:00:00+00:00",
    "2026-01-03T10:00:00+00:00",
)

BASE = {
    "app/__init__.py": "",
    "app/a.py": "from app import b\n",
    "app/b.py": "from app import c\n",
    "app/c.py": "VALUE = 1\n",
    "app/old.py": "X = 1\n",
    "app/user.py": "from app import old\n",
}


def build(tmp_path: Path) -> Path:
    """base commit, then a commit that edits c, adds a cycle, renames and deletes."""
    return make_repo(
        tmp_path / "r",
        [
            ("Ada", BASE, D1),
            (
                "Ada",
                {
                    "app/c.py": "from app import a\nVALUE = 2\n",  # a -> b -> c -> a
                    "app/new.py": "Y = 1\n",
                    "app/old.py": None,
                    "app/user.py": "VALUE = 3\n",
                },
                D2,
            ),
        ],
    )


def analyze(root: Path, refs: str = "HEAD~1", **kwargs) -> "object":
    repo = GitRepository.containing(str(root))
    assert repo is not None
    return ChangeAnalyzer(repo, str(root), **kwargs).analyze(RefRange.parse(refs, repo))


@needs_git
def test_ranges_parse_two_and_three_dots_and_default_head(tmp_path: Path) -> None:
    repo = GitRepository.containing(str(build(tmp_path)))
    one = RefRange.parse("HEAD~1", repo)
    assert one.head == "HEAD" and one.label == "HEAD~1..HEAD"
    assert RefRange.parse("HEAD~1...HEAD", repo) == one
    assert RefRange.parse("HEAD~1..HEAD", repo).base_commit == one.base_commit


@needs_git
def test_unknown_and_empty_refs_give_a_clear_error(tmp_path: Path) -> None:
    repo = GitRepository.containing(str(build(tmp_path)))
    with pytest.raises(RefError, match="unknown ref `nope`"):
        RefRange.parse("nope", repo)
    with pytest.raises(RefError, match="give a base ref"):
        RefRange.parse("..HEAD", repo)
    with pytest.raises(RefError):
        RefRange.parse("--output=x", repo)


@needs_git
def test_changed_files_are_grouped_by_status(tmp_path: Path) -> None:
    root = build(tmp_path)
    repo = GitRepository.containing(str(root))
    files = DiffReader(repo).read(RefRange.parse("HEAD~1", repo), str(root))
    status = {f.path: f.status for f in files}
    assert status == {
        "app/c.py": "modified",
        "app/new.py": "added",
        "app/old.py": "deleted",
        "app/user.py": "modified",
    }


@needs_git
def test_a_rename_keeps_the_old_name(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path / "r",
        [
            ("Ada", {"a.py": "x = 1\n" * 30}, D1),
            ("Ada", {"a.py": None, "b.py": "x = 1\n" * 30}, D2),
        ],
    )
    repo = GitRepository.containing(str(root))
    (change,) = DiffReader(repo).read(RefRange.parse("HEAD~1", repo), str(root))
    assert (change.status, change.path, change.old_path) == ("renamed", "b.py", "a.py")


@needs_git
def test_blast_radius_follows_importers_up_to_the_depth(tmp_path: Path) -> None:
    root = build(tmp_path)
    one = analyze(root, depth=1)
    assert [(a.path, a.depth) for a in one.affected if a.path.startswith("app/b")] == [
        ("app/b.py", 1)
    ]
    assert "app/a.py" not in {a.path for a in one.affected}
    three = analyze(root, depth=3)
    assert {a.path: a.depth for a in three.affected}["app/a.py"] == 2
    assert all(a.path not in {f.path for f in three.files} for a in three.affected)


@needs_git
def test_new_circular_dependency_is_found_against_the_base(tmp_path: Path) -> None:
    report = analyze(build(tmp_path))
    assert [c.files for c in report.new_cycles] == [
        ["app/a.py", "app/b.py", "app/c.py"]
    ]
    assert report.fixed_cycles == []
    skipped = analyze(build(tmp_path / "again"), compare_base=False)
    assert skipped.new_cycles == [] and not skipped.cycles_compared


@needs_git
def test_a_fixed_cycle_is_reported(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path / "r",
        [
            ("Ada", {"a.py": "import b\n", "b.py": "import a\n"}, D1),
            ("Ada", {"b.py": "X = 1\n"}, D2),
        ],
    )
    report = analyze(root)
    assert [c.files for c in report.fixed_cycles] == [["a.py", "b.py"]]


@needs_git
def test_dependents_of_a_deleted_file_are_still_affected(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path / "r",
        [
            (
                "Ada",
                {"lib.py": "X = 1\n", "use.py": "import lib\n", "ok.py": "Y = 1\n"},
                D1,
            ),
            ("Ada", {"lib.py": None}, D2),
        ],
    )
    report = analyze(root)
    assert [(a.path, a.via) for a in report.affected] == [("use.py", "lib.py")]


FLASK = (
    "from flask import Flask\napp = Flask(__name__)\n\n"
    "@app.route('/ping')\ndef ping():\n    return 'ok'\n"
)


@needs_git
def test_routes_added_and_removed_are_listed(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path / "r",
        [
            ("Ada", {"old_api.py": FLASK.replace("/ping", "/old")}, D1),
            ("Ada", {"old_api.py": None, "api.py": FLASK}, D2),
        ],
    )
    report = analyze(root)
    states = {(r.path, r.state) for r in report.routes}
    assert ("/ping", "added") in states and ("/old", "removed") in states


@needs_git
def test_the_working_tree_is_not_touched(tmp_path: Path) -> None:
    root = build(tmp_path)
    before = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, capture_output=True
    ).stdout
    analyze(root)
    after = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, capture_output=True
    ).stdout
    assert before == after == b""
    assert not [p for p in os.listdir(root) if p.startswith("gnost-base")]


@needs_git
def test_renderers_show_the_marker_footer_and_counts(tmp_path: Path) -> None:
    report = analyze(build(tmp_path))
    md = MarkdownRenderer().render(report)
    assert md.startswith(COMMENT_MARKER) and "Generated by [GNOST]" in md
    assert "New circular dependency" in md and "`app/c.py`" in md
    text = TextRenderer().render(report)
    assert "4 files (1 added, 2 modified, 1 deleted, 0 renamed)" in text
    data = report.to_dict()
    assert data["schema_version"] == "1.0" and data["counts"]["deleted"] == 1
    assert data["cycles"]["new"][0]["files"] == ["app/a.py", "app/b.py", "app/c.py"]


@needs_git
def test_the_command_writes_files_and_prints_json(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    root = build(tmp_path)
    code = ChangesCommand(str(root), "HEAD~1", output_format="json").run()
    out = capsys.readouterr().out
    assert code == 0 and json.loads(out)["range"]["base"] == "HEAD~1"
    assert (root / ".gnost" / "changes" / "changes.md").is_file()
    assert (
        json.loads((root / ".gnost" / "changes" / "changes.json").read_text())[
            "counts"
        ]["added"]
        == 1
    )


@needs_git
def test_the_command_exit_codes_for_mistakes(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    root = build(tmp_path)
    assert ChangesCommand(str(root), "nope").run() == 2
    assert "unknown ref" in capsys.readouterr().err
    plain = tmp_path / "plain"
    plain.mkdir()
    assert ChangesCommand(str(plain), "main").run() == 2
    assert "not inside a git repository" in capsys.readouterr().err
    assert ChangesCommand(str(root), "HEAD~1", depth=0).run() == 2


@needs_git
def test_a_subfolder_project_uses_paths_relative_to_it(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path / "r",
        [
            (
                "Ada",
                {
                    "svc/a.py": "import b\n",
                    "svc/b.py": "X = 1\n",
                    "other/z.py": "Z = 1\n",
                },
                D1,
            ),
            ("Ada", {"svc/b.py": "X = 2\n", "other/z.py": "Z = 2\n"}, D2),
        ],
    )
    repo = GitRepository.containing(str(root))
    sub = ChangeAnalyzer(repo, str(root / "svc")).analyze(
        RefRange.parse("HEAD~1", repo)
    )
    assert [f.path for f in sub.files] == ["b.py"]
    assert [a.path for a in sub.affected] == ["a.py"]
