"""
Prod Shift file contains changes needed to be done on prod which are different from local host

Gitleaks is not available on Debian which streamlit community cloud uses.

This is utility functions for managing the Gitleaks binary in production environments
(e.g., Streamlit Community Cloud) where direct package installation via apt/brew
is not possible.

This module ensures that the Gitleaks CLI tool is available at runtime by:

1. Checking if Gitleaks is already installed on the system.
2. Downloading the official prebuilt Linux binary from GitHub Releases if not.
3. Extracting it into a writable directory (/tmp) and making it executable.
4. Returning the path to the binary so it can be invoked with subprocess.

Notes:
- Pin the `GITLEAKS_VERSION` environment variable (default: v8.18.4) to control
  which release is downloaded.
- This approach avoids relying on apt/brew and keeps the app portable across
  cloud deployments.
- On Streamlit Community, binaries should be placed under `/tmp` since it is
  writable at runtime.

Secondly Class Extract is used to extract zip files on the prod as accepting folder path is not possible only accepting zip file is possible

"""

import os
import zipfile
import tempfile
from pathlib import Path
from typing import Iterable, Set
from gnost.utils.logger import AppLogger

logger = AppLogger.get_logger()


class Extract:
    CODE_EXTS: Set[str] = {".py"}

    EXCLUDE_DIRS: Set[str] = {
        "__MACOSX",
        ".git",
        ".hg",
        ".svn",
        ".idea",
        ".vscode",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        "node_modules",
        "venv",
        ".venv",
        "env",
        ".env",
    }

    @staticmethod
    def resolve_dest_folder(arg: str):
        host = os.getenv("HOST", "localhost").lower()

        base_path_lh = Path.cwd() / "user_project"
        base_path_prod = Path(tempfile.gettempdir()) / "user_project"

        if host == "localhost":
            base = base_path_lh
        elif host == "prod":
            base = base_path_prod
        else:
            raise ValueError(f"Unsupported HOST: {host}")

        return base / "single_file" if arg == "file" else base

    @staticmethod
    def safe_extract_zip(zf: zipfile.ZipFile, dest: Path, ignore_hidden_top_level=True):
        """Safely extract ZIP into dest, preventing zip-slip.
        Optionally skip top-level hidden/metadata entries ('.*', likely junk).
        """
        dest = dest.resolve()
        for member in zf.infolist():
            # Normalize and guard against traversal
            member_path = Path(member.filename)
            # Optionally skip hidden top-level entries (e.g., .git/, .DS_Store, __MACOSX/)
            if ignore_hidden_top_level and len(member_path.parts) > 0:
                top = member_path.parts[0]
                if top.startswith("."):
                    continue  # skip .git, .DS_Store, etc.

            # Final resolved path
            target_path = (dest / member.filename).resolve()
            if not str(target_path).startswith(str(dest)):
                raise RuntimeError(f"Blocked unsafe path: {member.filename}")

            if member.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(target_path, "wb") as out:
                    out.write(src.read())

    @staticmethod
    def is_hidden_dir(p: Path) -> bool:
        name = p.name
        return name.startswith(".") or name in Extract.EXCLUDE_DIRS

    @staticmethod
    def is_code_file(p: Path, exts: Iterable[str]) -> bool:
        # Skip dot-underscore resource-fork junk from macOS
        if p.name.startswith("._"):
            return False
        return p.is_file() and p.suffix.lower() in exts

    @staticmethod
    def count_code_files(root: Path, exts: Iterable[str]) -> int:
        """Count code files under root while pruning excluded/hidden dirs."""
        count = 0
        # manual walk to prune
        stack = [root]
        while stack:
            d = stack.pop()
            try:
                for entry in d.iterdir():
                    if entry.is_dir():
                        if not Extract.is_hidden_dir(entry):
                            stack.append(entry)
                    else:
                        if Extract.is_code_file(entry, exts):
                            count += 1
            except PermissionError:
                # just skip unreadable dirs
                continue
        return count

    @staticmethod
    def first_level_code_files(root: Path, exts: Iterable[str]) -> int:
        try:
            return sum(1 for p in root.iterdir() if Extract.is_code_file(p, exts))
        except PermissionError:
            return 0

    @staticmethod
    def filtered_subdirs(root: Path) -> list[Path]:
        try:
            return [
                d for d in root.iterdir() if d.is_dir() and not Extract.is_hidden_dir(d)
            ]
        except PermissionError:
            return []

    @staticmethod
    def find_best_project_root(base: Path, exts: Iterable[str] = CODE_EXTS) -> Path:
        """
        Heuristic:
        0) Normalize to an existing dir; otherwise return base.
        1) If base itself has code files at top level → return base.
        2) If base has exactly one subdir (after filtering) and no top-level code → recurse into it
            (handles zips that wrap the project in a single folder).
        3) Otherwise, choose the subdir with the most code files (deep count).
            Tie-breakers: shallower depth wins, then lexicographical name.
        4) If no subdir has code → return base.
        """
        base = base.resolve()
        if not base.exists() or not base.is_dir():
            return base

        # (1) code files directly at base?
        if Extract.first_level_code_files(base, exts) > 0:
            return base

        subs = Extract.filtered_subdirs(base)

        # (2) descend through single wrapper folder(s)
        if len(subs) == 1:
            only = subs[0]
            # guard against infinite loop by checking if it actually changes
            if only != base:
                return Extract.find_best_project_root(only, exts)

        # (3) pick subdir with most code files
        best = None
        best_count = -1
        for d in subs:
            cnt = Extract.count_code_files(d, exts)
            if (
                cnt > best_count
                or (cnt == best_count and len(d.parts) < len((best or d).parts))
                or (cnt == best_count and d.name < (best or d).name)
            ):
                best = d
                best_count = cnt

        # (4) fallback
        return best if best and best_count > 0 else base
