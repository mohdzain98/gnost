import json
from pathlib import Path

import pytest

import gnost.cli.app as app
from gnost.config.settings import (
    CONFIG_NAME,
    ConfigError,
    find_config,
    load_config,
)
from gnost.scanner.filters import is_excluded


def write(root: Path, text: str) -> Path:
    path = root / CONFIG_NAME
    path.write_text(text, encoding="utf-8")
    return path


# ---- finding and loading ----


def test_missing_config_gives_defaults(tmp_path):
    (tmp_path / ".git").mkdir()
    config = load_config(str(tmp_path))
    assert config.path is None and config.exclude == [] and config.warnings == []
    assert config.caution_settings().threshold == 40


def test_config_is_found_from_a_subfolder_but_not_above_the_repo_root(tmp_path):
    write(tmp_path, "exclude = ['x']\n")
    repo = tmp_path / "repo"
    (repo / "src" / "deep").mkdir(parents=True)
    (repo / ".git").mkdir()
    assert find_config(str(repo / "src" / "deep")) is None  # tmp_path is above the repo
    write(repo, "exclude = ['y']\n")
    assert find_config(str(repo / "src" / "deep")) == str(repo / CONFIG_NAME)


def test_full_example_loads(tmp_path):
    write(
        tmp_path,
        'exclude = ["legacy", "*.generated.ts"]\n'
        "[onboard]\nmax_edges = 120\ncollapse = 2\ndepth = 3\n"
        "[caution]\nthreshold = 55.5\nlimit = 4\n"
        "[caution.weights]\nsize = 0.2\n"
        "[caution.ranges]\nsize = [300, 1500]\n"
        '[analyze]\nanalyzers = ["readability"]\ntimeout = 60\nmax_findings = 7\nparallel = true\n',
    )
    config = load_config(str(tmp_path))
    assert config.warnings == []
    assert config.exclude == ["legacy", "*.generated.ts"]
    assert config.get("onboard", "max_edges") == 120
    assert config.get("analyze", "parallel") is True
    settings = config.caution_settings()
    assert settings.threshold == 55.5 and settings.limit == 4
    assert settings.weights["size"] == 0.2 and settings.weights["impact"] == 0.8
    assert settings.ranges["size"] == (300.0, 1500.0)


def test_pick_prefers_cli_then_config_then_default(tmp_path):
    write(tmp_path, "[onboard]\nmax_edges = 90\n")
    config = load_config(str(tmp_path))
    assert config.pick("onboard", "max_edges", 10, 200) == 10
    assert config.pick("onboard", "max_edges", None, 200) == 90
    assert config.pick("onboard", "depth", None, 4) == 4


# ---- validation ----


def test_unknown_keys_become_warnings(tmp_path):
    write(
        tmp_path,
        "colour = 'red'\n[onboard]\nmax_egdes = 3\n[caution.weights]\nspeed = 1\n[mystery]\nx = 1\n",
    )
    config = load_config(str(tmp_path))
    text = "\n".join(config.warnings)
    for key in ("colour", "onboard.max_egdes", "caution.weights.speed", "mystery"):
        assert f"'{key}'" in text


@pytest.mark.parametrize(
    "toml, fragment",
    [
        ("[onboard]\nmax_edges = 'many'\n", "'onboard.max_edges' must be an integer"),
        ("[onboard]\nmax_edges = true\n", "'onboard.max_edges' must be an integer"),
        ("exclude = 'legacy'\n", "'exclude' must be a list"),
        ("exclude = [1]\n", "list of strings"),
        ("[analyze]\nparallel = 'yes'\n", "'analyze.parallel' must be true or false"),
        ("[analyze]\nanalyzers = [1]\n", "list of strings"),
        ("[caution.weights]\nsize = 2\n", "between 0 and 1"),
        ("[caution.ranges]\nsize = [5]\n", "two numbers"),
        ("[caution.ranges]\nsize = [9, 3]\n", "first number below the second"),
        ("[onboard\n", "not valid TOML"),
    ],
)
def test_bad_values_raise_clear_errors(tmp_path, toml, fragment):
    path = write(tmp_path, toml)
    with pytest.raises(ConfigError) as err:
        load_config(str(tmp_path))
    assert fragment in str(err.value) and str(path) in str(err.value)


# ---- exclusion patterns ----


def test_is_excluded_patterns(tmp_path):
    root = str(tmp_path)

    def hit(rel, *patterns):
        return is_excluded(f"{root}/{rel}", root, list(patterns))

    assert hit("legacy/a.py", "legacy")  # a folder anywhere
    assert hit("src/legacy/a.py", "legacy")
    assert hit("src/a.generated.ts", "*.generated.ts")  # a file name
    assert hit("docs/build/x.js", "docs/build")  # a path
    assert hit("src/old/x.py", "src/old/")
    assert hit("src/a/x.py", "src/*/x.py")
    assert not hit("src/legacy_helpers.py", "legacy")
    assert not hit("a.py")
    assert not hit("a.py", "")


# ---- effect on onboard and analyze ----


def run_cli(monkeypatch, *argv):
    monkeypatch.setattr("sys.argv", ["gnost", *argv])
    return app.main()


def test_exclude_removes_files_from_onboard(fixture_repo, monkeypatch):
    root = fixture_repo("package_app")
    write(root, 'exclude = ["scripts", "notes.py"]\n')
    assert run_cli(monkeypatch, "onboard", str(root), "--insights-only") == 0
    data = json.loads((root / ".gnost/insights.json").read_text())
    assert [e["file"] for e in data["entry_points"]] == ["app/main.py"]
    assert "app/api/v1/notes.py" not in data["graph"]["nodes"]
    assert not any("seed" in n for n in data["graph"]["nodes"])


def test_config_sets_diagram_size_and_cli_overrides_it(fixture_repo, monkeypatch):
    root = fixture_repo("package_app")
    write(root, "[onboard]\nmax_edges = 4\n")
    run_cli(monkeypatch, "onboard", str(root))
    assert "dir_" in (root / ".gnost/flow/FLOW-full.mmd").read_text()

    run_cli(monkeypatch, "onboard", str(root), "--max-edges", "500")
    assert "dir_" not in (root / ".gnost/flow/FLOW-full.mmd").read_text()


def test_config_changes_what_counts_as_caution(fixture_repo, monkeypatch):
    root = fixture_repo("cyclic_py")
    write(root, "[caution]\nthreshold = 95\n")
    run_cli(monkeypatch, "onboard", str(root), "--insights-only")
    data = json.loads((root / ".gnost/insights.json").read_text())
    assert data["caution_areas"] == []

    write(root, "[caution.weights]\ncycles = 0.5\n")
    run_cli(monkeypatch, "onboard", str(root), "--insights-only")
    data = json.loads((root / ".gnost/insights.json").read_text())
    assert data["caution_areas"][0]["score"] == 50


def test_invalid_config_stops_the_command_with_exit_code_2(
    fixture_repo, monkeypatch, capsys
):
    root = fixture_repo("python_app")
    write(root, "[onboard]\nmax_edges = 'x'\n")
    assert run_cli(monkeypatch, "onboard", str(root)) == 2
    assert "gnost:" in capsys.readouterr().err
    assert not (root / ".gnost/ONBOARD.md").exists()


def test_unknown_key_warns_on_stderr_but_runs(fixture_repo, monkeypatch, capsys):
    root = fixture_repo("python_app")
    write(root, "bogus = 1\n")
    assert run_cli(monkeypatch, "onboard", str(root), "--insights-only") == 0
    assert "unknown setting 'bogus'" in capsys.readouterr().err


def test_analyze_reads_its_settings_from_the_config(fixture_repo, monkeypatch):
    root = fixture_repo("python_app")
    write(
        root,
        '[analyze]\nanalyzers = ["readability"]\ntimeout = 77\nmax_findings = 5\nparallel = true\n',
    )
    seen = {}
    monkeypatch.setattr(app.analysis, "initialize_analyzers", lambda: None)
    monkeypatch.setattr(
        app.analysis,
        "collect_code_files",
        lambda target, **kw: ([str(root / "main.py")], 1),
    )

    async def fake_run(cfg, show_progress):
        seen["cfg"] = cfg
        raise RuntimeError("stop here")

    monkeypatch.setattr(app.analysis, "run_async", fake_run)
    run_cli(monkeypatch, "analyze", str(root))
    cfg = seen["cfg"]
    assert cfg.enabled_analyzers == {"readability"}
    assert (cfg.timeout_seconds, cfg.max_findings_per_analyzer) == (77, 5)
    assert cfg.parallel_execution is True

    run_cli(monkeypatch, "analyze", str(root), "-a", "robustness", "--timeout", "10")
    cfg = seen["cfg"]
    assert cfg.enabled_analyzers == {"robustness"} and cfg.timeout_seconds == 10
    assert cfg.max_findings_per_analyzer == 5  # still from the config
