"""`gnost changes BASE[..HEAD]`: what a change touches, with risk and blast radius.

`ChangesCommand` resolves the refs, runs the ChangeAnalyzer, writes `.gnost/changes/` (Markdown
and JSON) and prints the chosen view. Returns an exit code, never raises for user mistakes.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Optional

from gnost.changes.analyzer import ChangeAnalyzer
from gnost.changes.impact import DEFAULT_DEPTH
from gnost.changes.refs import RefError, RefRange
from gnost.changes.report import ChangeReport
from gnost.changes.render import MarkdownRenderer, TextRenderer
from gnost.ci.exit_codes import ExitCode
from gnost.config.settings import ConfigError, load_config
from gnost.utils.footer import Footer
from gnost.utils.layout import LEGACY_OUTPUT_PATHS, OutputLayout
from gnost.vcs.git import GitError, GitRepository, GitUnavailable

FORMATS = ("text", "markdown", "json")


class ChangesCommand:
    """One run of `gnost changes` for a project folder."""

    def __init__(
        self,
        path: str,
        refs: str,
        depth: int = DEFAULT_DEPTH,
        output_format: str = "text",
        findings: bool = False,
        compare_base: bool = True,
        write: bool = True,
        output_root: Optional[str] = None,
        remote: bool = False,
    ) -> None:
        self.path = os.path.realpath(path)
        self.refs = refs
        self.depth = depth
        self.output_format = output_format
        self.findings = findings
        self.compare_base = compare_base
        self.write = write
        self.output_root = output_root
        self.remote = remote

    def run(self) -> int:
        """Run the analysis and report. 0 on success, 2 for a usage problem, 1 on errors."""
        try:
            # a remote repository's own config is never read
            config = load_config(self.output_root if self.remote else self.path)
            repo = GitRepository.containing(self.path)
        except ConfigError as exc:
            return self._fail(str(exc), ExitCode.USAGE)
        except GitUnavailable as exc:
            return self._fail(str(exc), ExitCode.USAGE)
        if repo is None:
            return self._fail(
                f"{self.path} is not inside a git repository", ExitCode.USAGE
            )
        if self.depth < 1:
            return self._fail("--depth must be 1 or more", ExitCode.USAGE)
        layout = OutputLayout(self.output_root or repo.root, config.output_dir)
        try:
            refs = RefRange.parse(self.refs, repo)
            analyzer = ChangeAnalyzer(
                repo,
                self.path,
                exclude=list(config.exclude or [])
                + [layout.relative_name, *LEGACY_OUTPUT_PATHS],
                depth=self.depth,
                compare_base=self.compare_base,
                findings=self.findings,
                caution=config.caution_settings(),
                history=config.history_settings(),  # a remote clone is complete enough
                risk=config.risk_settings(),
            )
            report = analyzer.analyze(refs)
        except RefError as exc:
            return self._fail(str(exc), ExitCode.USAGE)
        except GitError as exc:
            return self._fail(str(exc), ExitCode.ERROR)

        markdown = MarkdownRenderer(Footer(config.footer)).render(report)
        if self.write:
            self._write(layout, markdown, report.to_dict())
        self._print(report, markdown)
        return ExitCode.OK

    def _write(self, layout: OutputLayout, markdown: str, data: Dict[str, Any]) -> None:
        """Save changes.md and changes.json in the output folder."""
        layout.prepare()
        os.makedirs(layout.changes_dir, exist_ok=True)
        with open(layout.changes_md, "w", encoding="utf-8") as f:
            f.write(markdown)
        with open(layout.changes_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        print(f"Report written to {layout.changes_md}", file=sys.stderr)

    def _print(self, report: ChangeReport, markdown: str) -> None:
        """Show the report in the requested format on stdout."""
        if self.output_format == "markdown":
            print(markdown, end="")
        elif self.output_format == "json":
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(TextRenderer().render(report))

    @staticmethod
    def _fail(message: str, code: int) -> int:
        print(f"gnost: {message}", file=sys.stderr)
        return int(code)


def run(
    path: str,
    refs: str,
    depth: int = DEFAULT_DEPTH,
    output_format: str = "text",
    findings: bool = False,
    compare_base: bool = True,
    write: bool = True,
    output_root: Optional[str] = None,
    remote: bool = False,
) -> int:
    """Entry point used by the CLI."""
    return ChangesCommand(
        path,
        refs,
        depth,
        output_format,
        findings,
        compare_base,
        write,
        output_root,
        remote,
    ).run()
