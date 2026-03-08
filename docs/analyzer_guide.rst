Analyzer Guide
==============

This section documents how each analyzer works and what its findings mean.

Maintainability
---------------

Focus
~~~~~

Assesses complexity and long-term maintenance effort.

What it reports
~~~~~~~~~~~~~~~

- Cyclomatic complexity patterns
- Maintainability scoring signals
- Duplication and structural debt indicators

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
- Exception handling and runtime risk patterns
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
- Observatory gaps that reduce incident traceability

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

- ``ruff`` for readability findings.
- ``bandit`` and ``mypy`` for robustness findings.
- ``radon`` for maintainability findings.
