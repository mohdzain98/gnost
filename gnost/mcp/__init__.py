"""`gnost mcp`: a read-only Model Context Protocol server over stdio.

Gives coding agents the facts GNOST already knows about a project (entry points,
hotspots, risk, file neighbours, change impact). No dependencies, never writes files.
"""

from gnost.mcp.server import McpServer
from gnost.mcp.tools import ToolRegistry, default_tools

__all__ = ["McpServer", "ToolRegistry", "default_tools"]
