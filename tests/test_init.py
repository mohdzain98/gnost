"""`gnost init`: the generated config and the build-file integrations."""

from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET

from pathlib import Path
from typing import List

import pytest
import yaml

import gnost.cli.app as app
from gnost.cli.commands.init import InitCommand, default_config_text
from gnost.config.settings import (
    ANALYZE_MAX_FINDINGS,
    ANALYZE_TIMEOUT,
    SCHEMA,
    GnostConfig,
    _validate,
)
from gnost.core.caution import DEFAULT_RANGES, DEFAULT_WEIGHTS, CautionSettings
from gnost.reporters.mermaid import DEFAULT_MAX_EDGES
from gnost.utils import integrations as ig

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9 and 3.10
    import tomli as tomllib  # type: ignore[no-redef]


def _run(monkeypatch: pytest.MonkeyPatch, cwd: Path, *argv: str) -> int:
    monkeypatch.chdir(cwd)
    monkeypatch.setattr("sys.argv", ["gnost", "init", *argv])
    return app.main()


# ---------------------------------------------------------------- the config


def test_the_generated_config_is_valid_and_equals_the_defaults() -> None:
    config = GnostConfig()
    _validate(tomllib.loads(default_config_text()), config)
    assert config.warnings == []
    caution = CautionSettings()
    assert config.output_dir == ".gnost" and config.check_updates is True
    assert config.exclude == []
    assert config.get("onboard", "max_edges") == DEFAULT_MAX_EDGES
    assert config.get("caution", "threshold") == caution.threshold
    assert config.get("caution", "limit") == caution.limit
    assert config.get("caution", "weights") == DEFAULT_WEIGHTS
    assert {
        k: tuple(v) for k, v in config.get("caution", "ranges").items()
    } == DEFAULT_RANGES
    assert config.get("analyze", "timeout") == ANALYZE_TIMEOUT
    assert config.get("analyze", "max_findings") == ANALYZE_MAX_FINDINGS
    assert config.get("analyze", "parallel") is False
    # The built settings are exactly the defaults, so an init file changes nothing.
    built = config.caution_settings()
    assert built.weights == DEFAULT_WEIGHTS and built.ranges == DEFAULT_RANGES


def test_every_setting_the_tool_accepts_is_in_the_generated_file() -> None:
    """Adding a setting to the schema must be reflected in `gnost init`."""
    text = default_config_text()
    for section, keys in SCHEMA.items():
        for key in keys:
            assert key in text, (
                f"{section or 'top level'}: {key} is missing from `gnost init`"
            )


def test_init_writes_the_file_once_and_force_overwrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".git").mkdir()
    assert _run(monkeypatch, tmp_path) == 0
    target = tmp_path / ".gnost.toml"
    assert target.read_text() == default_config_text()
    assert "Next: gnost onboard ." in capsys.readouterr().out

    target.write_text("exclude = ['mine']\n")
    assert _run(monkeypatch, tmp_path) == 1  # refuses, keeps the user's file
    assert target.read_text() == "exclude = ['mine']\n"
    assert "--force" in capsys.readouterr().out

    assert _run(monkeypatch, tmp_path, "--force") == 0
    assert target.read_text() == default_config_text()


def test_print_and_dry_run_write_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".git").mkdir()
    assert _run(monkeypatch, tmp_path, "--print") == 0
    assert capsys.readouterr().out == default_config_text()
    assert _run(monkeypatch, tmp_path, "--dry-run") == 0
    assert not (tmp_path / ".gnost.toml").exists()


def test_init_writes_at_the_repository_root_from_a_subfolder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".git").mkdir()
    sub = tmp_path / "service" / "src"
    sub.mkdir(parents=True)
    assert _run(monkeypatch, sub) == 0
    assert (tmp_path / ".gnost.toml").is_file()


# ------------------------------------------------------------------ pom.xml

POM_WITH_PLUGINS = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <build>
        <pluginManagement>
            <plugins>
                <plugin><artifactId>managed</artifactId></plugin>
            </plugins>
        </pluginManagement>
        <plugins>
            <!-- </plugins> in a comment must not confuse the editor -->
            <plugin>
                <artifactId>maven-compiler-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
    <profiles>
        <profile>
            <build>
                <plugins>
                    <plugin><artifactId>in-profile</artifactId></plugin>
                </plugins>
            </build>
        </profile>
    </profiles>
</project>
"""


def _plugins_of(xml: str) -> List[str]:
    """artifactIds under project/build/plugins (namespace or not)."""

    def local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    root = ET.fromstring(xml)
    build = next((c for c in root if local(c.tag) == "build"), None)
    plugins = next(
        (c for c in (build if build is not None else []) if local(c.tag) == "plugins"),
        None,
    )
    if plugins is None:
        return []
    return [
        next(a.text for a in p if local(a.tag) == "artifactId")
        for p in plugins
        if local(p.tag) == "plugin"
    ]


def test_the_plugin_goes_into_the_real_build_plugins_only() -> None:
    out = ig.PomIntegration().edit(POM_WITH_PLUGINS)
    assert _plugins_of(out) == ["maven-compiler-plugin", "gnost-maven-plugin"]
    assert "<version>0.7.0</version>" in out
    # Only additions: every original line is still there, in order.
    import difflib

    ops = difflib.SequenceMatcher(
        None, POM_WITH_PLUGINS.splitlines(), out.splitlines(), autojunk=False
    ).get_opcodes()
    assert {tag for tag, *_ in ops} <= {"equal", "insert"}
    # The new block is indented like its neighbours.
    assert (
        "\n            <plugin>\n                <groupId>io.github.mohdzain98</groupId>"
        in out
    )


def test_a_build_without_plugins_gets_one() -> None:
    pom = "<project>\n  <modelVersion>4.0.0</modelVersion>\n  <build>\n    <finalName>x</finalName>\n  </build>\n</project>\n"
    out = ig.PomIntegration().edit(pom)
    assert _plugins_of(out) == ["gnost-maven-plugin"]
    assert "  <build>\n    <finalName>x</finalName>\n    <plugins>" in out


def test_a_pom_without_build_gets_build_and_plugins_and_keeps_its_indent() -> None:
    pom = "<project>\n\t<modelVersion>4.0.0</modelVersion>\n</project>\n"
    out = ig.PomIntegration().edit(pom)
    assert _plugins_of(out) == ["gnost-maven-plugin"]
    assert "\n\t<build>\n\t\t<plugins>\n" in out


def test_windows_line_endings_are_kept() -> None:
    pom = POM_WITH_PLUGINS.replace("\n", "\r\n")
    out = ig.PomIntegration().edit(pom)
    assert "\n" not in out.replace("\r\n", "")  # no bare \n was introduced
    assert _plugins_of(out)[-1] == "gnost-maven-plugin"


def test_an_already_configured_pom_is_left_alone() -> None:
    once = ig.PomIntegration().edit(POM_WITH_PLUGINS)
    assert ig.PomIntegration().edit(once) is None


def test_a_broken_pom_is_refused() -> None:
    with pytest.raises(ig.IntegrationError):
        ig.PomIntegration().edit("<notapom></notapom>")
    with pytest.raises(ig.IntegrationError):
        ig.PomIntegration().edit("<project><build></project>")


def test_pom_flag_edits_the_file_and_dry_run_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".git").mkdir()
    pom = tmp_path / "pom.xml"
    pom.write_text(POM_WITH_PLUGINS, encoding="utf-8")
    assert _run(monkeypatch, tmp_path, "--pom", "--dry-run") == 0
    assert pom.read_text(encoding="utf-8") == POM_WITH_PLUGINS
    assert "would change" in capsys.readouterr().out
    assert _run(monkeypatch, tmp_path, "--pom") == 0
    assert _plugins_of(pom.read_text(encoding="utf-8"))[-1] == "gnost-maven-plugin"
    assert (
        _run(monkeypatch, tmp_path, "--pom", "--force") == 0
    )  # second time: nothing more to do
    assert pom.read_text(encoding="utf-8").count("gnost-maven-plugin") == 1


def test_pom_flag_without_a_pom_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".git").mkdir()
    assert _run(monkeypatch, tmp_path, "--pom") == 2
    assert "no pom.xml" in capsys.readouterr().err


# ------------------------------------------------------------- package.json


@pytest.mark.parametrize("indent", ["  ", "    ", "\t"])
def test_the_npm_script_keeps_the_files_indentation(indent: str) -> None:
    original = (
        json.dumps(
            {"name": "x", "scripts": {"test": "jest"}, "version": "1.0.0"},
            indent=indent,
        )
        + "\n"
    )
    out = ig.PackageJsonIntegration().edit(original)
    data = json.loads(out)
    assert data["scripts"] == {"test": "jest", "gnost": ig.NPM_SCRIPT}
    assert list(data) == ["name", "scripts", "version"]  # key order kept
    assert out.endswith("\n") and f'\n{indent}"name"' in out


def test_npm_script_when_there_are_no_scripts_or_one_exists() -> None:
    out = ig.PackageJsonIntegration().edit('{"name": "x"}')
    assert json.loads(out)["scripts"]["gnost"] == ig.NPM_SCRIPT
    assert ig.PackageJsonIntegration().edit('{"scripts": {"gnost": "mine"}}') is None


def test_npm_refuses_files_it_cannot_read() -> None:
    with pytest.raises(ig.IntegrationError):
        ig.PackageJsonIntegration().edit("{not json")
    with pytest.raises(ig.IntegrationError):
        ig.PackageJsonIntegration().edit("[1, 2]")


# ----------------------------------------------------------- GitHub workflow


def test_the_workflow_is_valid_yaml_and_is_not_overwritten(
    tmp_path, monkeypatch, capsys
):
    (tmp_path / ".git").mkdir()
    assert _run(monkeypatch, tmp_path, "--github-action") == 0
    wf = tmp_path / ig.WORKFLOW_PATH
    data = yaml.safe_load(wf.read_text())
    steps = data["jobs"]["gnost"]["steps"]
    assert steps[0]["with"]["fetch-depth"] == 0
    assert steps[1]["uses"].startswith("mohdzain98/gnost@v")
    assert steps[1]["with"]["comment"] == "true"
    assert data["permissions"]["pull-requests"] == "write"
    # pull requests to main or master only, no push trigger (YAML reads `on` as True)
    assert data[True] == {"pull_request": {"branches": ["main", "master"]}}
    wf.write_text("# mine\n")
    assert _run(monkeypatch, tmp_path, "--github-action") == 0
    assert wf.read_text() == "# mine\n"
    assert "already exists" in capsys.readouterr().out


def test_the_default_workflow_points_fork_users_to_the_flag(
    tmp_path, monkeypatch
) -> None:
    (tmp_path / ".git").mkdir()
    assert _run(monkeypatch, tmp_path, "--github-action") == 0
    text = (tmp_path / ig.WORKFLOW_PATH).read_text()
    assert "--fork-comments" in text and 'fork-comments: "true"' not in text
    assert not (tmp_path / ig.COMMENT_WORKFLOW_PATH).exists()


def test_fork_comments_needs_the_github_action_flag(
    tmp_path, monkeypatch, capsys
) -> None:
    (tmp_path / ".git").mkdir()
    assert _run(monkeypatch, tmp_path, "--fork-comments") == 2
    assert "only works together with --github-action" in capsys.readouterr().err
    assert (
        not (tmp_path / ".github").exists() and not (tmp_path / ".gnost.toml").exists()
    )


def test_fork_comments_writes_both_workflows(tmp_path, monkeypatch) -> None:
    (tmp_path / ".git").mkdir()
    assert _run(monkeypatch, tmp_path, "--github-action", "--fork-comments") == 0
    main = yaml.safe_load((tmp_path / ig.WORKFLOW_PATH).read_text())
    assert main["jobs"]["gnost"]["steps"][1]["with"]["fork-comments"] == "true"
    comment = yaml.safe_load((tmp_path / ig.COMMENT_WORKFLOW_PATH).read_text())
    # follows the GNOST workflow by name, in the base repository, with the smallest permissions
    assert comment[True] == {
        "workflow_run": {"workflows": [main["name"]], "types": ["completed"]}
    }
    assert comment["permissions"] == {"actions": "read", "pull-requests": "write"}
    job = comment["jobs"]["comment"]
    assert "head_repository.full_name != github.repository" in job["if"]
    uses = [step.get("uses", "") for step in job["steps"]]
    assert not any(
        u.startswith("actions/checkout") for u in uses
    )  # never the fork's code
    script = job["steps"][1]["with"]["script"]
    assert "/^[0-9]{1,10}$/" in script  # the artifact's number is checked
    assert "pr.head.sha !== run.head_sha" in script
    assert "github-actions[bot]" in script  # only its own comment is updated


def test_fork_comments_notes_an_old_workflow_and_force_rewrites_both(
    tmp_path, monkeypatch, capsys
) -> None:
    (tmp_path / ".git").mkdir()
    assert _run(monkeypatch, tmp_path, "--github-action") == 0
    capsys.readouterr()
    assert _run(monkeypatch, tmp_path, "--github-action", "--fork-comments") == 0
    out = capsys.readouterr().out
    assert 'add `fork-comments: "true"`' in out
    assert (tmp_path / ig.COMMENT_WORKFLOW_PATH).exists()
    assert (
        _run(monkeypatch, tmp_path, "--github-action", "--fork-comments", "--force")
        == 0
    )
    assert 'fork-comments: "true"' in (tmp_path / ig.WORKFLOW_PATH).read_text()
    assert "Note:" not in capsys.readouterr().out


def test_fork_comments_dry_run_lists_both(tmp_path, monkeypatch, capsys) -> None:
    (tmp_path / ".git").mkdir()
    assert (
        _run(monkeypatch, tmp_path, "--github-action", "--fork-comments", "--dry-run")
        == 0
    )
    out = capsys.readouterr().out
    assert "gnost.yml" in out and "gnost-comment.yml" in out
    assert not (tmp_path / ".github").exists()


def test_the_action_skips_the_comment_on_forks_and_only_edits_its_own() -> None:
    action = yaml.safe_load(
        (Path(__file__).parent.parent / "action.yml").read_text(encoding="utf-8")
    )
    steps = {s.get("name", s.get("id")): s for s in action["runs"]["steps"]}
    comment = steps["Comment on the pull request"]
    assert "steps.analyze.outputs.fork != 'true'" in comment["if"]
    assert "github-actions[bot]" in comment["with"]["script"]
    handover = steps[
        "Hand the report to the comment workflow (pull request from a fork)"
    ]
    assert handover["with"]["name"] == "gnost-comment"
    assert "fork-comments" in action["inputs"]
    run = steps["analyze"]["run"]
    assert (
        'cat "$CHANGES"; } >> "$GITHUB_STEP_SUMMARY"' in run
    )  # every PR gets the report


# ------------------------------------------------------------------ AGENTS.md


def test_agents_file_points_to_the_gnost_folder_and_is_kept_when_present(
    tmp_path, monkeypatch, capsys
):
    (tmp_path / ".git").mkdir()
    assert _run(monkeypatch, tmp_path, "--agents") == 0
    text = (tmp_path / "AGENTS.md").read_text()
    assert ".gnost/insights.json" in text and "gnost changes" in text
    (tmp_path / "AGENTS.md").write_text("# mine\n")
    assert _run(monkeypatch, tmp_path, "--agents") == 0
    assert (tmp_path / "AGENTS.md").read_text() == "# mine\n"


# ------------------------------------------------------- open for extension


def test_a_new_integration_needs_no_change_to_the_command(tmp_path: Path) -> None:
    class MarkerFile(ig.CreatesFile):
        flag, help, label, relative_path = "marker", "Write MARKER", "marker", "MARKER"

        def content(self) -> str:
            return "hello\n"

    (tmp_path / ".git").mkdir()
    command = InitCommand(str(tmp_path), [MarkerFile()])
    assert command.run() == 0
    assert (tmp_path / "MARKER").read_text() == "hello\n"


def test_the_command_and_its_flags_come_from_the_registry() -> None:
    flags = {i.flag for i in InitCommand.available()}
    assert flags == {"pom", "npm", "github-action", "fork-comments", "agents"}
    help_text = subprocess.run(
        [sys.executable, "-m", "gnost.cli.app", "init", "--help"],
        capture_output=True,
        text=True,
    ).stdout
    for flag in flags:
        assert f"--{flag}" in help_text
