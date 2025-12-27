import os
from gnost.config.languages import LANGUAGES
from gnost.scanner.filters import should_skip, DEFAULT_EXCLUDES
from gnost.scanner.classify import classify_lines


def scan(path=".", include=None, exclude=None):
    include = set(include or [])
    exclude = DEFAULT_EXCLUDES | set(exclude or [])

    files = []
    by_language = {}
    by_folder = {}

    for root, _, filenames in os.walk(path):
        rel_root = os.path.relpath(root, path)

        if should_skip(rel_root, include, exclude):
            continue

        for name in filenames:
            ext = name.split(".")[-1].lower()
            if ext not in LANGUAGES:
                continue

            full_path = os.path.join(root, name)

            try:
                with open(full_path, "r", errors="ignore") as f:
                    lines = f.readlines()
            except Exception:
                continue

            code, comments, blanks = classify_lines(lines, LANGUAGES[ext]["comment"])

            loc = code + comments + blanks

            record = {
                "path": os.path.join(rel_root, name),
                "language": ext,
                "loc": loc,
                "code": code,
                "comments": comments,
                "blanks": blanks,
            }

            files.append(record)

            by_language.setdefault(
                ext, {"files": 0, "loc": 0, "code": 0, "comments": 0, "blanks": 0}
            )

            lang = by_language[ext]
            lang["files"] += 1
            lang["loc"] += loc
            lang["code"] += code
            lang["comments"] += comments
            lang["blanks"] += blanks

            folder = rel_root.split(os.sep)[0]
            by_folder[folder] = by_folder.get(folder, 0) + loc

    return {
        "files": files,
        "by_language": by_language,
        "by_folder": by_folder,
    }
