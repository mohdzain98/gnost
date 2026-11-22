"""The MCP tools: one small class each, collected in a `ToolRegistry`.

Every tool is read-only and returns text for the agent. Add a tool by subclassing `Tool`
and listing it in `default_tools`; nothing else changes (open-closed).
"""

from __future__ import annotations

import contextlib
import io
from typing import Any, Dict, Iterable, List, Optional

from gnost.mcp.project import ProjectData, ProjectError

LIMIT_DEFAULT = 10
LIMIT_MAX = 50


class Tool:
    """Base class: a name, a description, a JSON schema for the arguments, and `run`."""

    name = ""
    description = ""
    properties: Dict[str, Any] = {}
    required: List[str] = []

    def schema(self) -> Dict[str, Any]:
        """The tool entry returned by `tools/list`."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": self.properties,
                "required": self.required,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": False},
        }

    def run(self, project: ProjectData, args: Dict[str, Any]) -> str:
        """Return the answer text; raise ProjectError for problems the agent should read."""
        raise NotImplementedError

    @staticmethod
    def limit(args: Dict[str, Any]) -> int:
        """The `limit` argument clamped to 1..LIMIT_MAX."""
        value = args.get("limit", LIMIT_DEFAULT)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ProjectError("`limit` must be a whole number")
        return max(1, min(value, LIMIT_MAX))


LIMIT_PROPERTY = {
    "limit": {
        "type": "integer",
        "description": f"How many items (default {LIMIT_DEFAULT}, at most {LIMIT_MAX})",
    }
}


class OverviewTool(Tool):
    """What the project is: languages, framework, size, how to run it."""

    name = "gnost_overview"
    description = (
        "Summary of the project: languages, framework, file count, how to install, "
        "run and test it, and architecture rule status."
    )

    def run(self, project: ProjectData, args: Dict[str, Any]) -> str:
        data = project.insights
        info = data.get("project", {})
        lines = [
            f"Project: {info.get('name', '?')}",
            f"Framework: {info.get('framework') or 'none detected'}",
            "Languages: "
            + (
                ", ".join(
                    f"{k} ({v} files)" for k, v in info.get("languages", {}).items()
                )
                or "none"
            ),
            f"Files: {info.get('files', 0)}; "
            f"entry points: {data.get('stats', {}).get('entry_points', 0)}; "
            f"import cycles: {data.get('stats', {}).get('cycles_import_time', 0)}",
        ]
        arch = data.get("architecture", {})
        if arch.get("configured"):
            lines.append(
                f"Architecture rules: {len(arch.get('violations', []))} violation(s)"
            )
        for group, steps in data.get("quickstart", {}).items():
            if steps:
                lines.append(f"{group.capitalize()}:")
                lines.extend(f"  - {step['text']}" for step in steps)
        return "\n".join(lines)


class EntryPointsTool(Tool):
    """Where the program starts."""

    name = "gnost_entry_points"
    description = (
        "Entry points of the project (where execution starts) and HTTP routes."
    )
    properties = LIMIT_PROPERTY

    def run(self, project: ProjectData, args: Dict[str, Any]) -> str:
        data, limit = project.insights, self.limit(args)
        lines = [
            f"{e['file']} [{e['priority']}]: {e['reason']}"
            for e in data.get("entry_points", [])[:limit]
        ]
        routes = data.get("routes", [])[:limit]
        if routes:
            lines.append("Routes:")
            lines.extend(
                f"  {r['method']} {r['path']} -> {r['file']}:{r['line']}"
                for r in routes
            )
        return "\n".join(lines) or "No entry points detected."


class HotspotsTool(Tool):
    """The files everything else depends on."""

    name = "gnost_hotspots"
    description = (
        "The most important files by how many files import them (fan-in), what they import "
        "and how close they are to the entry points. Read these first."
    )
    properties = LIMIT_PROPERTY

    def run(self, project: ProjectData, args: Dict[str, Any]) -> str:
        rows = project.insights.get("hotspots", [])[: self.limit(args)]
        return (
            "\n".join(
                f"{h['file']}: score {h['score']}, imported by {h['fan_in']}, "
                f"imports {h['fan_out']}, layer {h['layer']}"
                for h in rows
            )
            or "No hotspots."
        )


class RiskTool(Tool):
    """Files that are fragile and change often."""

    name = "gnost_risk"
    description = (
        "Files that are risky to change: structurally fragile and changing often (needs git "
        "history). Also lists caution areas (complexity, size, coupling)."
    )
    properties = LIMIT_PROPERTY

    def run(self, project: ProjectData, args: Dict[str, Any]) -> str:
        data, limit = project.insights, self.limit(args)
        lines = [
            f"{r['path']}: risk {r['risk']}, {r['commits']} commits, {r['authors']} authors"
            + (f" ({'; '.join(r['reasons'])})" if r.get("reasons") else "")
            for r in data.get("risk", {}).get("files", [])[:limit]
        ]
        cautions = data.get("caution_areas", [])[:limit]
        if cautions:
            lines.append("Caution areas:")
            lines.extend(
                f"  {c['path']} [{c['category']}, {c['severity']}]: {c['description']}"
                for c in cautions
            )
        return "\n".join(lines) or "No risky files recorded."


class FileTool(Tool):
    """One file: what it imports, who imports it, and what GNOST knows about it."""

    name = "gnost_file"
    description = (
        "For one file: the files it imports, the files that import it (what a change here "
        "can break), its layer, and any caution area."
    )
    properties = {
        "file": {"type": "string", "description": "Path relative to the project root"}
    }
    required = ["file"]

    def run(self, project: ProjectData, args: Dict[str, Any]) -> str:
        rel = project.resolve(args.get("file", ""))
        data = project.insights
        nodes = set(data.get("graph", {}).get("nodes", []))
        if rel not in nodes:
            raise ProjectError(f"{rel} is not in the dependency graph")
        edges = project.edges()
        imports = sorted(e["target"] for e in edges if e["source"] == rel)
        importers = sorted(e["source"] for e in edges if e["target"] == rel)
        layer = next(
            (n for n, files in data.get("layers", {}).items() if rel in files), "?"
        )
        lines = [f"{rel} (layer: {layer})"]
        lines.append(f"Imports ({len(imports)}): " + ", ".join(imports[:LIMIT_MAX]))
        lines.append(
            f"Imported by ({len(importers)}): " + ", ".join(importers[:LIMIT_MAX])
        )
        lines.extend(
            f"Caution [{c['category']}, {c['severity']}]: {c['description']}"
            for c in data.get("caution_areas", [])
            if c["path"] == rel
        )
        return "\n".join(lines)


class ChangesTool(Tool):
    """Impact of a change, computed from git (writes nothing)."""

    name = "gnost_changes"
    description = (
        "What a change touches: changed files with risk, files that depend on them, routes "
        "and import cycles. `refs` is a base ref (e.g. main) or BASE..HEAD."
    )
    properties = {
        "refs": {"type": "string", "description": "Base ref or BASE..HEAD, e.g. main"}
    }
    required = ["refs"]

    def run(self, project: ProjectData, args: Dict[str, Any]) -> str:
        from gnost.cli.commands.changes import ChangesCommand

        refs = args.get("refs")
        if not isinstance(refs, str) or not refs.strip() or refs.startswith("-"):
            raise ProjectError("`refs` must be a git ref such as main or main..HEAD")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ChangesCommand(
                project.root, refs, output_format="markdown", write=False
            ).run()
        if code not in (0, 3):
            raise ProjectError(err.getvalue().strip() or "gnost changes failed")
        return out.getvalue() or "No changes."


class ToolRegistry:
    """The tools by name; `call` runs one and turns problems into tool errors."""

    def __init__(self, tools: Iterable[Tool]) -> None:
        self._tools = {t.name: t for t in tools}

    def list(self) -> List[Dict[str, Any]]:
        """The `tools/list` payload."""
        return [t.schema() for t in self._tools.values()]

    def has(self, name: str) -> bool:
        """True when a tool with this name exists."""
        return name in self._tools

    def call(
        self, name: str, args: Optional[Dict[str, Any]], project: ProjectData
    ) -> Dict[str, Any]:
        """Run a tool; the result follows MCP (`content` + `isError`)."""
        try:
            text = self._tools[name].run(project, args or {})
            return {"content": [{"type": "text", "text": text}], "isError": False}
        except ProjectError as exc:
            return {"content": [{"type": "text", "text": str(exc)}], "isError": True}
        except Exception as exc:  # a tool bug must not end the session
            message = f"{name} failed: {exc}"
            return {"content": [{"type": "text", "text": message}], "isError": True}


def default_tools() -> ToolRegistry:
    """All tools GNOST offers."""
    return ToolRegistry(
        [
            OverviewTool(),
            EntryPointsTool(),
            HotspotsTool(),
            RiskTool(),
            FileTool(),
            ChangesTool(),
        ]
    )
