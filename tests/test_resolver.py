from pathlib import Path

from gnost.core.graph import DependencyGraph
from gnost.languages.python import PythonAdapter
from gnost.scanner.engine import ScannerEngine


def _graph(root: Path) -> DependencyGraph:
    scan = ScannerEngine([PythonAdapter()]).scan(str(root))
    return DependencyGraph.from_scan(scan)


def _deps(graph: DependencyGraph, root: Path, rel: str) -> set:
    return {
        Path(d).relative_to(root).as_posix()
        for d in graph.dependencies_of(str(root / rel))
    }


def test_package_app_resolution(fixture_repo):
    root = fixture_repo("package_app")
    graph = _graph(root)

    assert _deps(graph, root, "app/main.py") == {
        "app/services/__init__.py",
        "app/api/v1/__init__.py",
        "app/api/v1/chat.py",
        "app/api/v1/notes.py",
        "app/config.py",
    }
    # relative imports: `from .notes import helper` and `from ...models import Note`
    assert _deps(graph, root, "app/api/v1/chat.py") == {
        "app/services/store.py",
        "app/services/__init__.py",
        "app/api/v1/notes.py",
    }
    assert _deps(graph, root, "app/api/v1/notes.py") == {
        "app/models.py",
        "app/config.py",
    }


def test_exact_module_names_not_suffix_matches(tmp_path):
    """`import config` must not bind to some_other/config.py."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "config.py").write_text("")
    (tmp_path / "other").mkdir()
    (tmp_path / "other" / "config.py").write_text("")
    (tmp_path / "main.py").write_text("import config\n")
    assert _deps(_graph(tmp_path), tmp_path, "main.py") == set()


def test_src_layout(tmp_path):
    pkg = tmp_path / "src" / "mylib"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text("")
    (pkg / "api.py").write_text("from mylib.core import x\n")
    graph = _graph(tmp_path)
    assert _deps(graph, tmp_path, "src/mylib/api.py") == {"src/mylib/core.py"}


def test_import_of_symbol_from_module_links_module(tmp_path):
    (tmp_path / "util.py").write_text("def f(): ...\n")
    (tmp_path / "main.py").write_text("from util import f\n")
    assert _deps(_graph(tmp_path), tmp_path, "main.py") == {"util.py"}


def test_self_import_is_ignored(tmp_path):
    (tmp_path / "a.py").write_text("import a\n")
    assert _deps(_graph(tmp_path), tmp_path, "a.py") == set()


# ---- JavaScript / TypeScript ----


def _js_deps(fixture_repo, rel):
    from gnost.languages.javascript import JavaScriptAdapter
    from gnost.languages.typescript import TypeScriptAdapter

    root = fixture_repo("react_app")
    scan = ScannerEngine([JavaScriptAdapter(), TypeScriptAdapter()]).scan(str(root))
    graph = DependencyGraph.from_scan(scan)
    return root, graph, _deps(graph, root, rel)


def test_tsconfig_alias_with_comments_and_references(fixture_repo):
    _, _, deps = _js_deps(fixture_repo, "src/main.tsx")
    assert deps == {"src/App.tsx"}


def test_js_multiline_dynamic_reexport_and_query_imports(fixture_repo):
    _, _, deps = _js_deps(fixture_repo, "src/App.tsx")
    assert deps == {
        "src/components/ui/button.tsx",
        "src/hooks/useThing.ts",
        "src/pages/Home.tsx",  # lazy(() => import('@/pages/Home'))
        "src/pages/About.tsx",  # lazy(() => import('./pages/About'))
    }  # '@/lib/schema.json?raw' is not a scanned source file


def test_js_index_and_reexport_resolution(fixture_repo):
    root, graph, deps = _js_deps(fixture_repo, "src/pages/About.tsx")
    assert deps == {"src/components/ui/index.ts"}
    assert _deps(graph, root, "src/components/ui/index.ts") == {
        "src/components/ui/button.tsx"
    }
    assert _deps(graph, root, "src/pages/Home.tsx") == {"src/lib/index.ts"}
    assert _deps(graph, root, "src/lib/index.ts") == {"src/lib/helper.ts"}


def test_at_alias_falls_back_to_src_without_tsconfig(tmp_path):
    from gnost.languages.typescript import TypeScriptAdapter

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.ts").write_text("import { b } from '@/b';\n")
    (tmp_path / "src" / "b.ts").write_text("export const b = 1;\n")
    scan = ScannerEngine([TypeScriptAdapter()]).scan(str(tmp_path))
    graph = DependencyGraph.from_scan(scan)
    assert _deps(graph, tmp_path, "src/a.ts") == {"src/b.ts"}


def test_tsconfig_base_url(tmp_path):
    from gnost.languages.typescript import TypeScriptAdapter

    (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {"baseUrl": "src"}}')
    (tmp_path / "src" / "utils").mkdir(parents=True)
    (tmp_path / "src" / "utils" / "x.ts").write_text("")
    (tmp_path / "src" / "a.ts").write_text(
        "import x from 'utils/x';\nimport r from 'react';\n"
    )
    scan = ScannerEngine([TypeScriptAdapter()]).scan(str(tmp_path))
    graph = DependencyGraph.from_scan(scan)
    assert _deps(graph, tmp_path, "src/a.ts") == {"src/utils/x.ts"}
