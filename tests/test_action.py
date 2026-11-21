"""The GitHub Action (action.yml): it is valid, and every input it reads is declared."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

ACTION = Path(__file__).resolve().parent.parent / "action.yml"


@pytest.fixture(scope="module")
def action() -> Dict[str, Any]:
    return yaml.safe_load(ACTION.read_text(encoding="utf-8"))


def test_the_action_is_a_composite_action_with_a_name(action: Dict[str, Any]) -> None:
    assert action["name"] and action["description"]
    assert action["runs"]["using"] == "composite"
    assert all("run" in s or "uses" in s for s in action["runs"]["steps"])
    assert all("shell" in s for s in action["runs"]["steps"] if "run" in s)


def test_every_input_it_reads_is_declared_with_a_default(
    action: Dict[str, Any],
) -> None:
    text = ACTION.read_text(encoding="utf-8")
    used = set(re.findall(r"inputs\.([a-z\-]+)", text))
    assert used and used <= set(action["inputs"])
    assert all(
        "default" in spec and spec["description"] for spec in action["inputs"].values()
    )


def test_the_flags_it_passes_exist_in_the_command_line() -> None:
    import gnost.cli.app as app  # noqa: F401 - makes sure the parser can be built

    text = ACTION.read_text(encoding="utf-8")
    for flag in (
        "--sarif",
        "--fail-under",
        "--baseline",
        "--fail-on-new",
        "--no-progress",
        "-o",
    ):
        assert flag in text
    cli = Path(app.__file__).read_text(encoding="utf-8")
    for flag in (
        "--sarif",
        "--fail-under",
        "--baseline",
        "--fail-on-new",
        "--no-progress",
    ):
        assert f'"{flag}"' in cli


def test_the_outputs_point_at_a_real_step(action: Dict[str, Any]) -> None:
    ids = {s.get("id") for s in action["runs"]["steps"]}
    step = re.search(
        r"steps\.([a-z\-]+)\.outputs", action["outputs"]["exit-code"]["value"]
    ).group(1)  # type: ignore[union-attr]
    assert step in ids


def test_the_comment_step_uses_the_same_marker_as_the_markdown_report() -> None:
    from gnost.changes.render import COMMENT_MARKER

    assert COMMENT_MARKER in ACTION.read_text(encoding="utf-8")
