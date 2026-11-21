"""Remote repositories: address checks, safe cloning, cleanup, and the untrusted-code guarantee."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from gitrepo import make_repo
from gnost.cli import app
from gnost.vcs.git import GitError, GitRunner
from gnost.vcs.remote import CloneLimits, RemoteClone, RemoteError, RemoteUrl

needs_git = pytest.mark.skipif(
    shutil.which("git") is None, reason="git is not installed"
)
D1 = "2026-01-01T10:00:00+00:00"


@pytest.mark.parametrize(
    "text",
    [
        "https://github.com/owner/repo",
        "https://github.com/owner/repo.git",
        "ssh://git@github.com/owner/repo.git",
        "git@github.com:owner/repo.git",
    ],
)
def test_https_and_ssh_addresses_are_accepted(text: str) -> None:
    assert RemoteUrl.parse(text).text == text
    assert RemoteUrl.looks_remote(text)


@pytest.mark.parametrize(
    "text",
    [
        "ssh://git@host:2222/owner/repo.git",
        "https://user@host/owner/repo",
        "https://host/owner/repo/",
        "git@host:group/subgroup/repo.git",
    ],
)
def test_additional_repository_address_forms_are_accepted(text: str) -> None:
    assert RemoteUrl.parse(text).text == text
    assert RemoteUrl.looks_remote(text)


@pytest.mark.parametrize(
    "text",
    [
        "http://example.com/r.git",
        "git://example.com/r.git",
        "ext::sh -c touch% /tmp/pwned",
        "file:///etc/passwd",
        "--upload-pack=touch /tmp/pwned",
        "https://example.com/r.git --evil",
        "ftp://example.com/r",
        "",
    ],
)
def test_anything_that_could_run_a_program_is_refused(text: str) -> None:
    with pytest.raises(RemoteError):
        RemoteUrl.parse(text)


def test_folders_are_not_mistaken_for_addresses(tmp_path: Path) -> None:
    assert not RemoteUrl.looks_remote(".")
    assert not RemoteUrl.looks_remote(str(tmp_path))
    assert not RemoteUrl.looks_remote("src/app")
    assert RemoteUrl("https://h/o/my-repo.git").name == "my-repo"
    assert RemoteUrl("git@h:o/r").name == "r"


@pytest.mark.skipif(
    os.name == "nt", reason="Windows paths cannot contain the SCP colon"
)
def test_existing_scp_style_folder_is_not_mistaken_for_an_address(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    address = Path("git@host:group/subgroup/repo.git")
    monkeypatch.chdir(tmp_path)
    address.mkdir(parents=True)

    assert address.is_dir()
    assert not RemoteUrl.looks_remote(str(address))


class FakeRunner(GitRunner):
    """Records the clone commands and fails the ones named in `fail`."""

    def __init__(self, fail: int = 0) -> None:
        super().__init__()
        self.calls: List[List[str]] = []
        self.envs: List[Optional[Dict[str, str]]] = []
        self.fail = fail

    def run(
        self,
        args: List[str],
        cwd: str,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> str:  # type: ignore[override]
        self.calls.append(args)
        self.envs.append(env)
        if len(self.calls) <= self.fail:
            raise GitError("git clone failed: filter not supported")
        target = args[-1]
        os.makedirs(target, exist_ok=True)
        Path(target, "a.py").write_text("x = 1\n")
        return ""


def test_the_clone_command_turns_off_everything_that_could_run_code() -> None:
    runner = FakeRunner()
    with RemoteClone(RemoteUrl("https://h/o/r"), runner=runner):
        pass
    args = runner.calls[0]
    joined = " ".join(args)
    for expected in (
        "core.hooksPath=" + os.devnull,
        "core.symlinks=false",
        "protocol.allow=never",
        "protocol.https.allow=always",
        "--no-recurse-submodules",
        "--filter=blob:none",
        "--no-tags",
    ):
        assert expected in joined
    assert "protocol.file.allow" not in joined
    assert (
        args[-3] == "--" and args[-2] == "https://h/o/r"
    )  # the address can never be a flag
    env = runner.envs[0] or {}
    assert (
        env["GIT_TERMINAL_PROMPT"] == "0" and "BatchMode=yes" in env["GIT_SSH_COMMAND"]
    )


def test_a_server_without_filters_falls_back_to_a_shallow_clone() -> None:
    runner = FakeRunner(fail=1)
    with RemoteClone(RemoteUrl("https://h/o/r"), runner=runner):
        pass
    assert "--filter=blob:none" in runner.calls[0]
    assert (
        "--depth=500" in runner.calls[1] and "--filter=blob:none" not in runner.calls[1]
    )


def test_a_clone_that_fails_twice_explains_what_to_do() -> None:
    with pytest.raises(RemoteError, match="could not clone r"):
        with RemoteClone(RemoteUrl("https://h/o/r"), runner=FakeRunner(fail=2)):
            pass


def test_the_clone_is_deleted_after_use_and_after_an_error() -> None:
    clone = RemoteClone(RemoteUrl("https://h/o/r"), runner=FakeRunner())
    with clone as folder:
        assert os.path.isdir(folder)
    assert not os.path.exists(folder)
    with pytest.raises(KeyboardInterrupt):
        with RemoteClone(RemoteUrl("https://h/o/r"), runner=FakeRunner()) as again:
            raise KeyboardInterrupt
    assert not os.path.exists(again)


def test_a_checkout_over_the_size_limit_is_refused_and_removed() -> None:
    clone = RemoteClone(
        RemoteUrl("https://h/o/r"),
        limits=CloneLimits(max_megabytes=0),
        runner=FakeRunner(),
    )
    with pytest.raises(RemoteError, match="larger than 0 MB"):
        clone.__enter__()
    assert not os.path.exists(clone.folder)


@needs_git
def test_a_real_clone_through_git(tmp_path: Path) -> None:
    source = make_repo(tmp_path / "src", [("Ada", {"m.py": "x = 1\n"}, D1)])
    with RemoteClone(RemoteUrl(source.as_uri()), protocols=("file",)) as folder:
        assert (Path(folder) / "m.py").read_text() == "x = 1\n"
    assert not os.path.exists(folder)


def test_a_file_address_is_not_allowed_by_default(tmp_path: Path) -> None:
    source = make_repo(tmp_path / "src", [("Ada", {"m.py": "x = 1\n"}, D1)])
    with pytest.raises(RemoteError):
        with RemoteClone(RemoteUrl(source.as_uri())):
            pass


# ---------------------------------------------------------------- untrusted code

EVIL_PLUGIN = (
    "import os\n"
    "canary = os.environ['GNOST_CANARY']\n"
    "open(canary, 'a').write('plugin ran\\n')\n"
    "from mypy.plugin import Plugin\n"
    "class P(Plugin):\n    pass\n"
    "def plugin(version):\n    return P\n"
)


def hostile_repo(root: Path) -> Path:
    """A repository whose own tool configs try to run code or write outside the clone."""
    files = {
        "evil_plugin.py": EVIL_PLUGIN,
        "mypy.ini": "[mypy]\nplugins = evil_plugin\nmypy_path = .\n",
        "setup.cfg": "[mypy]\nplugins = evil_plugin\n",
        "pyproject.toml": '[tool.mypy]\nplugins = ["evil_plugin"]\n',
        ".gnost.toml": 'output_dir = "/tmp/gnost-should-never-be-written"\n',
        "app.py": "def f(x):\n    return x\n",
    }
    return make_repo(root, [("Mallory", files, D1)])


@needs_git
def test_the_threat_is_real_a_repo_mypy_config_does_run_its_plugin(
    tmp_path: Path,
) -> None:
    repo = hostile_repo(tmp_path / "evil")
    canary = tmp_path / "canary-control"
    env = dict(os.environ, GNOST_CANARY=str(canary))
    subprocess.run(
        [sys.executable, "-m", "mypy", str(repo / "app.py")],
        cwd=repo,
        env=env,
        capture_output=True,
    )
    assert canary.exists(), (
        "control failed: mypy no longer runs repo plugins, the test below proves nothing"
    )


class LocalTarget:
    """Lets the CLI treat a local repository as a remote address (tests only)."""

    def __init__(self, source: Path) -> None:
        self.source = source


@needs_git
def test_analyzing_a_remote_repository_never_runs_its_code_or_reads_its_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = hostile_repo(tmp_path / "evil")
    canary = tmp_path / "canary"
    monkeypatch.setenv("GNOST_CANARY", str(canary))
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)

    import gnost.cli.commands.remote as remote_module

    class FileUrl(RemoteUrl):
        @staticmethod
        def looks_remote(text: str) -> bool:
            return text.startswith("file://")

        @classmethod
        def parse(cls, text: str) -> "FileUrl":
            return cls(text)

    class FileClone(RemoteClone):
        def __init__(
            self, url: RemoteUrl, ref: Optional[str] = None, **kw: Any
        ) -> None:
            super().__init__(url, ref, protocols=("file",), **kw)

    monkeypatch.setattr(remote_module, "RemoteUrl", FileUrl)
    monkeypatch.setattr(remote_module, "RemoteClone", FileClone)
    monkeypatch.setattr(
        sys, "argv", ["gnost", "analyze", repo.as_uri(), "--no-progress", "-o"]
    )

    app.main()

    assert not canary.exists(), "the repository's mypy plugin ran"
    report = work / ".gnost" / "evil" / "analysis" / "analysis.json"
    assert (
        report.is_file()
    )  # outputs: the current folder, in a folder named after the repository
    assert (
        "Missing Function Annotations" in report.read_text()
    )  # mypy did run, with our config
    assert not os.path.exists("/tmp/gnost-should-never-be-written")
    assert not [
        p
        for p in os.listdir(tempfile_dir())
        if p.startswith("gnost-clone-") and str(repo.name) in p
    ]
    assert os.environ.get("GNOST_UNTRUSTED_REPO") is None  # restored afterwards


def tempfile_dir() -> str:
    import tempfile

    return tempfile.gettempdir()


def test_a_plain_http_address_is_a_usage_error_not_a_crash(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setattr(sys, "argv", ["gnost", "onboard", "http://github.com/a/b"])
    assert app.main() == 2
    assert "use the https:// address" in capsys.readouterr().err


def test_remove_tree_deletes_read_only_files(tmp_path: Path) -> None:
    """git marks object files read-only; Windows refuses to delete those without a chmod."""
    import stat

    from gnost.utils.fs import remove_tree

    folder = tmp_path / "clone" / ".git" / "objects"
    folder.mkdir(parents=True)
    locked = folder / "pack.idx"
    locked.write_text("x")
    locked.chmod(stat.S_IREAD)
    remove_tree(str(tmp_path / "clone"))
    assert not (tmp_path / "clone").exists()


def test_the_slug_is_a_safe_folder_name() -> None:
    assert RemoteUrl("https://github.com/o/jev-use").slug == "jev-use"
    assert RemoteUrl("git@github.com:o/my repo.git".replace(" ", "")).slug == "myrepo"
    assert RemoteUrl("https://h/o/..").slug == "repository"
    assert "/" not in RemoteUrl("https://h/o/a%2Fb").slug
