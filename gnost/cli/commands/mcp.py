"""`gnost mcp [PATH]`: serve the project's GNOST facts to coding agents over stdio.

Loads the config for the output folder name, then hands stdin/stdout to the McpServer.
Read-only: it reads `.gnost/insights.json` and never writes or runs project code.
"""

from __future__ import annotations

import os
import sys

from gnost.ci.exit_codes import ExitCode
from gnost.config.settings import ConfigError, load_config
from gnost.mcp import McpServer, default_tools
from gnost.mcp.project import ProjectData


def run(path: str) -> int:
    """Serve until the client closes stdin. Returns an exit code."""
    root = os.path.abspath(path)
    if not os.path.isdir(root):
        print(f"gnost: not a folder: {root}", file=sys.stderr)
        return int(ExitCode.USAGE)
    try:
        config = load_config(root)
    except ConfigError as exc:
        print(f"gnost: {exc}", file=sys.stderr)
        return int(ExitCode.USAGE)
    server = McpServer(ProjectData(root, config.output_dir), default_tools())
    try:
        server.serve(sys.stdin, sys.stdout)
    except KeyboardInterrupt:
        return int(ExitCode.INTERRUPTED)
    return int(ExitCode.OK)
