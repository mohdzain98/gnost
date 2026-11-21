What does this change touch?
============================

``gnost changes`` answers the question a reviewer asks first: *what does this change reach, and how
risky is it?* It compares two points in git history, like a pull request does, and reports on the
files in between.

.. code-block:: bash

   gnost changes origin/main            # your branch against main
   gnost changes v0.5.3..HEAD           # everything since a release
   gnost changes main --format markdown # the text for a pull request comment

``BASE`` alone means ``BASE..HEAD``. Both ``..`` and ``...`` work the same: the comparison starts at
the commit where ``HEAD`` split from ``BASE``, so commits that landed on ``BASE`` meanwhile are not
counted as your changes. Your working tree is never touched: the base version is exported to a
temporary folder, scanned, and removed.

What you get
------------

* **Changed files**, grouped as added, modified, deleted and renamed (renames keep the old name).
* **Blast radius:** the files that import a changed file, directly (distance 1) or through other
  files, up to ``--depth`` (default 3). Files that imported a deleted or renamed file are included.
* **Risky files in this change:** the caution score of each changed file, combined with how often it
  has changed (see :doc:`onboard`). Only files at or above the ``[risk] threshold`` are listed.
* **Routes:** routes that were added or removed, and routes whose handler is in a changed or
  affected file.
* **Circular dependencies** that the change creates or fixes, found by scanning both versions.
  Use ``--no-cycles`` to skip the base scan (faster on very large repositories).
* **Findings in changed files** with ``--findings``: the :doc:`analyze` analyzers run on the changed
  Python files only.

Output
------

The terminal shows a short summary. ``--format markdown`` or ``--format json`` print the other forms
instead. The files are always written, unless you pass ``--no-write``:

* ``.gnost/changes/changes.md``: Markdown that GitHub renders; this is also the pull request comment.
* ``.gnost/changes/changes.json``: the same facts for tools (``schema_version`` ``1.0``).

Pull request comment
--------------------

With the GitHub Action, ``comment: "true"`` posts this report as one comment on each pull request and
updates it on every push (see :doc:`ci`). The workflow needs ``fetch-depth: 0`` so the base branch is
available, and ``pull-requests: write``.

Limits
------

* A shallow clone does not have the base commit. Fetch it (``git fetch origin main``) or use
  ``fetch-depth: 0``.
* Imports are read as written. A change that only breaks something at run time, with no import
  between the files, does not show up in the blast radius.
* Circular dependencies are matched by the set of files in them, so a cycle that gains a file is
  reported as a new one.
* The routes, blast radius and risk describe the folder as it is now; ``HEAD`` should be the commit
  you have checked out (GNOST says so when it is not).
