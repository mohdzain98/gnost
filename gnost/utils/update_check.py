"""Tells people on a terminal when a newer GNOST release exists (`gnost --version`).

`UpdateNotifier` composes a `Version` comparison, an on-disk `UpdateCache`, a `PyPIFeed` and an
`UpdatePolicy`. Everything is silent on failure and off in CI, scripts and when switched off.
Its only request goes to pypi.org (never a GNOST server), at most once a day.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, TextIO, Tuple

PYPI_URL = "https://pypi.org/pypi/gnost/json"
URL_ENV = "GNOST_UPDATE_CHECK_URL"  # tests point this at a local server
SWITCH_OFF_ENV = "GNOST_NO_UPDATE_CHECK"
INSTALL_DOCS = "https://gnost.readthedocs.io/en/stable/install.html"


@dataclass(frozen=True, order=True)
class Version:
    """A release number that sorts correctly: 0.10.0 > 0.9.0 and 0.6.0 > 0.6.0rc2 > 0.6.0rc1."""

    release: Tuple[int, ...]
    stage: int  # a < b < rc < final
    number: int

    _PATTERN = re.compile(r"^(\d+(?:\.\d+)*)(?:(a|b|rc)(\d+))?$")
    _STAGES = {"a": 1, "b": 2, "rc": 3}

    @classmethod
    def parse(cls, text: str) -> Optional["Version"]:
        """The version for text such as 0.6.0 or 0.6.0rc1, or None for any other form."""
        match = cls._PATTERN.match(text.strip())
        if not match:
            return None
        numbers = [int(n) for n in match.group(1).split(".")]
        while len(numbers) > 1 and numbers[-1] == 0:
            numbers.pop()
        return cls(
            tuple(numbers),
            cls._STAGES.get(match.group(2) or "", 4),
            int(match.group(3) or 0),
        )

    def is_newer_than(self, other: "Version") -> bool:
        """Whether this release comes after other."""
        return self > other


class UpdateCache:
    """Remembers the last answer (a day) and the last failure (six hours) in a small JSON file."""

    FRESH_FOR = 24 * 3600
    RETRY_AFTER_FAILURE = 6 * 3600

    def __init__(self, path: str) -> None:
        self.path = path

    @classmethod
    def in_home(cls, home: Optional[str] = None) -> "UpdateCache":
        """The cache in ~/.gnost (or in `home`)."""
        base = home or os.path.join(os.path.expanduser("~"), ".gnost")
        return cls(os.path.join(base, "update-check.json"))

    def fresh_latest(self, now: float) -> Optional[str]:
        """The stored latest version if it was learned less than a day ago."""
        data = self._read()
        latest, when = data.get("latest"), data.get("checked_at")
        if (
            isinstance(latest, str)
            and isinstance(when, (int, float))
            and now - when < self.FRESH_FOR
        ):
            return latest
        return None

    def stored_latest(self) -> Optional[str]:
        """The stored latest version, however old."""
        latest = self._read().get("latest")
        return latest if isinstance(latest, str) else None

    def recently_failed(self, now: float) -> bool:
        """True if the last attempt failed less than six hours ago."""
        failed = self._read().get("failed_at")
        return (
            isinstance(failed, (int, float)) and now - failed < self.RETRY_AFTER_FAILURE
        )

    def record_success(self, latest: str, now: float) -> None:
        """Store a freshly learned latest version."""
        self._write({"latest": latest, "checked_at": now})

    def record_failure(self, now: float) -> None:
        """Remember a failed attempt, keeping any older answer."""
        self._write({**self._read(), "failed_at": now})

    def _read(self) -> Dict[str, Any]:
        """The stored data, or {} if the file is missing or unreadable."""
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _write(self, data: Dict[str, Any]) -> None:
        """Save data; an unwritable cache is not a problem."""
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except OSError:
            pass


class PyPIFeed:
    """Asks the package index for the latest non-pre-release version of gnost."""

    def __init__(self, url: Optional[str] = None, timeout: float = 1.5) -> None:
        self.url = url or os.environ.get(URL_ENV) or PYPI_URL
        self.timeout = timeout

    def latest(self) -> Optional[str]:
        """The latest version string; raises on any network or format problem."""
        request = urllib.request.Request(
            self.url, headers={"User-Agent": "gnost-update-check"}
        )
        with urllib.request.urlopen(
            request, timeout=self.timeout, context=self._tls()
        ) as response:
            if response.status != 200:
                return None
            version = json.load(response).get("info", {}).get("version")
        return version if isinstance(version, str) else None

    @staticmethod
    def _tls() -> Any:
        """A TLS context with certifi's certificates when available (frozen builds need them)."""
        try:
            import ssl

            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except Exception:
            return None


class UpdatePolicy:
    """Decides whether the check may run: terminal only, never in CI, and not switched off."""

    def __init__(self, env: Mapping[str, str], config_allows: bool = True) -> None:
        self.env = env
        self.config_allows = config_allows

    def allows(self, stream: TextIO) -> bool:
        """True if a notice may be shown on this stream."""
        if not self.config_allows or self.env.get(SWITCH_OFF_ENV, "").strip() not in (
            "",
            "0",
        ):
            return False
        if self.env.get("CI", "").strip() not in ("", "0", "false", "False"):
            return False
        try:
            return bool(stream.isatty())
        except Exception:
            return False


class UpdateNotifier:
    """Prints one line on a terminal when a newer release exists; silent on any failure."""

    def __init__(
        self,
        current: str,
        cache: UpdateCache,
        feed: PyPIFeed,
        policy: UpdatePolicy,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.current = current
        self.cache = cache
        self.feed = feed
        self.policy = policy
        self.clock = clock

    @classmethod
    def standard(cls, current: str, config_allows: bool = True) -> "UpdateNotifier":
        """The notifier used by the command line: real cache, PyPI and environment."""
        return cls(
            current,
            UpdateCache.in_home(),
            PyPIFeed(),
            UpdatePolicy(dict(os.environ), config_allows),
        )

    def notify(self, stream: Optional[TextIO] = None) -> bool:
        """Print the update line to stderr if one is due; returns whether it did."""
        try:
            out = stream if stream is not None else sys.stderr
            if not self.policy.allows(out):
                return False
            latest = self.latest_version()
            if latest and self._is_newer(latest):
                print(self.message(latest), file=out)
                return True
        except Exception:
            pass
        return False

    def latest_version(self) -> Optional[str]:
        """The latest release, from the cache when fresh, else from the network."""
        now = self.clock()
        fresh = self.cache.fresh_latest(now)
        if fresh or self.cache.recently_failed(now):
            return fresh or self.cache.stored_latest()
        try:
            found = self.feed.latest()
        except Exception:
            found = None
        if found:
            self.cache.record_success(found, now)
            return found
        self.cache.record_failure(now)
        return self.cache.stored_latest()

    def message(self, latest: str) -> str:
        """The two-line notice: what is available and how to upgrade."""
        return (
            f"A new version of gnost is available: {latest} (you have {self.current}).\n"
            f"Upgrade: {self.upgrade_command()}  ({INSTALL_DOCS})"
        )

    @staticmethod
    def upgrade_command() -> str:
        """The upgrade command that matches how this copy of gnost was installed."""
        if getattr(sys, "frozen", False):
            return "npm install --global gnost-cli@latest (or pull the newest Docker image)"
        if "pipx" in sys.prefix.replace("\\", "/").lower():
            return "pipx upgrade gnost"
        return "pip install -U gnost"

    def _is_newer(self, latest: str) -> bool:
        """True when latest is a valid release after the current one."""
        new, old = Version.parse(latest), Version.parse(self.current)
        return new is not None and old is not None and new.is_newer_than(old)
