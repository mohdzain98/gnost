Gallery
=======

Real output of ``gnost onboard`` on well-known open source projects, so you can see what you get before
you install anything. Each project also has its ``gnost analyze`` report (scores and findings, JSON). Each guide has the entry points, the execution flow, routes, change hotspots and
the files that are risky to change. GitHub renders the Mermaid diagrams.

.. list-table::
   :header-rows: 1
   :widths: 22 14 22 22 20

   * - Project
     - Language
     - Guide
     - Code quality (``gnost analyze``)
     - Project map
   * - `spring-petclinic <https://github.com/spring-projects/spring-petclinic>`_
     - Java
     - `ONBOARD.md <https://github.com/mohdzain98/gnost/blob/main/docs/gallery/spring-petclinic/ONBOARD.md>`_
     - `analysis.json <https://github.com/mohdzain98/gnost/blob/main/docs/gallery/spring-petclinic/analysis/analysis.json>`_
     - `mindmap.svg <https://github.com/mohdzain98/gnost/blob/main/docs/gallery/spring-petclinic/mindmap.svg>`_
   * - `flask <https://github.com/pallets/flask>`_
     - Python
     - `ONBOARD.md <https://github.com/mohdzain98/gnost/blob/main/docs/gallery/flask/ONBOARD.md>`_
     - `analysis.json <https://github.com/mohdzain98/gnost/blob/main/docs/gallery/flask/analysis/analysis.json>`_
     - `mindmap.svg <https://github.com/mohdzain98/gnost/blob/main/docs/gallery/flask/mindmap.svg>`_
   * - `fastapi <https://github.com/fastapi/fastapi>`_
     - Python
     - `ONBOARD.md <https://github.com/mohdzain98/gnost/blob/main/docs/gallery/fastapi/ONBOARD.md>`_
     - `analysis.json <https://github.com/mohdzain98/gnost/blob/main/docs/gallery/fastapi/analysis/analysis.json>`_
     - `mindmap.svg <https://github.com/mohdzain98/gnost/blob/main/docs/gallery/fastapi/mindmap.svg>`_
   * - `express <https://github.com/expressjs/express>`_
     - JavaScript
     - `ONBOARD.md <https://github.com/mohdzain98/gnost/blob/main/docs/gallery/express/ONBOARD.md>`_
     - `analysis.json <https://github.com/mohdzain98/gnost/blob/main/docs/gallery/express/analysis/analysis.json>`_
     - `mindmap.svg <https://github.com/mohdzain98/gnost/blob/main/docs/gallery/express/mindmap.svg>`_

Make one for your own project:

.. code-block:: bash

   npx gnost-cli onboard https://github.com/owner/repo      # any public repository
   npx gnost-cli onboard .                                   # the folder you are in

Each guide was made with the command above on the project's default branch, using the GNOST version shown at
the end of the file. The project map is the image ``gnost onboard . --inject-mindmap`` adds to a README.
