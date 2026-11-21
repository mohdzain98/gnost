import fnmatch
import os
from typing import Optional


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
    ".gnost",
}


def should_skip(path, include, exclude):
    parts = set(path.replace("\\", "/").split("/"))

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
    ".gnost",
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


def _matches(pattern: str, rel_path: str, is_dir: bool) -> bool:
    """Whether one .gitignore pattern covers rel_path, following git's rules.

    No slash (but a trailing one): any depth. A slash: relative to the root. A trailing slash: folders only.
    """
    rule = pattern.replace("\\", "/")
    dir_only = rule.endswith("/")
    rule = rule.rstrip("/")
    anchored = "/" in rule
    rule = rule.lstrip("/")
    parts = rel_path.split("/")

    if not anchored:
        for index, part in enumerate(parts):
            is_last = index == len(parts) - 1
            if dir_only and is_last and not is_dir:
                continue
            if fnmatch.fnmatch(part, rule):
                return True
        return False

    if rule.startswith("**/"):
        tail = rule[3:]
        return any(
            fnmatch.fnmatch("/".join(parts[i:]), tail)
            or fnmatch.fnmatch("/".join(parts[i:]), tail + "/*")
            for i in range(len(parts))
        )
    if fnmatch.fnmatch(rel_path, rule) or rel_path.startswith(rule + "/"):
        return not (dir_only and rel_path == rule and not is_dir)
    return any(
        fnmatch.fnmatch("/".join(parts[: i + 1]), rule) for i in range(len(parts) - 1)
    )


def is_gitignored(path: str, root: str, patterns: list[str]) -> bool:
    """True if the .gitignore patterns cover path (the last matching pattern wins)."""
    if not patterns:
        return False

    rel_path = os.path.relpath(path, root).replace(os.sep, "/")
    is_dir = os.path.isdir(path)
    ignored = False

    for pat in patterns:
        negate = pat.startswith("!")
        rule = pat[1:] if negate else pat
        if _matches(rule, rel_path, is_dir):
            ignored = not negate

    return ignored


def should_ignore(path: str, root: Optional[str] = None) -> bool:
    """True for ignored folders and files; with root, only the part below it counts."""
    if is_virtualenv_dir(path):
        return True

    check = os.path.relpath(path, root) if root else path
    for part in check.replace("\\", "/").split("/"):
        if part in IGNORE_DIRS:
            return True

    for name in IGNORE_FILES:
        if path.endswith(name):
            return True

    return False


# -------------------------
# Onboarding scan filters
# -------------------------

NOISE_DIRS = {"vendor", "vendors", "third_party", "site-packages", "bower_components"}
JS_SUFFIXES = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")
NOISE_SUFFIXES = (".min.js", ".min.mjs", ".bundle.js", ".d.ts")
TEST_DIRS = {"tests", "test", "__tests__", "e2e"}


def _rel_parts(path: str, root: str) -> list[str]:
    return os.path.relpath(path, root).replace(os.sep, "/").split("/")


def is_noise_file(path: str, root: str) -> bool:
    """Vendored, minified, bundled or generated files that are not project code."""
    parts = _rel_parts(path, root)
    name = parts[-1].lower()
    # A vendor/ folder is third-party code for JS, but in Python it is often a
    # project package, so only the file-name rules apply there.
    if name.endswith(JS_SUFFIXES) and set(parts[:-1]) & NOISE_DIRS:
        return True
    return name.endswith(NOISE_SUFFIXES)


def is_test_file(path: str, root: str) -> bool:
    """Test files: they exercise the code but are not part of its execution flow."""
    parts = _rel_parts(path, root)
    if set(parts[:-1]) & TEST_DIRS:
        return True
    name = parts[-1].lower()
    stem = name.rsplit(".", 1)[0]
    return (
        name == "conftest.py"
        or stem.startswith("test_")
        or stem.endswith("_test")
        or ".test." in name
        or ".spec." in name
    )


# -------------------------
# Exclusion patterns
# -------------------------


def is_excluded(path: str, root: str, patterns: "list[str]") -> bool:
    """Whether `path` matches an `exclude` pattern.

    A pattern matches the whole relative path (`src/legacy/*.js`), the file name
    (`*.generated.ts`) or any folder in the path (`legacy`, `docs/build`).
    """
    if not patterns:
        return False
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    parts = rel.split("/")
    for pattern in patterns:
        pat = pattern.strip().rstrip("/")
        while pat.startswith(
            "./"
        ):  # not lstrip("./"): it would turn ".gnost" into "gnost"
            pat = pat[2:]
        if not pat:
            continue
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(parts[-1], pat):
            return True
        if any(fnmatch.fnmatch(part, pat) for part in parts[:-1]):
            return True
        if "/" in pat and (rel == pat or rel.startswith(pat + "/")):
            return True
    return False
