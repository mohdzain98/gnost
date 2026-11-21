Use GNOST in CI
===============

``gnost analyze`` can stop a pull request that makes the code worse, show only the problems a change
*adds*, and put its findings in GitHub's code scanning. Everything below works in any CI system that can
run the Docker image, and there is a ready-made GitHub Action.

.. note::

   ``gnost analyze`` supports **Python** code today, so these checks gate Python code. JavaScript,
   TypeScript and Java analysis is planned for a later release. ``gnost onboard`` works for all of them.

Exit codes
----------

Scripts and CI can rely on these:

.. list-table::
   :header-rows: 1
   :widths: 10 90

   * - Code
     - Meaning
   * - ``0``
     - Success.
   * - ``1``
     - Something went wrong while running (an unexpected error, or a file could not be written).
   * - ``2``
     - A mistake in how the command or ``.gnost.toml`` was written: unknown option, missing path,
       a baseline file that does not exist, ``--fail-on-new`` without ``--baseline``.
   * - ``3``
     - **The quality gate failed**: the score is under ``--fail-under``, or there are new findings
       with ``--fail-on-new``.
   * - ``130``
     - Interrupted (Ctrl+C).

The score gate
--------------

``gnost analyze`` ends with a *final score* from 0 to 10 (higher is better). Make the job fail below a
threshold:

.. code-block:: bash

   gnost analyze . --fail-under 7.5       # exit code 3 if the final score is under 7.5

Run ``gnost analyze .`` once to see where you are, set the threshold a little under it, and raise it as
the code improves. The same setting can live in ``.gnost.toml`` (``[analyze] fail_under = 7.5``).

Only new findings: the baseline
-------------------------------

On an existing project the first run reports every old problem, which no one will fix at once. A
**baseline** records today's findings so that later runs report only what is new.

.. code-block:: bash

   gnost analyze . --write-baseline       # once: writes .gnost/baseline.json; commit it
   gnost analyze . --baseline --fail-on-new   # in CI: exit code 3 if anything new appeared

With ``--baseline`` the report, the JSON, the HTML page and the SARIF file contain only the new findings,
and the terminal says how many known findings were hidden. The final score still covers everything, so
``--fail-under`` keeps its meaning. Without ``--fail-on-new`` the baseline only filters the report.

When you have cleaned things up, refresh it with ``--write-baseline`` again and commit the change.

How findings are matched: a finding is recognised by *what it is and where* (the analyzer, the rule, its
title with numbers removed, the file and the function), **not** by its line number, so moving code
around does not make old findings look new. Findings are counted, not just listed: if a file had two
findings of one kind and now has three, one is new, and fixing one of three never hides a newly added
one.

SARIF and GitHub code scanning
------------------------------

.. code-block:: bash

   gnost analyze . --sarif                # writes .gnost/analysis/analysis.sarif
   gnost analyze . --sarif results.sarif  # or a path of your choice

`SARIF <https://sarifweb.azurewebsites.net/>`_ is the standard format for code analysis results. GitHub
shows it as alerts on pull requests and in the Security tab. Each result carries a stable fingerprint,
so an alert is not reopened every time the line moves. Paths are relative to the repository root.

The GitHub Action
-----------------

.. code-block:: yaml

   name: GNOST
   on:
     pull_request:
     push:
       branches: [main]

   permissions:
     contents: read
     security-events: write     # to upload the findings to code scanning

   jobs:
     gnost:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
           with:
             fetch-depth: 0     # full history, for the change features
         - uses: mohdzain98/gnost@v0.6.1
           with:
             fail-under: "7.5"
             baseline: .gnost/baseline.json
             fail-on-new: "true"

The action runs GNOST's Docker image, writes the SARIF file and uploads it, adds the score to the job
summary, and then fails the job if the gate failed. Pinning ``@v0.6.1`` also pins the GNOST version.

.. list-table::
   :header-rows: 1
   :widths: 22 18 60

   * - Input
     - Default
     - What it does
   * - ``path``
     - ``.``
     - Folder to analyze, relative to the repository root.
   * - ``fail-under``
     - none
     - Fail when the final score (0 to 10) is below this.
   * - ``baseline``
     - none
     - Baseline file; only findings not in it are reported.
   * - ``fail-on-new``
     - ``false``
     - With a baseline, fail when there are new findings.
   * - ``sarif``
     - ``true``
     - Upload the findings to code scanning. Set ``false`` if your repository does not have code scanning.
   * - ``onboard``
     - ``false``
     - Also write the onboarding guide and attach it to the run.
   * - ``comment``
     - ``false``
     - On pull requests, post one comment (updated on each push) from :doc:`changes`. Needs ``fetch-depth: 0`` and ``pull-requests: write``.
   * - ``version``
     - the action's version
     - GNOST version (Docker image tag).

The step also has an output, ``exit-code``.

Other CI systems
----------------

Any system that runs containers can use the same image:

.. code-block:: bash

   docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/repo -w /repo \
     ghcr.io/mohdzain98/gnost:latest analyze /repo --fail-under 7.5 --sarif --no-progress

The command exits with code 3 when the gate fails, which every CI system treats as a failed job. If
``pip`` is available, ``pip install gnost`` and ``gnost analyze . --fail-under 7.5`` does the same.

Maven
-----

The Maven plugin passes the same options to the ``analyze`` goal:

.. code-block:: bash

   mvn gnost:analyze -Dgnost.failUnder=7.5
   mvn gnost:analyze -Dgnost.baseline=true -Dgnost.failOnNew=true -Dgnost.sarif=true

``true`` means the default file in ``.gnost/``; give a path to use another one.
