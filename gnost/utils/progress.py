import threading
from contextlib import contextmanager
from typing import Any, Iterator, Optional


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
