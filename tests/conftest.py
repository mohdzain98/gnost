"""Shared pytest helpers: fixture copying and fake repo roots."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

# Fixture projects contain files named test_*.py that must not be collected.
collect_ignore_glob = ["fixtures/*"]


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Callable[[str], Path]:
    """Copy a fixture project into tmp_path and mark it as a repo root."""

    def _make(name: str) -> Path:
        dest = tmp_path / name
        shutil.copytree(FIXTURES / name, dest)
        (dest / ".git").mkdir()
        return dest

    return _make
