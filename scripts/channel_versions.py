"""Derive per-channel version strings from the Python (PEP 440) version."""

from __future__ import annotations

import re
import sys
from pathlib import Path

PEP440 = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?$")
PRE_NAMES = {"a": "alpha", "b": "beta", "rc": "rc"}


def read_version() -> str:
    """Read __version__ from gnost/__init__.py without importing the package."""
    init = Path(__file__).resolve().parent.parent / "gnost" / "__init__.py"
    match = re.search(r'__version__\s*=\s*"([^"]+)"', init.read_text(encoding="utf-8"))
    if not match:
        raise SystemExit("__version__ not found")
    return match.group(1)


def to_npm(version: str) -> str:
    """Convert 0.5.0rc1 to 0.5.0-rc.1 (SemVer)."""
    m = PEP440.match(version)
    if not m:
        raise ValueError(f"unsupported version: {version}")
    major, minor, patch, pre, num = m.groups()
    base = f"{major}.{minor}.{patch}"
    return f"{base}-{PRE_NAMES[pre]}.{num}" if pre else base


def to_docker(version: str) -> str:
    """Docker tags may not contain '+'; PEP 440 finals/prereleases are already valid."""
    if not PEP440.match(version):
        raise ValueError(f"unsupported version: {version}")
    return version


def main(argv: list[str]) -> int:
    """Print the version for the requested channel (pypi, npm, docker)."""
    channel = argv[1] if len(argv) > 1 else "pypi"
    version = argv[2] if len(argv) > 2 else read_version()
    out = {"pypi": lambda v: v, "npm": to_npm, "docker": to_docker}.get(channel)
    if out is None:
        print("usage: channel_versions.py [pypi|npm|docker] [version]", file=sys.stderr)
        return 2
    print(out(version))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
