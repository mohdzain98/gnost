import importlib.util
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _archive(tmp_path, key, exe):
    src = tmp_path / "src" / "gnost"
    src.mkdir(parents=True)
    (src / exe).write_text("bin")
    (src / "_internal").mkdir()
    (src / "_internal" / "lib.so").write_text("x")
    archives = tmp_path / "archives"
    archives.mkdir()
    with tarfile.open(archives / f"gnost-0.5.0-{key}.tar.gz", "w:gz") as t:
        t.add(src, arcname="gnost")
    return archives


def test_zip_holds_bundle_and_checksum(tmp_path):
    archives = _archive(tmp_path, "linux-x64", "gnost")
    out = tmp_path / "out"
    assert _load("build_maven").main(["x", str(archives), str(out)]) == 0
    with zipfile.ZipFile(out / "linux-x64.zip") as z:
        names = set(z.namelist())
        assert {"gnost/gnost", "gnost/gnost.sha256", "gnost/_internal/lib.so"} <= names
        assert len(z.read("gnost/gnost.sha256").split()[0]) == 64


def test_windows_classifier_is_not_win32(tmp_path):
    archives = _archive(tmp_path, "win32-x64", "gnost.exe")
    out = tmp_path / "out"
    assert _load("build_maven").main(["x", str(archives), str(out)]) == 0
    assert [p.name for p in out.iterdir()] == ["windows-x64.zip"]


def test_excluded_platform_is_left_out(tmp_path, monkeypatch):
    archives = _archive(tmp_path, "win32-x64", "gnost.exe")
    monkeypatch.setenv("GNOST_MAVEN_EXCLUDE", "windows-x64")
    assert _load("build_maven").main(["x", str(archives), str(tmp_path / "o")]) == 1


def test_maven_version_strings():
    cv = _load("channel_versions")
    assert cv.to_maven("0.5.0rc1") == "0.5.0-rc1"
    assert cv.to_maven("0.5.0") == "0.5.0"
