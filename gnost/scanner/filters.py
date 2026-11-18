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


def should_ignore(path: str, root: str | None = None) -> bool:
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
        pat = pattern.strip().rstrip("/").lstrip("./")
        if not pat:
            continue
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(parts[-1], pat):
            return True
        if any(fnmatch.fnmatch(part, pat) for part in parts[:-1]):
            return True
        if "/" in pat and (rel == pat or rel.startswith(pat + "/")):
            return True
    return False
