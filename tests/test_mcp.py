"""`gnost mcp`: the protocol conversation through a real subprocess, plus tool and path rules."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from gnost.mcp import McpServer, default_tools
from gnost.mcp.project import ProjectData, ProjectError

APP = "from lib import helper\n\n\ndef main():\n    helper()\n\n\nif __name__ == '__main__':\n    main()\n"
LIB = "def helper():\n    return 1\n"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A small project with an onboard run already done."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "app.py").write_text(APP)
    (tmp_path / "lib.py").write_text(LIB)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "gnost.cli.app",
            "onboard",
            str(tmp_path),
            "--no-progress",
        ],
        check=True,
        capture_output=True,
    )
    return tmp_path


def talk(root: Path, *messages: Any) -> List[Optional[Dict[str, Any]]]:
    """Send raw lines (dicts become JSON) to `gnost mcp` and return the replies."""
    lines = [m if isinstance(m, str) else json.dumps(m) for m in messages]
    proc = subprocess.run(
        [sys.executable, "-m", "gnost.cli.app", "mcp", str(root)],
        input="\n".join(lines) + "\n",
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return [json.loads(line) for line in proc.stdout.splitlines()]


def call(ident: int, name: str, **arguments: Any) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": ident,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


def test_initialize_then_list_then_call(project: Path) -> None:
    replies = talk(
        project,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        call(3, "gnost_entry_points"),
    )
    assert len(replies) == 3  # the notification gets no reply
    assert replies[0]["result"]["protocolVersion"] == "2024-11-05"
    assert replies[0]["result"]["serverInfo"]["name"] == "gnost"
    names = {t["name"] for t in replies[1]["result"]["tools"]}
    assert names == {
        "gnost_overview",
        "gnost_entry_points",
        "gnost_hotspots",
        "gnost_risk",
        "gnost_file",
        "gnost_changes",
    }
    assert "app.py" in replies[2]["result"]["content"][0]["text"]


def test_file_tool_shows_imports_and_importers(project: Path) -> None:
    reply = talk(project, call(1, "gnost_file", file="lib.py"))[0]
    text = reply["result"]["content"][0]["text"]
    assert "Imported by (1): app.py" in text


def test_a_path_outside_the_project_is_refused(project: Path) -> None:
    reply = talk(project, call(1, "gnost_file", file="../../etc/passwd"))[0]
    assert reply["result"]["isError"] is True
    assert "outside the project" in reply["result"]["content"][0]["text"]


def test_missing_analysis_tells_the_agent_what_to_run(tmp_path: Path) -> None:
    reply = talk(tmp_path, call(1, "gnost_overview"))[0]
    assert reply["result"]["isError"] is True
    assert "gnost onboard" in reply["result"]["content"][0]["text"]


def test_protocol_errors(project: Path) -> None:
    replies = talk(
        project,
        "{not json",
        {"jsonrpc": "2.0", "id": 1, "method": "nope"},
        call(2, "no_such_tool"),
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "gnost_risk", "arguments": []},
        },
        {"jsonrpc": "2.0", "id": 4, "method": "ping"},
        "[1, 2]",
    )
    codes = [r.get("error", {}).get("code") for r in replies]
    assert codes == [-32700, -32601, -32602, -32602, None, -32600]
    assert replies[4]["result"] == {}


def test_limit_must_be_a_number(project: Path) -> None:
    reply = talk(project, call(1, "gnost_hotspots", limit="many"))[0]
    assert reply["result"]["isError"] is True


def test_changes_tool_is_read_only_and_refuses_option_like_refs(project: Path) -> None:
    reply = talk(project, call(1, "gnost_changes", refs="--output=x"))[0]
    assert reply["result"]["isError"] is True
    assert not (project / "x").exists()


def test_the_server_never_writes_files(project: Path) -> None:
    before = sorted(str(p) for p in project.rglob("*") if p.is_file())
    talk(
        project,
        call(1, "gnost_overview"),
        call(2, "gnost_risk"),
        call(3, "gnost_hotspots"),
    )
    assert sorted(str(p) for p in project.rglob("*") if p.is_file()) == before


def test_insights_reload_when_the_file_changes(project: Path) -> None:
    data = ProjectData(str(project))
    first = data.insights["project"]["name"]
    path = project / ".gnost" / "insights.json"
    payload = json.loads(path.read_text())
    payload["project"]["name"] = "renamed"
    path.write_text(json.dumps(payload))
    os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 5))
    assert first != "renamed" and data.insights["project"]["name"] == "renamed"
    with pytest.raises(ProjectError):
        data.resolve("")


def test_server_object_handles_lines_without_a_process(project: Path) -> None:
    server = McpServer(ProjectData(str(project)), default_tools())
    assert server.handle_line('{"jsonrpc":"2.0","method":"x"}') is None
