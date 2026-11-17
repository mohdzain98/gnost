import importlib.util
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "build_npm", ROOT / "scripts" / "build_npm.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_assembles_platform_and_main_packages(tmp_path):
    src = tmp_path / "src" / "gnost"
    src.mkdir(parents=True)
    (src / "gnost").write_text("bin")
    archives = tmp_path / "archives"
    archives.mkdir()
    with tarfile.open(archives / "gnost-0.5.0rc1-linux-x64.tar.gz", "w:gz") as t:
        t.add(src, arcname="gnost")
    out = tmp_path / "out"

    assert _load().main(["x", str(archives), str(out), "0.5.0rc1"]) == 0

    import json

    main = json.loads((out / "gnost-cli" / "package.json").read_text())
    assert main["version"] == "0.5.0-rc.1"
    assert main["optionalDependencies"] == {"gnost-cli-linux-x64": "0.5.0-rc.1"}
    platform = json.loads((out / "gnost-cli-linux-x64" / "package.json").read_text())
    assert platform["os"] == ["linux"] and platform["cpu"] == ["x64"]
    sums = json.loads((out / "gnost-cli" / "checksums.json").read_text())
    assert len(sums["linux-x64"]) == 64


def test_windows_package_is_not_named_win32(tmp_path):
    import json

    src = tmp_path / "src" / "gnost"
    src.mkdir(parents=True)
    (src / "gnost.exe").write_text("bin")
    archives = tmp_path / "archives"
    archives.mkdir()
    with tarfile.open(archives / "gnost-0.5.0-win32-x64.tar.gz", "w:gz") as t:
        t.add(src, arcname="gnost")
    out = tmp_path / "out"
    assert _load().main(["x", str(archives), str(out), "0.5.0"]) == 0
    pkg = json.loads((out / "gnost-cli-windows-x64" / "package.json").read_text())
    assert pkg["name"] == "gnost-cli-windows-x64"
    assert pkg["os"] == ["win32"] and pkg["cpu"] == ["x64"]
    main = json.loads((out / "gnost-cli" / "package.json").read_text())
    assert main["optionalDependencies"] == {"gnost-cli-windows-x64": "0.5.0"}
