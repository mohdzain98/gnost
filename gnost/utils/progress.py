from contextlib import contextmanager


try:
    from tqdm import tqdm
except Exception:
    tqdm = None


@contextmanager
def progress_bar(enabled=False, total=None, desc=None):
    if not enabled or tqdm is None:
        yield None
        return

    bar = tqdm(total=total, desc=desc)
    try:
        yield bar
    finally:
        bar.close()
