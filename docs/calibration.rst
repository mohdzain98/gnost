Rule calibration
================

How the built-in rules for JavaScript, TypeScript and Java were checked on real projects. The same tables
help you read your own scores. Python uses its external tools and is not listed here.

**Method.** ``gnost analyze -o`` on well-known open source projects. Thresholds were chosen so a rule selects
roughly the worst 3 % of functions: complexity 10, function length 60 lines, file length 500 lines, nesting 4,
5 parameters. Every false positive found became a test fixture and a fix. Twelve shared rules have the same id,
analyzer and severity in every language, enforced by a test.

JavaScript and TypeScript
-------------------------

.. list-table::
   :header-rows: 1

   * - Project
     - Files
     - Time
     - Findings
     - Final score
   * - express (JS)
     - 50
     - 1.1 s
     - 60
     - 8.67
   * - vercel/commerce (Next.js, TS)
     - about 120
     - 0.3 s
     - 37
     - 8.53
   * - vue core (TS)
     - about 490
     - 7.7 s
     - 1,135
     - 7.58
   * - jquery (older JS)
     - about 150
     - 2.6 s
     - 325
     - 7.47
   * - a React app (TS)
     - about 400
     - 3.8 s
     - 601
     - 7.69

Java
----

.. list-table::
   :header-rows: 1

   * - Project
     - Time
     - Findings
     - Final score
   * - spring-petclinic
     - 0.3 s
     - 3
     - 8.67
   * - apache commons-lang
     - 6.2 s
     - 280
     - 8.71
   * - jsoup
     - 2.3 s
     - 87
     - 8.61
   * - gson
     - 2.4 s
     - 129
     - 8.06

What the checks changed
-----------------------

* Test code is exempt from the noisy rules (empty catch, swallowed errors, long files, naming, ``eval``).
* A ``catch`` block that only holds a comment, or mentions an error, is not reported as swallowed. Swallowed
  errors are LOW severity.
* Javadoc is not "commented-out code"; generated folders (``dist``, ``build``, ``target``, ``.gradle`` and
  others) are skipped.

Reading the score
-----------------

The final score is the average severity of the findings, not their number, so it does not grow worse with the
size of a project. Use the findings list and ``gnost analyze --baseline --fail-on-new`` to track change over time.
A size-aware score is planned.
