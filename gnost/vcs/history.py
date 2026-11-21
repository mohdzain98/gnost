"""Change history per file: how often, by how many people and how recently files change.

`HistoryReader` runs one `git log` call, `LogParser` turns it into counts (following renames and
skipping bots and giant commits), and `ChangeRanker` scores files from pluggable `Signal`s.
Used by `gnost onboard` for the Change Hotspots table and the `change_history` JSON field.
"""

from __future__ import annotations

import fnmatch
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from gnost.vcs.git import GitError, GitRepository, GitRunner, GitUnavailable

RECORD = "\x1e"
FIELD = "\x1f"
LOG_FORMAT = f"--format={RECORD}%H{FIELD}%aN{FIELD}%at"
DAY = 86400


class Reason:
    """Why history is not used. The first two are silent: most folders are not repositories."""

    NO_GIT = "no_git"
    NOT_A_REPO = "not_repo"
    DISABLED = "disabled"
    EMPTY = "empty"
    SHALLOW = "shallow"
    ERROR = "error"
    SILENT = {NO_GIT, NOT_A_REPO, DISABLED}


@dataclass(frozen=True)
class HistorySettings:
    """The [history] settings: window, filters and how many files to list."""

    enabled: bool = True
    days: int = 365
    max_commits: int = 5000
    recent_days: int = 90
    exclude_authors: Tuple[str, ...] = ("*[bot]", "dependabot*", "renovate*")
    max_files_per_commit: int = 150  # bigger commits are mass reformats or vendoring
    min_commits: int = 2
    top: int = 15
    allow_shallow: bool = False  # set for remote clones; not a .gnost.toml key


@dataclass
class FileChange:
    """Everything counted about one file over the window."""

    path: str
    commits: int = 0
    recent_commits: int = 0
    authors: Set[str] = field(default_factory=set)
    added: int = 0
    removed: int = 0
    last_changed: int = 0  # unix time of the newest change

    @property
    def author_count(self) -> int:
        """Number of distinct people who changed the file."""
        return len(self.authors)


@dataclass
class ChangeHistory:
    """The counted history of a folder, or the reason there is none."""

    available: bool
    reason_kind: Optional[str] = None
    reason: Optional[str] = None
    window_days: int = 365
    commits: int = 0  # commits that were counted
    skipped_commits: int = 0  # bots and giant commits (merges are excluded by git)
    files: Dict[str, FileChange] = field(default_factory=dict)


@dataclass(frozen=True)
class Hotspot:
    """A file with its change-activity score (0 to 100)."""

    change: FileChange
    score: float


@dataclass
class ChangeInsights:
    """What onboard reports: the history, the ranked files and the settings used."""

    history: ChangeHistory
    hotspots: List[Hotspot]
    settings: HistorySettings

    @property
    def note_worth_showing(self) -> bool:
        """True when history is missing for a reason the reader should be told."""
        return (
            not self.history.available and self.history.reason_kind not in Reason.SILENT
        )


# ------------------------------------------------------------------ parsing


class LogParser:
    """Turns `git log --numstat` output (newest commit first) into per-file counts."""

    _BRACES = re.compile(r"^(.*)\{(.*) => (.*)\}(.*)$")

    def __init__(self, settings: HistorySettings, now: float) -> None:
        self.settings = settings
        self.now = now
        self._renamed: Dict[str, str] = {}  # old path -> the file's name today

    def parse(self, text: str) -> ChangeHistory:
        """Count every commit in the log text."""
        history = ChangeHistory(available=True, window_days=self.settings.days)
        recent_after = self.now - self.settings.recent_days * DAY
        for record in text.split(RECORD):
            commit = self._read_record(record)
            if commit is None:
                continue
            author, when, changed = commit
            if self._is_ignored(author, len(changed)):
                history.skipped_commits += 1
                continue
            history.commits += 1
            for path, added, removed in changed:
                entry = history.files.setdefault(path, FileChange(path))
                entry.commits += 1
                entry.authors.add(author)
                entry.added += added
                entry.removed += removed
                entry.last_changed = max(entry.last_changed, when)
                if when >= recent_after:
                    entry.recent_commits += 1
        return history

    def _read_record(
        self, record: str
    ) -> Optional[Tuple[str, int, List[Tuple[str, int, int]]]]:
        """(author, time, [(path, added, removed)]) for one commit, or None if it is junk."""
        if not record.strip():
            return None
        header, _, body = record.partition("\n")
        parts = header.split(FIELD)
        if len(parts) != 3 or not parts[2].isdigit():
            return None
        changed: List[Tuple[str, int, int]] = []
        for line in body.splitlines():
            cols = line.split("\t", 2)
            if len(cols) == 3:
                added, removed, raw = cols
                changed.append(
                    (
                        self._current_name(raw),
                        int(added) if added.isdigit() else 0,  # binary files print "-"
                        int(removed) if removed.isdigit() else 0,
                    )
                )
        return parts[1], int(parts[2]), changed

    def _current_name(self, raw: str) -> str:
        """The path a numstat entry refers to today, learning renames as it goes."""
        old, new = self._split_rename(raw)
        target = self._follow(new)
        if old is not None:
            self._renamed[old] = target  # older commits used the old name
        return target

    def _follow(self, path: str) -> str:
        """Follow recorded renames to the file's current name."""
        hops = 0
        while path in self._renamed and hops < 50:
            path = self._renamed[path]
            hops += 1
        return path

    def _split_rename(self, raw: str) -> Tuple[Optional[str], str]:
        """(old path or None, new path) from 'a/{b => c}/d', 'x => y' or a plain path."""
        match = self._BRACES.match(raw)
        if match:
            pre, old, new, post = match.groups()
            return (pre + old + post).replace("//", "/"), (pre + new + post).replace(
                "//", "/"
            )
        if " => " in raw:
            old, new = raw.split(" => ", 1)
            return old, new
        return None, raw

    def _is_ignored(self, author: str, files_changed: int) -> bool:
        """Bots and mass-change commits say nothing about individual files."""
        lowered = author.lower()
        is_bot = any(
            fnmatch.fnmatch(lowered, p.lower()) for p in self.settings.exclude_authors
        )
        return is_bot or files_changed > self.settings.max_files_per_commit


# ------------------------------------------------------------------ ranking


class Signal(ABC):
    """One measure of change activity with a weight; add a subclass to add a measure."""

    weight: float = 1.0

    @abstractmethod
    def value(self, change: FileChange) -> int:
        """The raw number this signal reads from a file's counts."""


class CommitsSignal(Signal):
    """How many commits touched the file."""

    weight = 0.5

    def value(self, change: FileChange) -> int:
        return change.commits


class RecentSignal(Signal):
    """How many of those commits are recent."""

    weight = 0.3

    def value(self, change: FileChange) -> int:
        return change.recent_commits


class AuthorsSignal(Signal):
    """How many different people changed it."""

    weight = 0.2

    def value(self, change: FileChange) -> int:
        return change.author_count


class ChangeRanker:
    """Scores files 0 to 100 as the weighted percentile of each signal among the changed files.

    Ties are broken by commits, then path, so the same history gives the same order.
    """

    DEFAULT_SIGNALS: Sequence[Signal] = (
        CommitsSignal(),
        RecentSignal(),
        AuthorsSignal(),
    )

    def __init__(
        self, settings: HistorySettings, signals: Optional[Sequence[Signal]] = None
    ) -> None:
        self.settings = settings
        self.signals = tuple(signals or self.DEFAULT_SIGNALS)

    def rank(
        self, history: ChangeHistory, keep: Optional[Set[str]] = None
    ) -> List[Hotspot]:
        """Hotspots for files changed at least min_commits times (and in `keep`, if given)."""
        files = [
            f
            for f in history.files.values()
            if f.commits >= self.settings.min_commits
            and (keep is None or f.path in keep)
        ]
        if not files:
            return []
        total = sum(s.weight for s in self.signals)
        columns = [
            (s.weight, self._percentiles([s.value(f) for f in files]))
            for s in self.signals
        ]
        ranked = [
            Hotspot(f, round(100 * sum(w * col[i] for w, col in columns) / total, 1))
            for i, f in enumerate(files)
        ]
        ranked.sort(key=lambda h: (-h.score, -h.change.commits, h.change.path))
        return ranked

    @staticmethod
    def _percentiles(values: List[int]) -> List[float]:
        """For each value, the share of the others it beats (ties count half)."""
        n = len(values)
        if n == 1:
            return [1.0]
        ordered = sorted(values)
        return [
            (
                sum(1 for o in ordered if o < v)
                + (sum(1 for o in ordered if o == v) - 1) / 2.0
            )
            / (n - 1)
            for v in values
        ]


# ------------------------------------------------------------------ reading


class HistoryReader:
    """Reads the change history of a folder from git; never raises.

    The git runner and the clock are arguments so tests need no patching.
    """

    def __init__(
        self,
        settings: HistorySettings,
        runner: Optional[GitRunner] = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.settings = settings
        self.runner = runner or GitRunner()
        self.clock = clock

    def analyze(self, scan_root: str, scanned: Iterable[str]) -> ChangeInsights:
        """History plus the ranked hotspots among the scanned files (paths relative to scan_root)."""
        history = self.read(scan_root)
        hotspots = (
            ChangeRanker(self.settings).rank(history, set(scanned))
            if history.available
            else []
        )
        return ChangeInsights(
            history=history, hotspots=hotspots, settings=self.settings
        )

    def read(self, scan_root: str) -> ChangeHistory:
        """The counted history of scan_root, or a ChangeHistory that says why there is none."""
        if not self.settings.enabled:
            return self._unavailable(
                Reason.DISABLED, "history is switched off in .gnost.toml"
            )
        try:
            repo = GitRepository.containing(scan_root, self.runner)
        except GitUnavailable as exc:
            # Mention it only when the folder looks like a repository.
            kind = Reason.ERROR if self._has_git_dir(scan_root) else Reason.NO_GIT
            return self._unavailable(kind, str(exc))
        if repo is None:
            return self._unavailable(
                Reason.NOT_A_REPO,
                "this folder is not inside a git repository, so there is no history",
            )
        problem = repo.history_problem(self.settings.allow_shallow)
        if problem:
            return self._unavailable(
                Reason.SHALLOW if "shallow" in problem else Reason.EMPTY, problem
            )
        now = self.clock()
        try:
            log = repo.run(self._log_command(now), cwd=scan_root)
        except GitError as exc:
            return self._unavailable(Reason.ERROR, str(exc))
        return LogParser(self.settings, now).parse(log)

    def _log_command(self, now: float) -> List[str]:
        """The one git log call: numstat, renames, mailmap, relative to the scanned folder."""
        since = datetime.fromtimestamp(now - self.settings.days * DAY, tz=timezone.utc)
        return [
            "log",
            "--no-merges",
            "--use-mailmap",
            "-M",
            "--numstat",
            "--relative",
            f"--since={since:%Y-%m-%d}",
            "-n",
            str(self.settings.max_commits),
            LOG_FORMAT,
            "--",
            ".",
        ]

    def _unavailable(self, kind: str, reason: str) -> ChangeHistory:
        """A ChangeHistory that records why there is none."""
        return ChangeHistory(
            available=False,
            reason_kind=kind,
            reason=reason,
            window_days=self.settings.days,
        )

    @staticmethod
    def _has_git_dir(path: str) -> bool:
        """True if path or a parent folder has a .git entry."""
        current = os.path.abspath(path)
        while True:
            if os.path.exists(os.path.join(current, ".git")):
                return True
            parent = os.path.dirname(current)
            if parent == current:
                return False
            current = parent
