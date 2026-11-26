Analyzer Guide
==============

This section documents how each analyzer works and what its findings mean.

The four analyzers cover **Python, JavaScript, TypeScript and Java**. Python is checked by external tools
(listed at the end); the other languages are checked by GNOST's own rules, which read the syntax tree
(tree-sitter) and need nothing else installed. Twelve core rules have the same id, analyzer and severity in
every language, so a score, a baseline or a SARIF file means the same everywhere. The rules per language are
listed on the :doc:`analyze` page, and :doc:`calibration` shows how they were tested on real projects.

Maintainability
---------------

Focus
~~~~~

Assesses complexity and long-term maintenance effort.

What it reports
~~~~~~~~~~~~~~~

- Cyclomatic complexity patterns
- Maintainability scoring signals
- Long functions and files, deep nesting, too many parameters, very large classes
- Duplication indicators (Python only for now)

Severity meaning
~~~~~~~~~~~~~~~~

- **High**: highly complex or brittle code blocks.
- **Medium**: moderate complexity and localized maintainability concerns.
- **Low**: minor maintainability observations.

Robustness
----------

Focus
~~~~~

Checks correctness and static safety issues.

What it reports
~~~~~~~~~~~~~~~

- Type mismatch and contract-safety patterns
- Exception handling and runtime risk patterns (empty or too broad ``catch`` / ``except``, ``eval``, string ``==`` in Java)
- Critical correctness blind spots

Severity meaning
~~~~~~~~~~~~~~~~

- **High**: likely runtime failure under realistic inputs.
- **Medium**: defects under edge conditions.
- **Low**: potential quality improvements.

Observability
-------------

Focus
~~~~~

Checks codebase visibility and production debugging readiness.

What it reports
~~~~~~~~~~~~~~~

- Missing or weak logging in critical execution paths
- Incomplete structured logging and context
- Gaps that reduce incident traceability (print statements instead of logging, swallowed errors)

Severity meaning
~~~~~~~~~~~~~~~~

- **High**: production blind spots that can block triage.
- **Medium**: partial observability with weak correlation.
- **Low**: formatting/coverage improvements.

Readability
-----------

Focus
~~~~~

Assesses clarity and naming/readability patterns.

What it reports
~~~~~~~~~~~~~~~

- Style violations and structure clarity signals
- Naming and documentation consistency

Severity meaning
~~~~~~~~~~~~~~~~

- **High**: difficult to read and review safely.
- **Medium**: readability reduced in important sections.
- **Low**: minor style consistency issues.

Tools and scope
~~~~~~~~~~~~~~~

**Python** uses external tools:

- ``ruff`` for readability findings.
- ``bandit`` and ``mypy`` for robustness findings.
- ``radon`` for maintainability findings.

**JavaScript, TypeScript and Java** use GNOST's own rules for all four analyzers. Test files are exempt from the
rules that do not apply to them, and generated folders (``node_modules``, ``dist``, ``build``, ``target`` and
others) are skipped. Duplicate-code detection is not available for these languages yet.

Each analyzer's score comes from the density of its findings: their severity weights per 1,000 analyzed lines,
on a log curve from 10 down to 0. More findings or more severe ones lower it, and a bigger project carries the
same findings more easily. :doc:`scoring` has the formula, the curve and a worked example.
