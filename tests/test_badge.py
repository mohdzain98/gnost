"""`gnost analyze --badge`: the SVG, its colour, the README line and where it is written."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from gnost.cli.app import _badge_path
from gnost.config.settings import ConfigError, GnostConfig, _validate
from gnost.reporters.badge import ScoreBadge
from gnost.utils.layout import OutputLayout

SVG = "{http://www.w3.org/2000/svg}"


@pytest.mark.parametrize(
    "score, colour",
    [
        (9.62, "#44cc11"),
        (8.0, "#44cc11"),
        (7.99, "#dfb317"),
        (6.0, "#dfb317"),
        (5.96, "#e05d44"),
    ],
)
def test_the_colour_follows_the_terminal(score: float, colour: str) -> None:
    assert ScoreBadge(score).colour == colour


def test_the_badge_is_valid_svg_with_the_score() -> None:
    root = ET.fromstring(ScoreBadge(6.8).svg())
    texts = [t.text for t in root.iter(f"{SVG}text")]
    assert texts == ["gnost", "gnost", "6.80", "6.80"]
    assert root.find(f"{SVG}title").text == "gnost: 6.80 / 10"  # type: ignore[union-attr]
    assert int(root.get("width", "0")) > 50 and root.get("height") == "20"
    assert "href" not in ScoreBadge(6.8).svg()  # self-contained: nothing to load


def test_the_label_is_escaped() -> None:
    ET.fromstring(ScoreBadge(9, label="a<b&c").svg())  # still parses


def test_write_creates_the_folder(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "badge.svg"
    ScoreBadge(9.1).write(str(target))
    assert "9.10" in target.read_text(encoding="utf-8")


def test_the_readme_line_is_relative_to_the_repository(tmp_path: Path) -> None:
    badge = tmp_path / ".gnost" / "badge.svg"
    assert (
        ScoreBadge.markdown(str(badge), str(tmp_path))
        == "![GNOST score](.gnost/badge.svg)"
    )


def test_where_the_badge_goes(tmp_path: Path) -> None:
    layout = OutputLayout(str(tmp_path))
    assert _badge_path(None, None, layout) is None
    assert _badge_path(None, False, layout) is None
    assert _badge_path("", None, layout) == layout.badge_svg
    assert _badge_path(None, True, layout) == layout.badge_svg
    assert _badge_path(None, "docs/score.svg", layout) == os.path.join(
        str(tmp_path), "docs", "score.svg"
    )
    assert _badge_path("mine.svg", "docs/score.svg", layout) == os.path.abspath(
        "mine.svg"
    )


def test_the_config_value_is_checked() -> None:
    config = GnostConfig()
    _validate({"analyze": {"badge": True}}, config)
    assert config.get("analyze", "badge") is True
    with pytest.raises(ConfigError):
        _validate({"analyze": {"badge": 1}}, GnostConfig())
