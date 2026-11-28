"""Tests for `gnost summary --git`: language shares counted the way GitHub's language bar does.

Each test builds a small git repository, commits it, and checks what is counted and what is
left out (vendored, documentation, generated, data and prose, .gitattributes overrides).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict

import pytest

from gnost.vcs.linguist import GitError, LinguistCounter

pytestmark = pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="needs git",
)


def _repo(root: Path, files: Dict[str, str]) -> None:
    """A repository with these files committed."""
    for path, text in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    env = dict(
        os.environ,
        GIT_AUTHOR_NAME="t",
        GIT_AUTHOR_EMAIL="t@t",
        GIT_COMMITTER_NAME="t",
        GIT_COMMITTER_EMAIL="t@t",
    )
    for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "x"]):
        subprocess.run(["git", *cmd], cwd=root, check=True, env=env)


def _shares(root: Path) -> Dict[str, int]:
    return {
        lang.name: lang.bytes for lang in LinguistCounter(str(root)).count().languages
    }


def test_only_programming_and_markup_files_are_counted(tmp_path: Path) -> None:
    _repo(
        tmp_path,
        {
            "app/main.py": "x" * 100,
            "app/page.html": "h" * 40,
            "app/ui.tsx": "t" * 10,
            "Dockerfile": "d" * 5,
            "data.json": "{}" * 50,  # data
            "notes.md": "n" * 70,  # prose
        },
    )
    assert _shares(tmp_path) == {"Python": 100, "HTML": 40, "TSX": 10, "Dockerfile": 5}


def test_vendored_documentation_and_generated_files_are_left_out(
    tmp_path: Path,
) -> None:
    _repo(
        tmp_path,
        {
            "src/app.py": "x" * 50,
            "src/vendor/lib.py": "v" * 500,
            "web/app.min.js": "m" * 500,
            "node_modules/pkg/index.js": "n" * 500,
            "tests/fixtures/sample.py": "f" * 500,
            "docs/conf.py": "c" * 500,
            "src/readme.py": "r" * 500,  # GitHub treats it as a README
            "src/changes.py": "k" * 30,  # but this one is code
            "api/service_pb2.py": "g" * 500,
        },
    )
    result = LinguistCounter(str(tmp_path)).count()
    assert {lang.name: lang.bytes for lang in result.languages} == {"Python": 80}
    assert result.skipped["vendored"] == 4 and result.skipped["documentation"] == 2
    assert result.skipped["generated"] == 1


def test_gitattributes_overrides_win(tmp_path: Path) -> None:
    _repo(
        tmp_path,
        {
            ".gitattributes": (
                "lib/** linguist-vendored\n"
                "vendor/** -linguist-vendored\n"
                "*.sql linguist-detectable\n"
                "*.inc linguist-language=PHP\n"
                "gen.py linguist-generated\n"
                "hidden.js -linguist-detectable\n"
            ),
            "main.py": "x" * 10,
            "lib/a.py": "l" * 100,
            "vendor/b.py": "v" * 20,
            "gen.py": "g" * 100,
            "page.inc": "p" * 7,
            "hidden.js": "j" * 100,
        },
    )
    assert _shares(tmp_path) == {"Python": 30, "PHP": 7}


def test_only_committed_files_count_and_shares_add_up(tmp_path: Path) -> None:
    _repo(tmp_path, {"a.py": "x" * 75, "b.js": "y" * 25})
    (tmp_path / "new.py").write_text("z" * 1000, encoding="utf-8")  # not committed
    result = LinguistCounter(str(tmp_path)).count()
    assert [(lang.name, round(lang.share)) for lang in result.languages] == [
        ("Python", 75),
        ("JavaScript", 25),
    ]
    assert result.total == 100


def test_a_subfolder_counts_only_its_files(tmp_path: Path) -> None:
    _repo(tmp_path, {"api/a.py": "x" * 10, "web/b.js": "y" * 10})
    assert _shares(tmp_path / "web") == {"JavaScript": 10}


def test_a_folder_outside_git_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(GitError):
        LinguistCounter(str(tmp_path)).count()


def test_summary_keeps_its_default_and_adds_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    import gnost.cli.app as app

    _repo(tmp_path, {"main.py": "print(1)\n", "vendor/x.py": "print(2)\n" * 50})
    monkeypatch.setattr("sys.argv", ["gnost", "summary", str(tmp_path)])
    assert app.main() == 0
    plain = capsys.readouterr().out
    assert "GNOST — Summary" in plain and "LOC" in plain
    monkeypatch.setattr("sys.argv", ["gnost", "summary", "--git", str(tmp_path)])
    assert app.main() == 0
    out = capsys.readouterr().out
    assert "GitHub" in out and "100.0%" in out and "1 vendored" in out


def test_summary_git_outside_a_repository_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    import gnost.cli.app as app

    monkeypatch.setattr("sys.argv", ["gnost", "summary", "--git", str(tmp_path)])
    assert app.main() == 2
    assert "needs a git repository" in capsys.readouterr().err
