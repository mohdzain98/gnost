"""Print the build-time settings the Maven plugin needs for one GNOST release.

Usage: build_maven.py <archive-dir> [version]
Looks in <archive-dir> for the release archives gnost-<version>-<platform>.tar.gz|zip and
prints one line of Maven options, for example:
    -Dgnost.release.version=0.5.3 -Dgnost.sha.linux-x64=<sha256> ...
The plugin embeds these, so it downloads only files whose SHA-256 it was built with.
Set GNOST_MAVEN_EXCLUDE=win32-x64,... to leave platforms out.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from channel_versions import read_version  # noqa: E402

PLATFORMS = ("darwin-arm64", "linux-x64", "win32-x64")


def sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_archives(directory: Path, version: str) -> Dict[str, Path]:
    """Map platform key to its release archive (the exact name the plugin downloads)."""
    excluded = set(filter(None, os.environ.get("GNOST_MAVEN_EXCLUDE", "").split(",")))
    found: Dict[str, Path] = {}
    for key in PLATFORMS:
        if key in excluded:
            continue
        ext = "zip" if key.startswith("win32") else "tar.gz"
        matches = sorted(directory.rglob(f"gnost-{version}-{key}.{ext}"))
        if matches:
            found[key] = matches[0]
    return found


def main(argv: List[str]) -> int:
    """Print the options; return 1 if no archive was found."""
    directory = Path(argv[1])
    version = argv[2] if len(argv) > 2 else read_version()
    archives = find_archives(directory, version)
    if not archives:
        print(f"no release archives for {version} in {directory}", file=sys.stderr)
        return 1
    parts = [f"-Dgnost.release.version={version}"]
    parts += [f"-Dgnost.sha.{key}={sha256(path)}" for key, path in archives.items()]
    print(" ".join(parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
