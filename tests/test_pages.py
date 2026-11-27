"""`gnost onboard --pages`: where the explorer goes, never overwriting, the address and the CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pytest

import gnost.cli.app as app
from gnost.config.settings import ConfigError, GnostConfig, _validate
from gnost.reporters import pages as pages_module
from gnost.reporters.pages import (
    MARKER,
    GitHubRepo,
    PagesError,
    PagesPublisher,
    PagesRequest,
)
from gnost.vcs.git import GitError

PAGE = "<!doctype html>\n<html><body>explorer</body></html>\n"


class FakeRepository:
    """Answers the two git questions the publisher asks."""

    def __init__(self, answers: Dict[str, str]) -> None:
        self.answers = answers

    def run(self, args: List[str], cwd: Optional[str] = None) -> str:
        key = " ".join(args)
        if key not in self.answers:
            raise GitError(f"git {args[0]} failed")
        return self.answers[key]


GITHUB = FakeRepository(
    {
        "remote get-url origin": "git@github.com:Some-Owner/demo.git\n",
        "symbolic-ref --short refs/remotes/origin/HEAD": "origin/trunk\n",
    }
)


def publish(root: Path, folder: Optional[str] = None, repository=GITHUB):
    return PagesPublisher(str(root), folder, "--pages", repository).publish(PAGE)  # type: ignore[arg-type]


# ------------------------------------------------------------ where it goes


def test_without_a_site_the_explorer_is_the_home_page(tmp_path: Path) -> None:
    result = publish(tmp_path)
    page = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    assert result.path == "docs/index.html"
    assert page.startswith(f"<!doctype html>\n{MARKER}\n")  # marker after the doctype
    assert result.lines[0] == (
        "Pages: no site found in docs/, so the explorer is the site's home page: docs/index.html"
    )
    assert result.url == "https://some-owner.github.io/demo/"
    assert result.lines[-1] == (
        "Pages: URL after you enable Pages (Settings > Pages > Branch: trunk, folder /docs): "
        "https://some-owner.github.io/demo/"
    )


@pytest.mark.parametrize(
    "site",
    [
        "docs/conf.py",
        "docs/source/conf.py",
        "mkdocs.yml",
        "docs/_config.yml",
        "docs/index.md",
        "docusaurus.config.ts",
        "docs/index.html",
    ],
)
def test_an_existing_site_moves_the_explorer_to_docs_gnost(
    tmp_path: Path, site: str
) -> None:
    (tmp_path / site).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / site).write_text("theirs", encoding="utf-8")
    result = publish(tmp_path)
    assert result.path == "docs/gnost/index.html"
    assert result.lines[0] == (
        f"Pages: docs/ already has a site (found {site}), so the explorer goes to "
        "docs/gnost/index.html"
    )
    assert result.url == "https://some-owner.github.io/demo/gnost/"
    if site == "docs/index.html":
        assert (tmp_path / site).read_text(encoding="utf-8") == "theirs"


def test_a_second_run_updates_the_same_page(tmp_path: Path) -> None:
    publish(tmp_path)
    again = publish(tmp_path)
    assert again.path == "docs/index.html"
    assert again.lines[0] == "Pages: updated docs/index.html (written by GNOST before)"
    assert not again.warnings


def test_a_site_that_appears_later_moves_the_page_with_a_warning(
    tmp_path: Path,
) -> None:
    publish(tmp_path)
    (tmp_path / "docs" / "conf.py").write_text("project = 'x'", encoding="utf-8")
    moved = publish(tmp_path)
    assert moved.path == "docs/gnost/index.html"
    assert moved.warnings == [
        "Pages: docs/ now has a site (found docs/conf.py), so the explorer moved to "
        "docs/gnost/; the old docs/index.html was left in place"
    ]
    assert (tmp_path / "docs" / "index.html").exists()  # left in place
    assert publish(tmp_path).path == "docs/gnost/index.html"  # and it stays there


def test_a_configured_folder_wins(tmp_path: Path) -> None:
    result = PagesPublisher(
        str(tmp_path),
        "docs/gnost",
        '.gnost.toml (pages = "docs/gnost")',
        GITHUB,  # type: ignore[arg-type]
    ).publish(PAGE)
    assert result.path == "docs/gnost/index.html"
    assert (
        result.lines[0]
        == 'Pages: using docs/gnost/ from .gnost.toml (pages = "docs/gnost")'
    )


def test_a_folder_outside_docs_is_served_from_the_root(tmp_path: Path) -> None:
    result = publish(tmp_path, "site")
    assert result.url == "https://some-owner.github.io/demo/site/"
    assert "folder / (root)" in result.lines[-1]


# ------------------------------------------------------------ never overwrite


def test_a_page_gnost_did_not_write_is_never_overwritten(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.html").write_text("theirs", encoding="utf-8")
    with pytest.raises(PagesError) as error:
        publish(tmp_path, "docs")
    assert str(error.value) == (
        'Pages: docs/index.html exists and was not written by GNOST; set pages = "docs/gnost" '
        "or move that file"
    )
    assert (tmp_path / "docs" / "index.html").read_text(encoding="utf-8") == "theirs"


@pytest.mark.parametrize("folder", ["../elsewhere", "/abs/path", ".", "docs/../.."])
def test_a_folder_must_be_inside_the_repository(tmp_path: Path, folder: str) -> None:
    with pytest.raises(PagesError):
        publish(tmp_path, folder)


# ------------------------------------------------------------ language bar


def test_gitattributes_is_written_once_and_kept(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / ".gitattributes").write_text("*.svg binary", encoding="utf-8")
    first = publish(tmp_path)
    attributes = tmp_path / "docs" / ".gitattributes"
    assert attributes.read_text(encoding="utf-8") == (
        "*.svg binary\n/index.html linguist-generated=true\n"
    )
    assert any(".gitattributes" in line for line in first.lines)
    publish(tmp_path)
    assert attributes.read_text(encoding="utf-8").count("linguist-generated") == 1


def test_a_deleted_gitattributes_is_not_written_again(tmp_path: Path) -> None:
    publish(tmp_path)
    (tmp_path / "docs" / ".gitattributes").unlink()  # the user wants the page counted
    again = publish(tmp_path)
    assert not (tmp_path / "docs" / ".gitattributes").exists()
    assert not any(".gitattributes" in line for line in again.lines)


def test_a_large_page_gets_a_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pages_module, "LARGE_PAGE", 10)
    result = publish(tmp_path)
    assert result.warnings and result.warnings[0].startswith(
        "Pages: the page is 0.0 MB"
    )


# ------------------------------------------------------------ the address


@pytest.mark.parametrize(
    "address",
    [
        "https://github.com/Some-Owner/demo.git",
        "https://github.com/Some-Owner/demo",
        "https://token@github.com/Some-Owner/demo.git",
        "git@github.com:Some-Owner/demo.git",
        "git@github.com-work:Some-Owner/demo.git",  # SSH host alias
        "ssh://git@github.com/Some-Owner/demo.git",
    ],
)
def test_github_addresses_are_read(address: str) -> None:
    assert GitHubRepo.parse(address) == GitHubRepo("Some-Owner", "demo")


@pytest.mark.parametrize(
    "address",
    ["https://gitlab.com/o/r.git", "git@bitbucket.org:o/r.git", "/srv/repo.git"],
)
def test_other_hosts_have_no_pages_address(address: str) -> None:
    assert GitHubRepo.parse(address) is None


def test_a_user_site_repository_is_served_at_the_root() -> None:
    assert GitHubRepo("me", "me.github.io").pages_url("") == "https://me.github.io/"
    assert (
        GitHubRepo("me", "me.github.io").pages_url("gnost")
        == "https://me.github.io/gnost/"
    )


def test_without_a_github_remote_the_rule_is_printed(tmp_path: Path) -> None:
    result = publish(tmp_path, repository=FakeRepository({}))
    assert result.url is None
    assert result.lines[-1].startswith("Pages: no github.com 'origin' remote")


# ------------------------------------------------------------ flag and config


def test_flag_and_config_combine() -> None:
    assert PagesRequest.resolve(None, None) is None
    assert PagesRequest.resolve(None, False) is None
    assert PagesRequest.resolve(None, True) == PagesRequest()
    assert PagesRequest.resolve("", None) == PagesRequest()
    assert PagesRequest.resolve("site", "docs") == PagesRequest("site", "--pages site")
    assert PagesRequest.resolve("", "docs/gnost") == PagesRequest(
        "docs/gnost", '.gnost.toml (pages = "docs/gnost")'
    )


def test_the_config_value_is_checked() -> None:
    config = GnostConfig()
    _validate({"onboard": {"pages": "docs/gnost"}}, config)
    assert config.get("onboard", "pages") == "docs/gnost"
    with pytest.raises(ConfigError, match="true, false or a folder name"):
        _validate({"onboard": {"pages": 3}}, GnostConfig())


def _onboard(monkeypatch: pytest.MonkeyPatch, root: Path, *flags: str) -> int:
    (root / "app.py").write_text("print('hi')\n", encoding="utf-8")
    monkeypatch.chdir(root)
    monkeypatch.setenv("GNOST_NO_UPDATE_CHECK", "1")
    monkeypatch.setattr("sys.argv", ["gnost", "onboard", ".", "--no-progress", *flags])
    return int(app.main() or 0)


def test_the_cli_publishes_the_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    assert _onboard(monkeypatch, tmp_path, "--pages") == 0
    assert MARKER in (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    assert "GitHub Pages: docs/index.html" in capsys.readouterr().out


def test_the_cli_refuses_a_foreign_page_before_writing_anything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.html").write_text("theirs", encoding="utf-8")
    assert _onboard(monkeypatch, tmp_path, "--pages", "docs") == 2
    assert "was not written by GNOST" in capsys.readouterr().err
    assert not (tmp_path / ".gnost" / "flow.html").exists()


def test_the_cli_refuses_pages_without_the_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    assert _onboard(monkeypatch, tmp_path, "--pages", "--no-html") == 2
    assert "--pages needs the explorer page" in capsys.readouterr().err
