import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _archive(directory, key, version="0.5.3"):
    directory.mkdir(parents=True, exist_ok=True)
    ext = "zip" if key.startswith("win32") else "tar.gz"
    path = directory / f"gnost-{version}-{key}.{ext}"
    path.write_bytes(f"archive {key}".encode())
    return path


def test_options_carry_the_version_and_each_checksum(tmp_path, capsys):
    linux = _archive(tmp_path, "linux-x64")
    win = _archive(tmp_path, "win32-x64")
    assert _load("build_maven").main(["x", str(tmp_path), "0.5.3"]) == 0
    out = capsys.readouterr().out.split()
    assert out[0] == "-Dgnost.release.version=0.5.3"
    sums = dict(o[len("-Dgnost.sha.") :].split("=") for o in out[1:])
    assert sums["linux-x64"] == hashlib.sha256(linux.read_bytes()).hexdigest()
    assert sums["win32-x64"] == hashlib.sha256(win.read_bytes()).hexdigest()
    assert "darwin-arm64" not in sums


def test_release_candidate_names_are_matched_exactly(tmp_path, capsys):
    _archive(tmp_path, "linux-x64", "0.5.3rc1")
    assert _load("build_maven").main(["x", str(tmp_path), "0.5.3"]) == 1
    assert _load("build_maven").main(["x", str(tmp_path), "0.5.3rc1"]) == 0
    assert "-Dgnost.release.version=0.5.3rc1" in capsys.readouterr().out


def test_excluded_platform_is_left_out(tmp_path, monkeypatch, capsys):
    _archive(tmp_path, "linux-x64")
    _archive(tmp_path, "win32-x64")
    monkeypatch.setenv("GNOST_MAVEN_EXCLUDE", "win32-x64")
    assert _load("build_maven").main(["x", str(tmp_path), "0.5.3"]) == 0
    assert "win32-x64" not in capsys.readouterr().out


def test_nothing_found_fails(tmp_path):
    assert _load("build_maven").main(["x", str(tmp_path), "0.5.3"]) == 1


def test_maven_version_strings():
    cv = _load("channel_versions")
    assert cv.to_maven("0.5.0rc1") == "0.5.0-rc1"
    assert cv.to_maven("0.5.0") == "0.5.0"


def test_symlinked_library_is_stored_as_a_file(tmp_path):
    """npm packs no symlinks; the shared helper replaces them with copies."""
    import os

    root = tmp_path / "gnost"
    (root / "_internal").mkdir(parents=True)
    (root / "_internal" / "real.dylib").write_text("lib")
    os.symlink("real.dylib", root / "_internal" / "Python")
    _load("archive_utils").dereference(root)
    assert not (root / "_internal" / "Python").is_symlink()
    assert (root / "_internal" / "Python").read_text() == "lib"
