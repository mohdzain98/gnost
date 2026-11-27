"""The two refs a change is measured between, and the files that differ.

`RefRange` parses `BASE`, `BASE..HEAD` or `BASE...HEAD`. Like a pull request, the comparison
starts at the commit where HEAD split from BASE. `DiffReader` lists the changed files.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Tuple

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
    added: Optional[int] = None  # lines added; None when binary or unknown
    removed: Optional[int] = None  # lines removed; None when binary or unknown
    binary: bool = False  # True only when git --numstat reported `-`


class DiffReader:
    """Lists the files that changed in a range, limited to the scanned folder."""

    def __init__(self, repo: GitRepository) -> None:
        self.repo = repo

    def read(self, refs: RefRange, scan_root: str) -> List[ChangedFile]:
        """Changed files under scan_root, sorted by path, with paths relative to scan_root."""
        args = ["diff", "--name-status", "-z", "-M", "--relative"]
        # --relative limits the list to scan_root and makes the paths relative to it
        text = self.repo.run([*args, refs.base_commit, refs.head_commit], cwd=scan_root)
        stats = self._numstat(refs, scan_root)
        files = []
        for item in self._parse_z(text):
            added, removed, binary = stats.get(item.path, (None, None, False))
            files.append(replace(item, added=added, removed=removed, binary=binary))
        return sorted(files, key=lambda f: f.path)

    def _numstat(
        self, refs: RefRange, scan_root: str
    ) -> Dict[str, Tuple[Optional[int], Optional[int], bool]]:
        """Parse `git diff --numstat -z -M --relative` into {path: (added, removed, binary)}."""
        text = self.repo.run(
            [
                "diff",
                "--numstat",
                "-z",
                "-M",
                "--relative",
                refs.base_commit,
                refs.head_commit,
            ],
            cwd=scan_root,
        )
        tokens = text.split("\0")
        out: Dict[str, Tuple[Optional[int], Optional[int], bool]] = {}
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            i += 1
            if not tok or "\t" not in tok:
                continue
            added_s, removed_s, path_s = tok.split("\t", 2)
            if path_s == "":
                # Rename entry: followed by old_path\0new_path\0
                if i + 1 < len(tokens):
                    path_s = tokens[i + 1]
                    i += 2
                else:
                    continue
            binary = added_s == "-" or removed_s == "-"
            added = None if added_s == "-" else int(added_s)
            removed = None if removed_s == "-" else int(removed_s)
            out[path_s] = (added, removed, binary)
        return out

    @staticmethod
    def _parse_z(text: str) -> List[ChangedFile]:
        """Parse NUL-delimited `git diff --name-status -z -M` output."""
        tokens = text.split("\0")
        items: List[ChangedFile] = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            i += 1
            if not tok:
                continue
            code = tok[:1]
            status = STATUS_NAMES.get(code)
            if code in ("R", "C"):
                if i + 1 >= len(tokens):
                    break
                old_path, new_path = tokens[i], tokens[i + 1]
                i += 2
                if status is not None:
                    old = old_path if status == "renamed" else None
                    items.append(ChangedFile(new_path, status, old))
            else:
                if i >= len(tokens):
                    break
                path = tokens[i]
                i += 1
                if status is not None:
                    items.append(ChangedFile(path, status))
        return items

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
