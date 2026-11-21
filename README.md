# GNOST — Codebase Knowledge
[![PyPI](https://img.shields.io/pypi/v/gnost?label=PyPI)](https://pypi.org/project/gnost/)
[![npm](https://img.shields.io/npm/v/gnost-cli?label=npm)](https://www.npmjs.com/package/gnost-cli)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-2496ED?logo=docker&logoColor=white)](https://github.com/mohdzain98/gnost/pkgs/container/gnost)
[![Maven](https://img.shields.io/maven-central/v/io.github.mohdzain98/gnost-maven-plugin?label=Maven)](https://central.sonatype.com/artifact/io.github.mohdzain98/gnost-maven-plugin)
[![Tests](https://github.com/mohdzain98/gnost/actions/workflows/tests.yml/badge.svg)](https://github.com/mohdzain98/gnost/actions/workflows/tests.yml)
[![GitHub Action](https://img.shields.io/badge/GitHub_Action-GNOST-2088FF?logo=githubactions&logoColor=white)](https://github.com/marketplace/actions/gnost-codebase-onboarding-and-quality-gate)
[![License](https://img.shields.io/github/license/mohdzain98/gnost)](./LICENSE)

GNOST is a lightweight static analysis CLI tool that helps developers understand unfamiliar codebases in minutes.<br>
It automatically detects entry points, maps execution flow, identifies critical files, and generates onboarding documentation and Mermaid diagrams.  

It also performs quality analysis (`gnost analyze`) for maintainability, robustness, observability, and readability to provide a fast quality score and prioritized findings.

Perfect for first-day onboarding, audits, and codebase exploration.

![GNOST flow explorer: folder overview, open a folder, open a file, hover for details](https://raw.githubusercontent.com/mohdzain98/gnost/main/assets/viewer_demo.gif)

**See real output before you install anything:** the [gallery](https://gnost.readthedocs.io/en/latest/gallery.html) has guides for flask, fastapi, express and spring-petclinic.

## 🚀 Why GNOST?
- Quickly build a mental model of a new codebase, **even from a repository address** (`gnost onboard https://github.com/owner/repo`)
- See how execution flows without reading everything
- Generate onboarding docs and Mermaid diagrams with one command

## 🧠 What GNOST Does
- Works on a folder **or a repository address** (`gnost onboard https://github.com/owner/repo`): read-only clone, nothing in it is run, deleted afterwards
- Detects **where execution starts**
- Infers **high-level execution flow**
- Identifies **hotspot files** (most important code)
- Generates **onboarding documentation**
- Produces **Mermaid flow diagrams**, plus an interactive **browser explorer** (`gnost open flow`)
- Finds **HTTP routes** (Flask, FastAPI, Django, Express, NestJS, Spring), **circular imports** and **caution areas** (risky files to read carefully)
- Traces **function-level flows** for Python, and exports everything as **JSON** for tools and AI
- Reads an optional **`.gnost.toml`** for excludes, weights and thresholds
- Runs code **quality analysis** for maintainability, robustness, observability, and readability

## Install

Pick the channel you already use. The same version is published to all of them.

| Channel | Command | Needs |
|---|---|---|
| pip | `pip install gnost` | Python 3.9+ |
| uv / pipx | `uvx gnost onboard .` or `pipx run gnost onboard .` | Python 3.9+ |
| npm | `npx gnost-cli onboard .` | Node 18+ (no Python) |
| Docker | `docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/repo ghcr.io/mohdzain98/gnost onboard /repo` | Docker (no Python) |
| Maven | `mvn io.github.mohdzain98:gnost-maven-plugin:0.6.0:onboard` | Java 8+, Maven 3.6.3+ (no Python) |

The npm package carries a standalone binary for macOS (Apple silicon), Linux (x86_64) and Windows (x86_64).
The Maven plugin is small: it uses a matching `gnost` found on your `PATH`, or downloads the same binary once from the
GitHub Release (checked against a SHA-256 built into the plugin) and keeps it in `~/.gnost`.

The Maven goals run the same commands as the CLI:

| Maven goal | Runs |
|---|---|
| `mvn gnost:onboard` | `gnost onboard` |
| `mvn gnost:analyze` | `gnost analyze` |
| `mvn gnost:summary`, `gnost:stats`, `gnost:folders`, `gnost:files` | the same commands |
| `mvn gnost:changes -Dgnost.refs=origin/main` | `gnost changes` |
| `mvn gnost:open`, `gnost:init`, `gnost:version` | the same commands |
| `mvn gnost:help` | lists the goals and their options |

Options are `-Dgnost.*` properties, for example `mvn gnost:analyze -Dgnost.out=true`.
See the [install guide](https://gnost.readthedocs.io/en/latest/install.html) for details.

Run the onboarding scan:

```bash
gnost onboard .
```

## Explore the flow in your browser (since 0.4.0)

`gnost onboard .` saves everything in a `.gnost/` folder in your project: the guide (`ONBOARD.md`),
`insights.json`, Mermaid diagrams in `flow/` and the explorer page. For big projects,
`gnost open` opens them as an interactive explorer instead of one tangled picture:

```bash
gnost open flow
# or any file: gnost open .gnost/flow/flow-complete.mmd   (gnost show FILE does the same)
```

- **Folder overview first.** Each outlined box is a folder; arrows show how many imports go between them.
- **Click a folder** to see its files and the files it touches, with one arrow per neighbouring folder.
- **Click a file** (or pick it from the list) to see what it imports and what imports it.
- **Hover anything** and everything not connected to it fades, so its boxes and arrows stand out; the line at the bottom
  tells you its connections (for example `gnost/core/resolver.py: imports 2 files · imported by 6 files`).
- **Zoom** with the magnifier `+` / `-` buttons, the mouse wheel, or the Fit button.
- Dark by default, with a light theme button. Circular imports are red and orange.

| Folder overview (hovering a folder) | A file and what connects to it |
| --- | --- |
| ![Folder overview](https://raw.githubusercontent.com/mohdzain98/gnost/main/assets/viewer_folders.png) | ![File view with hover](https://raw.githubusercontent.com/mohdzain98/gnost/main/assets/viewer_file_hover.png) |

The example above is GNOST analysing its own source code.

## Minimal usage examples

```bash
gnost summary .
gnost stats .
```

## Analysis (since 0.3.0)

```bash
gnost analyze .
gnost analyze . --parallel -o
gnost open report
```

### Analysis report preview

![GNOST analysis report](https://raw.githubusercontent.com/mohdzain98/gnost/main/assets/report_example.png)

## What does my change touch? (since 0.6.0)

```bash
gnost changes origin/main                      # files, blast radius, risky files, routes, new cycles
gnost analyze . --fail-under 7.5 --sarif       # quality gate for CI, SARIF for GitHub code scanning
gnost onboard https://github.com/owner/repo    # a repository by address; nothing in it is run
```

Run it on every pull request with the GitHub Action (a comment with the blast radius and risk, plus a quality gate):

```yaml
- uses: actions/checkout@v4
  with: { fetch-depth: 0 }        # full history, for hotspots and `gnost changes`
- uses: mohdzain98/gnost@v0.6.0
  with: { comment: "true", fail-under: "7.5" }   # needs `pull-requests: write`
```

See [Use GNOST in CI](https://gnost.readthedocs.io/en/latest/ci.html), or run `gnost init --github-action` to write the workflow for you.

### Analysis scope

- `gnost analyze` currently supports Python codebases only.
- JavaScript/TypeScript/Java analysis is planned for future releases.

## 🌍 Supported Languages
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Java](https://img.shields.io/badge/Java-ED8B00?style=for-the-badge&logo=openjdk&logoColor=white)

## 🎯 Who Is This For?
- Developers joining a new team
- Engineers reviewing legacy code
- Startup founders auditing repos
- Tech leads onboarding new hires
- Open-source contributors

## 📊 Example Use Cases
- First-day onboarding automation
- Codebase documentation generation
- Architecture visualization
- Legacy system analysis
- Rapid technical due diligence


## 📦 Details
![Python](https://img.shields.io/pypi/pyversions/gnost?label=pip%3A%20Python)
![Node](https://img.shields.io/node/v/gnost-cli?label=npm%3A%20Node)
[![PyPI downloads](https://static.pepy.tech/badge/gnost)](https://pepy.tech/project/gnost)
[![npm downloads](https://img.shields.io/npm/dt/gnost-cli?label=npm%20downloads)](https://www.npmjs.com/package/gnost-cli)

Install commands for every channel are in the [Install](#install) table above.

## 📚 Documentation:
[![Docs](https://img.shields.io/readthedocs/gnost?label=docs)](https://gnost.readthedocs.io)

## 📜 Changelog:
[![Changelog](https://img.shields.io/badge/changelog-CHANGELOG.md-blue)](./CHANGELOG.md)

## 🧩 Philosophy
GNOST prioritizes:
- Fast insights over deep AST complexity
- Practical developer onboarding
- Clear summaries over raw metrics
- Zero-config usage

It is designed to be simple, fast, and immediately useful.

## License

MIT License
