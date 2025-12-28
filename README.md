# GNOST — Codebase Knowledge
![Status](https://img.shields.io/badge/status-v0.1.0--pre--release-yellow)
![License](https://img.shields.io/badge/license-MIT-blue)



GNOST helps developers understand unfamiliar codebases by automatically identifying **entry points**, **execution flow**, and **core logic**.

It is designed for **first-day onboarding**, not just code statistics.

---

## What GNOST Does

- Detects **where execution starts**
- Infers **high-level execution flow**
- Identifies **hotspot files** (most important code)
- Generates **onboarding documentation**
- Produces **Mermaid flow diagrams**
- Works across multiple languages

Supported languages:
- Python
- JavaScript
- TypeScript
- Java

---

## Installation

```bash
pip install gnost
```

## Quick Start
```bash
gnost onboard .
```
This will:
- Print a human-readable onboarding summary
- Generate ONBOARD.md
- Generate an execution flow diagram

## Usage
```bash
gnost summary [path]
gnost stats [path]
gnost folders [path]
gnost files [path] --top 10
gnost onboard [path]
```

## Key Commands
- `summary` Show a high-level project summary
- `stats` Show detailed language statistics
- `folders` Show LOC grouped by folder
- `files` Show largest files by LOC
- `onboard` Generate onboarding summary and flow diagrams
- `version` Display GNOST version

## Onboarding & Flow Analysis
- Generate onboarding documentation:
  ```bash
  gnost onboard .
  ```
- Generate only a Mermaid flow diagram:
  ```bash
  gnost onboard . --mermaid
  ```
  This produces:
  - ONBOARD.md — onboarding guide
  - FLOW.mmd — pure Mermaid flow diagram

### Options
- `--include` Comma-separated folders to include
- `--exclude` Comma-separated folders to exclude
- `--top` Number of files to show with files
- `--version` Show version and exit
- `--help` Show help

## examples
```bash
gnost summary .
gnost stats .
gnost onboard .
gnost onboard . --mermaid
gnost files src --top 20
```

## Philosophy
GNOST is not a **static analyzer or linter**.

It focuses on:
- Mental model generation
- Execution understanding
- Developer onboarding

It uses **heuristic-based static analysis** to stay fast, simple, and language-agnostic.

## Roadmap

### v0.2.0 (Planned)

- Hotspot visualization in Mermaid diagrams
- Standalone `gnost hotspots` command
- Improved JavaScript / TypeScript import resolution
- Better framework awareness (Express, Spring MVC)
- Optional Tree-sitter based parsing for deeper analysis
- GitHub Action enhancements (PR comments, annotations)

## License
MIT License