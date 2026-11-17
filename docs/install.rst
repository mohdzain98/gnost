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

.. tab-set::

   .. tab-item:: Maven

      Coming in 0.5.x. Until then use Docker, or ``uvx`` / ``npx`` if you have
      Python or Node.

   .. tab-item:: Gradle

      Planned for later. Use Docker, ``uvx`` or ``npx`` meanwhile.

Which channel should I use?
---------------------------

* You have Python: ``pip install gnost`` or ``uvx gnost``.
* You work in JavaScript or TypeScript: ``npx gnost-cli``.
* You want nothing installed, or a CI job: the Docker image.

First run
---------

``gnost onboard`` writes into your project: ``ONBOARD.md`` and ``docs/flow/``.
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
