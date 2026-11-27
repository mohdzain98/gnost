Calibration
===========

How the built-in rules and the score were checked on real projects. The tables also help you read your own
score: they show where well-known projects land. :doc:`scoring` explains the formula.

Method
------

``gnost analyze . -o --max-findings 100000`` (GNOST 0.7.1) on the default branch of well-known open source
projects, cloned in November 2026, with all analyzers and every finding kept. *Lines* are the non-blank lines of
the analyzed files (tests included), *density* is the severity-weighted findings per 1,000 lines, *score* is the
final score, and *old formula* is the 0.7.0 score (average severity, ``score = "average"``) of the same run, for
comparison. Times are on an Apple silicon laptop. Python times include mypy, bandit, radon and ruff.

**Rule thresholds** for JavaScript, TypeScript and Java were chosen so that a rule selects roughly the worst 3 %
of functions: complexity 10, function length 60 lines, file length 500 lines, nesting 4, 5 parameters. Every
false positive found became a test fixture and a fix. Twelve shared rules have the same id, analyzer and
severity in every language, enforced by a test.

**The score curve** ``10 − 2 × ln(1 + density)`` was chosen from these runs. It is the gentlest log curve that
puts clearly cleaner projects ahead with a useful gap (express 9.62 against jquery 8.50), while well-regarded
Python projects stay around 6 to 7 and do not fall to 0. A steeper curve (2.5 instead of 2) pushed requests
below 5, which says more about the strictness of mypy and the docstring rules than about requests.

JavaScript and TypeScript
-------------------------

.. list-table::
   :header-rows: 1

   * - Project
     - Files
     - Lines
     - Time
     - Findings
     - Density
     - Score
     - Old formula
   * - express (JS)
     - 142
     - 18,004
     - 0.9 s
     - 46
     - 0.21
     - **9.62**
     - 8.85
   * - vercel/commerce (Next.js, TS)
     - 66
     - 3,527
     - 0.3 s
     - 35
     - 1.02
     - **8.59**
     - 8.63
   * - vue core (TS)
     - 519
     - 156,229
     - 7.4 s
     - 972
     - 1.08
     - **8.53**
     - 7.84
   * - jquery (older JS)
     - 222
     - 43,881
     - 2.3 s
     - 254
     - 1.12
     - **8.50**
     - 7.71

Java
----

.. list-table::
   :header-rows: 1

   * - Project
     - Files
     - Lines
     - Time
     - Findings
     - Density
     - Score
     - Old formula
   * - spring-petclinic
     - 20
     - 2,023
     - 0.3 s
     - 3
     - 0.12
     - **9.77**
     - 8.67
   * - apache commons-lang
     - 647
     - 196,517
     - 8.8 s
     - 749
     - 0.40
     - **9.32**
     - 8.58
   * - jsoup
     - 216
     - 57,081
     - 3.1 s
     - 307
     - 0.64
     - **9.01**
     - 8.42
   * - gson
     - 268
     - 52,087
     - 2.2 s
     - 145
     - 0.39
     - **9.34**
     - 8.15

Python
------

.. list-table::
   :header-rows: 1

   * - Project
     - Files
     - Lines
     - Time
     - Findings
     - Density
     - Score
     - Old formula
   * - requests
     - 37
     - 9,841
     - 6.2 s
     - 315
     - 6.55
     - **5.96**
     - 7.47
   * - flask
     - 83
     - 14,119
     - 12.0 s
     - 323
     - 3.93
     - **6.81**
     - 7.85
   * - fastapi
     - 1,237
     - 117,671
     - 214.5 s
     - 3,382
     - 3.91
     - **6.82**
     - 8.12
   * - GNOST itself
     - 480
     - 52,332
     - 40.5 s
     - 1,013
     - 3.68
     - **6.91**
     - 7.70

Python projects show four to six times the density of JS and Java projects. Most of it is mypy type findings
and ruff's docstring rules (``D205``, ``D212``, ``D400`` and others), which the JS/TS/Java rules do not have.
Compare a Python project with other Python projects. ``analyze .`` covers the whole folder, so fastapi's 1,237
files are 658 in ``tests/``, 488 tutorial examples in ``docs_src/`` and only 54 in the ``fastapi`` package itself.
Run ``gnost analyze fastapi`` (the package folder) to score only the library.

What the checks changed
-----------------------

* Test code is exempt from the noisy rules (empty catch, swallowed errors, long files, naming, ``eval``).
* A ``catch`` block that only holds a comment, or mentions an error, is not reported as swallowed. Swallowed
  errors are LOW severity.
* Javadoc is not "commented-out code"; generated folders (``dist``, ``build``, ``target``, ``.gradle`` and
  others) are skipped.
* **0.7.1:** ``analyze`` checks the whole folder it is given. Before, a project without code at its top level
  was analyzed from its largest sub-folder, often ``tests/``. The 0.7.0 tables of this page measured
  jsoup and commons-lang from ``src/test`` only (87 and 280 findings then, 307 and 749 now). The React app of the
  0.7.0 table is a private project and was not measured again.

Reading the score
-----------------

* 9 and above: clean, well-kept code for its size (express, gson, commons-lang, jsoup).
* 8 to 9: large or older code bases with a steady stream of complexity findings (vue core, jquery).
* 6 to 7: Python projects under full mypy and docstring checks (flask, fastapi).

Track your own score over time and use ``gnost analyze --baseline --fail-on-new`` so nothing new slips in.
See :doc:`scoring` for the formula and :doc:`ci` for gating on it.
