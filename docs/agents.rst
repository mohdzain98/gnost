Use GNOST with coding agents
============================

``gnost mcp`` starts a small `Model Context Protocol <https://modelcontextprotocol.io>`_ server so an AI
coding agent (Claude Code, Codex, Cursor, VS Code, Windsurf and others) can ask GNOST about your project instead of
reading hundreds of files to find the entry point.

It is **read-only**: it reads ``.gnost/insights.json`` and, for ``gnost_changes``, your git history. It never
writes files, never runs project code and never uses the network. Paths an agent asks about must stay inside
the project.

Set it up
---------

1. Create the facts once (and again after big changes)::

      gnost onboard .

2. Register the server in your agent. Most clients take a command and arguments:

   .. code-block:: json

      {
        "mcpServers": {
          "gnost": { "command": "gnost", "args": ["mcp", "/path/to/project"] }
        }
      }

   Without a global install use ``"command": "npx", "args": ["gnost-cli", "mcp", "."]`` or
   ``"command": "uvx", "args": ["gnost", "mcp", "."]``. In Claude Code: ``claude mcp add gnost -- gnost mcp .``

Tools
-----

.. list-table::
   :header-rows: 1

   * - Tool
     - What the agent gets
   * - ``gnost_overview``
     - Languages, framework, size, how to install, run and test, architecture rule status
   * - ``gnost_entry_points``
     - Where the program starts, and HTTP routes
   * - ``gnost_hotspots``
     - The files everything depends on (read these first)
   * - ``gnost_risk``
     - Files that are fragile and change often, and caution areas
   * - ``gnost_file``
     - One file: what it imports, who imports it, its layer, caution areas
   * - ``gnost_changes``
     - Impact of a change (``main`` or ``main..HEAD``): changed files with risk, dependents, routes, cycles

If ``insights.json`` is missing the tool says to run ``gnost onboard`` (the server does not create it). It is
read again when the file changes, so an agent sees fresh facts after you re-run ``onboard``.

Notes
-----

* The server is a long-running process on stdio, so there is no Maven goal for it.
* Messages are one JSON object per line (JSON-RPC 2.0); diagnostics go to stderr, never stdout.
