# GNOST — Current Status

Published: **0.3.0**. In progress: **0.4.0** (branch `release/0.4.0`, uncommitted; version in files is already `0.4.0`). See `CHANGELOG.md` for history and `project-docs/DOCUMENTATION.md` for architecture.

## Language support

| Feature | Python | JavaScript | TypeScript | Java |
|---|---|---|---|---|
| `onboard` (entry points, flow, ONBOARD.md) | Yes | Yes | Yes (`.ts`; `.tsx` unverified) | Yes |
| LOC commands (`summary`, `stats`, ...) | Yes | Yes | Yes | Yes |
| **`analyze` (quality analysis)** | **Yes** | No | No | No |

**`gnost analyze` works on Python only.** The restriction is structural, not a flag:

- `gnost/analysis/utils/extract.py`: `CODE_EXTS = {".py"}`; with no `.py` files the command logs "No Python files found after filtering." and returns 0.
- `gnost/analysis/core/file_utils.py`: `find_python_files` accepts only `.py`; every analyzer's `get_supported_file_types()` returns `[".py"]`.
- Tooling is Python-specific: radon, bandit, mypy, ruff and the `ast` module.

JS/TS/Java analyzers are planned (see CHANGELOG).

## What works

- `onboard`, LOC commands, `analyze` with 4 analyzers (maintainability, observability, readability, robustness), JSON and HTML reports, `open report`.
- CI: ruff + pytest on Python 3.9–3.12; PyPI publish on `v*` tags.
- Docs on Read the Docs.

## Done so far for 0.4.0: checkpoints C0 (Foundation), C0.5 (Onboard correctness), C1 (Cycles + insights JSON), C2 (Mermaid), C3 (Routes), C4 (Caution + config), C5 (Function-level flow)

- 211 tests: scanner, graph, flow, adapters, packaging, plus golden snapshots of `onboard` on 5 fixture projects (`tests/fixtures`, `tests/snapshots`).
- `onboard` output made deterministic (sorted flow/Mermaid/ranker iteration).
- Fixed: robustness analyzer needed `./mypy.ini` in the cwd and silently returned no type findings; a strict config is now bundled (`gnost/analysis/config/mypy.ini`).
- Fixed: report templates were missing from the 0.3.0 wheel; now package data.
- Removed dead code (plugins stub, `core/counter.py`, `LANG_EXTENSIONS`, unused `ToolRunner` tools, `find_duplicate_code`, commented blocks). `analysis/utils/analyze.py` and `df_handling.py` are NOT dead: the analyzers import them.
- `requires-python >=3.9`; stale docstring and CHANGELOG footer fixed.

## C5: Function-level flow, Python (done)

`gnost/core/callgraph.py` builds a function call graph from the syntax tree and imports; entries are primary `__main__` blocks and routes. Output in ONBOARD.md, `docs/flow/function-flow.md` and JSON schema 1.3 (`flows`, `callgraph`). Limits: calls on other objects are not followed, Django view modules are not traced, JS/TS/Java have no function-level flow (0.6.0).

## C4: Caution scoring and `.gnost.toml` (done)

Rule-based caution score (noisy-OR over cycles, size, impact, coupling, complexity, observability) replaces the old fan-in/import-count rules; `.gnost.toml` configures exclusions, diagram size, caution weights/ranges/threshold and analyze options with CLI > file > default precedence. Schema `1.2`. Known gaps: JS/TS/Java complexity is a keyword-count estimate; the score does not use git history (planned for 0.5.0); `exclude` is not applied to the LOC tables' glob patterns (plain folder names only).

## C3: Route-to-handler mapping (done)

`gnost/routes/` finds endpoints for Flask, FastAPI, Django, Express/Fastify/Hono, NestJS and Spring and resolves prefixes across files. Output: Routes table in ONBOARD.md, terminal section, JSON schema 1.1. Real project check: 33/33 FastAPI routes correct. Gaps: file-based routers (Next.js), runtime-built paths (shown as `<dynamic>`), Express app instances created in one file and mounted in another through non-relative imports.

## C2: Mermaid improvements (done)

Size-aware diagrams (folder grouping, edge budget, character guard), drill-down in `FLOW-full.md`, cycle/deferred styling with legend, labelled nodes, `--max-edges` and `--collapse`. Not verified in a real Mermaid renderer (none available here); tests check structure and GitHub's limits. Worth opening `test-results/*/flow/FLOW-full.md` in a Markdown preview once.

## C1: Cycles and insights JSON (done)

`gnost onboard` reports circular dependencies (import-time vs deferred) and can export everything as schema-versioned JSON (`--json`, `--insights-only`). Real projects: the Python backend has 1 import-time cycle (the Celery app/tasks pattern) and 4 deferred ones; the React frontend has 1 deferred. Cycle highlighting in Mermaid diagrams comes with S3. JSON edges include a `deferred` flag so later items (caution scoring, change intelligence) can use it. The JSON now carries everything planned for 0.4.0 (schema 1.3).

## C0.5: Onboard correctness (done)

Found by running `onboard` on a real 250-file FastAPI project. Fixed: package/`from x import y`/relative imports, Java and TSX/JSX resolution, wrong entry points (tests, vendored minified JS, one-off scripts), path explosion (1,620 -> 107 paths), cycles dropping flows, inconsistent path display, stale-variable bug in feature-path chains. Details in CHANGELOG. Checked against that project: 0 unresolved internal imports (was 124+). Also checked on its React/Vite frontend (382 files): `@/` alias imports, multi-line and dynamic imports now resolve (1,333 resolved, the 10 left are `.css`/`.json` assets); `Hub.listen` no longer a false server entry; barrel `index.ts` files are not entry points; `main.tsx` is the single flow root.

## Known limitations (not fixed yet)

- Python entry points and frameworks use the syntax tree and manifests; JS/TS and Java entry points are still regex/text based (a Java string containing `public static void main(String` would match). Files that do not parse fall back to regexes.
- JS/TS: `tsconfig` paths are read, but bundler-only aliases (vite/webpack config) are not, and monorepos with several tsconfig files only use the root ones. Bare package imports are not project files. Frameworks come from `package.json`, `pyproject.toml`, `requirements*.txt`, `Pipfile`, `pom.xml` and `build.gradle`; manifests are searched two folders deep. Java same-package references without an import are invisible, and wildcard imports are skipped.
- Cycles are file-level; a cycle between a package's `__init__.py` and its submodules is reported like any other.
- ONBOARD.md's LOC tables count every file, while the language counts and flow exclude tests and vendored files, so the two can differ.
- Hotspot scoring (the "Hotspots" list) still counts paths through a file, so entry points rank high; the caution score is separate and does not have this problem.
- `jscpd` (npm) is optional; duplication falls back to an AST-hash check.

## Remaining cleanup

- `analysis/core/transformers.py` still has transformers for tools no analyzer uses (gitleaks, pylint, semgrep, safety, ...).
- `analysis/utils/mi.py` is used only for a diagnostic path; leave until analyzers get tests.

## Roadmap

See `project-docs/tasks/ROADMAP.md` for the full ladder and `project-docs/tasks/PLAN_0.4.0.md` for the checkpoint plan.

- **0.4.0** (in progress, one release): foundation (tests, cleanup), circular dependency detection, insights JSON export and `--insights-only`, improved Mermaid output, route-to-handler mapping, caution scoring, `.gnost.toml` config, and AST-aware flow for Python. Fixes afterwards ship as 0.4.x patches.
- **0.5.0** to **0.7.0**: shipped (distribution, change intelligence, multi-language `analyze` with tree-sitter, architecture rules, `gnost mcp`). 0.7.0 was released 2026-11-22.
- **0.7.1** (in progress on `release/0.7.1`): `analyze` root-detection fix (done: it analyzed `tests/` instead of the project when tests had the most files), size-aware quality score (built: density on a log curve, docs page "How the score works"), GitHub Pages explorer (built: `onboard --pages`), PR-only workflow (built) and fork-PR comments (built; test on a real fork PR with the rc).
- **0.8.0**: visual project map (2D mind map, README mind map as SVG or rotating GIF, 3D view).
- **0.9.0**: GNOST for AI agents (agent skill file, more MCP tools).
- **0.10.0**: Jupyter notebooks, HTML and CSS in `stats` and the summary only.
- **0.11.0**: one new full language; Go first, then Kotlin, C#, Rust.
