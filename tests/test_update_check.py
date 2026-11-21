"""Tests for the update notice: version order, caching, the policy and the command-line wiring."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Callable, Dict, Optional

import pytest

import gnost.cli.app as app
from gnost import __version__
from gnost.utils import update_check as uc
from gnost.utils.update_check import (
    PyPIFeed,
    UpdateCache,
    UpdateNotifier,
    UpdatePolicy,
    Version,
)


class Tty(io.StringIO):
    """A text stream that claims to be a terminal."""

    def isatty(self) -> bool:
        return True


class FakeFeed(PyPIFeed):
    """A feed that returns a fixed answer (or fails) and counts its requests."""

    def __init__(
        self, answer: Optional[str] = "0.6.0", error: Optional[Exception] = None
    ) -> None:
        super().__init__("http://unused")
        self.answer, self.error, self.calls = answer, error, 0

    def latest(self) -> Optional[str]:
        self.calls += 1
        if self.error:
            raise self.error
        return self.answer


def notifier(
    tmp_path: Path,
    feed: Optional[FakeFeed] = None,
    now: float = 1000.0,
    env: Optional[Dict[str, str]] = None,
    allow: bool = True,
    current: str = "0.5.3",
) -> UpdateNotifier:
    return UpdateNotifier(
        current,
        UpdateCache.in_home(str(tmp_path)),
        feed or FakeFeed(),
        UpdatePolicy(env or {}, allow),
        clock=lambda: now,
    )


def test_a_newer_release_prints_one_line_with_the_upgrade_hint(tmp_path: Path) -> None:
    out = Tty()
    assert notifier(tmp_path).notify(out)
    text = out.getvalue()
    assert "A new version of gnost is available: 0.6.0 (you have 0.5.3)" in text
    assert "Upgrade: " in text and "gnost.readthedocs.io" in text


@pytest.mark.parametrize("latest", ["0.5.3", "0.5.2", "0.5.3rc1", "0.4.0"])
def test_the_same_or_an_older_release_prints_nothing(
    tmp_path: Path, latest: str
) -> None:
    assert notifier(tmp_path, FakeFeed(latest)).notify(Tty()) is False


def test_versions_sort_like_releases() -> None:
    def parsed(text: str) -> Version:
        found = Version.parse(text)
        assert found is not None
        return found

    assert parsed("0.6.0").is_newer_than(parsed("0.6.0rc2"))
    assert parsed("0.6.0rc2").is_newer_than(parsed("0.6.0rc1"))
    assert parsed("0.6.0rc1").is_newer_than(parsed("0.5.9"))
    assert not parsed("0.6.0rc1").is_newer_than(parsed("0.6.0"))
    assert parsed("0.6") == parsed("0.6.0")
    assert parsed("0.10.0").is_newer_than(parsed("0.9.0"))  # numbers, not text
    assert Version.parse("not-a-version") is None
    assert Version.parse("0.6.0.dev1") is None  # unknown forms are left alone


def test_only_a_terminal_gets_the_notice(tmp_path: Path) -> None:
    feed = FakeFeed()
    assert notifier(tmp_path, feed).notify(io.StringIO()) is False
    assert feed.calls == 0


@pytest.mark.parametrize("env", [{"CI": "true"}, {"CI": "1"}, {uc.SWITCH_OFF_ENV: "1"}])
def test_ci_and_the_off_switch_skip_the_check_entirely(
    tmp_path: Path, env: Dict[str, str]
) -> None:
    feed = FakeFeed()
    out = Tty()
    assert notifier(tmp_path, feed, env=env).notify(out) is False
    assert out.getvalue() == "" and feed.calls == 0


def test_config_can_switch_it_off(tmp_path: Path) -> None:
    feed = FakeFeed()
    assert notifier(tmp_path, feed, allow=False).notify(Tty()) is False
    assert feed.calls == 0


@pytest.mark.parametrize(
    "error", [OSError("no network"), TimeoutError("timed out"), None]
)
def test_any_failure_is_silent(tmp_path: Path, error: Optional[Exception]) -> None:
    out = Tty()
    feed = FakeFeed(answer=None, error=error)
    assert notifier(tmp_path, feed).notify(out) is False
    assert out.getvalue() == ""


def test_a_bad_answer_from_the_server_is_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Response:
        status = 200

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

        def read(self, *args: object) -> bytes:
            return b"<html>not json</html>"

    monkeypatch.setattr(uc.urllib.request, "urlopen", lambda *a, **k: Response())
    out = Tty()
    real = UpdateNotifier(
        "0.5.3",
        UpdateCache.in_home(str(tmp_path)),
        PyPIFeed("http://x"),
        UpdatePolicy({}),
    )
    assert real.notify(out) is False and out.getvalue() == ""


def test_a_fresh_cache_makes_no_request(tmp_path: Path) -> None:
    notifier(tmp_path, now=1000.0).notify(Tty())
    feed = FakeFeed()
    out = Tty()
    assert notifier(tmp_path, feed, now=1000.0 + 3600).notify(out)
    assert "0.6.0" in out.getvalue() and feed.calls == 0


def test_the_cache_expires_after_a_day(tmp_path: Path) -> None:
    notifier(tmp_path, FakeFeed("0.6.0"), now=1000.0).notify(Tty())
    feed = FakeFeed("0.7.0")
    notifier(tmp_path, feed, now=1000.0 + 24 * 3600 + 1).notify(Tty())
    assert feed.calls == 1


def test_a_failed_attempt_is_not_repeated_for_six_hours(tmp_path: Path) -> None:
    feed = FakeFeed(error=OSError("offline"))
    notifier(tmp_path, feed, now=1000.0).notify(Tty())
    notifier(tmp_path, feed, now=1000.0 + 3600).notify(Tty())
    assert feed.calls == 1
    notifier(tmp_path, feed, now=1000.0 + 6 * 3600 + 1).notify(Tty())
    assert feed.calls == 2


def test_an_unwritable_cache_is_not_a_problem(tmp_path: Path) -> None:
    blocked = tmp_path / "file"
    blocked.write_text("x")  # a file where the folder should be
    out = Tty()
    assert notifier(blocked).notify(out) and "0.6.0" in out.getvalue()


def test_the_cache_file_holds_only_the_version_and_times(tmp_path: Path) -> None:
    notifier(tmp_path, now=1000.0).notify(Tty())
    data = json.loads((tmp_path / "update-check.json").read_text())
    assert data == {"latest": "0.6.0", "checked_at": 1000.0}


def test_the_upgrade_command_matches_the_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert UpdateNotifier.upgrade_command() in (
        "pip install -U gnost",
        "pipx upgrade gnost",
    )
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert "gnost-cli" in UpdateNotifier.upgrade_command()


def _terminal_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *argv: str, config: str = ""
) -> Callable[[], int]:
    """Set up a fake terminal and a feed that says 99.0.0, then return a way to run main()."""
    if config:
        (tmp_path / ".gnost.toml").write_text(config)
    monkeypatch.setattr("sys.stderr", Tty())
    monkeypatch.setattr(PyPIFeed, "latest", lambda self: "99.0.0")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv(uc.SWITCH_OFF_ENV, raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["gnost", *argv])
    return app.main


def test_the_version_commands_print_the_notice_on_stderr_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _terminal_run(tmp_path, monkeypatch, "version")() == 0
    assert (
        capsys.readouterr().out == f"gnost {__version__}\n"
    )  # stdout stays exactly the version
    assert "99.0.0" in sys.stderr.getvalue()  # type: ignore[attr-defined]

    run = _terminal_run(tmp_path, monkeypatch, "--version")
    with pytest.raises(SystemExit) as stop:
        run()
    assert stop.value.code == 0
    assert capsys.readouterr().out == f"gnost {__version__}\n"
    assert "99.0.0" in sys.stderr.getvalue()  # type: ignore[attr-defined]


def test_check_updates_false_in_the_config_switches_it_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = _terminal_run(
        tmp_path, monkeypatch, "version", config="check_updates = false\n"
    )
    assert run() == 0
    assert sys.stderr.getvalue() == ""  # type: ignore[attr-defined]
