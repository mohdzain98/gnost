# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

---
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

## Planned v0.3.0 — Deeper Code Intelligence [Unreleased]
- **Planned**
- Circular Dependency Detection
  - Identify and report cyclic dependencies between modules

- **LOC-Based Risk Analysis**
  - Detect large and complex files using lines-of-code metrics

- **AST-Aware Flow Analysis**
  - Language-specific execution flow using AST parsing (Python, JS/TS)

- **Advanced Mermaid Enhancements**
  - Smarter diagram simplification for large codebases
  - Path-level annotations and divergence markers

- **Advanced Caution Scoring**
  - More accurate severity ranking using multiple signals

- **CLI Enhancements**
  - --insights-only mode
  - Configurable thresholds for caution detection

- **Export & Integration**
  - JSON export of onboarding insights
  - Better integration with documentation and CI workflows

```GNOST is in early development v0.2.0. APIs and behavior may evolve.```
