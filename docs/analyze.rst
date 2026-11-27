Analyze
=======

``gnost analyze`` runs quality analyzers and reports scores plus findings.

Current implementation target
-----------------------------

- **Python**, checked with mypy, bandit, radon and ruff.
- **JavaScript and TypeScript** (``.js .jsx .mjs .cjs .ts .tsx .mts .cts``), checked with GNOST's own rules
  (since 0.7.0). Nothing else has to be installed: no Node, no ESLint, no JDK.
- **Java** (``.java``), checked with the same kind of rules (since 0.7.0).

A project can mix languages. The same four analyzers (robustness, maintainability, observability, readability)
and the same score cover all of them. ``node_modules``, build output (``dist``, ``build``, ``.next``, ``coverage``),
minified files, ``.d.ts`` files and Maven or Gradle output (``target``, ``.gradle``) are skipped, and test files are exempt from the rules that do not apply to
tests (for example ``console.log`` and long functions).

JavaScript and TypeScript rules
-------------------------------

Every finding carries a rule id. The same id is used for the same idea in every language, so a baseline or a
SARIF alert keeps its meaning. Findings marked *per file* are one finding with a count, so a few hundred long
lines are one remark and not hundreds.

.. list-table::
   :header-rows: 1
   :widths: 22 14 14 50

   * - Rule
     - Analyzer
     - Severity
     - What it flags
   * - ``ROB-EMPTY-CATCH``
     - robustness
     - medium
     - A ``catch`` block or ``.catch()`` handler with nothing in it (a comment counts as a reason)
   * - ``ROB-LOOSE-EQUALITY``
     - robustness
     - low
     - ``==`` and ``!=`` (comparing with ``null`` is accepted). Per file
   * - ``ROB-UNSAFE-EVAL``
     - robustness
     - high
     - ``eval()`` and ``new Function()``. Not in test files
   * - ``ROB-UNSAFE-HTML``
     - robustness
     - high
     - ``innerHTML`` or ``dangerouslySetInnerHTML`` set from a value that is not a literal. Not in test files
   * - ``ROB-UNTYPED-ANY``
     - robustness
     - low
     - An explicit ``any`` (TypeScript). Per file
   * - ``ROB-TS-SUPPRESS``
     - robustness
     - low
     - ``@ts-ignore`` and ``@ts-nocheck`` (TypeScript). Per file
   * - ``MNT-COMPLEXITY``
     - maintainability
     - low to high
     - Cyclomatic complexity above 10 (above 15 medium, above 20 high)
   * - ``MNT-LONG-FUNCTION``
     - maintainability
     - low, medium
     - A function longer than 60 lines (120 medium). Not in test files
   * - ``MNT-LONG-FILE``
     - maintainability
     - low, medium
     - A file longer than 500 lines (1000 medium)
   * - ``MNT-DEEP-NESTING``
     - maintainability
     - low
     - Control statements nested more than 4 levels deep
   * - ``MNT-MANY-PARAMS``
     - maintainability
     - low
     - More than 5 parameters
   * - ``OBS-SWALLOWED-ERROR``
     - observability
     - low
     - A ``catch`` that does not log, rethrow, use or report the error. Not in test files
   * - ``OBS-PRINT-LOGGING``
     - observability
     - info
     - ``console.log``, ``debug``, ``info`` and ``trace`` instead of a logger. Per file, not in test files
   * - ``RDB-NAMING``
     - readability
     - info
     - snake_case functions and variables, lowercase class names. Per file
   * - ``RDB-LONG-LINE``
     - readability
     - info
     - Lines over 120 characters (links and imports are exempt). Per file
   * - ``RDB-COMMENTED-CODE``
     - readability
     - info
     - Comments that are mostly code. Per file
   * - ``RDB-TODO``
     - readability
     - info
     - ``TODO``, ``FIXME``, ``XXX`` and ``HACK`` comments. Per file

Java rules
----------

Java has the same twelve core rules as JavaScript and TypeScript (``ROB-EMPTY-CATCH``, ``MNT-COMPLEXITY``,
``MNT-LONG-FUNCTION``, ``MNT-LONG-FILE``, ``MNT-DEEP-NESTING``, ``MNT-MANY-PARAMS``, ``OBS-SWALLOWED-ERROR``,
``OBS-PRINT-LOGGING``, ``RDB-NAMING``, ``RDB-LONG-LINE``, ``RDB-COMMENTED-CODE``, ``RDB-TODO``), with the same
severity, and these of its own:

.. list-table::
   :header-rows: 1
   :widths: 26 16 12 46

   * - Rule
     - Analyzer
     - Severity
     - What it flags
   * - ``ROB-CATCH-GENERIC``
     - robustness
     - low
     - ``catch (Exception e)`` or ``catch (Throwable t)``
   * - ``ROB-STRING-EQUALITY``
     - robustness
     - medium
     - A string literal compared with ``==`` or ``!=``
   * - ``ROB-UNSAFE-EXEC``
     - robustness
     - high
     - ``Runtime.getRuntime().exec(...)`` with a command that is not a literal. Not in test files
   * - ``OBS-PRINT-STACKTRACE``
     - observability
     - low
     - ``printStackTrace()`` instead of logging. Per file, not in test files
   * - ``MNT-GOD-CLASS``
     - maintainability
     - low, medium
     - A class with more than 30 methods (60 medium). Not in test files

``OBS-PRINT-LOGGING`` means ``System.out`` and ``System.err`` in Java. Classes named ``*Test``, ``*Tests`` or ``*IT``
and anything under a ``test`` folder count as test files.

The thresholds are fixed in 0.7.0. Limit the languages with ``--language`` (repeatable) or ``languages = [...]`` in
the ``[analyze]`` section of ``.gnost.toml``.

Command reference
-----------------

.. code-block:: bash

   gnost analyze [path]

Key options
-----------

- ``-a`` / ``--analyzer``
  Run only selected analyzers (repeatable).
- ``--language``
  Analyze only these languages (repeatable): ``python``, ``javascript``, ``typescript``, ``java``.
- ``--parallel``
  Run analyzers in parallel.
- ``-o`` / ``--out``
  Write artifacts to:

  - ``.gnost/analysis/analysis.json``
  - ``.gnost/analysis/analysis.html``

- ``--max-findings N``
  Limit the findings listed per analyzer (default 1000). The score still counts the ones left out
  (see :doc:`scoring`).
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

Score
-----

Every analyzer gets a score from 0 to 10, and the project a final score. The score comes from the finding
*density*: the severity weights of the findings per 1,000 analyzed lines, on the curve
``10 − 2 × ln(1 + density)``. More findings, or more severe ones, lower it, and a bigger project carries the same
findings more easily. :doc:`scoring` has the weights, the curve, a worked example and how to compare scores;
:doc:`calibration` shows where well-known projects land.

CI options
----------

``--badge [FILE]`` writes the final score as a README badge (``.gnost/badge.svg``); see :doc:`scoring`.

``--fail-under SCORE``, ``--baseline`` / ``--write-baseline`` / ``--fail-on-new`` and ``--sarif`` make
``analyze`` usable as a quality gate and a code scanning source. See :doc:`ci`.

Output behavior
---------------

- Terminal: table with analyzer scores and severity counts, and the final score. :doc:`scoring` explains how
  the scores are computed (finding density on a log curve).
- JSON: machine-readable results for CI or pipelines.
- HTML: interactive report for human review.

Open the report
---------------

After analysis output, use:

- ``gnost open report``
- ``gnost open rpt`` (alias)

If needed, also use OS command directly:

- macOS: ``open .gnost/analysis/analysis.html``
- Linux: ``xdg-open .gnost/analysis/analysis.html``
- Windows: ``start "" .gnost\analysis\analysis.html``

Example
-------

.. code-block:: bash

   gnost analyze . --parallel -o
   gnost open report
