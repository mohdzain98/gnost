Configuration
=============

GNOST works without any configuration. To change its defaults for a project, add a
``.gnost.toml`` file at the root of the repository (GNOST looks for it from the folder
you scan upwards, and stops at the repository root).

Order of precedence: **command-line flags**, then ``.gnost.toml``, then the built-in
defaults. Unknown settings are reported as warnings and ignored; a setting with the
wrong type stops the command with a message that names the file and the setting.

A complete example
------------------

.. code-block:: toml

   # Files and folders skipped by onboard and analyze.
   # A name matches a folder anywhere, a pattern matches file names or paths.
   exclude = ["legacy", "*.generated.ts", "docs/build"]

   [onboard]
   max_edges = 150      # largest diagram drawn file by file (default 200)
   collapse = 1         # always group diagrams by folder
   depth = 3            # limit how deep the execution flow goes

   [caution]            # which files are "risky to change"
   threshold = 50       # lowest caution score reported, 0-100 (default 40)
   limit = 15           # most files reported (default 10)

   [caution.weights]    # the most each signal can add to a score, 0-1
   size = 0.5

   [caution.ranges]     # [value that counts as 0, value that counts as 1]
   size = [300, 1500]   # lines of code

   [analyze]
   analyzers = ["maintainability", "readability"]
   timeout = 600
   max_findings = 500
   parallel = true

Caution score
-------------

``gnost onboard`` ranks files by how risky they are to change and lists the worst under
"Caution Areas". Each file gets a score from 0 to 100 built from these signals:

=============  ========================================================  ===============
Signal         Meaning                                                   Default weight
=============  ========================================================  ===============
cycles         part of a circular dependency (deferred ones count less)  0.9
impact         how many files import it                                  0.8
size           lines of code                                             0.7
complexity     most complex function (Python) or branch count estimate   0.7
coupling       how many project files it imports                         0.5
observability  ``except`` blocks that neither log nor re-raise (Python)  0.4
=============  ========================================================  ===============

Signals combine like independent risks: one strong signal is enough to flag a file and
several moderate ones add up. Signals that cannot be measured for a language (complexity
estimates for JS/TS/Java, observability outside Python) are left out and the score is
marked *partial*. Generated files (in a ``generated`` folder or with a "generated" header)
are never listed.

Each entry in the insights JSON includes the score and the ``factors`` behind it, so
scripts can see why a file was flagged.
