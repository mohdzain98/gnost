"""JSON-RPC 2.0 over stdio: the subset of MCP an agent needs to list and call tools.

One JSON message per line in, one per line out. Notifications get no reply; stdout carries
only protocol messages (diagnostics go to stderr).
"""

from __future__ import annotations

import json
from typing import IO, Any, Dict, Optional

from gnost import __version__
from gnost.mcp.project import ProjectData
from gnost.mcp.tools import ToolRegistry

SUPPORTED_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS = (
    -32700,
    -32600,
    -32601,
    -32602,
)


class McpServer:
    """Reads requests from `stdin`, writes responses to `stdout`, until input ends."""

    def __init__(self, project: ProjectData, tools: ToolRegistry) -> None:
        self.project = project
        self.tools = tools

    def serve(self, stdin: IO[str], stdout: IO[str]) -> None:
        """Handle messages line by line until the client closes the input."""
        for line in stdin:
            if not line.strip():
                continue
            reply = self.handle_line(line)
            if reply is not None:
                stdout.write(json.dumps(reply, separators=(",", ":")) + "\n")
                stdout.flush()

    def handle_line(self, line: str) -> Optional[Dict[str, Any]]:
        """One raw line to one response (None for notifications)."""
        try:
            message = json.loads(line)
        except ValueError:
            return self._error(None, PARSE_ERROR, "Parse error")
        if not isinstance(message, dict) or not isinstance(message.get("method"), str):
            return self._error(
                message.get("id") if isinstance(message, dict) else None,
                INVALID_REQUEST,
                "Invalid request",
            )
        if "id" not in message:
            return None  # notification
        return self._dispatch(message["id"], message["method"], message.get("params"))

    def _dispatch(self, ident: Any, method: str, params: Any) -> Dict[str, Any]:
        params = params if isinstance(params, dict) else {}
        if method == "initialize":
            return self._result(ident, self._initialize(params))
        if method == "ping":
            return self._result(ident, {})
        if method == "tools/list":
            return self._result(ident, {"tools": self.tools.list()})
        if method == "tools/call":
            name = params.get("name")
            if not isinstance(name, str) or not self.tools.has(name):
                return self._error(ident, INVALID_PARAMS, f"Unknown tool: {name}")
            arguments = params.get("arguments")
            if arguments is not None and not isinstance(arguments, dict):
                return self._error(
                    ident, INVALID_PARAMS, "`arguments` must be an object"
                )
            return self._result(ident, self.tools.call(name, arguments, self.project))
        return self._error(ident, METHOD_NOT_FOUND, f"Method not found: {method}")

    @staticmethod
    def _initialize(params: Dict[str, Any]) -> Dict[str, Any]:
        wanted = params.get("protocolVersion")
        version = wanted if wanted in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0]
        return {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "gnost", "version": __version__},
            "instructions": (
                "Read-only facts about this codebase from GNOST: start with gnost_overview, "
                "then gnost_entry_points and gnost_hotspots."
            ),
        }

    @staticmethod
    def _result(ident: Any, result: Dict[str, Any]) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": ident, "result": result}

    @staticmethod
    def _error(ident: Any, code: int, message: str) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": ident,
            "error": {"code": code, "message": message},
        }
