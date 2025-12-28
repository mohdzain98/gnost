GNOST — Codebase Knowledge
=======================================

GNOST helps developers understand unfamiliar codebases by identifying
entry points, execution flow, and core logic automatically.

It is designed for **first-day onboarding**, not just code statistics.

---

Usage
-----

Run GNOST commands from the root of a repository::

    gnost summary [path]
    gnost stats [path]
    gnost folders [path]
    gnost files [path] --top 10
    gnost onboard [path]

---

Key Commands
------------

``summary``
    Show a high-level project summary.

``stats``
    Show detailed language statistics.

``folders``
    Show lines of code grouped by folder.

``files``
    Show the largest files by lines of code.

``onboard``
    Generate onboarding summary and execution flow outputs.

``version``
    Display GNOST version.

---

Onboarding & Flow Analysis
--------------------------

Generate onboarding documentation::

    gnost onboard .

Generate only a Mermaid flow diagram::

    gnost onboard . --mermaid

This produces:

- **ONBOARD.md** — onboarding guide for new contributors
- **FLOW.mmd** — pure Mermaid execution flow diagram

---

Options
-------

``--include``
    Comma-separated folders to include.

``--exclude``
    Comma-separated folders to exclude.

``--top``
    Number of files to show with ``files``.

``--version``
    Show version and exit.

``--help``
    Show help information.

---

Examples
--------

Run GNOST on the current directory::

    gnost summary .
    gnost stats .
    gnost onboard .

Generate only a flow diagram::

    gnost onboard . --mermaid

Show largest files::

    gnost files src --top 20

---

Supported Languages
-------------------

- Python
- JavaScript
- TypeScript
- Java

---

Links
-----

- Source Code: https://github.com/mohdzain98/gnost
- Documentation: https://gnost.readthedocs.io
- PyPI: https://pypi.org/project/gnost/
