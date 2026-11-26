"""Publishes the flow explorer where GitHub Pages can serve it (`gnost onboard --pages`).

Pages serves only the repository root or `docs/`, so the explorer is copied to `docs/index.html`
or, when `docs/` already holds a site, `docs/gnost/index.html`. GNOST never overwrites a page it
did not write (it marks its own), and keeps the page out of GitHub's language bar.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from gnost.vcs.git import GitError, GitRepository

DOCS = "docs"
OWN_FOLDER = "docs/gnost"
PAGE = "index.html"
MARKER = "<!-- gnost:pages - the GNOST flow explorer; gnost onboard --pages rewrites this file -->"
ATTRIBUTES_LINE = "/index.html linguist-generated=true"  # this folder's page only
LARGE_PAGE = 5 * 1024 * 1024


class PagesError(Exception):
    """The page cannot be written where it should go; the message says what to change."""


@dataclass(frozen=True)
class GitHubRepo:
    """The owner and name of a GitHub repository, read from its `origin` address."""

    owner: str
    name: str

    # https://github.com/o/r(.git), ssh://git@github.com/o/r, git@github.com:o/r, and SSH
    # host aliases such as git@github.com-work:o/r
    _ADDRESS = re.compile(
        r"^(?:https?://(?:[^@/]+@)?|ssh://[^@/]+@|[^@/]+@)"
        r"github\.com(?:-[\w.-]+)?[:/]([\w.-]+)/([\w.-]+?)(?:\.git)?/?$"
    )

    @classmethod
    def parse(cls, address: str) -> Optional["GitHubRepo"]:
        """The repository of a github.com address, or None for any other host."""
        found = cls._ADDRESS.match(address.strip())
        return cls(found.group(1), found.group(2)) if found else None

    def pages_url(self, served: str) -> str:
        """The Pages address of a folder served from the site root (`""` is the home page)."""
        user_site = self.name.lower() == f"{self.owner.lower()}.github.io"
        base = f"https://{self.owner.lower()}.github.io/" + (
            "" if user_site else f"{self.name}/"
        )
        return base + (f"{served}/" if served else "")


@dataclass(frozen=True)
class PagesRequest:
    """`--pages` or `[onboard] pages` as asked: a folder, or None to choose one from `docs/`."""

    folder: Optional[str] = None
    origin: str = "--pages"

    @classmethod
    def resolve(
        cls, flag: Optional[str], configured: object
    ) -> Optional["PagesRequest"]:
        """Combine the flag (None absent, "" bare) with the config value; None means off."""
        setting = (
            f'.gnost.toml (pages = "{configured}")'
            if isinstance(configured, str)
            else ""
        )
        if flag:
            return cls(flag, f"--pages {flag}")
        if flag == "":
            return cls(configured, setting) if isinstance(configured, str) else cls()
        if isinstance(configured, str) and configured:
            return cls(configured, setting)
        return cls() if configured is True else None


@dataclass(frozen=True)
class PagesTarget:
    """Where the page goes (a folder relative to the repository root) and why."""

    folder: str
    reason: str
    warning: Optional[str] = None


@dataclass
class PagesResult:
    """What publishing did: the file written, its address, and the lines to print."""

    path: str
    url: Optional[str]
    lines: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class PagesPlanner:
    """Chooses the folder for the page: the configured one, or by looking at `docs/`.

    No site in `docs/` puts the page at `docs/index.html` (the site's home page); an existing
    site (its own index page or a Sphinx, MkDocs, Jekyll or Docusaurus setup) moves it to `docs/gnost/`.
    """

    SITE_FILES: Tuple[str, ...] = (
        "docs/index.md",
        "docs/README.md",
        "docs/conf.py",
        "docs/source/conf.py",
        "docs/_config.yml",
        "docs/mkdocs.yml",
        "mkdocs.yml",
        "docs/docusaurus.config.js",
        "docs/docusaurus.config.ts",
        "docusaurus.config.js",
        "docusaurus.config.ts",
    )

    def __init__(
        self, root: str, configured: Optional[str] = None, origin: str = ""
    ) -> None:
        """`configured` is a folder from --pages or .gnost.toml; `origin` names where it came from."""
        self.root = root
        self.configured = configured
        self.origin = origin

    def choose(self) -> PagesTarget:
        """The target folder. Raises PagesError for a folder outside the repository."""
        if self.configured:
            folder = self._inside(self.configured)
            return PagesTarget(folder, f"Pages: using {folder}/ from {self.origin}")
        if self.is_ours(f"{OWN_FOLDER}/{PAGE}"):
            return PagesTarget(OWN_FOLDER, "")
        site = self.existing_site()
        if self.is_ours(f"{DOCS}/{PAGE}"):
            if not site:
                return PagesTarget(DOCS, "")
            return PagesTarget(
                OWN_FOLDER,
                "",
                f"Pages: {DOCS}/ now has a site (found {site}), so the explorer moved to "
                f"{OWN_FOLDER}/; the old {DOCS}/{PAGE} was left in place",
            )
        if site:
            return PagesTarget(
                OWN_FOLDER,
                f"Pages: {DOCS}/ already has a site (found {site}), so the explorer goes to "
                f"{OWN_FOLDER}/{PAGE}",
            )
        return PagesTarget(
            DOCS,
            f"Pages: no site found in {DOCS}/, so the explorer is the site's home page: "
            f"{DOCS}/{PAGE}",
        )

    def existing_site(self) -> Optional[str]:
        """The first file showing that a site already exists, or None."""
        if os.path.isfile(self._path(f"{DOCS}/{PAGE}")) and not self.is_ours(
            f"{DOCS}/{PAGE}"
        ):
            return f"{DOCS}/{PAGE}"
        for name in self.SITE_FILES:
            if os.path.isfile(self._path(name)):
                return name
        return None

    def is_ours(self, relative: str) -> bool:
        """True when the file exists and carries GNOST's marker."""
        try:
            with open(
                self._path(relative), encoding="utf-8", errors="ignore"
            ) as handle:
                return MARKER in handle.read(4096)
        except OSError:
            return False

    def _path(self, relative: str) -> str:
        return os.path.join(self.root, *relative.split("/"))

    def _inside(self, folder: str) -> str:
        """The folder as a clean relative POSIX path; it must stay inside the repository."""
        if os.path.isabs(folder):
            raise PagesError(
                f"Pages: the folder must be relative to the repository, got {folder}"
            )
        clean = os.path.normpath(folder).replace(os.sep, "/").strip("/")
        if clean in ("", ".") or clean == ".." or clean.startswith("../"):
            raise PagesError(
                f"Pages: '{folder}' is not a folder inside the repository; use docs or docs/gnost"
            )
        return clean


class PagesPublisher:
    """Writes the explorer into the chosen folder, with the marker and a `.gitattributes`."""

    def __init__(
        self,
        root: str,
        configured: Optional[str] = None,
        origin: str = "",
        repository: Optional[GitRepository] = None,
    ) -> None:
        self.root = root
        self.planner = PagesPlanner(root, configured, origin)
        self.repository = repository

    def check(self) -> PagesTarget:
        """Choose the target and refuse a foreign page there; call it before the slow work."""
        target = self.planner.choose()
        relative = f"{target.folder}/{PAGE}"
        path = os.path.join(self.root, *relative.split("/"))
        if os.path.isfile(path) and not self.planner.is_ours(relative):
            hint = (
                f'set pages = "{OWN_FOLDER}"'
                if target.folder != OWN_FOLDER
                else "choose another folder"
            )
            raise PagesError(
                f"Pages: {relative} exists and was not written by GNOST; {hint} or move that file"
            )
        return target

    def publish(self, html: str) -> PagesResult:
        """Write the page and return what happened. Raises PagesError instead of overwriting."""
        target = self.check()
        relative = f"{target.folder}/{PAGE}"
        path = os.path.join(self.root, *relative.split("/"))
        existed = os.path.isfile(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        page = self.mark(html)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(page)

        result = PagesResult(path=relative, url=None)
        if target.reason:
            result.lines.append(target.reason)
        if existed:
            result.lines.append(f"Pages: updated {relative} (written by GNOST before)")
        if target.warning:
            result.warnings.append(target.warning)
        if not existed and self.write_attributes(target.folder):
            result.lines.append(
                f"Pages: wrote {target.folder}/.gitattributes so the page does not count as HTML "
                "in GitHub's language bar (delete it to count it)"
            )
        size = len(page.encode("utf-8"))
        if size > LARGE_PAGE:
            result.warnings.append(
                f"Pages: the page is {size / 1024 / 1024:.1f} MB; GitHub Pages allows it, but every "
                "commit of a new version adds that much to the repository history"
            )
        result.url, where = self.address(target.folder)
        result.lines.append(where)
        return result

    @staticmethod
    def mark(html: str) -> str:
        """The page with GNOST's marker after the doctype (a comment before it breaks rendering)."""
        if MARKER in html:
            return html
        first, newline, rest = html.partition("\n")
        if first.lower().startswith("<!doctype"):
            return f"{first}\n{MARKER}\n{rest}" if newline else f"{first}\n{MARKER}\n"
        return f"{MARKER}\n{html}"

    def write_attributes(self, folder: str) -> bool:
        """Add the Linguist line to `<folder>/.gitattributes` once; True when the file changed."""
        path = os.path.join(self.root, *folder.split("/"), ".gitattributes")
        current = ""
        if os.path.isfile(path):
            with open(path, encoding="utf-8", errors="ignore") as handle:
                current = handle.read()
            if any(line.strip() == ATTRIBUTES_LINE for line in current.splitlines()):
                return False
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            if current and not current.endswith("\n"):
                handle.write("\n")
            handle.write(ATTRIBUTES_LINE + "\n")
        return True

    def address(self, folder: str) -> Tuple[Optional[str], str]:
        """The page's URL and the line that explains how to turn Pages on."""
        if folder == DOCS or folder.startswith(f"{DOCS}/"):
            setting, served = "/docs", folder[len(DOCS) :].strip("/")
        else:
            setting, served = "/ (root)", folder
        repo, branch = self._github()
        if repo is None:
            return None, (
                f"Pages: no github.com 'origin' remote, so the address is unknown; enable Pages "
                f"(Settings > Pages > folder {setting}) and open {served or 'the site root'}/ on your Pages site"
            )
        url = repo.pages_url(served)
        return url, (
            f"Pages: URL after you enable Pages (Settings > Pages > Branch: {branch}, "
            f"folder {setting}): {url}"
        )

    def _github(self) -> Tuple[Optional[GitHubRepo], str]:
        """The GitHub repository behind `origin` and its default branch (main if unknown)."""
        repository = self.repository
        if repository is None:
            try:
                repository = GitRepository.containing(self.root)
            except GitError:
                repository = None
        if repository is None:
            return None, "main"
        try:
            repo = GitHubRepo.parse(
                repository.run(["remote", "get-url", "origin"]).strip()
            )
        except GitError:
            return None, "main"
        try:
            head = repository.run(
                ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"]
            ).strip()
            branch = head.split("/", 1)[1] if "/" in head else "main"
        except GitError:
            branch = "main"
        return repo, branch
