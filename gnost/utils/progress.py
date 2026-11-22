"""Progress feedback for long commands, shown only where a person is watching.

`ProgressPolicy` decides whether to show it (a terminal yes; CI, pipes and `--no-progress` no).
`StepProgress` is a bar that names the step being done. `progress_bar` is the plain bar used by
the scan commands. All of it writes to stderr, so stdout stays clean for scripts.
"""

import os
import sys
import threading
from contextlib import contextmanager
from typing import Any, Iterator, List, Mapping, Optional, Sequence, TextIO


try:
    from tqdm import tqdm
except Exception:
    tqdm = None

_lock_ready = False


def _use_thread_lock() -> None:
    """Keep tqdm from creating a multiprocessing lock.

    That lock starts a helper that relaunches sys.executable, which breaks the standalone binary.
    """
    global _lock_ready
    if not _lock_ready:
        tqdm.set_lock(threading.RLock())
        _lock_ready = True


@contextmanager
def progress_bar(
    enabled: bool = False, total: Optional[int] = None, desc: Optional[str] = None
) -> Iterator[Any]:
    """Yield a tqdm progress bar when enabled, else None; always closes the bar."""
    if not enabled or tqdm is None:
        yield None
        return

    _use_thread_lock()
    bar = tqdm(total=total, desc=desc)
    try:
        yield bar
    finally:
        bar.close()


class ProgressPolicy:
    """Shows progress in a terminal, and nowhere a script or CI log would be cluttered."""

    OFF_VARIABLES = ("CI", "GNOST_NO_PROGRESS")

    def __init__(
        self,
        stream: Optional[TextIO] = None,
        environ: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.stream = stream if stream is not None else sys.stderr
        self.environ = environ if environ is not None else os.environ

    def enabled(self, force: bool = False, disabled: bool = False) -> bool:
        """True when progress should be shown: `force` wins, then `disabled`, then the terminal."""
        if force:
            return True
        if disabled or any(self.environ.get(v) for v in self.OFF_VARIABLES):
            return False
        try:
            return bool(self.stream.isatty())
        except (AttributeError, ValueError):
            return False


class StepProgress:
    """A progress bar that names the current step; does nothing when disabled.

    Use as a context manager and call `advance()` when a step is done.
    """

    def __init__(
        self,
        enabled: bool,
        steps: Sequence[str],
        announce: Optional[str] = None,
        stream: Optional[TextIO] = None,
    ) -> None:
        self.enabled = enabled
        self.steps: List[str] = list(steps)
        self.announce = announce
        self.stream = stream if stream is not None else sys.stderr
        self._context: Any = None
        self._bar: Any = None
        self._done = 0

    def __enter__(self) -> "StepProgress":
        if self.enabled and self.announce:
            print(self.announce, file=self.stream, flush=True)
        self._context = progress_bar(
            self.enabled,
            total=len(self.steps),
            desc=self.steps[0] if self.steps else None,
        )
        self._bar = self._context.__enter__()
        return self

    def advance(self) -> None:
        """Mark the current step done and show the name of the next one."""
        if self._bar is None:
            return
        self._done += 1
        self._bar.update(1)
        if self._done < len(self.steps):
            self._bar.set_description(self.steps[self._done])

    def __exit__(self, *exc: Any) -> None:
        self._context.__exit__(*exc)
