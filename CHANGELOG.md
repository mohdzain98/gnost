# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

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
- JavaScript (.js)
- TypeScript (.ts)
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

## [Unreleased]

### Planned

- Hotspot coloring in Mermaid diagrams
- JavaScript/TypeScript framework depth improvements
- GitHub Action for auto-generated onboarding docs
- Tree-sitter based AST parsing

```GNOST is in early development v0.1.0. APIs and behavior may evolve.```
