"""Repack built binary archives as the zip files the Maven artifacts carry.

Usage: build_maven.py <archive-dir> <out-dir>
Writes <out-dir>/<classifier>.zip for each platform archive found. Each zip holds
gnost/ (the PyInstaller bundle) and gnost/gnost.sha256 (SHA-256 of the executable).
Set GNOST_MAVEN_EXCLUDE=windows-x64,... to leave platforms out.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from archive_utils import dereference  # noqa: E402

# Archive platform key (as built by build_binary.py) -> Maven classifier.
CLASSIFIERS: Dict[str, str] = {
    "darwin-arm64": "darwin-arm64",
    "linux-x64": "linux-x64",
    "win32-x64": "windows-x64",
}


def _extract(archive: Path, dest: Path) -> Path:
    """Unpack an archive whose top folder is 'gnost'; return that folder."""
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as z:
            z.extractall(dest)
    else:
        with tarfile.open(archive) as t:
            t.extractall(dest)
    dereference(dest / "gnost")
    return dest / "gnost"


def build_zip(archive: Path, target: Path) -> str:
    """Write target from archive; return the SHA-256 of the executable."""
    with tempfile.TemporaryDirectory() as tmp:
        bundle = _extract(archive, Path(tmp))
        exe = bundle / ("gnost.exe" if (bundle / "gnost.exe").exists() else "gnost")
        digest = hashlib.sha256(exe.read_bytes()).hexdigest()
        (bundle / "gnost.sha256").write_text(f"{digest}  {exe.name}\n")
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            for path in sorted(bundle.rglob("*")):
                if path.is_file():
                    z.write(path, Path("gnost") / path.relative_to(bundle))
    return digest


def main(argv: List[str]) -> int:
    """Build one zip per platform archive present."""
    archives, out = Path(argv[1]), Path(argv[2])
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    excluded = set(filter(None, os.environ.get("GNOST_MAVEN_EXCLUDE", "").split(",")))
    built = []
    for key, classifier in CLASSIFIERS.items():
        if classifier in excluded or key in excluded:
            continue
        found = [
            p for p in archives.rglob(f"gnost-*-{key}.*") if p.suffix in (".gz", ".zip")
        ]
        if found:
            build_zip(found[0], out / f"{classifier}.zip")
            built.append(classifier)
    if not built:
        print("no binary archives found", file=sys.stderr)
        return 1
    print(f"built Maven binary zips for: {', '.join(built)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
