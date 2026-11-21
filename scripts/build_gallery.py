"""Build the showcase gallery: run `gnost onboard` on well-known projects and keep the guides.

Usage: python scripts/build_gallery.py [name ...]   (needs network and git)
Writes docs/gallery/<name>/ONBOARD.md and its flow/ pages; docs/gallery.rst links to them.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "gallery"
PROJECTS: Dict[str, str] = {
    "spring-petclinic": "https://github.com/spring-projects/spring-petclinic",
    "flask": "https://github.com/pallets/flask",
    "fastapi": "https://github.com/fastapi/fastapi",
    "express": "https://github.com/expressjs/express",
}


def build(name: str, url: str) -> bool:
    """Onboard one project into a temp folder and copy its guide; True on success."""
    with tempfile.TemporaryDirectory(prefix="gnost-gallery-") as work:
        done = subprocess.run(
            [sys.executable, "-m", "gnost.cli.app", "onboard", url, "--no-html"],
            cwd=work,
            env=dict(os.environ, GNOST_NO_UPDATE_CHECK="1"),
        )
        guide = Path(work) / ".gnost" / "ONBOARD.md"
        if done.returncode != 0 or not guide.is_file():
            return False
        target = OUT / name
        shutil.rmtree(target, ignore_errors=True)
        (target / "flow").mkdir(parents=True)
        shutil.copy(guide, target / "ONBOARD.md")
        for page in (Path(work) / ".gnost" / "flow").iterdir():
            if page.suffix in (".md", ".mmd"):  # the pages ONBOARD.md links to
                shutil.copy(page, target / "flow" / page.name)
        return True


def main(names: List[str]) -> int:
    """Build the named projects (all by default); returns 1 if any failed."""
    failed = [n for n in (names or PROJECTS) if not build(n, PROJECTS[n])]
    print("failed:", ", ".join(failed) if failed else "none")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
