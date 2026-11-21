"""Golden-file snapshots of `gnost onboard` output on the fixture projects.

Regenerate with: UPDATE_SNAPSHOTS=1 pytest tests/test_onboard_snapshots.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from gnost import __version__
from gnost.cli.commands.onboard import run

SNAPSHOTS = Path(__file__).parent / "snapshots"
PROJECTS = [
    "python_app",
    "js_app",
    "ts_app",
    "java_app",
    "cyclic_py",
    "package_app",
    "react_app",
    "deferred_cycle",
]
OUTPUTS = [
    ".gnost/ONBOARD.md",
    ".gnost/flow/FLOW-full.md",
    ".gnost/flow/FLOW-full.mmd",
    ".gnost/flow/FLOW-overview.mmd",
    ".gnost/flow/entry-paths.md",
    ".gnost/flow/folder-paths.md",
]
# Written only when the project has something to show.
OPTIONAL_OUTPUTS = [".gnost/flow/function-flow.md"]


def _normalize(text: str, root: Path) -> str:
    for variant in {str(root), str(root.resolve())}:
        text = text.replace(variant, "<ROOT>")
    # Known quirk: "First Files to Read" shortens absolute paths to their last
    # two parts, which can leak the parent (temp) directory name.
    text = text.replace(f"{root.parent.name}/", "")
    return text.replace(
        f" {__version__}.", " <VERSION>."
    )  # the footer names the version


@pytest.mark.parametrize("project", PROJECTS)
def test_onboard_snapshot(project, fixture_repo):
    root = fixture_repo(project)
    run(path=str(root))

    optional = [r for r in OPTIONAL_OUTPUTS if (root / r).exists()]
    for rel in OUTPUTS + optional:
        actual = _normalize((root / rel).read_text(encoding="utf-8"), root)
        golden = SNAPSHOTS / project / rel

        if os.environ.get("UPDATE_SNAPSHOTS"):
            golden.parent.mkdir(parents=True, exist_ok=True)
            golden.write_text(actual, encoding="utf-8")
            continue

        assert golden.exists(), (
            f"missing snapshot {golden}; run with UPDATE_SNAPSHOTS=1"
        )
        assert actual == golden.read_text(encoding="utf-8"), f"{project}/{rel} changed"


def test_onboard_mermaid_only(fixture_repo):
    root = fixture_repo("python_app")
    run(path=str(root), diagram_only=True)
    assert (root / ".gnost/flow/FLOW-full.mmd").exists()
    assert not (root / ".gnost/ONBOARD.md").exists()
