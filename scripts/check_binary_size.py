"""Fails the build when a binary archive grew more than the budget over its baseline.

`SizeBudget` compares gnost-<version>-<platform>.(tar.gz|zip) with the 0.6.1 sizes stored in
packaging/binary-size-baseline.json plus a budget (15 MiB). On failure it lists the biggest bundled
folders so the cause is visible. Run: python scripts/check_binary_size.py dist-binary
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "packaging" / "binary-size-baseline.json"
MIB = 1024 * 1024
ARCHIVE = re.compile(r"^gnost-.+-(?P<platform>[a-z0-9]+-[a-z0-9]+)\.(?:tar\.gz|zip)$")


@dataclass(frozen=True)
class Verdict:
    """The result for one archive."""

    platform: str
    size: int
    baseline: int
    budget: int  # bytes

    @property
    def growth(self) -> int:
        """Bytes added since the baseline (negative when smaller)."""
        return self.size - self.baseline

    @property
    def ok(self) -> bool:
        """True when the growth is within the budget."""
        return self.growth <= self.budget

    def describe(self) -> str:
        """One line for the build log."""
        sign = "+" if self.growth >= 0 else "-"
        state = "ok" if self.ok else "OVER BUDGET"
        return (
            f"{self.platform}: {self.size / MIB:.2f} MiB, {sign}{abs(self.growth) / MIB:.2f} MiB "
            f"vs baseline {self.baseline / MIB:.2f} MiB (budget +{self.budget / MIB:.0f} MiB): {state}"
        )


class SizeBudget:
    """Compares binary archives with the stored baseline sizes."""

    def __init__(self, baseline_path: Path = BASELINE) -> None:
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
        self.budget = int(data.get("budget_mib", 15) * MIB)
        self.platforms: Dict[str, int] = {
            k: int(v) for k, v in data["platforms"].items()
        }

    def check(self, archive: Path) -> Verdict:
        """The verdict for one archive; ValueError for a name or platform that is not known."""
        match = ARCHIVE.match(archive.name)
        if not match:
            raise ValueError(f"not a gnost binary archive name: {archive.name}")
        platform = match.group("platform")
        if platform not in self.platforms:
            raise ValueError(f"no baseline for platform {platform}")
        return Verdict(
            platform, archive.stat().st_size, self.platforms[platform], self.budget
        )

    @staticmethod
    def biggest_folders(bundle: Path, limit: int = 8) -> List[str]:
        """The largest top-level folders and files inside the bundle, to explain a failure."""
        sizes: Dict[str, int] = {}
        for item in bundle.iterdir():
            files = (
                [item]
                if item.is_file()
                else [p for p in item.rglob("*") if p.is_file()]
            )
            sizes[item.name] = sum(p.stat().st_size for p in files)
        ranked = sorted(sizes.items(), key=lambda kv: -kv[1])[:limit]
        return [f"  {size / MIB:7.2f} MiB  {name}" for name, size in ranked]


def archives_in(folder: Path) -> List[Path]:
    """The gnost binary archives directly inside a folder."""
    return sorted(p for p in folder.iterdir() if ARCHIVE.match(p.name))


def main(argv: Optional[List[str]] = None, baseline: Optional[Path] = None) -> int:
    """Check every archive in the folder (default dist-binary); 1 when any is over budget."""
    args = sys.argv[1:] if argv is None else argv
    folder = Path(args[0]) if args else ROOT / "dist-binary"
    budget = SizeBudget(baseline or BASELINE)
    found = archives_in(folder)
    if not found:
        print(f"no gnost archive found in {folder}", file=sys.stderr)
        return 2
    failed = False
    for archive in found:
        verdict = budget.check(archive)
        print(verdict.describe())
        failed = failed or not verdict.ok
    if failed:
        bundle = folder / "bundle" / "gnost"
        if not bundle.is_dir():
            bundle = bundle / "_internal"
        internal = bundle / "_internal" if (bundle / "_internal").is_dir() else bundle
        if internal.is_dir():
            print("Biggest parts of the bundle:")
            print("\n".join(SizeBudget.biggest_folders(internal)))
        print(
            "If the growth is intended, raise the baseline in packaging/binary-size-baseline.json "
            "in a reviewed commit.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
