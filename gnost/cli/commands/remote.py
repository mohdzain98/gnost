"""Lets `onboard`, `analyze` and `changes` take a repository address instead of a folder.

`RemoteTarget` decides whether the path argument is an address and, if so, clones it with
`RemoteClone`. While the clone is in use the process is marked as reading untrusted code, so
the analyzers ignore the repository's own tool configuration.
"""

from __future__ import annotations

import argparse
import os
import sys
from contextlib import contextmanager
from typing import Iterator, Optional

from gnost.analysis.utils.tool_command import UNTRUSTED_ENV
from gnost.vcs.remote import RemoteClone, RemoteUrl

COMMANDS = ("onboard", "analyze", "changes")


class RemoteTarget:
    """A repository address given where a folder is expected."""

    def __init__(self, url: RemoteUrl, ref: Optional[str]) -> None:
        self.url = url
        self.ref = ref

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> Optional["RemoteTarget"]:
        """The target for this command line, or None when the path is a normal folder."""
        path = getattr(args, "path", None)
        if args.cmd not in COMMANDS or not path or not RemoteUrl.looks_remote(path):
            return None
        return cls(RemoteUrl.parse(path), getattr(args, "ref", None))

    @contextmanager
    def open(self) -> Iterator[str]:
        """Clone, yield the local folder, then delete the clone and restore the environment."""
        print(
            f"Cloning {self.url.name} (read only, nothing in it is run)...",
            file=sys.stderr,
        )
        before = os.environ.get(UNTRUSTED_ENV)
        os.environ[UNTRUSTED_ENV] = "1"
        try:
            with RemoteClone(self.url, self.ref) as folder:
                yield folder
        finally:
            if before is None:
                os.environ.pop(UNTRUSTED_ENV, None)
            else:
                os.environ[UNTRUSTED_ENV] = before
