"""The binary size budget: under, at and over the limit, unknown names, and the report."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parent.parent
MIB = 1024 * 1024


def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_binary_size", ROOT / "scripts" / "check_binary_size.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look the module up by name
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def budget(tmp_path: Path):
    mod = script()
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "budget_mib": 15,
                "platforms": {"linux-x64": 100 * MIB, "win32-x64": 80 * MIB},
            }
        )
    )
    return mod, mod.SizeBudget(baseline)


def archive(folder: Path, name: str, size: int) -> Path:
    path = folder / name
    path.write_bytes(b"\0" * size)
    return path


def test_an_archive_within_the_budget_passes(tmp_path: Path, budget) -> None:
    _, sizes = budget
    verdict = sizes.check(archive(tmp_path, "gnost-0.7.0-linux-x64.tar.gz", 105 * MIB))
    assert verdict.ok and verdict.growth == 5 * MIB


def test_exactly_the_budget_passes_and_one_byte_more_fails(
    tmp_path: Path, budget
) -> None:
    _, sizes = budget
    at = sizes.check(archive(tmp_path, "gnost-0.7.0-linux-x64.tar.gz", 115 * MIB))
    assert at.ok
    over = sizes.check(
        archive(tmp_path, "gnost-0.7.0-win32-x64.zip", 80 * MIB + 15 * MIB + 1)
    )
    assert not over.ok and "OVER BUDGET" in over.describe()


def test_a_smaller_archive_passes(tmp_path: Path, budget) -> None:
    _, sizes = budget
    verdict = sizes.check(archive(tmp_path, "gnost-0.7.0-linux-x64.tar.gz", 90 * MIB))
    assert verdict.ok and verdict.growth < 0 and "-10.00 MiB" in verdict.describe()


def test_unknown_names_and_platforms_are_errors(tmp_path: Path, budget) -> None:
    _, sizes = budget
    with pytest.raises(ValueError, match="not a gnost binary archive"):
        sizes.check(archive(tmp_path, "something.tar.gz", 1))
    with pytest.raises(ValueError, match="no baseline for platform"):
        sizes.check(archive(tmp_path, "gnost-0.7.0-darwin-arm64.tar.gz", 1))


def test_the_report_names_the_biggest_parts(tmp_path: Path, budget) -> None:
    mod, _ = budget
    bundle = tmp_path / "bundle"
    (bundle / "big").mkdir(parents=True)
    (bundle / "big" / "a.bin").write_bytes(b"0" * 5000)
    (bundle / "small.txt").write_text("x")
    lines = mod.SizeBudget.biggest_folders(bundle)
    assert "big" in lines[0] and "small.txt" in lines[1]


def test_the_command_exit_codes(tmp_path: Path, budget, capsys) -> None:
    mod, _ = budget
    baseline = tmp_path / "baseline.json"
    out = tmp_path / "out"
    out.mkdir()
    assert mod.main([str(out)], baseline) == 2  # nothing to check
    archive(out, "gnost-0.7.0-linux-x64.tar.gz", 101 * MIB)
    assert mod.main([str(out)], baseline) == 0
    assert "ok" in capsys.readouterr().out
    archive(out, "gnost-0.7.0-win32-x64.zip", 200 * MIB)
    (out / "bundle" / "gnost" / "_internal" / "heavy").mkdir(parents=True)
    (out / "bundle" / "gnost" / "_internal" / "heavy" / "x.bin").write_bytes(
        b"0" * 4000
    )
    assert mod.main([str(out)], baseline) == 1
    captured = capsys.readouterr()
    assert "OVER BUDGET" in captured.out and "heavy" in captured.out
    assert "raise the baseline" in captured.err


def test_the_real_baseline_covers_the_three_platforms() -> None:
    mod = script()
    sizes = mod.SizeBudget()
    assert set(sizes.platforms) == {"darwin-arm64", "linux-x64", "win32-x64"}
    assert sizes.budget == 15 * MIB
