"""The tree-sitter layer: parser factory, JS/TS/Java queries, fallbacks and same-package Java edges."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

import pytest

from gnost.core.graph import DependencyGraph
from gnost.languages.java import JavaAdapter
from gnost.languages.javascript import JavaScriptAdapter
from gnost.languages.typescript import TypeScriptAdapter
from gnost.parsing import ParserFactory, default_factory
from gnost.parsing.queries import EcmaScriptQueries, JavaQueries
from gnost.scanner.engine import ScannerEngine

FACTORY = default_factory()
needs_grammars = pytest.mark.skipif(
    not (FACTORY.available("javascript") and FACTORY.available("java")),
    reason="tree-sitter grammars are not installed",
)


def regex_factory() -> ParserFactory:
    return ParserFactory(environ={"GNOST_PARSER": "regex"})


def pairs(edges) -> List[Tuple[str, bool]]:
    return [(e.target, e.deferred) for e in edges]


# --------------------------------------------------------------- the factory


@needs_grammars
def test_every_grammar_loads_and_parses() -> None:
    for grammar, code in (
        ("javascript", b"let a = 1;"),
        ("typescript", b"let a: number = 1;"),
        ("tsx", b"const a = <div/>;"),
        ("java", b"class A {}"),
    ):
        tree = FACTORY.parse(grammar, code)
        assert tree is not None and not tree.has_error, grammar


def test_a_grammar_that_cannot_load_is_reported_not_raised() -> None:
    def broken():
        raise ImportError("no wheel for this platform")

    factory = ParserFactory(environ={}, loaders={"java": broken})
    assert factory.available("java") is False
    assert factory.parse("java", b"class A {}") is None
    assert "no wheel" in (factory.reason("java") or "")
    assert factory.status(["java", "python"]) == {"java": "regex", "python": "ast"}


def test_the_switch_turns_tree_sitter_off() -> None:
    factory = regex_factory()
    assert factory.enabled is False and factory.parse("javascript", b"1") is None
    assert "GNOST_PARSER" in (factory.reason("javascript") or "")


@needs_grammars
def test_status_names_the_reader_of_each_language() -> None:
    status = FACTORY.status(["python", "javascript", "typescript", "java", "go"])
    assert status == {
        "java": "tree-sitter",
        "javascript": "tree-sitter",
        "python": "ast",
        "typescript": "tree-sitter",
    }


def test_unknown_extensions_have_no_grammar() -> None:
    assert FACTORY.grammar_for(".rb") is None
    assert FACTORY.grammar_for(".TSX") == "tsx"
    assert FACTORY.grammar_for(".mjs") == "javascript"


# --------------------------------------------------------- JavaScript / TypeScript


@needs_grammars
def test_comments_and_strings_cannot_fake_an_import() -> None:
    source = (
        "// import a from 'in-a-comment'\n"
        "/* const b = require('in-a-block') */\n"
        "const text = \"import c from 'in-a-string'\";\n"
        "import real from './real';\n"
    )
    assert pairs(JavaScriptAdapter().detect_imports("f.js", source)) == [
        ("./real", False)
    ]
    # the text reader is the one that is fooled; that is why the tree is used
    regex = JavaScriptAdapter(regex_factory()).detect_imports("f.js", source)
    assert len(regex) > 1


@needs_grammars
def test_every_import_form_in_javascript() -> None:
    source = (
        "import a from './a';\nimport {b} from './b';\nimport * as c from './c';\n"
        "import './side-effect';\nexport * from './re-export';\nexport {d} from './d';\n"
        "const e = require('./e');\nconst f = () => import('./f');\n"
        "const g = require(`./template`);\nconst h = require(name);\n"
    )
    got = dict(pairs(JavaScriptAdapter().detect_imports("m.js", source)))
    assert got == {
        "./a": False,
        "./b": False,
        "./c": False,
        "./side-effect": False,
        "./re-export": False,
        "./d": False,
        "./e": False,
        "./f": True,  # dynamic import: deferred
        "./template": False,
    }  # require(name) is not a literal, so it is not an edge


@needs_grammars
def test_type_only_imports_are_deferred_in_typescript() -> None:
    source = (
        "import type {A} from './a';\nimport {type B, type C} from './b';\n"
        "import {type D, E} from './c';\nexport type {F} from './f';\n"
        "import x = require('./x');\nimport {y} from './y';\nimport type {Y} from './y';\n"
    )
    got = dict(pairs(TypeScriptAdapter().detect_imports("m.ts", source)))
    assert got["./a"] is True and got["./b"] is True and got["./f"] is True
    assert got["./c"] is False  # one real name makes it a real import
    assert got["./x"] is False
    assert got["./y"] is False  # one eager import makes the edge eager


@needs_grammars
def test_tsx_and_jsx_files_parse() -> None:
    tsx = "import React from 'react';\nexport const A = () => <div>{import('./lazy')}</div>;\n"
    assert (
        dict(pairs(TypeScriptAdapter().detect_imports("a.tsx", tsx)))["react"] is False
    )
    jsx = "import B from './b';\nconst C = () => <B/>;\n"
    assert pairs(JavaScriptAdapter().detect_imports("c.jsx", jsx)) == [("./b", False)]


@needs_grammars
def test_a_syntax_error_does_not_lose_the_rest_of_the_file() -> None:
    source = (
        "import ok from './ok';\nfunction broken( {{{ \nimport also from './also';\n"
    )
    got = dict(pairs(JavaScriptAdapter().detect_imports("bad.js", source)))
    assert "./ok" in got


@needs_grammars
def test_empty_binary_and_non_utf8_content_do_not_crash() -> None:
    adapter = JavaScriptAdapter()
    assert adapter.detect_imports("e.js", "") == []
    assert adapter.detect_imports("b.js", "\x00\x01\x02 import") == []
    assert adapter.detect_imports("n.js", "const s = '\udcff'; import a from './a';")


@needs_grammars
def test_very_deep_nesting_does_not_hit_the_recursion_limit() -> None:
    source = "const x = " + "(" * 4000 + "1" + ")" * 4000 + ";\nimport a from './a';\n"
    assert ("./a", False) in pairs(JavaScriptAdapter().detect_imports("d.js", source))


def test_the_regex_fallback_matches_the_tree_on_ordinary_code() -> None:
    source = "import a from './a';\nconst b = require('./b');\nimport('./c');\n"
    tree = dict(pairs(JavaScriptAdapter().detect_imports("m.js", source)))
    regex = dict(
        pairs(JavaScriptAdapter(regex_factory()).detect_imports("m.js", source))
    )
    assert tree == regex == {"./a": False, "./b": False, "./c": True}


# ---------------------------------------------------------------------- Java


JAVA = (
    "package p.q;\nimport a.B;\nimport a.*;\nimport static a.C.helper;\nimport static a.D.*;\n"
    "@Service\nclass X extends Base implements Port {\n  Helper h;\n"
    "  void run() { Util.go(); int k = Config.LIMIT; Missing m; }\n  class Inner {}\n}\n"
)


@needs_grammars
def test_java_queries() -> None:
    tree = FACTORY.parse("java", JAVA.encode())
    queries = JavaQueries()
    assert queries.package(tree) == "p.q"
    assert queries.imports(tree) == ["a.B", "a.C", "a.D"]
    assert queries.declared_types(tree) == {"X", "Inner"}
    assert {"Service", "Base", "Port", "Helper", "Util", "Config", "Missing"} <= (
        queries.referenced_types(tree)
    )


@needs_grammars
def test_java_adds_same_package_candidates_but_not_imported_or_own_names() -> None:
    edges = JavaAdapter().detect_imports("X.java", JAVA)
    targets = [e.target for e in edges]
    assert targets[:3] == ["a.B", "a.C", "a.D"]  # explicit imports first
    assert "p.q.Helper" in targets and "p.q.Util" in targets and "p.q.Base" in targets
    assert "p.q.X" not in targets and "p.q.Inner" not in targets  # its own types
    assert "p.q.B" not in targets  # imported explicitly
    assert len(targets) == len(set(targets))


def test_java_without_a_package_has_no_same_package_candidates() -> None:
    edges = JavaAdapter().detect_imports("A.java", "class A { B b; }")
    assert [e.target for e in edges] == []


def test_java_regex_fallback_reads_plain_imports_only() -> None:
    edges = JavaAdapter(regex_factory()).detect_imports(
        "A.java", "package p;\nimport a.B;\nimport a.*;\nclass A { Same s; }\n"
    )
    assert [e.target for e in edges] == ["a.B"]


@needs_grammars
def test_same_package_classes_become_edges_in_the_graph(tmp_path: Path) -> None:
    """Java needs no import inside a package, so the graph used to miss these edges (issue #26)."""
    base = tmp_path / "src" / "main" / "java" / "demo"
    other = tmp_path / "src" / "main" / "java" / "lib"
    base.mkdir(parents=True)
    other.mkdir(parents=True)
    (base / "App.java").write_text(
        "package demo;\nimport lib.Tool;\nclass App { Service s = new Service(); Tool t; }\n"
    )
    (base / "Service.java").write_text(
        "package demo;\nclass Service { Repo repo; Names n = Names.DEFAULT; }\n"
    )
    (base / "Repo.java").write_text("package demo;\nclass Repo {}\n")
    (base / "Names.java").write_text(
        "package demo;\nclass Names { static Names DEFAULT; }\n"
    )
    (other / "Tool.java").write_text("package lib;\nclass Tool {}\n")
    scan = ScannerEngine(adapters=[JavaAdapter()]).scan(str(tmp_path))
    graph = DependencyGraph.from_scan(scan)
    rel = lambda p: os.path.basename(p)  # noqa: E731
    edges = {
        (rel(s), rel(d)) for s in graph.all_nodes() for d in graph.dependencies_of(s)
    }
    assert edges == {
        ("App.java", "Service.java"),
        ("App.java", "Tool.java"),
        ("Service.java", "Repo.java"),
        ("Service.java", "Names.java"),
    }


@needs_grammars
def test_a_nested_class_import_resolves_to_the_outer_file(tmp_path: Path) -> None:
    root = tmp_path / "src" / "main" / "java" / "a"
    root.mkdir(parents=True)
    (root / "Outer.java").write_text(
        "package a;\npublic class Outer { public class Inner {} }\n"
    )
    (root / "User.java").write_text(
        "package a;\nimport a.Outer.Inner;\nclass User { Inner i; }\n"
    )
    scan = ScannerEngine(adapters=[JavaAdapter()]).scan(str(tmp_path))
    graph = DependencyGraph.from_scan(scan)
    user = next(f for f in graph.all_nodes() if f.endswith("User.java"))
    assert [os.path.basename(d) for d in graph.dependencies_of(user)] == ["Outer.java"]


# ------------------------------------------------------------ query classes direct


@needs_grammars
def test_ecmascript_queries_report_duplicates_in_source_order() -> None:
    tree = FACTORY.parse("javascript", b"import a from 'x'; require('x'); import('y');")
    refs = EcmaScriptQueries().imports(tree)
    assert [(r.target, r.deferred) for r in refs] == [
        ("x", False),
        ("x", False),
        ("y", True),
    ]


# -------------------------------------------------------------------- the report


@needs_grammars
def test_insights_json_says_how_each_language_is_read(tmp_path: Path) -> None:
    import json
    import shutil

    import jsonschema

    from gnost.cli.commands.onboard import run
    from gnost.reporters.insights_json import SCHEMA_PATH

    root = tmp_path / "app"
    shutil.copytree(Path(__file__).parent / "fixtures" / "java_app", root)
    run(path=str(root))
    payload = json.loads((root / ".gnost" / "insights.json").read_text())
    assert payload["project"]["parsers"] == {"java": "tree-sitter"}
    jsonschema.validate(payload, json.load(open(SCHEMA_PATH)))
    os.environ["GNOST_PARSER"] = "regex"
    try:
        run(path=str(root))
    finally:
        del os.environ["GNOST_PARSER"]
    again = json.loads((root / ".gnost" / "insights.json").read_text())
    assert again["project"]["parsers"] == {"java": "regex"}
