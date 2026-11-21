"""Cloning a remote repository safely so GNOST can read it.

`RemoteUrl` recognises https and ssh addresses (and nothing else). `RemoteClone` makes a
partial clone in a temporary folder with hooks, symlinks and submodules off, a time and a size
limit, and always removes it. A repository you do not trust is only ever read, never run.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from types import TracebackType
from typing import Dict, List, Optional, Sequence, Type

from gnost.vcs.git import GitError, GitRunner

SCP_STYLE = re.compile(r"^[\w.-]+@[\w.-]+:[\w./~-]+$")  # git@github.com:owner/repo.git
FALLBACK_DEPTH = 500
MB = 1024 * 1024


class RemoteError(GitError):
    """The address is not allowed or the clone failed; the message tells the user what to do."""


@dataclass(frozen=True)
class RemoteUrl:
    """A repository address GNOST is willing to clone."""

    text: str

    @staticmethod
    def looks_remote(text: str) -> bool:
        """True when the argument is an address rather than a folder on disk."""
        lowered = text.lower()
        return lowered.startswith(
            ("http://", "https://", "ssh://", "git://", "ext::")
        ) or bool(SCP_STYLE.match(text) and not os.path.exists(text))

    @classmethod
    def parse(cls, text: str) -> "RemoteUrl":
        """Accept https:// and ssh addresses; refuse anything that could run a program."""
        value = text.strip()
        lowered = value.lower()
        if value.startswith("-") or any(c in value for c in "\n\r\0 "):
            raise RemoteError(f"not a valid repository address: {text!r}")
        if lowered.startswith(("https://", "ssh://")) or SCP_STYLE.match(value):
            return cls(value)
        if lowered.startswith(("http://", "git://")):
            raise RemoteError(
                "plain http:// and git:// addresses are not encrypted; use the https:// address"
            )
        raise RemoteError(
            f"unsupported repository address {text!r}; use https://... or git@host:owner/repo"
        )

    @property
    def name(self) -> str:
        """The repository name, for messages."""
        tail = re.split(r"[/:]", self.text.rstrip("/"))[-1]
        return tail[:-4] if tail.endswith(".git") else tail


@dataclass(frozen=True)
class CloneLimits:
    """How long a clone may take and how big the checked out files may get."""

    timeout: int = 600  # seconds
    max_megabytes: int = 500


class RemoteClone:
    """Clones one address into a temporary folder; `with` removes it again, even on Ctrl+C.

    Safe defaults: no hooks, no submodules, no symlinks, no prompts, only https and ssh.
    """

    def __init__(
        self,
        url: RemoteUrl,
        ref: Optional[str] = None,
        limits: Optional[CloneLimits] = None,
        runner: Optional[GitRunner] = None,
        protocols: Sequence[str] = ("https", "ssh"),
    ) -> None:
        self.url = url
        self.ref = ref
        self.limits = limits or CloneLimits()
        self.runner = runner or GitRunner(timeout=self.limits.timeout)
        self.protocols = tuple(protocols)
        self._temp: Optional[str] = None
        self.folder = ""

    def __enter__(self) -> str:
        self._temp = tempfile.mkdtemp(prefix="gnost-clone-")
        self.folder = os.path.join(self._temp, self.url.name or "repo")
        try:
            self._clone()
            self._check_size()
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return os.path.realpath(self.folder)

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        if self._temp:
            shutil.rmtree(self._temp, ignore_errors=True)
            self._temp = None

    # ------------------------------------------------------------ steps

    def _clone(self) -> None:
        """Partial clone first; a plain shallow clone if the server cannot filter."""
        try:
            self._git(["--filter=blob:none"])
        except GitError as first:
            shutil.rmtree(self.folder, ignore_errors=True)
            try:
                self._git([f"--depth={FALLBACK_DEPTH}"])
            except GitError as second:
                raise RemoteError(self._explain(second, first)) from second

    def _git(self, extra: List[str]) -> None:
        args = [
            "-c",
            "core.hooksPath=" + os.devnull,
            "-c",
            "core.symlinks=false",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "protocol.allow=never",
            *[
                part
                for proto in self.protocols
                for part in ("-c", f"protocol.{proto}.allow=always")
            ],
            "clone",
            "--no-tags",
            "--single-branch",
            "--no-recurse-submodules",
            *extra,
        ]
        if self.ref:
            args += ["--branch", self.ref]
        args += ["--", self.url.text, self.folder]
        self.runner.run(
            args, cwd=self._temp or ".", timeout=self.limits.timeout, env=self._env()
        )

    @staticmethod
    def _env() -> Dict[str, str]:
        """No prompts, no askpass helper, ssh must never wait for a password."""
        return {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "echo",
            "GIT_SSH_COMMAND": "ssh -o BatchMode=yes",
            "GIT_CONFIG_NOSYSTEM": "1",
        }

    def _check_size(self) -> None:
        """Refuse a checkout bigger than the limit."""
        total = 0
        for base, _dirs, files in os.walk(self.folder):
            for name in files:
                try:
                    total += os.lstat(os.path.join(base, name)).st_size
                except OSError:
                    continue
            if total > self.limits.max_megabytes * MB:
                raise RemoteError(
                    f"{self.url.name} is larger than {self.limits.max_megabytes} MB; "
                    "clone it yourself and run GNOST on the folder"
                )

    def _explain(self, error: GitError, first: GitError) -> str:
        """A short, actionable message for a failed clone."""
        text = f"{error}".lower() + f" {first}".lower()
        if "timed out" in text or "took longer" in text:
            return (
                f"cloning {self.url.name} took longer than {self.limits.timeout} seconds; "
                "clone it yourself and run GNOST on the folder"
            )
        if (
            "authentication" in text
            or "permission denied" in text
            or "could not read" in text
        ):
            return (
                f"could not clone {self.url.name}: access was refused. "
                "GNOST never asks for a password; use a public https:// address, or clone it "
                "yourself with your credentials and run GNOST on the folder"
            )
        if "not found" in text or "does not exist" in text:
            return f"could not clone {self.url.name}: the repository or branch was not found"
        return f"could not clone {self.url.name}: {error}"
