import sys

from gnost.analysis.utils import tool_command as tc


def test_plain_install_uses_tool_name():
    assert tc.tool_command("radon") == ["radon"]
    assert tc.tool_command("ruff") == ["ruff"]


def test_frozen_python_tools_use_hidden_entry(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert tc.tool_command("mypy") == [sys.executable, "--run-tool", "mypy"]
    assert tc.bundled_tool_available("bandit")
    assert not tc.bundled_tool_available("jscpd")


def test_unknown_tool_entry_is_rejected():
    assert tc.run_tool_entry(["nope"]) == 2
