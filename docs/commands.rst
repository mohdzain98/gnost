Commands by channel
===================

GNOST has one set of commands. Which ones you can run depends on how you installed it:
the Python package, the npm package and the Docker image run **every** command, and the
Maven plugin runs **three** of them for now.

The commands do not change with the language you analyze. ``gnost onboard`` and
``gnost summary`` work the same on Python, JavaScript, TypeScript and Java projects.
Only ``gnost analyze`` is limited by language: it supports Python code today.

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
   * - ``stats``, ``folders``, ``files``
     - yes
     - yes
     - yes
     - not yet
   * - ``open`` (report, flow), ``show``
     - yes
     - yes
     - yes, with ``--no-open``
     - not yet
   * - ``version``
     - yes
     - yes
     - yes
     - not yet (the plugin version is in the command)

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

      The goals are ``onboard``, ``analyze``, ``summary`` and ``help`` (``mvn gnost:help``
      lists them). There is no ``open`` or ``version`` goal yet. Use the latest version number from
      `Maven Central <https://central.sonatype.com/artifact/io.github.mohdzain98/gnost-maven-plugin>`_.

Maven goals and options
-----------------------

Options are Maven properties: ``-Dgnost.<name>=<value>``. They mirror the command-line flags.
Output goes to your project folder (``ONBOARD.md``, ``docs/``), not to ``target/``.
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
     - Show a progress bar.
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
     - Write ``docs/analysis/gnost_analysis.json`` and ``.html``.
   * - ``gnost.parallel``
     - ``--parallel``
     - Run the analyzers in parallel.
   * - ``gnost.analyzer``
     - ``-a, --analyzer``
     - Run only this analyzer.
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

Examples
~~~~~~~~

.. code-block:: bash

   mvn gnost:onboard
   mvn gnost:onboard -Dgnost.layered=true -Dgnost.depth=3
   mvn gnost:analyze -Dgnost.out=true -Dgnost.parallel=true
   mvn gnost:summary -Dgnost.exclude=target,node_modules

Commands the plugin does not have yet
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``stats``, ``folders``, ``files`` and ``open`` are not Maven goals yet; they are planned for 0.6.0. In a Java project
use another channel for them, for example ``npx gnost-cli open flow`` or
``uvx gnost files .``. ``open flow`` shows the diagrams that ``gnost:onboard`` wrote to ``docs/flow``.
