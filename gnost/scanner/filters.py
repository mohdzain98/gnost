import fnmatch
import os


DEFAULT_EXCLUDES = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".env",
    ".smenv",
    "dist",
    "build",
    "target",
    ".gradle",
    "__pycache__",
}


def should_skip(path, include, exclude):
    parts = set(path.split("/"))

    if parts & exclude:
        return True

    if include and not (parts & include):
        return True

    return False


IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".env",
    ".smenv",
    "dist",
    "build",
    "target",
    ".gradle",
    ".idea",
    "out",
}

IGNORE_FILES = {
    ".DS_Store",
}


def is_virtualenv_dir(path: str) -> bool:
    if not os.path.isdir(path):
        return False

    if os.path.isfile(os.path.join(path, "pyvenv.cfg")):
        return True

    if os.path.isfile(os.path.join(path, "bin", "activate")):
        return True

    if os.path.isfile(os.path.join(path, "Scripts", "activate")):
        return True

    return False


def load_gitignore(root: str) -> list[str]:
    gitignore_path = os.path.join(root, ".gitignore")
    if not os.path.isfile(gitignore_path):
        return []

    patterns = []
    with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            patterns.append(raw)

    return patterns


def is_gitignored(path: str, root: str, patterns: list[str]) -> bool:
    if not patterns:
        return False

    rel_path = os.path.relpath(path, root).replace(os.sep, "/")
    ignored = False

    for pat in patterns:
        negate = pat.startswith("!")
        rule = pat[1:] if negate else pat
        rule = rule.replace("\\", "/")

        if rule.endswith("/"):
            rule = rule.rstrip("/")
            match = rel_path == rule or rel_path.startswith(rule + "/")
        else:
            match = fnmatch.fnmatch(rel_path, rule) or fnmatch.fnmatch(
                os.path.basename(rel_path), rule
            )

        if match:
            ignored = not negate

    return ignored


def should_ignore(path: str) -> bool:
    if is_virtualenv_dir(path):
        return True

    for part in path.split("/"):
        if part in IGNORE_DIRS:
            return True

    for name in IGNORE_FILES:
        if path.endswith(name):
            return True

    return False
