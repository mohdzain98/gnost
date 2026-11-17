"""Shared pytest helpers: fixture copying and fake repo roots."""

from __future__ import annotations

import os
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
        if os.environ.get("GNOST_TEST_CRLF"):
            for p in dest.rglob("*"):
                if p.is_file() and p.suffix in {
                    ".py",
                    ".js",
                    ".ts",
                    ".tsx",
                    ".java",
                    ".json",
                    ".toml",
                    ".jsx",
                }:
                    p.write_bytes(
                        p.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
                    )
        (dest / ".git").mkdir()
        return dest

    return _make
