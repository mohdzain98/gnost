"""Build throwaway git repositories with fixed dates and authors for tests."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

# (author name, files {path: text or None to delete}, ISO date)
Commit = Tuple[str, Dict[str, Optional[str]], str]


def _git(root: Path, *args: str, env: Optional[Dict[str, str]] = None) -> None:
    full = dict(os.environ)
    full.update({"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull})
    full.update(env or {})
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, env=full)


def make_repo(root: Path, commits: Iterable[Commit]) -> Path:
    """Create a repository at root with the given commits, oldest first."""
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    for author, files, when in commits:
        for rel, text in files.items():
            target = root / rel
            if text is None:
                target.unlink()
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        email = f"{author.lower().replace(' ', '.')}@example.com"
        env = {
            "GIT_AUTHOR_NAME": author,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_AUTHOR_DATE": when,
            "GIT_COMMITTER_NAME": author,
            "GIT_COMMITTER_EMAIL": email,
            "GIT_COMMITTER_DATE": when,
        }
        _git(root, "add", "-A", env=env)
        _git(
            root, "commit", "-q", "--allow-empty", "-m", f"change by {author}", env=env
        )
    return root
