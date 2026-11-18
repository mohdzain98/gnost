"""Assemble the npm packages from built binary archives.

Usage: build_npm.py <archive-dir> <out-dir> [version]
Writes <out-dir>/gnost-cli and one gnost-cli-<platform> folder per archive found.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from archive_utils import dereference  # noqa: E402
from channel_versions import read_version, to_npm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "packaging" / "npm" / "gnost-cli"
PLATFORMS = ("darwin-arm64", "linux-x64", "win32-x64")
# Windows is not called "win32": npm's spam filter rejected gnost-cli-win32-x64.
PACKAGE_NAMES = {"win32-x64": "gnost-cli-windows-x64"}


def package_name(key: str) -> str:
    """npm package name for a platform key (must match the launcher's table)."""
    return PACKAGE_NAMES.get(key, f"gnost-cli-{key}")


def sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def unpack(archive: Path, dest: Path) -> None:
    """Unpack an archive whose top folder is 'gnost' into dest/bundle."""
    tmp = dest / "_unpack"
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as z:
            z.extractall(tmp)
    else:
        with tarfile.open(archive) as t:
            t.extractall(tmp)
    shutil.move(str(tmp / "gnost"), str(dest / "bundle"))
    shutil.rmtree(tmp)
    dereference(dest / "bundle")


def build_platform(key: str, archive: Path, out: Path, version: str) -> str:
    """Create gnost-cli-<key>; return the SHA-256 of its executable."""
    os_name, cpu = key.split("-")
    pkg = out / package_name(key)
    pkg.mkdir(parents=True)
    unpack(archive, pkg)
    exe = pkg / "bundle" / ("gnost.exe" if os_name == "win32" else "gnost")
    exe.chmod(0o755)
    meta: Dict[str, object] = {
        "name": package_name(key),
        "version": version,
        "description": f"GNOST standalone binary for {key}",
        "license": "MIT",
        "os": [os_name],
        "cpu": [cpu],
        "files": ["bundle"],
        "repository": {
            "type": "git",
            "url": "git+https://github.com/mohdzain98/gnost.git",
        },
    }
    (pkg / "package.json").write_text(json.dumps(meta, indent=2) + "\n")
    (pkg / "README.md").write_text(f"Binary for {key}. Install `gnost-cli` instead.\n")
    return sha256(exe)


def main(argv: List[str]) -> int:
    """Build all packages for the archives present."""
    archives, out = Path(argv[1]), Path(argv[2])
    version = to_npm(argv[3] if len(argv) > 3 else read_version())
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    checksums: Dict[str, str] = {}
    excluded = set(filter(None, os.environ.get("GNOST_NPM_EXCLUDE", "").split(",")))
    for key in PLATFORMS:
        if key in excluded:
            continue
        found = [
            p for p in archives.rglob(f"gnost-*-{key}.*") if p.suffix in (".gz", ".zip")
        ]
        if found:
            checksums[key] = build_platform(key, found[0], out, version)
    main_pkg = out / "gnost-cli"
    shutil.copytree(
        MAIN, main_pkg, ignore=shutil.ignore_patterns("test", "node_modules")
    )
    meta = json.loads((main_pkg / "package.json").read_text())
    meta["version"] = version
    meta["optionalDependencies"] = {package_name(k): version for k in checksums}
    (main_pkg / "package.json").write_text(json.dumps(meta, indent=2) + "\n")
    (main_pkg / "checksums.json").write_text(json.dumps(checksums, indent=2) + "\n")
    (main_pkg / "README.md").write_text(
        "# gnost-cli\n\nGNOST codebase knowledge CLI as a standalone binary (no Python needed).\n\n"
        "```\nnpx gnost-cli onboard .\n```\n\nDocs: https://gnost.readthedocs.io\n"
    )
    print(f"built {len(checksums)} platform package(s) + gnost-cli {version} in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
