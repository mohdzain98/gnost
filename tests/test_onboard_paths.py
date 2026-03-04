from pathlib import Path

from gnost.cli.commands.onboard import resolve_repo_root


def test_resolve_repo_root_from_nested_directory(tmp_path: Path):
    repo = tmp_path / "repo"
    nested = repo / "gnost" / "pkg"
    nested.mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    assert resolve_repo_root(str(nested)) == str(repo)


def test_resolve_repo_root_from_file_path(tmp_path: Path):
    repo = tmp_path / "repo"
    target_dir = repo / "gnost"
    target_dir.mkdir(parents=True)
    target_file = target_dir / "module.py"
    target_file.write_text("print('ok')\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    assert resolve_repo_root(str(target_file)) == str(repo)
