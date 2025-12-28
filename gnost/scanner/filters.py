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
