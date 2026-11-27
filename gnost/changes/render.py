"""Turns a ChangeReport into Markdown (also the pull request comment) and terminal text.

`MarkdownRenderer` starts with a hidden marker so the GitHub Action can find and update its own
comment, and ends with a footer linking to GNOST. `TextRenderer` is the short terminal summary.
"""

from __future__ import annotations

from typing import Iterable, List

from gnost.changes.report import ChangeReport
from gnost.utils.footer import Footer

COMMENT_MARKER = "<!-- gnost-changes -->"
LIST_LIMIT = 15
ICONS = {"added": "A", "modified": "M", "deleted": "D", "renamed": "R"}


def _line_delta(f: "ChangedFile") -> str:
    if f.added is None or f.removed is None:
        return " (binary)"
    return f" (+{f.added} -{f.removed})"


class MarkdownRenderer:
    """Writes the report as Markdown that GitHub shows well."""

    def __init__(self, footer: Footer = Footer()) -> None:
        self.footer = footer

    def render(self, report: ChangeReport) -> str:
        """The whole document, ending with a newline."""
        parts: List[str] = [
            COMMENT_MARKER,
            f"## GNOST: what changed in `{report.label}`",
            self._summary(report),
            self._risk(report),
            self._cycles(report),
            self._architecture(report),
            self._routes(report),
            self._blast(report),
            self._findings(report),
            self._files(report),
            "\n".join(f"> {n}" for n in report.notes),
            self.footer.for_languages(report.languages).line(),
        ]
        return "\n\n".join(p for p in parts if p).strip() + "\n"

    def _summary(self, r: ChangeReport) -> str:
        c = r.counts
        bits = [f"{n} {name}" for name, n in c.items() if n]
        head = f"**{len(r.files)} files changed** ({', '.join(bits) or 'none'})"
        if r.affected:
            return f"{head}; **{len(r.affected)}** other files depend on them."
        return head + "."

    def _risk(self, r: ChangeReport) -> str:
        if not r.risks:
            return "**Risk:** no changed file is fragile enough to flag."
        rows = [
            "**Risky files in this change**",
            "",
            "| File | Risk | Why |",
            "|---|---|---|",
        ]
        for x in r.risks[:LIST_LIMIT]:
            rows.append(f"| `{x.path}` | {x.level:.0f} | {x.why or '-'} |")
        return "\n".join(rows)

    def _cycles(self, r: ChangeReport) -> str:
        if not r.cycles_compared:
            return ""
        lines = [
            f"- New circular dependency ({c.kind}): {', '.join(f'`{f}`' for f in c.files)}"
            for c in r.new_cycles
        ] + [
            f"- Fixed circular dependency: {', '.join(f'`{f}`' for f in c.files)}"
            for c in r.fixed_cycles
        ]
        return "**Circular dependencies**\n\n" + "\n".join(lines) if lines else ""

    def _architecture(self, r: ChangeReport) -> str:
        change = r.architecture
        if change is None or not change.configured:
            return ""
        lines = [
            f"- Breaks `{v['rule']}`: `{v['source']}` imports `{v['target']}`"
            for v in change.new
        ] + [
            f"- Fixed `{v['rule']}`: `{v['source']}` no longer imports `{v['target']}`"
            for v in change.fixed
        ]
        if not lines:
            return "**Architecture rules:** this change adds no violations."
        title = (
            "**Architecture rules**"
            if change.compared
            else "**Architecture rules** (base not scanned: violations in changed files)"
        )
        return title + "\n\n" + "\n".join(lines)

    def _routes(self, r: ChangeReport) -> str:
        if not r.routes:
            return ""
        lines = [
            f"- `{x.method} {x.path}` ({x.state}) in `{x.file}`"
            for x in r.routes[:LIST_LIMIT]
        ]
        return "**Routes touched**\n\n" + "\n".join(lines)

    def _blast(self, r: ChangeReport) -> str:
        if not r.affected:
            return ""
        lines = [
            f"- `{a.path}` (distance {a.depth}, via `{a.via}`)"
            for a in r.affected[:LIST_LIMIT]
        ]
        more = len(r.affected) - LIST_LIMIT
        if more > 0:
            lines.append(f"- … and {more} more")
        return (
            f"<details><summary>Blast radius: {len(r.affected)} files</summary>\n\n"
            + "\n".join(lines)
            + "\n\n</details>"
        )

    def _findings(self, r: ChangeReport) -> str:
        if r.findings is None:
            return ""
        if not r.findings:
            return "**Findings in changed files:** none."
        lines = [
            f"- {f.severity}: {f.title} (`{f.file}:{f.line}`)"
            for f in r.findings[:LIST_LIMIT]
        ]
        return f"**Findings in changed files ({len(r.findings)})**\n\n" + "\n".join(
            lines
        )

    def _files(self, r: ChangeReport) -> str:
        lines = [
            f"- {ICONS[f.status]} `{f.old_path} → {f.path}`{_line_delta(f)}"
            if f.old_path
            else f"- {ICONS[f.status]} `{f.path}`{_line_delta(f)}"
            for f in r.files[: LIST_LIMIT * 4]
        ]
        return (
            f"<details><summary>Changed files ({len(r.files)})</summary>\n\n"
            + "\n".join(lines)
            + "\n\n</details>"
            if lines
            else ""
        )


class TextRenderer:
    """The short summary printed in the terminal."""

    def render(self, report: ChangeReport) -> str:
        """Plain text lines, no colors, so it also works in CI logs."""
        c = report.counts
        out = [
            f"Changes {report.label}: {len(report.files)} files "
            f"({c['added']} added, {c['modified']} modified, {c['deleted']} deleted, {c['renamed']} renamed)",
            f"Blast radius: {len(report.affected)} files depend on them (depth {report.depth})",
        ]
        out += self._section(
            "Changed files",
            (
                f"{ICONS[f.status]} {f.old_path} -> {f.path}{_line_delta(f)}"
                if f.old_path
                else f"{ICONS[f.status]} {f.path}{_line_delta(f)}"
                for f in report.files
            ),
        )
        out += self._section(
            "Risky files",
            (f"{x.path}  risk {x.level:.0f}  {x.why}" for x in report.risks),
        )
        out += self._section(
            "New circular dependencies",
            (" -> ".join(c.files) for c in report.new_cycles),
        )
        out += self._section(
            "Fixed circular dependencies",
            (" -> ".join(c.files) for c in report.fixed_cycles),
        )
        if report.architecture is not None and report.architecture.configured:
            out += self._section(
                "Architecture rules broken by this change",
                (
                    f"{v['rule']}: {v['source']} -> {v['target']}"
                    for v in report.architecture.new
                ),
            )
            out += self._section(
                "Architecture rules fixed by this change",
                (
                    f"{v['rule']}: {v['source']} -> {v['target']}"
                    for v in report.architecture.fixed
                ),
            )
        out += self._section(
            "Routes touched",
            (f"{x.method} {x.path} ({x.state})" for x in report.routes),
        )
        if report.findings is not None:
            out += self._section(
                f"Findings in changed files ({len(report.findings)})",
                (
                    f"{f.severity}: {f.title} ({f.file}:{f.line})"
                    for f in report.findings[:10]
                ),
            )
        out += [f"Note: {n}" for n in report.notes]
        return "\n".join(out)

    @staticmethod
    def _section(title: str, lines: Iterable[str]) -> List[str]:
        rows = [f"  {x}" for x in lines]
        if len(rows) > 10:
            rows = rows[:10] + [f"  ... and {len(rows) - 10} more (see changes.md)"]
        return [f"{title}:", *rows] if rows else []
