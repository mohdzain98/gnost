"""Tests for the git layer: the runner, finding a repository and why history may be missing."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from gitrepo import make_repo
from gnost.vcs.git import GitError, GitRepository, GitRunner, GitUnavailable

pytestmark = pytest.mark.skipif(
    not GitRunner().available(), reason="git is not installed"
)

COMMITS = [
    ("Ada Lovelace", {"a.py": "x = 1\n"}, "2026-01-01T10:00:00+00:00"),
    (
        "Grace Hopper",
        {"a.py": "x = 2\n", "b/c.py": "y = 1\n"},
        "2026-02-01T10:00:00+00:00",
    ),
]


def test_a_repository_is_found_from_a_folder_inside_it(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", COMMITS)
    found = GitRepository.containing(str(repo / "b"))
    assert found is not None and found.root == str(repo.resolve())
    assert found.commit_count() == 2 and found.history_problem() is None


def test_a_folder_outside_any_repository(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    assert GitRepository.containing(str(plain)) is None


def test_an_empty_repository_has_no_history(tmp_path: Path) -> None:
    repo = tmp_path / "empty"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    found = GitRepository.containing(str(repo))
    assert found is not None and found.commit_count() == 0
    assert "no commits" in (found.history_problem() or "")


def test_a_shallow_clone_is_detected_with_advice(tmp_path: Path) -> None:
    origin = make_repo(tmp_path / "origin", COMMITS)
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", origin.resolve().as_uri(), str(clone)],
        check=True,
        capture_output=True,
    )
    shallow = GitRepository.containing(str(clone))
    assert shallow is not None and shallow.is_shallow()
    assert "fetch-depth: 0" in (shallow.history_problem() or "")
    full = GitRepository.containing(str(origin))
    assert full is not None and not full.is_shallow()


def test_missing_git_gives_a_clear_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(GitUnavailable) as err:
        GitRunner().run(["status"], str(tmp_path))
    assert "Install git" in str(err.value)
    with pytest.raises(GitUnavailable):
        GitRepository.containing(str(tmp_path))


def test_a_failing_command_raises_with_the_reason(tmp_path: Path) -> None:
    with pytest.raises(GitError) as err:
        GitRunner().run(["log", "--no-such-option"], str(tmp_path))
    assert "git log failed" in str(err.value)


def test_commits_use_the_dates_given(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "dated", COMMITS)
    found = GitRepository.containing(str(repo))
    assert found is not None
    out = found.run(["log", "--format=%an|%aI"]).strip().splitlines()
    assert out == [
        "Grace Hopper|2026-02-01T10:00:00Z",
        "Ada Lovelace|2026-01-01T10:00:00Z",
    ]


def test_the_runner_can_be_replaced_in_tests(tmp_path: Path) -> None:
    class Recorded(GitRunner):
        def __init__(self) -> None:
            super().__init__()
            self.calls: list = []

        def run(self, args, cwd, timeout=None, env=None) -> str:  # type: ignore[override]
            self.calls.append(args)
            return "false\n" if args[0] == "rev-parse" else "7\n"

    runner = Recorded()
    repo = GitRepository(str(tmp_path), runner)
    assert repo.commit_count() == 7 and not repo.is_shallow()
    assert runner.calls == [
        ["rev-list", "--count", "HEAD"],
        ["rev-parse", "--is-shallow-repository"],
    ]
