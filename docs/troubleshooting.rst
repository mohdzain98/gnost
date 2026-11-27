Troubleshooting
===============

Common messages GNOST prints, what causes them, and how to resolve them.

Shallow clone history warnings
------------------------------

**Message:** ``this is a shallow clone, so the history is cut short; ...``

**Cause:** The Git repository was cloned with ``--depth`` (such as GitHub Actions ``actions/checkout`` default ``fetch-depth: 1``), so commit history needed for churn hotspots and ``gnost changes`` is missing.

**Fix:** Fetch the complete history before running GNOST:

.. code-block:: yaml

   - uses: actions/checkout@v4
     with:
       fetch-depth: 0

Or locally in an existing checkout:

.. code-block:: bash

   git fetch --unshallow

Git is not installed or not on PATH
-----------------------------------

**Message:** ``git is not installed or not on PATH, so history is not available.``

**Cause:** GNOST could not locate a ``git`` executable in the process ``PATH``.

**Fix:** Install Git (`https://git-scm.com <https://git-scm.com>`_) and ensure the directory containing ``git`` is on your ``PATH`` before running GNOST.

Unsupported platform in npm wrapper (``gnost-cli``)
---------------------------------------------------

**Message:** ``gnost-cli has no prebuilt binary for <platform>-<arch>.`` (or ``The platform package @gnost-cli/... is not installed.`` when optional dependencies were omitted)

**Cause:** Prebuilt native binaries for ``gnost-cli`` ship only for supported platforms (``darwin-arm64``, ``linux-x64``, ``win32-x64``), or npm skipped optional platform dependencies via ``--no-optional`` / ``--omit=optional``.

**Fix:** Install via Python (``pipx install gnost``) or use the Docker image (``ghcr.io/mohdzain98/gnost``), or reinstall ``gnost-cli`` with optional dependencies enabled.

Remote repository access refused
--------------------------------

**Message:** ``could not clone <repo>: access was refused.``

**Cause:** ``gnost onboard <url>`` disables interactive credential prompts (``GIT_TERMINAL_PROMPT=0``) and cannot authenticate against private repositories.

**Fix:** Pass a public ``https://`` URL, or clone the private repository locally with your own Git credentials and run ``gnost onboard <folder>`` on the local checkout.

Exit codes and quality gate failures
------------------------------------

``gnost analyze`` returns specific exit codes so scripts and CI workflows can distinguish setup errors from quality-gate violations:

- ``0`` — Success.
- ``1`` — Unexpected runtime error or output write failure.
- ``2`` — Invalid CLI option, missing path, invalid ``.gnost.toml``, missing baseline file, or invalid flag combination (for example ``--fail-on-new`` without ``--baseline``).
- ``3`` — Quality gate failed: the project score is below ``--fail-under`` or new findings were introduced under ``--baseline --fail-on-new``. Inspect ``.gnost/analysis/analysis.json`` (or run ``gnost open report``) to review findings.
- ``130`` — Interrupted (``Ctrl+C``).

See :doc:`ci` for full CI configuration and baseline details.
