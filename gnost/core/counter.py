import os
from gnost.config.languages import LANG_EXTENSIONS


def count_loc(path: str = "."):
    results = {}
    file_count = {}

    for root, _, files in os.walk(path):
        for f in files:
            ext = f.split(".")[-1].lower()
            if ext in LANG_EXTENSIONS:
                file_count.setdefault(ext, 0)
                results.setdefault(ext, 0)
                file_count[ext] += 1

                try:
                    with open(os.path.join(root, f), "r", errors="ignore") as fh:
                        results[ext] += sum(1 for _ in fh)
                except:
                    pass

    return results, file_count
