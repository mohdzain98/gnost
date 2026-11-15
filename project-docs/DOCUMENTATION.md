# GNOST — Project Documentation

Developer-facing documentation for the GNOST codebase (v0.4.0). User-facing docs live in `docs/` (Read the Docs, Sphinx) and are not duplicated here.

## 1. What GNOST is

A static-analysis CLI with two main capabilities:

- **`gnost onboard`** — builds an onboarding guide (`ONBOARD.md`) and Mermaid execution-flow diagrams for an unfamiliar repository.
- **`gnost analyze`** — scores code quality across four analyzers and writes JSON/HTML reports.

It also has LOC reporting commands (`summary`, `stats`, `folders`, `files`), `open` and `version`.

## 2. Install and entry point

- Package: `gnost` on PyPI. Entry point: `gnost = "gnost.cli:main"` (`pyproject.toml`) -> `gnost/cli/app.py` (argparse).
- Runtime dependencies: rich, tqdm, termcolor, bandit, radon, mypy, ruff. Optional: `jscpd` (npm) for duplicate detection.
- Dev: `pip install -e . pytest ruff`, then `ruff check .` and `pytest -q` (same as CI).

## 3. CLI reference

| Command | Purpose |
|---|---|
| `summary\|stats\|folders\|files [path]` | LOC reports. Options: `--include`, `--exclude`, `--progress`; `files` also `--top N` (default 5) |
| `onboard [path]` | Options: `--mermaid`, `--progress`, `--inject`, `--layered`, `--depth N`, `--json [FILE]`, `--insights-only`, `--max-edges N`, `--collapse [LEVEL]` |
| `analyze [path]` | Options: `-a/--analyzer` (repeatable), `--parallel`, `-o/--out`, `-v/--verbose`, `--quiet`, `--list-analyzers`, `--timeout` (default 900), `--compact`, `--no-progress`, `--max-findings` (default 1000) |
| `open [report\|rpt] [--path FILE]` | Open `docs/analysis/gnost_analysis.html` in the browser |
| `version` / `--version` | Print version |

## 4. Architecture

```
gnost/
  cli/            app.py (argparse, dispatch, score table); commands/onboard.py, commands/analysis.py
  scanner/        ScannerEngine (file walk, adapter matching), LOC counting, ignore filters
  languages/      LanguageAdapter ABC + manifests.py (package.json / pyproject / pom readers) + python / javascript / typescript / java adapters
  core/           ImportResolver, DependencyGraph, cycles, caution (scoring), callgraph (function-level), FlowBuilder, ranker, InsightBuilder
  models/         insight dataclasses
  reporters/      onboarding (summary, markdown, mermaid + mermaid_graph, readme, insights_json) + LOC tables + analysis_html
  analysis/
    config/       bundled strict mypy.ini
    core/         engine, interfaces (QualityAnalyzer, registry), models, aggregator, transformers, tool_runner, file_utils
    analyzers/    maintainability, observability, readability, robustness
    utils/        extract (CODE_EXTS), duplicate_code (jscpd), mi (radon)
  routes/         HTTP route extraction per framework (python, javascript, java) + shared prefix resolution
  config/         languages.py (LOC comment prefixes), settings.py (.gnost.toml loader and validation)
  utils/          logger, printer, progress
```

### 4.1 `onboard` flow (`cli/commands/onboard.py`)

1. Resolve repo root by walking up to `.git` or `pyproject.toml`; all outputs go there, not to the scanned path.
2. Create `docs/` and `docs/flow/`.
3. `ScannerEngine.scan` with Python, JavaScript, TypeScript and Java adapters. Test files and vendored/minified files are skipped. Python imports come from `ast` (regex fallback); other languages use regex. Entry points are ranked primary or secondary.
4. `DependencyGraph.from_scan` (imports resolved by `ImportResolver`: exact Python module names including packages and relative imports, JS/TS relative paths plus tsconfig `paths`/`baseUrl` aliases, Java package paths) -> `FlowBuilder.build` (breadth-first from primary entry points, each file expanded once; also keeps every edge and each file's depth) -> `InsightBuilder.build`.
5. Write outputs (below), print terminal summary, optionally inject a link into `README.md` (`--inject`).

Outputs: `ONBOARD.md` (including a Circular Dependencies section), `docs/insights/gnost_insights.json` (with `--json`, schema in `gnost/schemas/insights.schema.json`), `docs/flow/FLOW-full.mmd`, `FLOW-full.md`, `function-flow.md` (Python call trees), `FLOW-overview.mmd`, `entry-paths.md`, `folder-paths.md`. With `--mermaid`, only `FLOW-full.mmd`.

### 4.2 `analyze` flow (`cli/commands/analysis.py`)

1. Register the four analyzers.
2. Collect `.py` files (`Extract.CODE_EXTS = {".py"}`), skipping hidden/venv/build directories.
3. Build `AnalysisConfiguration` and run `UnifiedAnalysisEngine` (optionally parallel, with timeout).
4. Aggregate findings (dedupe, priority and risk scoring).
5. Print the "Analysis Scores" table. With `-o`, write `docs/analysis/gnost_analysis.json` and `.html` under the repo root.

### 4.3 Analyzers

| Analyzer | Tools | Checks |
|---|---|---|
| Maintainability | radon cc/mi, jscpd (AST-hash fallback) | cyclomatic complexity, risk ranking, maintainability index, function duplication, coupling/cohesion |
| Observability | Python `ast` | logging coverage, critical functions and error handlers without logging, logging patterns |
| Readability | ruff | naming, documentation, formatting, clarity rules |
| Robustness | bandit (B110, B113), mypy strict, AST | swallowed exceptions, missing request timeouts, type errors, unsafe dict access |

### 4.4 Scoring

- Per finding: severity weight (Critical 10, High 7, Medium 4, Low 2, Info 1) x confidence; the sum is scaled to a 0–100 risk score in `analysis/core/aggregator.py`.
- CLI score: `10 * (1 - risk/100)`, shown per analyzer and as a final score out of 10.
- Finding priority: severity 40%, confidence 20%, category 20%, remediation complexity 10%.

## 5. Tests and CI

- `tests/` (pytest, 211 tests): analyze CLI, markdown reporter, repo-root resolution, scanner, graph, flow, language adapters, packaging, and golden snapshots of `onboard` (`tests/fixtures`, `tests/snapshots`; regenerate with `UPDATE_SNAPSHOTS=1 pytest tests/test_onboard_snapshots.py`).
- Still missing: tests for the analyzers themselves.
- `.github/workflows/tests.yml`: Python 3.9–3.12, ruff + pytest. `publish-pypi.yml`: publishes on `v*` tags.

## 6. Repository layout notes

- `docs/` — Sphinx/Read the Docs source (`index`, `onboard`, `analyze`, `analyzer_guide`). Note that `gnost onboard` and `gnost analyze -o` also write generated files into `docs/flow/` and `docs/analysis/` of the scanned repo.
- `project-docs/tasks/` (git-ignored) — roadmap and plans. `test/` (git-ignored) — old manual samples; the tracked fixtures are in `tests/fixtures/`.
- `assets/report_example.png` — report screenshot used in README and docs.

## 7. Adding a language adapter (onboard)

Subclass `LanguageAdapter` (`gnost/languages/base.py`), implement `detect_entry_points`, `detect_imports`, `detect_framework`, `detect_calls`, `is_entry_file_name`, then register it in `cli/commands/onboard.py`.

## 8. Adding an analyzer

Implement `QualityAnalyzer` (`gnost/analysis/core/interfaces.py`), including `get_supported_file_types()`, and register it in `Analysis.initialize_analyzers`. Note that file discovery is currently Python-only (see `project-docs/STATUS.md`).
