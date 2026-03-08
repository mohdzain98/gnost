Analyze
=======

``gnost analyze`` runs quality analyzers and reports scores plus findings.

Current implementation target
----------------------------

- ``Python`` (for now)
- JavaScript / TypeScript / Java support is planned in upcoming releases.

Command reference
-----------------

.. code-block:: bash

   gnost analyze [path]

Key options
-----------

- ``-a`` / ``--analyzer``
  Run only selected analyzers (repeatable).
- ``--parallel``
  Run analyzers in parallel.
- ``-o`` / ``--out``
  Write artifacts to:

  - ``docs/analysis/gnost_analysis.json``
  - ``docs/analysis/gnost_analysis.html``

- ``--max-findings N``
  Limit findings collected per analyzer.
- ``--compact``
  Emit compact JSON when ``-o`` is enabled.
- ``--timeout SECONDS``
  Analyzer timeout for each analyzer.
- ``--no-progress``
  Hide progress bar.
- ``--quiet``
  Reduce logs to warnings/errors only.
- ``--verbose``
  Print tracebacks for failures.
- ``--list-analyzers``
  Print analyzer names and exit.

Output behavior
--------------

- Terminal: table with analyzer scores and severity counts.
- JSON: machine-readable results for CI or pipelines.
- HTML: interactive report for human review.

Open the report
---------------

After analysis output, use:

- ``gnost open report``
- ``gnost open rpt`` (alias)

If needed, also use OS command directly:

- macOS: ``open docs/analysis/gnost_analysis.html``
- Linux: ``xdg-open docs/analysis/gnost_analysis.html``
- Windows: ``start "" docs\analysis\gnost_analysis.html``

Example
-------

.. code-block:: bash

   gnost analyze . --parallel -o
   gnost open report
