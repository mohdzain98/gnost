from pathlib import Path

from gnost.core.flow import FlowResult
from gnost.reporters.markdown import MarkdownReporter
from gnost.scanner.models import ScanResult


def test_markdown_reporter_writes_to_output_root_and_includes_tables(tmp_path: Path):
    repo_root = tmp_path / "repo"
    scan_root = repo_root / "gnost"
    scan_root.mkdir(parents=True)

    scan = ScanResult(
        root=str(scan_root),
        languages={"python": 1},
        files=[],
        entry_points=[],
        framework=None,
    )
    flow = FlowResult(entry_points=[], paths=[], layers={"entry": set(), "core": set(), "leaf": set()})

    loc_data = {
        "files": [],
        "by_folder": {},
        "by_language": {
            "py": {"files": 1, "loc": 42, "code": 30, "comments": 5, "blanks": 7}
        },
    }

    reporter = MarkdownReporter(
        scan=scan,
        flow=flow,
        output_file="ONBOARD.md",
        output_root=str(repo_root),
        loc_data=loc_data,
    )
    reporter.write()

    output_file = repo_root / "ONBOARD.md"
    assert output_file.exists()

    content = output_file.read_text(encoding="utf-8")
    assert "## Summary Table" in content
    assert "## Stats Table" in content
    assert "| Python | 1 | 42 |" in content
    assert "docs/flow/FLOW-full.md" in content
