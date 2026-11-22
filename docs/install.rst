Install
=======

GNOST ships through the package managers of the languages it analyzes.
Pick the channel you already use.

.. tab-set::

   .. tab-item:: pip / uv

      Needs Python 3.9 or newer.

      .. code-block:: bash

         pip install gnost
         gnost onboard .

      Without installing into a project:

      .. code-block:: bash

         uvx gnost onboard .
         pipx run gnost onboard .

   .. tab-item:: npm

      Needs Node 18 or newer. **No Python needed**: the package carries a
      standalone binary for macOS (Apple silicon), Linux (x86_64) and Windows (x86_64).

      .. code-block:: bash

         npx gnost-cli onboard .
         npm install --global gnost-cli    # then: gnost onboard .
         npm install --save-dev gnost-cli  # then use it in a package.json script

      Do not install with ``--no-optional``: the binary comes in an optional
      platform package.

   .. tab-item:: Docker

      No Python or Node needed. Mount the project at ``/repo``:

      .. code-block:: bash

         docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/repo \
           ghcr.io/mohdzain98/gnost onboard /repo

      Use the same ``--user`` option so the files it writes belong to you.

   .. tab-item:: Maven

      Needs Java 8 or newer and Maven 3.6.3 or newer, and plugin version 0.5.3 or newer.
      **No Python or Node needed.** The plugin is small. It looks for ``gnost`` in this
      order:

      1. ``-Dgnost.binary=/path/to/gnost``, if you set it.
      2. A ``gnost`` on your ``PATH`` (from ``pip``, ``pipx`` or ``npm``) **of the same
         version as the plugin**. A different version is ignored, with a warning.
      3. A copy in ``~/.gnost``. The first time, the plugin downloads the standalone
         binary for your machine (macOS Apple silicon, Linux x86_64, Windows x86_64) from
         the GitHub Release of the same version, checks its SHA-256 against the value
         built into the plugin, and keeps it there.

      Run it without editing your ``pom.xml``:

      .. code-block:: bash

         mvn io.github.mohdzain98:gnost-maven-plugin:0.7.0:onboard

      Or add the plugin once and use the short form:

      .. code-block:: xml

         <plugin>
           <groupId>io.github.mohdzain98</groupId>
           <artifactId>gnost-maven-plugin</artifactId>
           <version>0.7.0</version>
         </plugin>

      .. code-block:: bash

         mvn gnost:onboard
         mvn gnost:analyze -Dgnost.out=true
         mvn gnost:summary
         mvn gnost:help

      Options are ``-Dgnost.*`` properties that mirror the command-line flags, for
      example ``-Dgnost.mermaid=true``, ``-Dgnost.depth=2``, ``-Dgnost.out=true``.
      Use ``-Dgnost.path=DIR`` to scan another folder and ``-Dgnost.args="..."`` to
      pass any other flag. Output is written to the project folder (``docs/``), not
      ``target/``. Every run prints the cache folder, the exact ``gnost`` command with its
      working directory, and the files it wrote.

      If your network can only reach Maven Central, the download fails with a message
      that tells you to install gnost where Maven can find it (``pipx install gnost`` or
      ``npm install --global gnost-cli``). A company mirror of the release files can be
      used with ``-Dgnost.downloadUrl=https://mirror.example.com/gnost/0.5.3``.

Gradle is planned for later. Use Docker, ``uvx`` or ``npx`` in Gradle projects meanwhile.

The standalone binaries (npm, and the one the Maven plugin downloads) need a Linux with glibc 2.35 or newer
(Ubuntu 22.04, Debian 12 or newer). On older systems use Docker, or ``pip`` / ``uvx``.

Which channel should I use?
---------------------------

* You have Python: ``pip install gnost`` or ``uvx gnost``.
* You work in JavaScript or TypeScript: ``npx gnost-cli``.
* You work in Java: ``mvn gnost:onboard`` (the Maven plugin).
* You want nothing installed, or a CI job: the Docker image.

First run
---------

``gnost onboard`` writes one folder into your project: ``.gnost/`` (the guide, diagrams, JSON and the explorer page).
``gnost analyze`` runs bandit, radon, mypy and ruff for you; the binary and the
Docker image already carry them. ``jscpd`` (duplicate code) is optional and is
used only if it is on your ``PATH``.

``gnost open`` writes a self-contained HTML page and opens it. The page works
offline and can be sent as a file.

Binaries and security prompts
-----------------------------

The binaries are not code-signed. For that reason they are not offered as
direct downloads; the npm and Docker channels avoid the browser download
warnings of macOS and Windows. If you still download an archive from the
GitHub Release, compare it with ``SHA256SUMS``.
