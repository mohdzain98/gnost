from pathlib import Path

from gnost.languages.java import JavaAdapter
from gnost.languages.javascript import JavaScriptAdapter
from gnost.languages.python import PythonAdapter
from gnost.languages.typescript import TypeScriptAdapter
from gnost.scanner.classify import classify_lines
from gnost.scanner.engine import ScannerEngine
from gnost.scanner.filters import is_gitignored, should_ignore
from gnost.scanner.loc import scan as loc_scan


def _engine() -> ScannerEngine:
    return ScannerEngine(
        [PythonAdapter(), JavaScriptAdapter(), TypeScriptAdapter(), JavaAdapter()]
    )


def test_scan_python_fixture(fixture_repo):
    root = fixture_repo("python_app")
    result = _engine().scan(str(root))

    assert result.languages == {"python": 6}
    assert result.framework == "FastAPI"
    rels = sorted(Path(f.path).relative_to(root).as_posix() for f in result.files)
    assert "app/api.py" in rels and "main.py" in rels
    reasons = {Path(e.file).name: e.reason for e in result.entry_points}
    assert reasons["main.py"] == "__main__ guard"
    assert reasons["api.py"] == "FastAPI app initialization"


def test_scan_js_fixture(fixture_repo):
    result = _engine().scan(str(fixture_repo("js_app")))
    assert result.languages == {"javascript": 4}
    assert result.framework == "Express"


def test_scan_java_fixture(fixture_repo):
    result = _engine().scan(str(fixture_repo("java_app")))
    assert result.languages == {"java": 3}
    assert [Path(e.file).name for e in result.entry_points] == ["App.java"]


def test_typescript_files_include_tsx(fixture_repo):
    result = _engine().scan(str(fixture_repo("ts_app")))
    names = {Path(f.path).name for f in result.files}
    assert result.languages == {"typescript": 3}
    assert "view.tsx" in names


def test_scan_skips_tests_and_minified_vendor_files(fixture_repo):
    root = fixture_repo("package_app")
    result = _engine().scan(str(root))
    rels = {Path(f.path).relative_to(root).as_posix() for f in result.files}
    assert "tests/test_chat.py" not in rels
    assert "app/static/vendor/chart.min.js" not in rels
    assert "app/main.py" in rels
    assert "javascript" not in result.languages


def test_entry_points_are_ranked_and_exclude_tests(fixture_repo):
    root = fixture_repo("package_app")
    result = _engine().scan(str(root))
    summary = [
        (Path(e.file).relative_to(root).as_posix(), e.priority)
        for e in result.entry_points
    ]
    assert summary == [("app/main.py", 0), ("scripts/seed.py", 1)]


def test_python_vendor_directory_is_kept(tmp_path):
    (tmp_path / "pkg" / "vendor").mkdir(parents=True)
    (tmp_path / "pkg" / "vendor" / "icons.py").write_text("X = 1\n")
    result = _engine().scan(str(tmp_path))
    assert result.languages == {"python": 1}


def test_filters_noise_and_test_files(tmp_path):
    from gnost.scanner.filters import is_noise_file, is_test_file

    root = str(tmp_path)
    assert is_noise_file(str(Path(root, "a/lib.min.js")), root)
    assert is_noise_file(str(Path(root, "types.d.ts")), root)
    assert is_noise_file(str(Path(root, "web/vendor/x.js")), root)
    assert not is_noise_file(str(Path(root, "pkg/vendor/x.py")), root)
    assert is_test_file(str(Path(root, "tests/a.py")), root)
    assert is_test_file(str(Path(root, "src/a.test.ts")), root)
    assert is_test_file(str(Path(root, "pkg/test_a.py")), root)
    assert not is_test_file(str(Path(root, "pkg/specs/models.py")), root)
    # a test-like directory above the scan root does not matter
    assert not is_test_file(str(Path(root, "pkg/a.py")), root)


def test_scan_respects_gitignore_and_builtin_ignores(fixture_repo):
    root = fixture_repo("python_app")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "x.py").write_text("x = 1\n")
    (root / "skipme.py").write_text("x = 1\n")
    (root / ".gitignore").write_text("skipme.py\n")

    names = {Path(f.path).name for f in _engine().scan(str(root)).files}
    assert "x.py" not in names
    assert "skipme.py" not in names


def test_should_ignore_and_gitignore_rules():
    assert should_ignore("/a/node_modules/b.js")
    assert should_ignore("/a/.DS_Store")
    assert not should_ignore("/a/src/b.js")
    assert is_gitignored("/r/build/x", "/r", ["build/"])
    assert is_gitignored("/r/a.log", "/r", ["*.log"])
    assert not is_gitignored("/r/a.log", "/r", ["*.log", "!a.log"])


def test_should_ignore_matches_below_the_scan_root_only(tmp_path: Path) -> None:
    root = tmp_path / "build" / "proj"
    (root / "src").mkdir(parents=True)
    (root / "build").mkdir()
    (root / "src" / "a.py").write_text("print(1)\n")
    (root / "build" / "b.py").write_text("print(2)\n")
    assert not should_ignore(str(root / "src" / "a.py"), str(root))
    assert should_ignore(str(root / "build" / "b.py"), str(root))
    names = {Path(f.path).name for f in _engine().scan(str(root)).files}
    assert "a.py" in names
    assert "b.py" not in names


def test_classify_lines():
    lines = ["# c\n", "\n", "x = 1\n", "   \n", "y = 2  # tail\n"]
    assert classify_lines(lines, "#") == (2, 1, 2)


def test_loc_scan_python_fixture(fixture_repo):
    root = fixture_repo("python_app")
    data = loc_scan(str(root))
    py = data["by_language"]["py"]
    assert py["files"] == 6
    assert py["loc"] == py["code"] + py["comments"] + py["blanks"]
    assert any(f["path"].endswith("api.py") for f in data["files"])


def test_loc_scan_counts_tsx_and_include_exclude(fixture_repo):
    root = fixture_repo("ts_app")
    data = loc_scan(str(root))
    assert set(data["by_language"]) == {"ts", "tsx"}
    excluded = loc_scan(str(root), exclude=["src"])
    assert excluded["files"] == []


def test_scan_combines_frameworks_across_languages(tmp_path):
    (tmp_path / "package.json").write_text('{"dependencies": {"react": "18"}}')
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.tsx").write_text("export {};\n")
    (tmp_path / "api.py").write_text("app = FastAPI()\n")
    assert _engine().scan(str(tmp_path)).framework == "FastAPI, React"


def test_plain_java_is_dropped_when_another_framework_exists(tmp_path):
    (tmp_path / "package.json").write_text('{"dependencies": {"next": "14"}}')
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages" / "index.js").write_text("export default 1;\n")
    (tmp_path / "A.java").write_text("class A {}\n")
    assert _engine().scan(str(tmp_path)).framework == "Next.js"


def test_declared_dependencies_override_a_source_guess(tmp_path):
    """requirements.txt lists no framework, so a stray Flask( call is ignored."""
    (tmp_path / "requirements.txt").write_text("rich\n")
    (tmp_path / "a.py").write_text("app = Flask(__name__)\n")
    assert _engine().scan(str(tmp_path)).framework is None


def test_gitignore_patterns_match_like_git(tmp_path: Path) -> None:
    root = tmp_path
    for rel in (
        "test/a.py",
        "pkg/test/b.py",
        "pkg/src/c.py",
        "build/d.py",
        "pkg/build/e.py",
        "x.log",
        "pkg/y.log",
    ):
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x\n")
    patterns = ["test/", "/build", "*.log", "!pkg/y.log"]

    def ignored(rel):
        return is_gitignored(str(root / rel), str(root), patterns)

    # "test/" has no other slash, so it matches a folder of that name at any depth.
    assert (
        ignored("test/a.py")
        and ignored("pkg/test/b.py")
        and not ignored("pkg/src/c.py")
    )
    # "/build" is relative to the root only.
    assert ignored("build/d.py") and not ignored("pkg/build/e.py")
    # Later negations win.
    assert ignored("x.log") and not ignored("pkg/y.log")


def test_folder_only_pattern_does_not_match_a_file_of_that_name(tmp_path: Path) -> None:
    (tmp_path / "test").write_text("a file called test\n")
    assert not is_gitignored(str(tmp_path / "test"), str(tmp_path), ["test/"])


def test_summary_scan_skips_vendored_and_minified_js(tmp_path: Path) -> None:
    from gnost.scanner.loc import scan

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.js").write_text("const a = 1;\n")
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor" / "big.js").write_text("const b = 2;\n" * 50)
    (tmp_path / "src" / "bundle.min.js").write_text("x\n" * 10)
    result = scan(str(tmp_path))
    assert [f["path"] for f in result["files"]] == [str(Path("src") / "app.js")]


def test_one_row_per_language() -> None:
    from gnost.config.languages import by_language_name

    merged = by_language_name(
        {
            "js": {"files": 2, "loc": 10, "code": 8},
            "jsx": {"files": 1, "loc": 5, "code": 4},
            "py": {"files": 3, "loc": 30, "code": 25},
        }
    )
    assert merged["JavaScript"] == {"files": 3, "loc": 15, "code": 12}
    assert list(merged) == ["JavaScript", "Python"]


def test_exclude_keeps_the_dot_of_hidden_folder_patterns(tmp_path) -> None:
    from gnost.scanner.filters import is_excluded

    root = str(tmp_path)
    assert is_excluded(str(tmp_path / ".gnost" / "a.py"), root, [".gnost"])
    assert not is_excluded(str(tmp_path / "gnost" / "a.py"), root, [".gnost"])
    assert is_excluded(str(tmp_path / "legacy" / "a.py"), root, ["./legacy"])
