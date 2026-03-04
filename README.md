# GNOST — Codebase Knowledge
![PyPI](https://img.shields.io/pypi/v/gnost)
![Python](https://img.shields.io/pypi/pyversions/gnost)
[![Tests](https://github.com/mohdzain98/gnost/actions/workflows/tests.yml/badge.svg)](https://github.com/mohdzain98/gnost/actions/workflows/tests.yml)
![License](https://img.shields.io/pypi/l/gnost)
![Downloads](https://static.pepy.tech/badge/gnost)

<!-- ![Monthly Downloads](https://static.pepy.tech/badge/gnost/month) -->

GNOST is a lightweight static analysis CLI tool that helps developers understand unfamiliar codebases in minutes.<br>
It automatically detects entry points, maps execution flow, identifies critical files, and generates onboarding documentation and Mermaid diagrams.

Perfect for first-day onboarding, audits, and codebase exploration.

## 🚀 Why GNOST?
- Quickly build a mental model of a new codebase
- See how execution flows without reading everything
- Generate onboarding docs and Mermaid diagrams with one command

## 🧠 What GNOST Does
- Detects **where execution starts**
- Infers **high-level execution flow**
- Identifies **hotspot files** (most important code)
- Generates **onboarding documentation**
- Produces **Mermaid flow diagrams**
- Works across multiple languages

## 📌 Getting Started
Install:

```bash
pip install gnost
```

Run the onboarding scan:

```bash
gnost onboard .
```

Minimal usage examples:

```bash
gnost summary .
gnost stats .
```
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
