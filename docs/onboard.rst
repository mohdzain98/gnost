Onboard
=======

``gnost onboard`` generates onboarding artifacts that help you quickly understand a repository.

What it generates
-----------------

- ``ONBOARD.md`` at repository root
- Mermaid diagrams under ``docs/flow``:

  - ``FLOW-full.mmd`` and ``FLOW-full.md``
  - ``FLOW-overview.mmd``
  - ``entry-paths.md``
  - ``folder-paths.md``

Command reference
-----------------

.. code-block:: bash

   gnost onboard [path]

Options
~~~~~~~

- ``--mermaid``: generate only Mermaid flow output.
- ``--progress``: show progress indicators.
- ``--inject``: inject onboarding link into repository README.
- ``--layered``: generate layered flow (Entry -> Core -> Leaf).
- ``--depth N``: limit execution depth.

Examples
~~~~~~~~

.. code-block:: bash

   gnost onboard .
   gnost onboard . --mermaid
   gnost onboard . --layered --depth 3
