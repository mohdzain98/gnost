"""Build the standalone gnost folder bundle with PyInstaller and archive it."""

from __future__ import annotations

import hashlib
import platform
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist-binary"
OS_NAMES = {"Darwin": "darwin", "Linux": "linux", "Windows": "win32"}
ARCH_NAMES = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "AMD64": "x64"}


def mypyc_module() -> str:
    """Find mypy's compiled helper module; its hash changes with the mypy version."""
    import mypy

    site = Path(mypy.__file__).resolve().parent.parent
    found = sorted(site.glob("*__mypyc*"))
    if not found:
        raise SystemExit("mypy's compiled module not found (is mypy a compiled wheel?)")
    return found[0].name.split(".")[0]


def ruff_binary() -> str:
    """Return the path of the installed ruff executable."""
    path = shutil.which("ruff")
    if not path:
        raise SystemExit("ruff executable not found on PATH")
    return path


def platform_tag() -> str:
    """Return <os>-<arch> using the names Node reports."""
    return f"{OS_NAMES[platform.system()]}-{ARCH_NAMES[platform.machine()]}"


def pyinstaller_args() -> List[str]:
    """Return the PyInstaller command-line arguments."""
    sep = ";" if platform.system() == "Windows" else ":"
    args = [
        str(ROOT / "packaging" / "entry.py"),
        "--noconfirm",
        "--clean",
        "--name",
        "gnost",
        "--onedir",
        "--distpath",
        str(DIST / "bundle"),
        "--workpath",
        str(DIST / "work"),
        "--specpath",
        str(DIST / "work"),
        "--hidden-import",
        mypyc_module(),
        "--add-binary",
        f"{ruff_binary()}{sep}bin",
    ]
    for pkg in ("mypy", "bandit", "radon", "gnost"):
        args += ["--collect-all", pkg]
    for pkg in ("mypy", "bandit", "radon", "gnost", "stevedore"):
        args += ["--copy-metadata", pkg]
    args += ["--collect-submodules", "stevedore"]
    return args


def archive(version: str) -> Path:
    """Archive the bundle as gnost-<version>-<os>-<arch> and return its path."""
    tag = platform_tag()
    base = f"gnost-{version}-{tag}"
    bundle = DIST / "bundle" / "gnost"
    if tag.startswith("win32"):
        out = DIST / f"{base}.zip"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for f in bundle.rglob("*"):
                z.write(f, Path("gnost") / f.relative_to(bundle))
    else:
        out = DIST / f"{base}.tar.gz"
        with tarfile.open(out, "w:gz") as t:
            t.add(bundle, arcname="gnost")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    (DIST / f"{out.name}.sha256").write_text(f"{digest}  {out.name}\n")
    return out


def main() -> int:
    """Build, archive and report the size."""
    import PyInstaller.__main__

    sys.path.insert(0, str(ROOT / "scripts"))
    from channel_versions import read_version

    shutil.rmtree(DIST, ignore_errors=True)
    PyInstaller.__main__.run(pyinstaller_args())
    out = archive(read_version())
    print(f"built {out} ({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
