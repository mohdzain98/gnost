GNOST — Codebase Knowledge
=======================================

GNOST helps developers understand unfamiliar codebases by identifying
entry points, execution flow, and core logic automatically.

It is designed for **first-day onboarding** as well as decorating your repo, not just code statistics.

Usage
-----

Complete CLI usage::

    usage: gnost [command]

    options:
    -h, --help  show this help message and exit
    --version   show program's version number and exit

    Available Commands:
    command
        summary   Show a summary table
        stats     Show detailed stats per language
        folders   Show LOC grouped by folder
        files     Show the largest files by LOC
        version   Display gnost version
        onboard   Onboard a new codebase

    Command Options:
    summary|stats|folders|files:
        --include  Comma-separated folder names to include
        --exclude  Comma-separated folder names to exclude
        --progress Show a progress bar while scanning

    onboard:
        --progress Show a progress bar while onboarding
        --mermaid  Generate only Mermaid flow diagram (FLOW.mmd)
        --inject   Inject onboarding link into README.md files
        --layered  Produce Layered mermaid as Entry -> Core -> Leaf
        --depth    Limit execution flow depth (e.g. --depth 2)

    files:
        --top      Number of files to show (default: 5)
    Use `gnost <command> --help` for full command options.


Run GNOST commands from the root of a repository::

    gnost summary [path]
    gnost stats [path]
    gnost folders [path]
    gnost files [path] --top 10
    gnost onboard [path]

Subcommand usage::

    gnost summary [path] [--include INCLUDE] [--exclude EXCLUDE] [--progress]
    gnost stats [path] [--include INCLUDE] [--exclude EXCLUDE] [--progress]
    gnost folders [path] [--include INCLUDE] [--exclude EXCLUDE] [--progress]
    gnost files [path] [--include INCLUDE] [--exclude EXCLUDE] [--progress] [--top TOP]
    gnost onboard [path] [--mermaid] [--progress] [--inject] [--layered] [--depth DEPTH]
    gnost version


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


Onboarding & Flow Analysis
--------------------------

Generate onboarding documentation::

    gnost onboard .

Generate only a Mermaid flow diagram::

    gnost onboard . --mermaid

This produces:

- **ONBOARD.md** — onboarding guide for new contributors
- **flow folder** — pure Mermaid execution flow diagrams

  - *flow-full.md* — Full Flow diagram
  - *flow-overview.mmd* — Overview Mermaid with entry and core nodes
  - *entry-paths.md* — Mermaid of different entry paths
  - *folder-paths.md* — Mermaid of all paths inside different folders


Options
-------

``--include``
    Comma-separated folders to include.

``--exclude``
    Comma-separated folders to exclude.

``--top``
    Number of files to show with ``files``.

``--progress``
    Show a progress bar while scanning or onboarding.

``--mermaid``
    Generate only Mermaid flow diagram (FLOW.mmd) (onboard).

``--inject``
    Inject onboarding link into README.md (onboard).

``--layered``
    Produce Layered mermaid as Entry -> Core -> Leaf (onboard).

``--depth``
    Limit execution flow depth (onboard) (e.g. ``--depth 2``).

``--version``
    Show version and exit.

``--help``
    Show help information.


Examples
--------

Run GNOST on the current directory::

    gnost summary .
    gnost stats .
    gnost onboard .

Generate only a flow diagram::

    gnost onboard . --mermaid

Generate layered flow diagram::

    gnost onboard . --layered

Generate flow diagram with desired depth::

    gnost onboard . --depth N

Generate layered flow diagram with depth of 3::

    gnost onboard . --layered --depth 3

Show largest files::

    gnost files src --top 20


Supported Languages
-------------------

- Python
- JavaScript
- TypeScript
- Java


Links
-----

- Source Code: https://github.com/mohdzain98/gnost
- Documentation: https://gnost.readthedocs.io
- PyPI: https://pypi.org/project/gnost/
