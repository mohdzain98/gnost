Commands by channel
===================

GNOST has one set of commands. Which ones you can run depends on how you installed it:
the Python package, the npm package and the Docker image run **every** command; the Maven
plugin runs all except ``mcp`` (a long-running process).

The commands do not change with the language you analyze. ``gnost onboard`` and
``gnost summary`` work the same on Python, JavaScript, TypeScript and Java projects.
``gnost analyze`` supports Python, JavaScript, TypeScript and Java; other languages are skipped.

What runs where
---------------

.. list-table::
   :header-rows: 1
   :widths: 22 16 16 16 30

   * - Command
     - pip / uvx
     - npm
     - Docker
     - Maven plugin
   * - ``onboard``
     - yes
     - yes
     - yes
     - yes (``gnost:onboard``)
   * - ``analyze``
     - yes
     - yes
     - yes
     - yes (``gnost:analyze``)
   * - ``summary``
     - yes
     - yes
     - yes
     - yes (``gnost:summary``)
   * - ``changes``
     - yes
     - yes
     - yes
     - yes (``gnost:changes``)
   * - ``init``
     - yes
     - yes
     - yes
     - yes (``gnost:init``)
   * - ``stats``, ``folders``, ``files``
     - yes
     - yes
     - yes
     - yes (``gnost:stats``, ``gnost:folders``, ``gnost:files``)
   * - ``open`` (report, flow), ``show``
     - yes
     - yes
     - yes, with ``--no-open``
     - yes (``gnost:open``; ``-Dgnost.open=false`` for CI)
   * - ``mcp`` (:doc:`agents`)
     - yes
     - yes
     - yes, with ``docker run -i``
     - no (long-running process)
   * - ``version``
     - yes
     - yes
     - yes
     - yes (``gnost:version``)

.. _remote-repositories:

Repositories by address
-----------------------

``onboard``, ``analyze`` and ``changes`` accept a repository address instead of a folder:

.. code-block:: bash

   gnost onboard https://github.com/spring-projects/spring-petclinic
   gnost analyze git@github.com:owner/repo.git --ref v1.2.0 -o
   gnost changes origin/main https://github.com/owner/repo   # BASE first, then the address

Only ``https://`` and ``ssh`` addresses work (``git@host:owner/repo`` too); plain ``http://``,
``git://`` and ``file://`` are refused. ``--ref`` picks a branch or tag.

* The repository is cloned into a temporary folder and **deleted afterwards**, also when you press
  Ctrl+C. The clone is partial (history without file contents until needed); if the server cannot do
  that, GNOST takes the last 500 commits instead and says the history is cut.
* **The results go to the current folder, in a folder named after the repository** (``.gnost/<repo-name>/``,
  for example ``.gnost/flask/``), not into the clone. Several runs never overwrite each other. Open the page with
  ``gnost open .gnost/<repo-name>/flow.html``; the command is printed at the end of the run.
* **Nothing in the repository is run.** Git hooks, submodules and symlinks are switched off. mypy,
  ruff and the other analyzers use GNOST's own settings, so a repository cannot make them load
  plugins from its ``mypy.ini`` or ``pyproject.toml``. The repository's own ``.gnost.toml`` is not
  read either (use the one in your current folder). A test checks this with a repository that tries
  to run a mypy plugin.
* GNOST never asks for a password. Private repositories need ssh keys already set up, or clone them
  yourself and give GNOST the folder.
* Limits: 10 minutes to clone and 500 MB of files. Bigger repositories: clone them yourself.

Running a command
-----------------

.. tab-set::

   .. tab-item:: pip / uvx

      .. code-block:: bash

         gnost <command> [options]
         uvx gnost <command> [options]

   .. tab-item:: npm

      .. code-block:: bash

         npx gnost-cli <command> [options]
         gnost <command> [options]            # after npm install --global gnost-cli

      Installed into a project with ``npm install gnost-cli`` (no ``--global``), the
      command is not on your ``PATH``. Run it with ``npx gnost <command>``.

   .. tab-item:: Docker

      .. code-block:: bash

         docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/repo \
           ghcr.io/mohdzain98/gnost <command> /repo [options]

      A container cannot open your browser. Use ``open flow --no-open -o /repo/flow.html``
      and open the file yourself.

   .. tab-item:: Maven

      .. code-block:: bash

         mvn io.github.mohdzain98:gnost-maven-plugin:<version>:<goal>
         mvn gnost:<goal>            # when the plugin is in your pom.xml

      There is a goal for every command: ``onboard``, ``analyze``, ``changes``, ``summary``,
      ``stats``, ``folders``, ``files``, ``open``, ``init``, ``version`` and ``help`` (``mvn gnost:help``
      lists them). Use the latest version number from
      `Maven Central <https://central.sonatype.com/artifact/io.github.mohdzain98/gnost-maven-plugin>`_.

Maven goals and options
-----------------------

Options are Maven properties: ``-Dgnost.<name>=<value>``. They mirror the command-line flags.
Output goes to the ``.gnost/`` folder in your project (``ONBOARD.md``, ``flow/``, ``insights.json``), not to ``target/``.
Each run prints the cache folder, the exact ``gnost`` command, its working directory and the
files it wrote.
The goals do not need a ``pom.xml``, and run once for the folder you start Maven in.

Options for every goal:

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Property
     - Default
     - What it does
   * - ``gnost.path``
     - current folder
     - Folder (or file) to scan.
   * - ``gnost.args``
     - none
     - Extra flags passed to the command as they are, for example ``-Dgnost.args="--include src"``.
   * - ``gnost.skip``
     - ``false``
     - Skip the goal.
   * - ``gnost.binary``
     - none
     - Path to a gnost executable. Skips the ``PATH`` lookup and the download.
   * - ``gnost.home``
     - ``~/.gnost``
     - Where the downloaded binary is kept.
   * - ``gnost.downloadUrl``
     - GitHub Release
     - Folder (or mirror) that holds ``gnost-VERSION-PLATFORM.tar.gz`` (``.zip`` on Windows).

``gnost:onboard`` (same as ``gnost onboard``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Property
     - Flag
     - What it does
   * - ``gnost.mermaid``
     - ``--mermaid``
     - Only the Mermaid flow diagram.
   * - ``gnost.layered``
     - ``--layered``
     - Layered diagram: entry, core, leaf.
   * - ``gnost.inject``
     - ``--inject``
     - Add a link to ``ONBOARD.md`` in ``README.md``.
   * - ``gnost.progress``
     - ``--progress``
     - Always show the progress bar.
   * - ``gnost.noProgress``
     - ``--no-progress``
     - Never show the progress bar (``onboard`` shows it by default in a terminal).
   * - ``gnost.depth``
     - ``--depth N``
     - Limit the execution flow depth.
   * - ``gnost.maxEdges``
     - ``--max-edges N``
     - Largest diagram drawn file by file (default 80).
   * - ``gnost.collapse``
     - ``--collapse [LEVEL]``
     - Group diagrams by folder.
   * - ``gnost.json``
     - ``--json [FILE]``
     - Also write the insights as JSON.
   * - ``gnost.insightsOnly``
     - ``--insights-only``
     - Write only the insights JSON.

``gnost:analyze`` (same as ``gnost analyze``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Property
     - Flag
     - What it does
   * - ``gnost.out``
     - ``-o, --out``
     - Write ``.gnost/analysis/analysis.json`` and ``analysis.html``.
   * - ``gnost.parallel``
     - ``--parallel``
     - Run the analyzers in parallel.
   * - ``gnost.analyzer``
     - ``-a, --analyzer``
     - Run only this analyzer.
   * - ``gnost.language``
     - ``--language``
     - Comma-separated languages to analyze: ``python``, ``javascript``, ``typescript``, ``java`` (default: all).
   * - ``gnost.listAnalyzers``
     - ``--list-analyzers``
     - List the analyzers and stop.
   * - ``gnost.quiet``
     - ``--quiet``
     - Only warnings and errors.
   * - ``gnost.noProgress``
     - ``--no-progress``
     - Hide progress updates.
   * - ``gnost.compact``
     - ``--compact``
     - Compact JSON with ``-o``.
   * - ``gnost.verbose``
     - ``-v, --verbose``
     - Show tracebacks on failures.
   * - ``gnost.timeout``
     - ``--timeout SECONDS``
     - Analyzer timeout (default 900).
   * - ``gnost.maxFindings``
     - ``--max-findings N``
     - Findings limit per analyzer (default 1000).
   * - ``gnost.failUnder``
     - ``--fail-under SCORE``
     - Fail the build when the final score (0-10) is lower. See :doc:`ci`.
   * - ``gnost.baseline``
     - ``--baseline [FILE]``
     - Report only findings not in the baseline (``true`` = ``.gnost/baseline.json``).
   * - ``gnost.writeBaseline``
     - ``--write-baseline [FILE]``
     - Save today's findings as the baseline.
   * - ``gnost.failOnNew``
     - ``--fail-on-new``
     - With a baseline, fail the build on new findings.
   * - ``gnost.sarif``
     - ``--sarif [FILE]``
     - Write the findings as SARIF (``true`` = ``.gnost/analysis/analysis.sarif``).

``gnost:summary`` (same as ``gnost summary``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Property
     - Flag
     - What it does
   * - ``gnost.include``
     - ``--include``
     - Comma-separated folder names to include.
   * - ``gnost.exclude``
     - ``--exclude``
     - Comma-separated folder names to exclude.
   * - ``gnost.progress``
     - ``--progress``
     - Show a progress bar.

``gnost:stats``, ``gnost:folders``, ``gnost:files`` (same as the commands)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These take the same ``gnost.include``, ``gnost.exclude`` and ``gnost.progress`` as ``gnost:summary``.
``gnost:files`` also has ``gnost.top`` (``--top``): how many files to show.

``gnost:changes`` (same as ``gnost changes``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Property
     - Flag
     - What it does
   * - ``gnost.refs`` (required)
     - ``BASE[..HEAD]``
     - What to compare, for example ``origin/main``.
   * - ``gnost.depth``
     - ``--depth``
     - How far to follow importers (default 3).
   * - ``gnost.format``
     - ``--format``
     - Print ``text``, ``markdown`` or ``json``.
   * - ``gnost.findings``
     - ``--findings``
     - Also run the analyzers on the changed Python files.
   * - ``gnost.noCycles``
     - ``--no-cycles``
     - Skip scanning the base commit.
   * - ``gnost.noWrite``
     - ``--no-write``
     - Do not write ``.gnost/changes/``.
   * - ``gnost.failOnViolations``
     - ``--fail-on-violations``
     - Fail the build (exit code 3) when the change breaks an ``[architecture]`` rule.

``gnost:open``, ``gnost:init`` and ``gnost:version``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Property
     - Flag
     - What it does
   * - ``gnost.target``
     - ``open`` argument
     - ``open``: ``report`` (default), ``flow`` or a ``.mmd``, ``.md`` or ``.html`` file.
   * - ``gnost.open``
     - ``--no-open``
     - ``open``: set ``-Dgnost.open=false`` to write the page without starting a browser (CI).
   * - ``gnost.output``, ``gnost.file``, ``gnost.view``
     - ``-o``, ``--path``, ``--view``
     - ``open``: where to save the page, a custom report or diagram, and the viewer.
   * - ``gnost.pom``, ``gnost.npm``, ``gnost.githubAction``, ``gnost.agents``
     - ``--pom``, ``--npm``, ``--github-action``, ``--agents``
     - ``init``: wire GNOST into the build.
   * - ``gnost.force``, ``gnost.print``, ``gnost.dryRun``
     - ``--force``, ``--print``, ``--dry-run``
     - ``init``: overwrite, print only, or show what would change.

``gnost:version`` takes no options. It prints the version of the binary the plugin would run.

Repository addresses: ``onboard``, ``analyze`` and ``changes`` accept
``-Dgnost.path=https://github.com/owner/repo`` (and ``-Dgnost.ref=BRANCH``); see
:ref:`remote-repositories`.

Examples
~~~~~~~~

.. code-block:: bash

   mvn gnost:onboard
   mvn gnost:onboard -Dgnost.layered=true -Dgnost.depth=3
   mvn gnost:analyze -Dgnost.out=true -Dgnost.parallel=true
   mvn gnost:summary -Dgnost.exclude=target,node_modules
   mvn gnost:changes -Dgnost.refs=origin/main -Dgnost.format=markdown
   mvn gnost:open -Dgnost.target=flow -Dgnost.open=false
   mvn gnost:init -Dgnost.pom=true -Dgnost.dryRun=true
