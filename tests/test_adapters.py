from pathlib import Path

from gnost.languages.java import JavaAdapter
from gnost.languages.javascript import JavaScriptAdapter
from gnost.languages.python import PythonAdapter
from gnost.languages.typescript import TypeScriptAdapter


def _write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def _targets(edges) -> list:
    return [e.target for e in edges]


# ---- Python ----


def test_python_imports():
    src = "import os\nimport a.b\nfrom x.y import z\nfrom q import r\n"
    assert sorted(_targets(PythonAdapter().detect_imports("f.py", src))) == [
        "a.b",
        "os",
        "q",
        "x.y",
    ]


def test_python_imports_keep_names_levels_and_nested_imports():
    src = (
        "from pkg import (\n    a,\n    b,\n)\n"
        "from . import sibling\n"
        "from ..up import thing as t\n"
        "def f():\n    import lazy.mod\n"
    )
    edges = {
        (e.target, tuple(e.names), e.level)
        for e in PythonAdapter().detect_imports("f.py", src)
    }
    assert edges == {
        ("pkg", ("a", "b"), 0),
        ("", ("sibling",), 1),
        ("up", ("thing",), 2),
        ("lazy.mod", (), 0),
    }


def test_python_imports_fall_back_to_regex_on_syntax_error():
    src = "import os\nfrom . import x\nprint 'py2'\n"
    edges = PythonAdapter().detect_imports("f.py", src)
    assert {(e.target, e.level) for e in edges} == {("os", 0), ("", 1)}


def test_python_entry_points(tmp_path):
    f = _write(
        tmp_path,
        "m.py",
        'app = Flask(__name__)\nif __name__ == "__main__":\n    uvicorn.run(app)\n',
    )
    reasons = [e.reason for e in PythonAdapter().detect_entry_points([f])]
    assert reasons == ["__main__ guard", "Flask app initialization", "uvicorn.run"]


def test_python_entry_points_skip_non_py(tmp_path):
    f = _write(tmp_path, "m.txt", 'if __name__ == "__main__": pass')
    assert PythonAdapter().detect_entry_points([f]) == []


def test_python_framework(tmp_path):
    adapter = PythonAdapter()
    assert (
        adapter.detect_framework([_write(tmp_path, "a.py", "FastAPI()")]) == "FastAPI"
    )
    assert adapter.detect_framework([_write(tmp_path, "b.py", "Flask(x)")]) == "Flask"
    assert adapter.detect_framework([_write(tmp_path, "c.py", "x = 1")]) is None


def test_python_main_guard_must_be_a_real_guard(tmp_path):
    f = _write(tmp_path, "m.py", 'x = "__name__ and __main__ in a string"\n')
    assert PythonAdapter().detect_entry_points([f]) == []


def test_python_entry_file_name():
    adapter = PythonAdapter()
    assert adapter.is_entry_file_name("/a/Main.py")
    assert adapter.is_entry_file_name("/a/manage.py")
    assert not adapter.is_entry_file_name("/a/util.py")


# ---- JavaScript / TypeScript ----


def test_js_imports():
    src = "import a from './a';\nconst b = require('./b');\nimport {c} from \"pkg\";\n"
    # source order, as the syntax tree gives it
    assert _targets(JavaScriptAdapter().detect_imports("f.js", src)) == [
        "./a",
        "./b",
        "pkg",
    ]


def test_js_imports_multiline_dynamic_reexport_and_side_effect():
    src = (
        "import {\n  a,\n  type B,\n} from './multi';\n"
        "import type { T } from './types';\n"
        "import './side.css';\n"
        "export * from './star';\n"
        "export { x } from './named';\n"
        "const L = lazy(() => import('./lazy'));\n"
        "const r = require('./cjs');\n"
        "// import fake from './not-a-statement-but-unavoidable';\n"
    )
    targets = set(_targets(JavaScriptAdapter().detect_imports("f.ts", src)))
    assert {
        "./multi",
        "./types",
        "./side.css",
        "./star",
        "./named",
        "./lazy",
        "./cjs",
    } <= targets


def test_js_listen_must_be_a_server_not_any_listen_call(tmp_path):
    adapter = JavaScriptAdapter()
    hub = _write(tmp_path, "page.tsx", "Hub.listen('auth', () => {});\n")
    assert adapter.detect_entry_points([hub]) == []
    srv = _write(
        tmp_path, "boot.js", "const s = http.createServer(h);\napp.listen(3000);\n"
    )
    assert [e.reason for e in adapter.detect_entry_points([srv])] == [
        "Server listen() call"
    ]


def test_js_entry_points(tmp_path):
    f = _write(tmp_path, "server.js", "app.listen(3000)\n")
    reasons = [e.reason for e in JavaScriptAdapter().detect_entry_points([f])]
    assert reasons == ["Common JS entry filename", "Server listen() call"]


def test_js_framework(tmp_path):
    adapter = JavaScriptAdapter()
    assert (
        adapter.detect_framework([_write(tmp_path, "a.js", "express()")]) == "Express"
    )
    assert (
        adapter.detect_framework([_write(tmp_path, "b.js", "@nestjs/core")]) == "NestJS"
    )
    assert adapter.detect_framework([_write(tmp_path, "c.js", "x")]) is None


def test_typescript_adapter(tmp_path):
    adapter = TypeScriptAdapter()
    assert adapter.name == "typescript"
    assert adapter.extensions == [".ts", ".tsx"]
    f = _write(tmp_path, "index.ts", "export const x = 1;\n")
    assert [e.reason for e in adapter.detect_entry_points([f])] == [
        "Common JS entry filename"
    ]


def test_js_adapter_matches_jsx_and_esm_extensions():
    assert {".js", ".jsx", ".mjs", ".cjs"} <= set(JavaScriptAdapter().extensions)


# ---- Java ----


def test_java_entry_points(tmp_path):
    f = _write(
        tmp_path,
        "A.java",
        "@SpringBootApplication\nclass A implements CommandLineRunner {\n"
        "  public static void main(String[] a) {}\n}\n",
    )
    reasons = [e.reason for e in JavaAdapter().detect_entry_points([f])]
    assert reasons == [
        "public static void main",
        "@SpringBootApplication",
        "CommandLineRunner",
    ]


def test_java_imports_and_framework(tmp_path):
    adapter = JavaAdapter()
    src = "package p;\nimport a.b.C;\nimport static a.b.Util.helper;\nimport a.c.*;\n"
    # a static import names its class; a wildcard import names only a package, so it is skipped
    assert _targets(adapter.detect_imports("A.java", src)) == ["a.b.C", "a.b.Util"]
    spring = _write(tmp_path, "S.java", "import org.springframework.web.X;")
    boot = _write(tmp_path, "B.java", "@SpringBootApplication")
    plain = _write(tmp_path, "P.java", "class P {}")
    assert adapter.detect_framework([spring]) == "Spring Framework"
    assert adapter.detect_framework([boot]) == "Spring Boot"
    assert adapter.detect_framework([plain]) == "Plain Java"


# ---- Framework detection from package.json ----


def _manifest(tmp_path: Path, deps: dict, sub: str = "") -> None:
    import json

    folder = tmp_path / sub if sub else tmp_path
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "package.json").write_text(json.dumps({"dependencies": deps}))


def _framework(tmp_path: Path):
    return JavaScriptAdapter().detect_framework_from_manifest(str(tmp_path))


def test_framework_react_with_vite(tmp_path):
    import json

    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"react": "1"}, "devDependencies": {"vite": "5"}})
    )
    assert _framework(tmp_path) == "React (Vite)"


def test_framework_meta_framework_wins_over_library(tmp_path):
    _manifest(tmp_path, {"react": "1", "next": "14", "express": "4"})
    assert _framework(tmp_path) == "Next.js"


def test_framework_backend_and_other_stacks(tmp_path):
    _manifest(tmp_path, {"@nestjs/core": "10"})
    assert _framework(tmp_path) == "NestJS"
    (tmp_path / "package.json").unlink()
    _manifest(tmp_path, {"vue": "3"})
    assert _framework(tmp_path) == "Vue"
    (tmp_path / "package.json").unlink()
    _manifest(tmp_path, {"express": "4"})
    assert _framework(tmp_path) == "Express"


def test_framework_monorepo_lists_each_package(tmp_path):
    _manifest(tmp_path, {"express": "4"}, "api")
    _manifest(tmp_path, {"react": "18"}, "web")
    assert _framework(tmp_path) == "Express, React"


def test_framework_ignores_node_modules_and_bad_json(tmp_path):
    _manifest(tmp_path, {"next": "14"}, "node_modules/some-lib")
    (tmp_path / "package.json").write_text("{not json")
    assert _framework(tmp_path) is None


def test_framework_is_none_without_known_dependencies(tmp_path):
    _manifest(tmp_path, {"lodash": "4"})
    assert _framework(tmp_path) is None


# ---- Python and Java frameworks from manifests ----


def _py_framework(tmp_path: Path):
    return PythonAdapter().detect_framework_from_manifest(str(tmp_path))


def test_python_framework_from_pyproject_project_dependencies(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nkeywords = ["flask"]\n'
        'dependencies = [\n  "fastapi>=0.100",\n  "uvicorn[standard]",\n]\n'
    )
    assert _py_framework(tmp_path) == "FastAPI"  # keywords are not dependencies


def test_python_framework_from_optional_dependencies_and_poetry(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project.optional-dependencies]\nweb = ["Flask>=3"]\n'
    )
    assert _py_framework(tmp_path) == "Flask"
    (tmp_path / "pyproject.toml").write_text(
        '[tool.poetry.dependencies]\npython = "^3.11"\nDjango = "^5"\n'
    )
    assert _py_framework(tmp_path) == "Django"


def test_python_framework_from_requirements_and_pipfile(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "# web\n-r base.txt\nFastAPI==0.1\nrequests\n"
    )
    assert _py_framework(tmp_path) == "FastAPI"
    (tmp_path / "requirements.txt").unlink()
    (tmp_path / "Pipfile").write_text('[packages]\nflask = "*"\n')
    assert _py_framework(tmp_path) == "Flask"


def test_python_manifest_without_framework_is_trusted(tmp_path):
    """Declared dependencies name no framework: empty string, not None."""
    (tmp_path / "requirements.txt").write_text("rich\ntqdm\n")
    assert _py_framework(tmp_path) == ""


def test_python_without_manifest_or_dependencies_returns_none(tmp_path):
    assert _py_framework(tmp_path) is None
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
    assert _py_framework(tmp_path) is None


def test_python_detection_uses_syntax_not_text(tmp_path):
    """A regex or string that mentions Flask( / uvicorn.run is not an app."""
    f = _write(
        tmp_path,
        "adapter.py",
        'PATTERNS = {"Django": r"django\\.setup|manage\\.py", "x": "Flask("}\n'
        'HELP = "call uvicorn.run(app) and FastAPI("\n'
        'if __name__ == "__main__x":\n    pass\n',
    )
    adapter = PythonAdapter()
    assert adapter.detect_entry_points([f]) == []
    assert adapter.detect_framework([f]) is None


def test_python_framework_from_real_imports(tmp_path):
    adapter = PythonAdapter()
    assert (
        adapter.detect_framework([_write(tmp_path, "a.py", "import django\n")])
        == "Django"
    )
    assert (
        adapter.detect_framework(
            [_write(tmp_path, "b.py", "from flask import Flask\n")]
        )
        == "Flask"
    )


def test_java_framework_from_pom_and_gradle(tmp_path):
    adapter = JavaAdapter()
    (tmp_path / "pom.xml").write_text(
        "<dependency><artifactId>spring-boot-starter-web</artifactId></dependency>"
    )
    assert adapter.detect_framework_from_manifest(str(tmp_path)) == "Spring Boot"
    (tmp_path / "pom.xml").unlink()
    (tmp_path / "build.gradle.kts").write_text('plugins { id("io.quarkus") }')
    assert adapter.detect_framework_from_manifest(str(tmp_path)) == "Quarkus"
    (tmp_path / "build.gradle.kts").unlink()
    assert adapter.detect_framework_from_manifest(str(tmp_path)) is None
