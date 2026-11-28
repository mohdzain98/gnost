"""Build the showcase gallery: run `gnost onboard` on well-known projects and keep the guides.

Usage: python scripts/build_gallery.py [--analysis-only] [name ...]   (needs network and git)
Writes docs/gallery/<name>/ONBOARD.md, its flow/ pages, mindmap.svg (the project map) and
analysis/analysis.json; docs/gallery.rst links to them.
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


def gallery_note(data: dict, listed: int) -> str:
    """Say how many findings are shown, listed and left out by max_findings (all are scored)."""
    capped = sum(
        int(count)
        for metric in data.get("analysis_metrics", [])
        for count in (metric.get("capped_by_severity") or {}).values()
    )
    over = f", and {capped:,} more over the max_findings cap" if capped else ""
    return (
        f"Showing the {len(data['findings']):,} most severe of {listed:,} listed findings{over}; "
        "the score (summary.score) counts all of them."
    )


def trim_report(source: Path, target: Path, url: str) -> None:
    """Copy an analysis report with the most severe findings only and no local paths."""
    data = json.loads(source.read_text(encoding="utf-8"))
    findings = sorted(
        data.get("findings", []),
        key=lambda f: SEVERITY_ORDER.get(str(f.get("severity")), 9),
    )
    data["findings"] = findings[:FINDINGS_KEPT]
    scrub_paths(data, url)
    data["gallery_note"] = gallery_note(data, len(findings))
    target.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


def analyze_into(url: str, work: str, target: Path) -> bool:
    """Run `gnost analyze` on the repository and write the trimmed report; True on success."""
    report = subprocess.run(
        [sys.executable, "-m", "gnost.cli.app", "analyze", url, "-o", "--quiet"],
        cwd=work,
        env=dict(os.environ, GNOST_NO_UPDATE_CHECK="1", GNOST_NO_PROGRESS="1"),
    )
    source = Path(work) / ".gnost" / RemoteUrl(url).slug / "analysis" / "analysis.json"
    if (
        report.returncode not in (0, 3) or not source.is_file()
    ):  # 3: the score gate, not an error
        return False
    (target / "analysis").mkdir(parents=True, exist_ok=True)
    trim_report(source, target / "analysis" / "analysis.json", url)
    return True


def build(name: str, url: str, analysis_only: bool = False) -> bool:
    """Onboard and analyze one project in a temp folder and copy the results; True on success.

    With `analysis_only` the guide is left as it is and only the analysis report is replaced.
    """
    target = OUT / name
    with tempfile.TemporaryDirectory(prefix="gnost-gallery-") as work:
        if analysis_only:
            return analyze_into(url, work, target)
        done = subprocess.run(
            [
                sys.executable,
                "-m",
                "gnost.cli.app",
                "onboard",
                url,
                "--no-html",
                "--inject-mindmap",  # no README in the work folder: only writes the SVG
            ],
            cwd=work,
            env=dict(os.environ, GNOST_NO_UPDATE_CHECK="1"),
        )
        folder = (
            Path(work) / ".gnost" / RemoteUrl(url).slug
        )  # one folder per repository
        guide = folder / "ONBOARD.md"
        if done.returncode != 0 or not guide.is_file():
            return False
        shutil.rmtree(target, ignore_errors=True)
        (target / "flow").mkdir(parents=True)
        shutil.copy(guide, target / "ONBOARD.md")
        if (folder / "mindmap.svg").is_file():
            shutil.copy(folder / "mindmap.svg", target / "mindmap.svg")
        for page in (folder / "flow").iterdir():
            if page.suffix in (".md", ".mmd"):  # the pages ONBOARD.md links to
                shutil.copy(page, target / "flow" / page.name)
        analyze_into(url, work, target)
        return True


def main(args: List[str]) -> int:
    """Build the named projects (all by default); returns 1 if any failed."""
    analysis_only = "--analysis-only" in args
    names = [a for a in args if not a.startswith("--")]
    failed = [
        n for n in (names or PROJECTS) if not build(n, PROJECTS[n], analysis_only)
    ]
    print("failed:", ", ".join(failed) if failed else "none")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
