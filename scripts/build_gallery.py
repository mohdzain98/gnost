"""Build the showcase gallery: run `gnost onboard` on well-known projects and keep the guides.

Usage: python scripts/build_gallery.py [name ...]   (needs network and git)
Writes docs/gallery/<name>/ONBOARD.md, its flow/ pages and analysis/analysis.json; docs/gallery.rst links to them.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

from gnost.vcs.remote import RemoteUrl

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "gallery"
PROJECTS: Dict[str, str] = {
    "spring-petclinic": "https://github.com/spring-projects/spring-petclinic",
    "flask": "https://github.com/pallets/flask",
    "fastapi": "https://github.com/fastapi/fastapi",
    "express": "https://github.com/expressjs/express",
}


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
FINDINGS_KEPT = 150  # keeps the repository small; the summary still counts all of them


def scrub_paths(node: object, url: str) -> None:
    """Replace every `target_path` (a temporary clone folder) with the repository address."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "target_path":
                node[key] = url
            else:
                scrub_paths(value, url)
    elif isinstance(node, list):
        for item in node:
            scrub_paths(item, url)


def trim_report(source: Path, target: Path, url: str) -> None:
    """Copy an analysis report with the most severe findings only and no local paths."""
    data = json.loads(source.read_text(encoding="utf-8"))
    findings = sorted(
        data.get("findings", []),
        key=lambda f: SEVERITY_ORDER.get(str(f.get("severity")), 9),
    )
    data["findings"] = findings[:FINDINGS_KEPT]
    scrub_paths(data, url)
    data["gallery_note"] = (
        f"Showing the {len(data['findings'])} most severe of {len(findings)} findings; "
        "the summary counts all of them."
    )
    target.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


def build(name: str, url: str) -> bool:
    """Onboard one project into a temp folder and copy its guide; True on success."""
    with tempfile.TemporaryDirectory(prefix="gnost-gallery-") as work:
        done = subprocess.run(
            [sys.executable, "-m", "gnost.cli.app", "onboard", url, "--no-html"],
            cwd=work,
            env=dict(os.environ, GNOST_NO_UPDATE_CHECK="1"),
        )
        folder = (
            Path(work) / ".gnost" / RemoteUrl(url).slug
        )  # one folder per repository
        guide = folder / "ONBOARD.md"
        report = subprocess.run(
            [sys.executable, "-m", "gnost.cli.app", "analyze", url, "-o", "--quiet"],
            cwd=work,
            env=dict(os.environ, GNOST_NO_UPDATE_CHECK="1", GNOST_NO_PROGRESS="1"),
        )
        if done.returncode != 0 or not guide.is_file():
            return False
        target = OUT / name
        shutil.rmtree(target, ignore_errors=True)
        (target / "flow").mkdir(parents=True)
        shutil.copy(guide, target / "ONBOARD.md")
        for page in (folder / "flow").iterdir():
            if page.suffix in (".md", ".mmd"):  # the pages ONBOARD.md links to
                shutil.copy(page, target / "flow" / page.name)
        analysis = folder / "analysis"
        if report.returncode == 0 and (analysis / "analysis.json").is_file():
            (target / "analysis").mkdir()
            shutil.copy(
                analysis / "analysis.json", target / "analysis" / "analysis.json"
            )
        return True


def main(names: List[str]) -> int:
    """Build the named projects (all by default); returns 1 if any failed."""
    failed = [n for n in (names or PROJECTS) if not build(n, PROJECTS[n])]
    print("failed:", ", ".join(failed) if failed else "none")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
