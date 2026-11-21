"""The two refs a change is measured between, and the files that differ.

`RefRange` parses `BASE`, `BASE..HEAD` or `BASE...HEAD`. Like a pull request, the comparison
starts at the commit where HEAD split from BASE. `DiffReader` lists the changed files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from gnost.vcs.git import GitError, GitRepository

STATUS_NAMES = {
    "A": "added",
    "C": "added",
    "M": "modified",
    "T": "modified",
    "D": "deleted",
    "R": "renamed",
}


class RefError(GitError):
    """A ref could not be understood; the message says which one."""


@dataclass(frozen=True)
class RefRange:
    """BASE and HEAD as typed, and the commits they resolve to."""

    base: str
    head: str
    base_commit: str  # where the two sides split
    head_commit: str

    @classmethod
    def parse(cls, text: str, repo: GitRepository) -> "RefRange":
        """Read `BASE`, `BASE..HEAD` or `BASE...HEAD`; HEAD defaults to the current commit."""
        base, _, head = text.replace("...", "..").partition("..")
        base, head = base.strip(), (head.strip() or "HEAD")
        if not base:
            raise RefError("give a base ref, for example `gnost changes origin/main`")
        base_commit = cls._commit(repo, base)
        head_commit = cls._commit(repo, head)
        try:
            split = repo.merge_base(base_commit, head_commit)
        except GitError as exc:
            raise RefError(f"`{base}` and `{head}` have no common history") from exc
        return cls(base, head, split, head_commit)

    @staticmethod
    def _commit(repo: GitRepository, ref: str) -> str:
        try:
            commit = repo.resolve(ref)
        except GitError as exc:
            raise RefError(
                f"unknown ref `{ref}`. If this is a CI checkout, fetch the base branch "
                "first (in GitHub Actions: `fetch-depth: 0`)."
            ) from exc
        if not commit:
            raise RefError(f"unknown ref `{ref}`")
        return commit

    @property
    def label(self) -> str:
        """The range as shown to people, for example `main..feature`."""
        return f"{self.base}..{self.head}"


@dataclass(frozen=True)
class ChangedFile:
    """One file that differs between the two sides."""

    path: str  # relative to the scanned folder; the new name for a rename
    status: str  # added, modified, deleted or renamed
    old_path: Optional[str] = None  # the previous name of a renamed file


class DiffReader:
    """Lists the files that changed in a range, limited to the scanned folder."""

    def __init__(self, repo: GitRepository) -> None:
        self.repo = repo

    def read(self, refs: RefRange, scan_root: str) -> List[ChangedFile]:
        """Changed files under scan_root, sorted by path, with paths relative to scan_root."""
        args = ["diff", "--name-status", "-M", "--relative"]
        # --relative limits the list to scan_root and makes the paths relative to it
        text = self.repo.run([*args, refs.base_commit, refs.head_commit], cwd=scan_root)
        files = [f for f in (self._parse(line) for line in text.splitlines()) if f]
        return sorted(files, key=lambda f: f.path)

    @staticmethod
    def _parse(line: str) -> Optional[ChangedFile]:
        """One `git diff --name-status` line: `M<TAB>path` or `R90<TAB>old<TAB>new`."""
        parts = line.split("\t")
        if len(parts) < 2:
            return None
        status = STATUS_NAMES.get(parts[0][:1])
        if status is None:
            return None
        if status == "renamed" and len(parts) >= 3:
            return ChangedFile(parts[2], status, parts[1])
        return ChangedFile(parts[-1], status)
