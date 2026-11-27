Use GNOST in CI
===============

``gnost analyze`` can stop a pull request that makes the code worse, show only the problems a change
*adds*, and put its findings in GitHub's code scanning. Everything below works in any CI system that can
run the Docker image, and there is a ready-made GitHub Action.

.. note::

   ``gnost analyze`` supports **Python, JavaScript, TypeScript and Java** (JS/TS/Java since 0.7.0), so the
   quality gate works for all of them. Architecture rules (``gnost changes --fail-on-violations``) work for
   every language ``gnost onboard`` reads.

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

The score depends on how many findings there are for the size of the code (:doc:`scoring`). Python projects
score lower than JavaScript, TypeScript or Java projects of the same quality, because the Python checks (mypy,
ruff's docstring rules) report more, so pick the threshold from your own first run, not from another project.

.. note::

   **0.7.1 changed the score.** JS/TS/Java projects usually go up by 0.5 to 1.2, Python projects down by 0.8
   to 1.3. If a job that passed with 0.7.0 now fails ``--fail-under``, run once and move the threshold, or set
   ``[analyze] score = "average"`` to keep the old formula for now (it is removed in 0.8.0).

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
       branches: [main, master]   # pull requests into main or master
     push:
       branches: [main]           # only needed for code scanning (SARIF), see below

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
         - uses: mohdzain98/gnost@v0.7.0
           with:
             fail-under: "7.5"
             baseline: .gnost/baseline.json
             fail-on-new: "true"

The action runs GNOST's Docker image, writes the SARIF file and uploads it, adds the score to the job
summary, and then fails the job if the gate failed. Pinning ``@v0.7.0`` also pins the GNOST version.

**When it runs.** ``gnost init --github-action`` writes a workflow that runs on pull requests into ``main`` or
``master`` only: that is where the gate, the change report and the comment are useful, and it does not run a
second time when the pull request is merged. Add the ``push`` trigger above only if you upload findings to code
scanning (``sarif: "true"``): GitHub compares a pull request's alerts with the latest scan of the main branch,
so that branch needs scans of its own. Workflows written by an older ``gnost init`` are not changed; edit the
``on:`` block, or run ``gnost init --github-action --force`` to write the new one.

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
     - On pull requests, post one comment (updated on each push) from :doc:`changes`, and add the same report to
       the job summary. Needs ``fetch-depth: 0`` and ``pull-requests: write``. Pull requests from forks get the
       job summary only; see `Comments on pull requests from forks`_.
   * - ``fork-comments``
     - ``false``
     - On pull requests from forks, hand the report to the comment workflow (``gnost-comment.yml``) that posts it.
   * - ``version``
     - the action's version
     - GNOST version (Docker image tag).

The step also has an output, ``exit-code``.

Comments on pull requests from forks
------------------------------------

**Why a fork gets no comment.** For a pull request from a fork, GitHub runs your workflow with a **read-only**
token, whatever ``permissions:`` says, so a fork cannot write to your repository. The analysis runs as usual;
only the comment cannot be posted.

**What happens by default.** Every pull request, fork or not, gets the change report in the **job summary**
(the run's Summary page, linked from the Checks tab). On a fork's pull request the action skips the comment and
leaves a notice instead of an error:

.. code-block:: text

   Comments are not possible on pull requests from forks (GitHub gives them a read-only token).
   The change report is in the job summary. To comment anyway: gnost init --github-action --fork-comments

That is ``gnost init --github-action``: one workflow file, no extra permissions. It is enough for most
projects.

**Comments on forks too.** If outside contributors send pull requests and you want the comment on theirs as
well, use:

.. code-block:: bash

   gnost init --github-action --fork-comments

This writes two workflows, the pattern GitHub recommends for this case:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - File
     - What it does
   * - ``.github/workflows/gnost.yml``
     - Runs GNOST on the pull request (read-only for forks). On a fork's pull request it hands the report and
       the pull request number over as the ``gnost-comment`` artifact (``fork-comments: "true"``).
   * - ``.github/workflows/gnost-comment.yml``
     - Runs after "GNOST" finishes (``workflow_run``), in **your** repository with ``pull-requests: write``,
       downloads the artifact and posts or updates the comment.

The second workflow never checks out or runs the fork's code, and it trusts nothing in the artifact. The pull
request number must be a number, and that pull request must be open, come from the same fork and still point
at the commit that was analyzed. The report is only ever posted as text, at most 60,000 characters. It only
updates GNOST's own comment, never one that someone else wrote with the same marker. Already have a
``gnost.yml``? ``init`` says so; add ``fork-comments: "true"`` under ``with:`` of the GNOST step, or run with
``--force`` to write both files again.

**Why not** ``pull_request_target``\ **?** It would give a single file a write token, but a workflow that runs with
the base repository's rights *and* checks out the fork's code is the pattern GitHub's security guidance and
scanners warn about: the fork's code would run with access to your secrets and caches. The two-workflow setup
keeps the code that runs and the token that writes apart.

Other CI systems
----------------

Any system that runs containers can use the same image:

.. code-block:: bash

   docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/repo -w /repo \
     ghcr.io/mohdzain98/gnost:latest analyze /repo --fail-under 7.5 --sarif --no-progress

The command exits with code 3 when the gate fails, which every CI system treats as a failed job. If
``pip`` is available, ``pip install gnost`` and ``gnost analyze . --fail-under 7.5`` does the same.

Inside a CI job that already runs *in* the image (GitLab, Jenkins below), two things differ from
``docker run``: the image's entrypoint is ``gnost``, so set it to empty and call ``gnost`` yourself, and git
only trusts ``/repo`` by default, so allow the checkout folder (the ``GIT_CONFIG_*`` variables below do that
without writing a config file). Pin the image to a version (``:0.7.1``) so the score does not change under you.

GitLab CI
~~~~~~~~~

.. code-block:: yaml

   gnost:
     image:
       name: ghcr.io/mohdzain98/gnost:0.7.1
       entrypoint: [""]
     variables:
       GIT_DEPTH: "0"                     # full history, for hotspots and `gnost changes`
       GIT_CONFIG_COUNT: "1"
       GIT_CONFIG_KEY_0: safe.directory
       GIT_CONFIG_VALUE_0: "*"
     rules:
       - if: $CI_PIPELINE_SOURCE == "merge_request_event"
     script:
       - gnost analyze . --fail-under 7.5 --no-progress -o
       - gnost changes "origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME" --format markdown | tee gnost-changes.md
     artifacts:
       when: always
       paths: [.gnost/analysis/, gnost-changes.md]

The job runs on merge requests; ``gnost changes`` compares the merge request with its target branch, and the
report is kept as an artifact (post it as a merge request note with your own token if you want a comment).
Exit code 3 fails the job when the score is below ``--fail-under``.

Jenkins
~~~~~~~

A declarative pipeline with the Docker Pipeline plugin:

.. code-block:: groovy

   pipeline {
     agent {
       docker {
         image 'ghcr.io/mohdzain98/gnost:0.7.1'
         args '--entrypoint=""'
       }
     }
     environment {
       GIT_CONFIG_COUNT = '1'
       GIT_CONFIG_KEY_0 = 'safe.directory'
       GIT_CONFIG_VALUE_0 = '*'
     }
     stages {
       stage('GNOST') {
         steps {
           sh 'gnost analyze . --fail-under 7.5 --no-progress -o --sarif'
         }
       }
     }
     post {
       always {
         archiveArtifacts artifacts: '.gnost/analysis/**', allowEmptyArchive: true
         // with the Warnings Next Generation plugin, show the findings in Jenkins:
         // recordIssues tools: [sarif(pattern: '.gnost/analysis/analysis.sarif')]
       }
     }
   }

Without Docker on the agent, install it with ``pip install gnost`` (Python 3.9+) in a ``sh`` step instead.

Maven
-----

The Maven plugin passes the same options to the ``analyze`` goal:

.. code-block:: bash

   mvn gnost:analyze -Dgnost.failUnder=7.5
   mvn gnost:analyze -Dgnost.baseline=true -Dgnost.failOnNew=true -Dgnost.sarif=true

``true`` means the default file in ``.gnost/``; give a path to use another one.

Gradle
------

There is no Gradle plugin yet. Run GNOST from a task with whatever the build machine has: Node (``npx``,
which downloads the ``gnost-cli`` binary), Python (``uvx`` or ``pipx``), or Docker. In ``build.gradle.kts``:

.. code-block:: kotlin

   tasks.register<Exec>("gnostOnboard") {
       group = "documentation"
       description = "Write the GNOST onboarding guide to .gnost/"
       commandLine("npx", "--yes", "gnost-cli", "onboard", ".")
   }

   tasks.register<Exec>("gnostAnalyze") {
       group = "verification"
       description = "GNOST quality gate"
       commandLine("npx", "--yes", "gnost-cli", "analyze", ".", "--fail-under", "7.5", "--no-progress")
   }

Replace ``"npx", "--yes", "gnost-cli"`` with ``"uvx", "gnost"`` to use Python instead. A failed gate (exit code
3) fails the task, and so the build when another task depends on it. On CI, the GitHub Action or the Docker
image above are the simplest choice for Gradle projects too.
