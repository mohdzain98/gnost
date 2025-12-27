DEFAULT_EXCLUDES = {".git", "node_modules", ".venv", "dist", "build", "__pycache__"}


def should_skip(path, include, exclude):
    parts = set(path.split("/"))

    if parts & exclude:
        return True

    if include and not (parts & include):
        return True

    return False
