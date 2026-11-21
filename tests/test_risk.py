"""Risk (caution score x change activity): the calculator, the settings and the report."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, List, Optional

import pytest

from gitrepo import make_repo
from gnost.cli.commands.onboard import run
from gnost.config.settings import ConfigError, GnostConfig, _validate
from gnost.core.caution import CautionScore, Factor
from gnost.core.risk import RiskCalculator, RiskSettings
from gnost.vcs.git import GitRunner
from gnost.vcs.history import FileChange, HistorySettings, Hotspot

needs_git = pytest.mark.skipif(
    not GitRunner().available(), reason="git is not installed"
)
ROOT = os.path.abspath("/project")


def structural(path: str, score: float, *factors: str) -> CautionScore:
    return CautionScore(
        path=os.path.join(ROOT, path),
        score=score,
        level="high",
        partial=False,
        factors=[Factor(name, 1.0, 1.0, 0.5) for name in factors],
    )


def hotspot(path: str, score: float, commits: int = 4, authors: int = 2) -> Hotspot:
    change = FileChange(
        path,
        commits=commits,
        recent_commits=1,
        authors={f"a{i}" for i in range(authors)},
    )
    return Hotspot(change, score)


def rank(
    scores: List[CautionScore],
    hotspots: List[Hotspot],
    settings: Optional[RiskSettings] = None,
) -> List[str]:
    items = RiskCalculator(settings or RiskSettings()).rank(scores, hotspots, ROOT)
    return [f"{i.path}={i.risk:g}" for i in items]


def test_risk_is_the_caution_score_scaled_by_change_activity() -> None:
    scores = [structural("big.py", 80, "size"), structural("small.py", 80, "size")]
    hots = [hotspot("big.py", 100), hotspot("small.py", 50)]
    assert rank(scores, hots) == ["big.py=80", "small.py=40"]


def test_a_fragile_file_nobody_changes_is_not_listed() -> None:
    scores = [
        structural("fragile.py", 90, "complexity"),
        structural("busy.py", 60, "size"),
    ]
    assert rank(scores, [hotspot("busy.py", 100)]) == ["busy.py=60"]


def test_a_busy_but_simple_file_is_not_listed() -> None:
    scores = [structural("simple.py", 5, "size")]
    assert (
        rank(scores, [hotspot("simple.py", 100)]) == []
    )  # 5 is below the threshold of 20


def test_the_threshold_decides_what_is_listed() -> None:
    scores = [structural("a.py", 40, "size")]
    hots = [hotspot("a.py", 50)]  # risk 20
    assert rank(scores, hots, RiskSettings(threshold=20)) == ["a.py=20"]
    assert rank(scores, hots, RiskSettings(threshold=20.1)) == []


def test_churn_weight_dials_how_much_change_matters() -> None:
    scores = [structural("a.py", 60, "size")]
    hots = [hotspot("a.py", 50)]
    assert rank(scores, hots, RiskSettings(churn_weight=1.0)) == ["a.py=30"]
    assert rank(scores, hots, RiskSettings(churn_weight=0.5)) == ["a.py=45"]
    assert rank(scores, hots, RiskSettings(churn_weight=0.0)) == ["a.py=60"]


def test_the_order_is_by_risk_then_path() -> None:
    scores = [structural(p, 60, "size") for p in ("b.py", "a.py", "c.py")]
    hots = [hotspot("b.py", 100), hotspot("a.py", 100), hotspot("c.py", 80)]
    assert rank(scores, hots) == ["a.py=60", "b.py=60", "c.py=48"]


def test_each_item_explains_itself() -> None:
    scores = [structural("a.py", 70, "size", "complexity", "impact")]
    item = RiskCalculator(RiskSettings()).rank(
        scores, [hotspot("a.py", 80, commits=6, authors=3)], ROOT
    )[0]
    assert (item.structural, item.churn, item.risk) == (70, 80, 56)
    assert (item.commits, item.authors) == (6, 3)
    assert item.why == "large file, complex code"  # the strongest two


# ------------------------------------------------------------------- config


def test_risk_settings_come_from_the_config() -> None:
    config = GnostConfig()
    _validate({"risk": {"threshold": 35, "limit": 3, "churn_weight": 0.5}}, config)
    assert config.risk_settings() == RiskSettings(
        threshold=35, limit=3, churn_weight=0.5
    )
    assert GnostConfig().risk_settings() == RiskSettings()


@pytest.mark.parametrize(
    "bad",
    [
        {"threshold": 101},
        {"threshold": -1},
        {"limit": 0},
        {"churn_weight": 1.5},
        {"limit": "ten"},
    ],
)
def test_bad_risk_settings_are_refused(bad: object) -> None:
    with pytest.raises(ConfigError):
        _validate({"risk": bad}, GnostConfig())


# --------------------------------------------------------------- the report


def _stamp(day: str) -> str:
    return f"2026-{day}T10:00:00+00:00"


def _big(version: int) -> str:
    """A file big and branchy enough to score high on size and complexity."""
    body = "".join(
        f"def f{i}(x):\n    if x > {i}:\n        return x + {version}\n    return {i}\n\n"
        for i in range(260)
    )
    return body


@needs_git
def test_onboard_lists_the_fragile_file_that_keeps_changing(tmp_path: Path) -> None:
    commits = [
        (
            "Ada",
            {
                "main.py": "import big\nimport small\n",
                "big.py": _big(0),
                "small.py": "x = 0\n",
            },
            _stamp("01-05"),
        )
    ]
    for n, who in enumerate(["Grace", "Linus", "Ada", "Grace"], start=1):
        commits.append((who, {"big.py": _big(n)}, _stamp(f"0{n + 1}-10")))
    for n in range(1, 3):
        commits.append(("Ada", {"small.py": f"x = {n}\n"}, _stamp(f"05-0{n}")))
    repo = make_repo(tmp_path / "proj", commits)

    run(path=str(repo), history=HistorySettings(days=36500))
    md = (repo / ".gnost" / "ONBOARD.md").read_text(encoding="utf-8")
    section = md[md.index("## Risky and Changing") :]
    row = next(line for line in section.splitlines() if line.startswith("| `big.py`"))
    assert "large file" in row
    assert "`small.py`" not in section.split("## ")[1]  # simple files are not fragile

    data = json.loads((repo / ".gnost" / "insights.json").read_text())
    first = data["risk"]["files"][0]
    assert first["path"] == "big.py" and first["commits"] == 5 and first["authors"] == 3
    assert first["risk"] <= first["structural_score"] <= 100

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(Path("gnost/schemas/insights.schema.json").read_text())
    jsonschema.validate(data, schema)


def test_without_history_there_is_no_section_and_the_json_is_empty(
    fixture_repo: Callable[[str], Path],
) -> None:
    root = fixture_repo("python_app")
    run(path=str(root))
    assert "Risky and Changing" not in (root / ".gnost" / "ONBOARD.md").read_text(
        encoding="utf-8"
    )
    assert (
        json.loads((root / ".gnost" / "insights.json").read_text())["risk"]["files"]
        == []
    )
