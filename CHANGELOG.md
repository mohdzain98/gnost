# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.7.0] — Unreleased

### Changed
- **JavaScript, TypeScript and Java are now read with tree-sitter** instead of text patterns. An `import` in a comment or a string is no longer counted, `require()` and dynamic `import()` are read exactly, `import type` and imports of only `type` names are deferred, and a syntax error in one place no longer hides the rest of the file. The old reader is kept as a fallback when a grammar cannot be loaded (`GNOST_PARSER=regex` forces it).
- **Java: same-package references are now edges** (issue #26). A class in the same package needs no import, so spring-petclinic had 10 edges for 30 files and thin diagrams; it now has 40. Static imports are attributed to their class, wildcard imports are skipped, and an import of a nested class points to its outer class's file. Larger Java projects can now show circular dependencies that were invisible before.
- `insights.json` has `project.parsers` (how each language was read: `ast`, `tree-sitter` or `regex`).
- The binary build fails when an archive grows more than 15 MiB over the 0.6.1 size (`scripts/check_binary_size.py`, baseline in `packaging/binary-size-baseline.json`). tree-sitter adds about 0.5 MiB.

### Added
- **Architecture rules.** An `[architecture]` section in `.gnost.toml` declares layers (`layers = ["api", "service", "db"]`: a layer must not import one above it) and forbidden imports (`[[architecture.rules]]` with `from`, `must_not_import` and `allow`). They are checked on the import graph, so they work for every language `onboard` reads. `ONBOARD.md` and `insights.json` (`architecture`) list the violations, and `gnost changes` reports only the ones a change adds or fixes (renames are followed). `gnost changes --fail-on-violations`, or `fail = true`, exits with code 3 when a change adds one (Maven: `-Dgnost.failOnViolations`).
- **`gnost analyze` for JavaScript, TypeScript and Java.** `.js .jsx .mjs .cjs .ts .tsx .mts .cts` and `.java` files are now analyzed with GNOST's own rules (listed in the analyze docs), on top of tree-sitter, so nothing else has to be installed (no Node, no JDK). Twelve core rules mean the same in every language and have the same id and severity; each language adds a few of its own. The same four analyzers and the same score cover them, Python still uses mypy, bandit, radon and ruff and its results do not change, and mixed projects are scored together. Every finding has a rule id shared across languages (`ROB-EMPTY-CATCH`, `MNT-COMPLEXITY`, ...), so baselines, `--fail-under` and SARIF work as for Python. `node_modules`, build output, minified files and `.d.ts` are skipped; tests are exempt from rules that do not apply to them. New `--language` option and `[analyze] languages` setting (Maven: `-Dgnost.language`).
- **"Get it running" section.** `ONBOARD.md`, the terminal summary and `insights.json` (`quickstart`, schema 1.5) say how to install, build, run and test the project and which environment variables it needs. It is read from `package.json`, `pyproject.toml`, `requirements.txt`, `pom.xml`, `build.gradle`, `Makefile`, `Dockerfile`, `docker-compose.yml`, `.env.example` and, as a last resort, GitHub Actions workflows. Every line names its source file; nothing is guessed, and `.env.example` values are never copied.
- **`gnost mcp`: GNOST for coding agents.** A read-only Model Context Protocol server over stdio (no new dependency, no network). It answers from `.gnost/insights.json` with six tools: `gnost_overview`, `gnost_entry_points`, `gnost_hotspots`, `gnost_risk`, `gnost_file` (what a file imports and who imports it) and `gnost_changes` (impact of a change, computed from git, nothing written). Paths are kept inside the project and nothing in the repository is run. See the new "Use GNOST with coding agents" page.
- **Progress feedback by default.** `gnost onboard` shows a progress bar with the step it is on (and a start line) when run in a terminal, so a long run is no longer a blank screen. It stays quiet in CI and pipes; `--progress` forces it and `--no-progress` (or `GNOST_NO_PROGRESS=1`) turns it off. Everything goes to stderr. Maven: `-Dgnost.noProgress`.

---

## [0.6.1] — 2026-11-22

### Changed
- **The flow explorer is always interactive.** `flow.html` and `gnost open flow` used to show a flat Mermaid picture for diagrams under about 150 arrows, which is hard to use. Every `.mmd` diagram now opens as the interactive explorer, whatever its size (`--view mermaid` still draws the flat picture).
- **Results for a repository address go to `.gnost/<repo-name>/`** instead of `.gnost/`, so several repositories never overwrite each other. The end of the run prints the exact `gnost open` command.
- `ONBOARD.md` now names `flow-complete.mmd` and says how it relates to `FLOW-full.md` (the same for a small project).

### Added
- A **download button** in the explorer saves the diagram on screen as a PNG (with a margin and the theme's background).
- The explorer's **legend** is pinned at the top of the right panel, so it no longer scrolls out of view.

### Fixed
- The `git log` window used a date without a time, which git completes with the current time of day. A very large `[history] days` could return no history at some hours. It is now an exact timestamp (and no limit for a huge window).

---

## [0.6.0] — 2026-11-21

### Added
- **`gnost init`** writes a complete `.gnost.toml` with every setting at its default and a comment on each, so you never need the docs to start (`--print` shows it, `--force` overwrites). It can also wire GNOST into the build with small edits that keep your formatting and comments: `--pom` adds `gnost-maven-plugin` to `pom.xml`, `--npm` adds a `gnost` script to `package.json`, `--github-action` writes `.github/workflows/gnost.yml` (it runs the GNOST action: pull request comment, the `.gnost/` guide as an artifact, optional quality gate and code scanning). `--dry-run` shows what would change.
- **Update notice.** `gnost --version` and `gnost version` say on stderr when a newer release exists (checked at most once a day, against pypi.org). It prints nothing when offline, in scripts and pipes, or in CI, never changes the exit code, and can be switched off with `check_updates = false` or `GNOST_NO_UPDATE_CHECK=1`.
- **Change hotspots.** When the project is a git repository, `ONBOARD.md` has a "Change Hotspots" table (also in the terminal summary) and `insights.json` has `change_history`: the files that change most often, with commits, distinct authors, recent commits, lines added and removed and the last change, ranked by a 0 to 100 score. One `git log` call reads the history (365 days, 5,000 commits by default); renames are followed, `.mailmap` is honoured, bots and mass-reformat commits are ignored. Settings are in a new `[history]` section of `.gnost.toml`. With no usable history (not a repository, a shallow CI checkout, no git) the table is left out and the JSON says why. The insights schema is now 1.4 (the field is additive).
- **`gnost changes BASE[..HEAD]`** shows what a change touches, the way a reviewer would ask: the changed files (added, modified, deleted, renamed), the **blast radius** (files that import them, up to `--depth`, including importers of deleted files), the risky files among them, routes added, removed or touched, and **new or fixed circular dependencies** (the base commit is exported with `git archive` into a temporary folder; your working tree is never touched). `--findings` runs the analyzers on the changed Python files only. Output: terminal, `--format markdown|json`, and `.gnost/changes/changes.md` and `changes.json`.
- **Remote repositories.** `gnost onboard`, `analyze` and `changes` accept an `https://` or `ssh` repository address (and `--ref BRANCH`). GNOST makes a partial clone in a temporary folder, writes the results to the current folder and deletes the clone, also on Ctrl+C. Nothing from the repository runs: hooks, submodules and symlinks are off, the analyzers ignore the repository's own mypy and ruff configuration, and its `.gnost.toml` is not read. Limits: 10 minutes and 500 MB. Plain `http://`, `git://` and `file://` addresses are refused.
- **Maven goals for every command.** `gnost:changes`, `gnost:stats`, `gnost:folders`, `gnost:files`, `gnost:open` (`-Dgnost.open=false` for CI), `gnost:init` and `gnost:version` join `onboard`, `analyze` and `summary`. `onboard`, `analyze` and `changes` take `-Dgnost.ref` for repository addresses. Plugin release: 0.6.0.
- **Footer and `AGENTS.md`.** Generated Markdown files end with a "Generated by GNOST" line (the command suggested fits the main language: `uvx`, `npx` or `mvn`; switch it off with `footer = false`). `gnost init --agents` writes an `AGENTS.md` that points coding agents to `.gnost/ONBOARD.md` and `.gnost/insights.json`. A new docs page, "The GNOST folder", documents the layout and which parts are stable.
- **Pull request comment.** The GitHub Action has a new input `comment: "true"` that posts the `gnost changes` report as one comment per pull request and updates it on every push.
- **Risky and Changing.** `ONBOARD.md` (and the terminal summary and `insights.json`, under `risk`) lists the files that are both fragile to change and changing often: the caution score scaled by the change activity, with both scores, the number of commits and authors, and a plain-words reason such as "large file, complex code". A fragile file nobody touches, or a busy but simple one, is not listed. Needs git history. Settings are in a new `[risk]` section of `.gnost.toml` (`threshold`, `limit`, `churn_weight`). The existing caution score and its output are unchanged.
- **CI features for `gnost analyze`** (see the new "Use GNOST in CI" page). `--fail-under SCORE` fails the run when the final score (0 to 10) is lower. `--write-baseline` saves today's findings and `--baseline` then reports only new ones (matched by analyzer, rule, title, file and function, not by line number, and counted so a new finding is never hidden by a fixed one); `--fail-on-new` fails on any new finding. `--sarif` writes SARIF 2.1.0 with repository-relative paths and stable fingerprints for GitHub code scanning. `fail_under` and `baseline` can be set in `[analyze]` of `.gnost.toml`. The Maven `analyze` goal has the same options (`gnost.failUnder`, `gnost.baseline`, `gnost.writeBaseline`, `gnost.failOnNew`, `gnost.sarif`).
- **Exit codes** are now documented and consistent: 0 success, 1 error, 2 mistake in the command or config, **3 quality gate failed**, 130 interrupted.
- **GitHub Action.** `uses: mohdzain98/gnost@v0.6.0` runs the Docker image, uploads the findings to code scanning and fails the job when the gate fails (inputs: `path`, `fail-under`, `baseline`, `fail-on-new`, `sarif`, `onboard`, `version`).
- **Git layer** (internal, for the change features coming in this release): one safe place that runs `git`, with clear messages when git is missing, the folder is not a repository, the history is empty or the clone is shallow.

### Changed (breaking: where the files go)
- **The GNOST folder.** `gnost onboard` and `gnost analyze -o` now write everything into one folder in your project, `.gnost/`, instead of `ONBOARD.md` at the root and `docs/flow`, `docs/insights`, `docs/analysis`:

  | Before 0.6.0 | Now |
  |---|---|
  | `ONBOARD.md` | `.gnost/ONBOARD.md` |
  | `docs/flow/` | `.gnost/flow/` |
  | `docs/insights/gnost_insights.json` (only with `--json`) | `.gnost/insights.json` (always written) |
  | `docs/analysis/gnost_analysis.json` and `.html` | `.gnost/analysis/analysis.json` and `analysis.html` |
  | (none) | `.gnost/flow.html`, the flow explorer as one page that works offline |

  The folder has a `README.md` that says what it is, and a `.gitignore` for the large `.html` pages; the rest is safe to commit. Choose another folder with `output_dir` in `.gnost.toml`.
- **Nothing is moved or deleted for you.** `gnost open` still finds the old files when `.gnost/` does not exist yet, and tells you about the move. Run `gnost onboard .`, then delete the old files when you like. The scanners never read GNOST's own output (the new folder or the old locations). If you publish the Markdown with GitHub Pages (Jekyll), add `include: [".gnost"]` to `_config.yml`, because Jekyll skips folders that start with a dot.
- `gnost onboard` writes the insights JSON and the explorer page by default. `--mermaid` still writes only the diagram, `--insights-only` only the JSON, `--no-html` skips the page, and `--json FILE` now means "put the JSON at FILE instead". `gnost open flow` opens the saved page straight away.
- The README link added by `--inject` points to `.gnost/ONBOARD.md`, and the Maven plugin reports files written to `.gnost/`.

### Fixed
- The GitHub Action now has a unique name (`GNOST Codebase Onboarding and Quality Gate`), which the GitHub Marketplace requires. Use it as before: `uses: mohdzain98/gnost@v0.6.0`.
- Temporary clones were not deleted on Windows, because git marks its object files read-only. They are now removed.
- A very large `[history] days` crashed `gnost onboard` on Windows (a date before 1970).
- The Maven plugin's project and source-control URLs on Maven Central ended in `/gnost-maven-plugin` (Maven appends the module name to inherited URLs), which is a 404 on GitHub. The plugin POM now states them explicitly.
- Flow diagrams were empty for projects whose entry point imports nothing from the project, such as Spring Boot applications (components are found by scanning). When the entry points reach less than half of the connected files, GNOST now also walks from the files nobody imports.
- Exclude patterns that start with a dot (such as `.gnost`) lost the dot, so `.gnost` also excluded any folder named `gnost`. Only a leading `./` is removed now.
- **The standalone binary always exited with code 0**, even when a command failed (a missing path, a bad config, a failed gate). The `pip` and Docker commands were not affected, but the npm and Maven channels (which run the binary) could not fail a build. The binary now returns the real exit code.
- **Analysis score table:** findings of critical severity were counted under "info"; they are counted as high now.
- **Scan accuracy.** `gnost summary`, `stats`, `folders` and `files` skip vendored and minified JavaScript (a `vendor/` folder, `*.min.js`), as `onboard` always did; GNOST's own `vendor/` libraries had made up 12.3k of its 12.5k lines of JavaScript. `.gitignore` rules such as `test/` now match at any depth, like git does, and a folder-only rule no longer matches a file of that name. The summary shows one row per language (`JavaScript`, `TypeScript`) instead of one per file extension (`JavaScript.js`, `TypeScript.tsx`).
- **Help text.** `gnost --help` had an old `open:` block next to the docs' full `open|show:` block; there is one correct block now.

---
## [0.5.3] — Smaller Maven plugin — 2026-11-19

### Changed
- **Maven plugin:** it is now small (about 0.1 MB instead of 146 MB per release, because Maven Central limits how much each month's releases may total). It no longer carries the binaries. It uses `-Dgnost.binary`, then a `gnost` on `PATH` of the same version (a different version is ignored with a warning), then a copy in `~/.gnost`, which it downloads once from the GitHub Release of the same version after checking a SHA-256 built into the plugin. `-Dgnost.home` and `-Dgnost.downloadUrl` (a mirror) are new. If the download fails, the error tells you to install gnost with `pipx` or `npm` so it is found on `PATH`.
- **Maven plugin output:** every run prints the cache folder, the exact `gnost` command with its working directory, and the files it wrote.
- **Release pipeline:** release candidates never upload to Maven Central; they build the plugin, run its tests and smoke-test it against the real GitHub pre-release. Final tags upload and validate, and you publish in the Portal.

### Added
- **Maven `help` goal:** `mvn gnost:help` lists the goals and options. The README and the docs map each `mvn gnost:<goal>` to its `gnost <command>`.

### Fixed
- **Tests:** the Maven plugin's unit tests were never committed (a `.gitignore` rule for `test/` hid `src/test`), so CI compiled the plugin without running them. They are committed now and run on JDK 8, 11, 17 and 21.

The 0.5.0 plugin and its binaries stay on Maven Central. Use 0.5.3 or newer: 0.5.0 still has the `--progress` crash fixed in 0.5.2.

---
## [0.5.2] — Fixes — 2026-11-19

### Changed
- **Docs:** a "Commands by channel" page lists which commands run with pip, npm, Docker and the Maven plugin, with every Maven goal and option; the sidebar has a Home entry; the docs build without warnings.
- **npm page:** the flow explorer demo is shown in the `gnost-cli` README.

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
