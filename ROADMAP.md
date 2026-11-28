# GNOST roadmap

What has shipped and what is planned next. Plans are not promises: the order can change with feedback.
Ideas and votes go in [discussion #27](https://github.com/mohdzain98/gnost/discussions/27); a 👍 on a comment helps decide the order.

## Shipped

| Version | Highlights |
|---|---|
| 0.4.0 | Structural intelligence: circular dependencies, JSON export, route-to-handler mapping, caution scoring, `.gnost.toml` |
| 0.5.0 | Install from PyPI, npm, Docker and Maven |
| 0.6.0 | `gnost changes` (blast radius and risk of a change), remote repositories, the GitHub Action |
| 0.7.0 | `gnost analyze` for JavaScript, TypeScript and Java; architecture rules; "Get it running"; `gnost mcp` |
| 0.7.1 | Size-aware quality score, README badge, flow explorer on GitHub Pages, comments on pull requests from forks |
| 0.7.2 | SARIF upload fix for code scanning, line counts in `gnost changes`, troubleshooting page |

Details for every release are in the [CHANGELOG](CHANGELOG.md).

## Next

| Version | Theme |
|---|---|
| **0.8.0** (in progress) | **A readable map of the whole project.** A mind-map view of the project (folders as branches, files as leaves, entry points and hotspots highlighted), a mind map you can add to your README (SVG, or a rotating GIF), and a 3D view you can rotate and click through. The old `score = "average"` setting is removed. |
| **0.9.0** | **GNOST for AI agents.** Skills that coding agents (Claude Code, Codex, Cursor, Copilot) read: your coding style (`gnost learn`, Python first), GNOST's quality rules with a check loop, and how this project works. Bring your own agent: GNOST can ask a coding agent you already use, with read-only access, and checks what it returns. No model or API key inside GNOST. |
| **0.10.0** | **More file types and a faster core.** Jupyter notebooks, HTML and CSS in `gnost stats` and the summary. An optional Rust core (`gnost-core`) that reads and parses files in parallel, with the Python code as a fallback. |
| **0.11.0** | **One new language** for the flow, the dependency graph and `analyze`. Go first (written in the Rust core), then Kotlin, C# and Rust. |

## Later

- Duplicate-code detection for JavaScript, TypeScript and Java.
- The languages not picked for 0.11.0, and PHP.
- More CI examples (CircleCI and others) and more coding-agent integrations, as people ask.

## Want to help?

Issues labelled [good first issue](https://github.com/mohdzain98/gnost/labels/good%20first%20issue) are small and
have steps. Read [CONTRIBUTING.md](CONTRIBUTING.md) first.
