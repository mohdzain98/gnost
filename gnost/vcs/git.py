"""Running git safely and asking questions about a repository.

`GitRunner` is the one place that starts the git process (list arguments, no prompts,
fixed locale, a time limit). `GitRepository` wraps one repository on top of it.
Problems raise `GitError` with a message the user can act on.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tarfile
from typing import Dict, List, Optional

DEFAULT_TIMEOUT = 120


class GitError(Exception):
    """A git command failed; the message is meant for the user."""


class GitUnavailable(GitError):
    """git is not installed (or not on PATH)."""


class GitRunner:
    """Starts git commands with safe defaults; swap it out in tests."""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout

    def available(self) -> bool:
        """Whether a git executable is on PATH."""
        return shutil.which("git") is not None

    def run(
        self,
        args: List[str],
        cwd: str,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> str:
        """Run `git <args>` in cwd and return stdout as text; raise GitError on failure."""
        return self.run_bytes(args, cwd, timeout, env).decode("utf-8", "replace")

    def run_bytes(
        self,
        args: List[str],
        cwd: str,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> bytes:
        """Run `git <args>` in cwd and return raw stdout; raise GitError on any failure."""
        if not self.available():
            raise GitUnavailable(
                "git is not installed or not on PATH, so history is not available. "
                "Install git (https://git-scm.com) and run the command again."
            )
        limit = timeout or self.timeout
        try:
            done = subprocess.run(
                ["git", "-c", "core.quotepath=off", *args],
                cwd=cwd,
                capture_output=True,
                timeout=limit,
                env=self._environment(env),
            )
        except subprocess.TimeoutExpired as exc:
            raise GitError(f"git {args[0]} took longer than {limit} seconds") from exc
        except OSError as exc:
            raise GitError(f"could not run git: {exc}") from exc
        if done.returncode != 0:
            detail = done.stderr.decode("utf-8", "replace").strip().splitlines()
            raise GitError(
                f"git {args[0]} failed: {detail[-1] if detail else 'no details'}"
            )
        return done.stdout

    @staticmethod
    def _environment(extra: Optional[Dict[str, str]]) -> Dict[str, str]:
        """The process environment with prompts off and a stable locale."""
        env = dict(os.environ)
        env.update(
            {"GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C", "GIT_OPTIONAL_LOCKS": "0"}
        )
        env.update(extra or {})
        return env


class GitRepository:
    """One git repository (its top folder) and what can be asked of it."""

    def __init__(self, root: str, runner: Optional[GitRunner] = None) -> None:
        self.root = root
        self.runner = runner or GitRunner()

    @classmethod
    def containing(
        cls, path: str, runner: Optional[GitRunner] = None
    ) -> Optional["GitRepository"]:
        """The repository that contains path, or None. Raises GitUnavailable without git."""
        runner = runner or GitRunner()
        folder = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
        try:
            top = runner.run(
                ["rev-parse", "--show-toplevel"], folder, timeout=20
            ).strip()
        except GitUnavailable:
            raise
        except GitError:
            return None
        return cls(os.path.realpath(top), runner) if top else None

    def run(
        self, args: List[str], cwd: Optional[str] = None, timeout: Optional[int] = None
    ) -> str:
        """Run a git command here (or in cwd, a folder inside the repository)."""
        return self.runner.run(args, cwd or self.root, timeout)

    def is_shallow(self) -> bool:
        """True for a shallow clone (a CI checkout with fetch-depth 1), whose history is cut."""
        try:
            return (
                self.run(["rev-parse", "--is-shallow-repository"], timeout=20).strip()
                == "true"
            )
        except GitError:
            return False

    def commit_count(self) -> int:
        """Commits reachable from HEAD; 0 for an empty repository."""
        try:
            return int(self.run(["rev-list", "--count", "HEAD"], timeout=60).strip())
        except (GitError, ValueError):
            return 0

    def history_problem(self, allow_shallow: bool = False) -> Optional[str]:
        """Why history cannot be used here, as one sentence, or None if it can.

        `allow_shallow` accepts a cut-short history (a remote clone that had to be shallow).
        """
        if self.commit_count() == 0:
            return "the repository has no commits yet"
        if not allow_shallow and self.is_shallow():
            return (
                "this is a shallow clone, so the history is cut short; "
                "fetch it fully (in GitHub Actions: `fetch-depth: 0`)"
            )
        return None

    def resolve(self, ref: str) -> str:
        """The commit id a ref (branch, tag, `HEAD~3`, sha) points to; GitError if unknown."""
        if ref.startswith("-"):
            raise GitError(f"not a valid ref: {ref}")
        return self.run(
            ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"]
        ).strip()

    def merge_base(self, first: str, second: str) -> str:
        """The commit where two refs split (what a pull request is compared against)."""
        return self.run(["merge-base", first, second]).strip()

    def checkout_to(self, ref: str, dest: str, subpath: str = ".") -> None:
        """Export the files of `ref` (under subpath) into dest without touching the work tree."""
        args = ["archive", "--format=tar", ref]
        if subpath not in ("", "."):
            args += ["--", subpath]
        dest = os.path.realpath(dest)
        data = self.runner.run_bytes(args, self.root, timeout=600)
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            for member in tar.getmembers():
                target = os.path.realpath(os.path.join(dest, member.name))
                inside = target == dest or target.startswith(dest + os.sep)
                if not inside or not (member.isfile() or member.isdir()):
                    continue  # skips links and anything that would leave dest
                if hasattr(tarfile, "data_filter"):
                    tar.extract(member, dest, filter="data")
                else:
                    tar.extract(member, dest)
