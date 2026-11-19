# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

---
## [0.5.2] — Unreleased

### Fixed
- **Standalone binary (npm, Maven, GitHub Release):** `gnost onboard . --progress` on macOS printed "resource_tracker: process died unexpectedly" and a usage error after finishing. The progress bar library created a multiprocessing lock, which relaunched the binary with arguments it did not understand. The bar now uses a thread lock, and the binary runs such helper launches instead of rejecting them. The binary smoke test now covers `--progress`.
- **`gnost analyze -o`:** in a project with no `.git` or `pyproject.toml` above it, the report was written to `/docs/analysis` and failed on a read-only root. It now goes to `docs/analysis` inside the project, like `gnost onboard`.

---
## [0.5.1] — Distribution fixes — 2026-11-19

### Changed
- **npm:** the platform binaries moved to the `@gnost-cli` scope (`@gnost-cli/darwin-arm64`, `@gnost-cli/linux-x64`, `@gnost-cli/windows-x64`). `npx gnost-cli` is unchanged. The old `gnost-cli-<platform>` packages are deprecated.
- **npm and PyPI pages:** `gnost-cli` has its own README, keywords and links; the PyPI page uses a pip/pipx/uvx README.

### Fixed
- **Scanner:** a project that sits inside a folder named `build`, `out`, `dist`, `env` or similar is no longer skipped; ignored folders are matched below the scan root only.
- **Release tooling:** archive extraction uses the `data` filter where Python provides it.

---
## [0.5.0] — Distribution — 2026-11-18

GNOST is now installable without Python and without a global tool: from PyPI, npm, Maven and Docker.

### Added
- **npm:** `npx gnost-cli onboard .` runs a standalone binary (macOS Apple silicon, Linux x86_64, Windows x86_64). The `gnost-cli` package picks the matching platform package and checks its checksum before running.
- **Maven:** `mvn io.github.mohdzain98:gnost-maven-plugin:0.5.0:onboard` (also `analyze` and `summary`) runs the standalone binary for your platform from Maven Central, no Python or Node needed. Targets Java 8+ and Maven 3.6.3+; options are `-Dgnost.*` properties and output goes to the project folder. The binaries are the `gnost-binary` artifact with `darwin-arm64`, `linux-x64` and `windows-x64` classifiers.
- **Docker:** `ghcr.io/mohdzain98/gnost`, built from the exact PyPI release for amd64 and arm64. It includes git for the change analysis planned in 0.6.0.
- **Standalone binaries** built with PyInstaller and attached to each GitHub Release with `SHA256SUMS`. The analyzers (bandit, radon, mypy, ruff) run from inside the binary, so `gnost analyze` needs no other installation.
- **Offline `gnost open` pages:** the browser libraries are embedded in the page, so it works without internet and can be sent as a file.
- **Install guide** in the docs, with a tab per channel.
- **Release pipeline:** one workflow publishes to PyPI (trusted publishing), GHCR, npm and the Maven Central Portal; release candidates go to TestPyPI and npm `next`. A separate workflow installs every channel and checks the version, after each release and weekly.

### Fixed
- **Standalone binaries:** the Linux binary is built on Ubuntu 22.04 so it starts on Debian 12 and newer systems, and the macOS binary keeps its Python library in the npm and Maven packages (symlinks are replaced by real files).
- **Windows:** the console no longer crashes on non-ASCII characters (it used cp1252), and reports show project-relative paths with forward slashes. Windows is now tested in CI.

### Changed
- The version is written in one place (`gnost/__init__.py`); packaging and the docs read it from there.
- The old PyPI-token workflow is replaced by `release.yml`.

---
## [0.4.0] — Structural Intelligence — 2026-11-15

Onboard now builds a correct dependency graph, understands frameworks, routes, cycles and risky files, and ships an interactive flow explorer.

### Fixed (`gnost onboard` correctness)
- **Dependency graph:** Python imports are now parsed with `ast` and resolved by exact module name. Packages (`__init__.py`), `from pkg import submodule`, relative imports, `src/` layouts and imports inside functions now produce edges. Before, `from app.api.v1 import chat, ...` produced none, so whole parts of an application were missing from the flow. Matching by file-name suffix (which could pick the wrong file) is gone.
- Java imports now resolve to files by package path; `.jsx`, `.tsx`, `.mjs` and `.cjs` files are scanned and resolved.
- **JS/TS imports:** `tsconfig.json` / `jsconfig.json` `paths` and `baseUrl` (JSON with comments, `extends` and `references` followed) are honored, with `@/` falling back to `src/`. Multi-line `import { ... } from`, `export ... from`, side-effect imports and dynamic `import()` (React `lazy` routes) are now detected, `?raw`-style query suffixes are ignored, and `index` files resolve. On a 380-file React app, 1,333 imports now resolve (743 aliased imports resolved none before).
- **Entry points:** `Hub.listen(...)` and similar calls are no longer a "Server listen() call"; only `app/server/http.listen` or `createServer` count. `index`/`main`/`app` files are entry points only at the project root or in `src`, `server`, `app` or `bin`, so barrel files are not. An entry point that another entry point imports (`main.tsx` -> `App.tsx`) no longer starts a second traversal.
- **Frameworks:** JS/TS projects are now identified from `package.json` dependencies (root and sub-folders such as `web/`, `api/`, skipping `node_modules`): Next.js, Nuxt, SvelteKit, NestJS, Angular, Remix, Astro, React Native, React, Vue, Svelte, Solid, Express, Fastify and Koa, with the bundler named for UI libraries ("React (Vite)"). A repo with several stacks lists each one ("FastAPI, React (Vite)").
- **Python and Java frameworks:** read from `pyproject.toml` (project, optional and Poetry dependencies), `requirements*.txt`, `Pipfile`, `pom.xml` and `build.gradle(.kts)`: Django, FastAPI, Flask, Litestar, Sanic, Tornado, aiohttp, Starlette, Streamlit, Gradio, Spring Boot, Spring Framework, Quarkus, Micronaut, Android. When a project declares dependencies but none is a known framework, no framework is reported instead of guessing from source. Without a manifest, Python is detected from real imports and app construction, and `__main__` guards, `FastAPI(`, `Flask(` and `uvicorn.run` entry points from the syntax tree, so strings and regexes that mention them (gnost scanning itself was reported as Django) no longer match. "Plain Java" is dropped when another framework is found.
- **Hotspots:** files outside the flow no longer get scores around -400; the starting file is no longer counted in every path.
- **Entry points:** test files, vendored folders (JS) and minified, bundled or `.d.ts` files are no longer scanned. Helper scripts with only a `__main__` guard are secondary entry points and start the flow only when nothing else does. A real `if __name__ == "__main__"` is required, not just the words in the file.
- **Flow:** each file is expanded once per entry point, so path count is bounded by the number of files instead of exploding (1,620 paths and a 268 KB `folder-paths.md` on a 250-file project, now about 100 paths). Flows that pass through an import cycle are no longer dropped. Mermaid diagrams still draw every dependency edge.
- Reading lists show the 15 files closest to an entry point instead of every file; file paths are shown relative to the project root everywhere; the "Execution chain" under feature paths no longer prints an unrelated path.
- `onboard` output is deterministic.

### Improved (Mermaid diagrams)
- **Size-aware diagrams:** a diagram that would be too big to read (GitHub refuses Mermaid over about 50 000 characters or 500 edges) is grouped by folder, using the deepest folder level that fits; arrows show how many file-level imports they stand for. If even that is too coarse a detailed level is kept and the least important edges dropped (cycles first), and a character-limit guard trims further. On a 380-file React app the full flow went from 107 KB and 1,333 edges to 9 KB and 150 edges.
- **Drill-down:** when `FLOW-full.md` had to be grouped, it adds a detailed file-level diagram for each of the biggest folders.
- **Cycle highlighting:** import-time circular imports are thick red, cycles that only close through a deferred import are orange, and imports that do not run at load time are dotted; a legend line explains what is shown.
- **Readable nodes:** boxes are labelled with the file path (or folder and file count) instead of the mangled id.
- `gnost open flow` / `gnost open FILE` (and `gnost show FILE`, the same command): opens a `.mmd`, `.md` or `.html` file in the browser with diagrams rendered. Big diagrams open as an interactive explorer: a folder overview first, click a folder to open its files, click a file (or pick it from the list) to see what it imports and what imports it. Dark theme by default (light on a button), outlined folder boxes, and a hint line at the bottom that describes whatever you hover over, hover focus (everything not connected fades) and zoom +/- buttons. Needs internet for the scripts (offline since 0.5.0).
- `docs/flow/flow-complete.mmd`: every file and every import, ungrouped, for tools and AI (too big to read or render on GitHub for large projects).
- Shared folders (imported by most others, e.g. utilities or db) are no longer drawn as arrows in grouped diagrams; they are listed in a note, so large projects stay readable.
- New `onboard` options: `--max-edges N` (default 80; the overview uses at most 60) and `--collapse [LEVEL]` to force folder grouping. `--depth` now limits every diagram consistently.
- `folder-paths.md` is capped at the 12 biggest features and draws smaller per-feature diagrams (69 KB to 132 KB on a real project before, about 79 KB after with many more labels).

### Added
- **Function-level flow (Python):** `gnost onboard` now follows calls function by function, not just file by file. For the program's main entry points and its routes it lists what each one calls and what those call, in a "Function-level Flow" section of `ONBOARD.md`, in `docs/flow/function-flow.md` (one Mermaid diagram per entry) and in the insights JSON (schema `1.3`: `flows` with full call trees, `callgraph` counts and any files that could not be parsed). Calls are resolved through the syntax tree and imports: same-file functions, `from x import f`, `module.f()`, classes (to their `__init__`, `Class.method()`), `self.method()` including base classes in the same file, and Celery-style `task.delay()` / `.apply_async()`. Calls through other objects (`self.client.send()`) are not followed. On a real FastAPI project it traces `POST /v1/ingest` through the Celery task into both ingestion pipelines.
- **Caution scoring:** "Caution Areas" now come from a 0-100 score per file that combines cycles (import-time or deferred), size, how many files import it, how many it imports, cyclomatic complexity (exact for Python via radon, an estimate for other languages) and `except` blocks that neither log nor re-raise (Python). Signals combine like independent risks, so one strong signal flags a file; unmeasurable signals are left out and the score is marked partial. Generated files are never listed. Entries carry the score and the factors behind it in `ONBOARD.md` and the insights JSON (schema `1.2`: `score`, `partial`, `factors`; new categories `high_complexity` and `low_observability`).
- **`.gnost.toml` configuration:** `exclude` patterns (onboard and analyze), onboard diagram options, caution `threshold`, `limit`, `weights` and `ranges`, and analyze `analyzers`, `timeout`, `max_findings` and `parallel`. Precedence is command-line flags, then the file, then defaults; unknown keys warn and bad values stop the command with exit code 2 and a message naming the setting. See the new Configuration page in the docs. Adds a `tomli` dependency on Python below 3.11.
- **Route-to-handler mapping:** `gnost onboard` lists the HTTP endpoints of a project and the function behind each one, in a "Routes" table in `ONBOARD.md`, the terminal summary and the insights JSON (schema `1.1`: new `routes` array and `stats.routes`). Supported: Flask (routes, `Blueprint` and `url_prefix`), FastAPI/Starlette (`APIRouter`, `include_router(prefix=...)`, websockets), Django (`urlpatterns`, `include()`, DRF `router.register`), Express/Fastify/Hono (`app.get`, `router.use` mounts across files), NestJS controllers and Spring MVC/Boot controllers. URL prefixes are combined across files and router nesting; paths that are not literal strings are shown as `<dynamic>`. Verified on a real FastAPI project: all 33 endpoints found with the right prefixes.
- **Circular dependency detection** in `gnost onboard`: strongly connected components of the file graph (iterative Tarjan, safe on very deep graphs) with a concrete example loop per group. Each cycle is classified as *import-time* (the files import each other as modules load) or *deferred* (every loop goes through an import inside a function, under `TYPE_CHECKING`, a dynamic `import()` or `import type`). Reported in `ONBOARD.md`, the terminal summary and the JSON; import-time cycles also appear under Caution Areas.
- **Insights JSON export:** `gnost onboard --json [FILE]` writes `docs/insights/gnost_insights.json` next to the normal output; `--insights-only` writes only the JSON. Schema version `1.0`, described by `gnost/schemas/insights.schema.json` (shipped with the package): entry points, layers, first files, hotspots, caution areas, cycles, the dependency graph (with deferred edges flagged) and stats. Paths are relative and output is deterministic.
- Test suite for the scanner, import resolver, dependency graph, flow builder and language adapters.
- Test suite for the scanner, dependency graph, flow builder and language adapters.
- Golden-file snapshot tests of `gnost onboard` on Python, JavaScript, TypeScript, Java and cyclic fixtures (`UPDATE_SNAPSHOTS=1` regenerates them).

### Fixed
- `gnost analyze`: the robustness analyzer ran `mypy --config-file mypy.ini`, which only worked when that file existed in the working directory, so type findings were silently missing. A strict default config is now bundled with the package.
- The analyzer guide templates for the HTML report were missing from the published wheel; they are now included as package data.
- `gnost onboard` output is now deterministic (stable ordering of flow paths, Mermaid edges and hotspot ranking).

### Removed
- Unused code: plugin stub, `core/counter.py`, `LANG_EXTENSIONS`, unused external tools in `ToolRunner` (pylint, semgrep, gitleaks, pip-audit, pip-licenses, safety), `find_duplicate_code`, and commented-out blocks.

### Changed
- `requires-python` is now `>=3.9`, matching CI and the classifiers.

## [0.3.0] — Static Analysis & Reporting Improvements

### Added
- `gnost analyze`
  - Maintainers now get code quality scoring with findings and analyzer-level summaries.
  - Added JSON output and HTML report generation in `docs/analysis/`.
  - Added command guide coverage under Read the Docs (`analyze`, `analyzer guide` pages).
- `gnost open report`
  - Added report-opening helper command (and shorthand `gnost open rpt`).
  - Added usage hints with OS-specific shell command fallback.

### Changed
- Standardized analyzer result reporting in terminal and HTML output with severity breakdowns.
- Added `open report` flow guidance in post-analysis completion message.
- Updated README to concise usage-focused reference content.

### Fixed
- Updated changelog/versioning metadata and release documentation to `0.3.0`.

### Notes
- `gnost analyze` is currently Python-only.
- JavaScript/TypeScript and Java analyzers are planned in follow-up releases.

## [0.2.1] — Onboarding Output & Documentation Hardening

### Added
- **ONBOARD.md Tables**
  - Added a Summary table (Language, Files, LOC)
  - Added a Stats table (Language, Files, Code, Comments, Blanks, LOC)

- **Security Policy**
  - Added `SECURITY.md` with vulnerability reporting guidance

### Changed
- **Flow Output Location**
  - `gnost onboard` now writes flow artifacts to `docs/flow` at repository root
  - Automatically creates `docs/` when it does not exist
  - `ONBOARD.md` links now point to `docs/flow/*`

### Fixed
- **Repository Root Output Resolution**
  - Running `gnost onboard` from subdirectories (for example `gnost/`) now writes outputs to repo root (`<repo>/docs` and `<repo>/ONBOARD.md`)
- **Correctly map of JSX and TSX**
  - Now js is mapped as JavaScript.js and JSX is mapped as JavaScript.jsx
  - Same mapping for ts

## [0.2.0] — Human-First Onboarding Insights

### Added
- **Languages**
  - Support for JSX and TSX as JavaScript and TypeScript respectively

- **First Files to Read**
  - Automatically highlights the most important files to start with
  - Based on entry points, execution flow, and dependency influence

- **Caution Areas**
  - Identifies high-impact and tightly coupled files
  - Warns about areas that require extra care when modifying

- **Onboarding Insights Engine**
  - New analysis layer (InsightBuilder) producing structured onboarding insights
  - Decouples analysis from rendering for future extensibility

- **Improved Mermaid Flow Diagrams**
  - Added layered diagrams (Entry / Core / Leaf)
  - Support for execution depth limiting
  - Support for combined path diagrams for grouped execution flows
  - Cleaner node naming and reduced visual noise

### Improved
- Onboarding Output Quality
- Cleaner, more readable terminal summaries
- Shortened file paths for better CLI readability

### Markdown Onboarding Documentation
- ONBOARD.md now includes human-readable onboarding guidance
- Structured sections for reading order, architecture, and risks


## [0.1.1] – Metadata & Packaging Fixes

### Fixed
- Added Python version classifiers for PyPI
- Declared project license metadata
- Added project URLs (Homepage, Documentation, Source, Issues)

### Notes
- No functional changes

---

## [0.1.0] – Initial Public Release
**Release name:** Codebase Onboarding Intelligence

### Added
- Language-agnostic core architecture for codebase analysis
- `gnost onboard` command for first-time repository onboarding
- Entry point detection for:
  - Python
  - JavaScript
  - TypeScript
  - Java
- Execution flow inference based on static dependency graphs
- Hotspot ranking to identify the most important files
- Mermaid flowchart generation for visual execution paths
- Markdown onboarding document generation (`ONBOARD.md`)
- Diagram-only mode:
  ```bash
  gnost onboard --mermaid
  ```
    which outputs a pure Mermaid file (FLOW.mmd)
- Framework detection (heuristic-based):
  - FastAPI, Flask
  - Express, NestJS
  - Spring Boot

- Clean CLI output designed for developer onboarding
- Modular adapter system for adding new languages

### Supported Languages
- Python (.py)
- JavaScript (.js, .jsx)
- TypeScript (.ts, .tsx)
- Java (.java)

### Known Limitations
- Static analysis only (no runtime execution tracing)
- Heuristic-based parsing (no AST / Tree-sitter yet)
- Limited framework awareness for frontend-heavy projects (e.g., React, Next.js)
- No method-level call graph (file-level only)

### Stability Notes
- APIs and CLI flags may change before v1.0.0
- Output format is considered stable for 0.x usage
- Designed for onboarding and exploration, not security auditing

## Planned

See `project-docs/tasks/ROADMAP.md` in the repository for the full plan. Planned for 0.4.0: circular dependency detection, insights JSON export and `--insights-only`, improved Mermaid output, route-to-handler mapping, caution scoring, a `.gnost.toml` config file and AST-aware flow for Python.

```GNOST is in early development (v0.4.0 in progress). APIs and behavior may evolve.```
