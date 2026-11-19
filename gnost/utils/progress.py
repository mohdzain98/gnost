import threading
from contextlib import contextmanager


try:
    from tqdm import tqdm
except Exception:
    tqdm = None

_lock_ready = False


def _use_thread_lock() -> None:
    """Keep tqdm from creating a multiprocessing lock.

    That lock starts Python's resource tracker, which relaunches sys.executable.
    In the standalone binary that is gnost itself, and it fails on the arguments.
    """
    global _lock_ready
    if not _lock_ready:
        tqdm.set_lock(threading.RLock())
        _lock_ready = True


@contextmanager
def progress_bar(enabled=False, total=None, desc=None):
    if not enabled or tqdm is None:
        yield None
        return

    _use_thread_lock()
    bar = tqdm(total=total, desc=desc)
    try:
        yield bar
    finally:
        bar.close()
