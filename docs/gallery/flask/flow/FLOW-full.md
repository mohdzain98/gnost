# Full Execution Flow

```mermaid
flowchart TD
  dir_src_flask["src/flask<br/>16 files"]
  dir_examples_tutorial_flaskr["examples/tutorial/flaskr<br/>4 files"]
  dir_src_flask_sansio["src/flask/sansio<br/>3 files"]
  dir_src_flask_json["src/flask/json<br/>3 files"]
  dir_examples_celery_src_task_app["examples/celery/src/task_app<br/>3 files"]
  dir_examples_javascript_js_example["examples/javascript/js_example<br/>2 files"]
  dir_examples_celery_src_task_app -->|2| dir_src_flask
  dir_examples_javascript_js_example -->|2| dir_src_flask
  dir_examples_tutorial_flaskr -->|4| dir_src_flask
  dir_src_flask -->|3| dir_src_flask_json
  dir_src_flask ==>|9| dir_src_flask_sansio
  dir_src_flask_json -.->|2| dir_src_flask
  dir_src_flask_json -.-> dir_src_flask_sansio
  dir_src_flask_sansio ==>|14| dir_src_flask
  dir_src_flask_sansio --> dir_src_flask_json
  linkStyle 3,8 stroke:#f57c00,stroke-width:2px
  linkStyle 4,7 stroke:#d32f2f,stroke-width:3px
  linkStyle 5,6 stroke:#f57c00,stroke-width:2px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class dir_src_flask,dir_src_flask_sansio cycle
```

> Grouped by folder to stay readable: 6 folders; numbers on arrows count the file-level imports they stand for.
> Thick red arrows: circular imports that happen as modules load.
> Orange arrows (dotted when the import itself is deferred): circular dependencies that only close through an import inside a function, a type-only import or a dynamic import.

# Detail by folder

The diagram above groups files by folder. These show the files inside the biggest folders.

## `src/flask` (16 files)

```mermaid
flowchart TD
  src_flask___init___py["src/flask/__init__.py"]
  src_flask_app_py["src/flask/app.py"]
  src_flask_blueprints_py["src/flask/blueprints.py"]
  src_flask_cli_py["src/flask/cli.py"]
  src_flask_config_py["src/flask/config.py"]
  src_flask_ctx_py["src/flask/ctx.py"]
  src_flask_debughelpers_py["src/flask/debughelpers.py"]
  src_flask_globals_py["src/flask/globals.py"]
  src_flask_helpers_py["src/flask/helpers.py"]
  src_flask_logging_py["src/flask/logging.py"]
  src_flask_sessions_py["src/flask/sessions.py"]
  src_flask_signals_py["src/flask/signals.py"]
  src_flask_templating_py["src/flask/templating.py"]
  src_flask_testing_py["src/flask/testing.py"]
  src_flask_typing_py["src/flask/typing.py"]
  src_flask_wrappers_py["src/flask/wrappers.py"]
  src_flask___init___py ==> src_flask_app_py
  src_flask___init___py ==> src_flask_blueprints_py
  src_flask___init___py --> src_flask_config_py
  src_flask___init___py ==> src_flask_ctx_py
  src_flask___init___py --> src_flask_globals_py
  src_flask___init___py --> src_flask_helpers_py
  src_flask___init___py --> src_flask_signals_py
  src_flask___init___py ==> src_flask_templating_py
  src_flask___init___py ==> src_flask_wrappers_py
  src_flask_app_py ==> src_flask___init___py
  src_flask_app_py --> src_flask_cli_py
  src_flask_app_py ==> src_flask_ctx_py
  src_flask_app_py -.-> src_flask_debughelpers_py
  src_flask_app_py --> src_flask_globals_py
  src_flask_app_py --> src_flask_helpers_py
  src_flask_app_py --> src_flask_sessions_py
  src_flask_app_py --> src_flask_signals_py
  src_flask_app_py ==> src_flask_templating_py
  src_flask_app_py -.-> src_flask_testing_py
  src_flask_app_py --> src_flask_typing_py
  src_flask_app_py ==> src_flask_wrappers_py
  src_flask_blueprints_py --> src_flask_cli_py
  src_flask_blueprints_py --> src_flask_globals_py
  src_flask_blueprints_py --> src_flask_helpers_py
  src_flask_blueprints_py -.-> src_flask_wrappers_py
  src_flask_cli_py -.-> src_flask___init___py
  src_flask_cli_py -.-> src_flask_app_py
  src_flask_cli_py --> src_flask_globals_py
  src_flask_cli_py --> src_flask_helpers_py
  src_flask_ctx_py ==> src_flask___init___py
  src_flask_ctx_py -.-> src_flask_app_py
  src_flask_ctx_py --> src_flask_globals_py
  src_flask_ctx_py --> src_flask_helpers_py
  src_flask_ctx_py -.-> src_flask_sessions_py
  src_flask_ctx_py --> src_flask_signals_py
  src_flask_ctx_py --> src_flask_typing_py
  src_flask_ctx_py -.-> src_flask_wrappers_py
  src_flask_debughelpers_py --> src_flask_blueprints_py
  src_flask_debughelpers_py --> src_flask_globals_py
  src_flask_debughelpers_py -.-> src_flask_wrappers_py
  src_flask_globals_py -.-> src_flask_app_py
  src_flask_globals_py -.-> src_flask_ctx_py
  src_flask_globals_py -.-> src_flask_sessions_py
  src_flask_globals_py -.-> src_flask_wrappers_py
  src_flask_helpers_py --> src_flask_globals_py
  src_flask_helpers_py --> src_flask_signals_py
  src_flask_helpers_py -.-> src_flask_wrappers_py
  src_flask_logging_py --> src_flask_globals_py
  src_flask_sessions_py -.-> src_flask_app_py
  src_flask_sessions_py -.-> src_flask_wrappers_py
  src_flask_templating_py ==> src_flask_ctx_py
  src_flask_templating_py -.-> src_flask_debughelpers_py
  src_flask_templating_py --> src_flask_globals_py
  src_flask_templating_py --> src_flask_helpers_py
  src_flask_templating_py --> src_flask_signals_py
  src_flask_testing_py -.-> src_flask_app_py
  src_flask_testing_py --> src_flask_cli_py
  src_flask_testing_py --> src_flask_sessions_py
  src_flask_wrappers_py ==> src_flask___init___py
  src_flask_wrappers_py -.-> src_flask_debughelpers_py
  src_flask_wrappers_py --> src_flask_globals_py
  src_flask_wrappers_py --> src_flask_helpers_py
  linkStyle 0,1,3,7,8,9,11,17,20,29,50,58 stroke:#d32f2f,stroke-width:3px
  linkStyle 2,4,5,10,13,14,15,21,22,23,27,28,31,32,37,38,44,47,52,53,56,57,60,61 stroke:#f57c00,stroke-width:2px
  linkStyle 12,18,24,25,26,30,33,36,39,40,41,42,43,46,48,49,51,55,59 stroke:#f57c00,stroke-width:2px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class src_flask___init___py,src_flask_app_py,src_flask_blueprints_py,src_flask_ctx_py,src_flask_templating_py,src_flask_wrappers_py cycle
```

> Thick red arrows: circular imports that happen as modules load.
> Orange arrows (dotted when the import itself is deferred): circular dependencies that only close through an import inside a function, a type-only import or a dynamic import.

## `examples/tutorial/flaskr` (4 files)

```mermaid
flowchart TD
  examples_tutorial_flaskr___init___py["examples/tutorial/flaskr/__init__.py"]
  examples_tutorial_flaskr_auth_py["examples/tutorial/flaskr/auth.py"]
  examples_tutorial_flaskr_blog_py["examples/tutorial/flaskr/blog.py"]
  examples_tutorial_flaskr_db_py["examples/tutorial/flaskr/db.py"]
  examples_tutorial_flaskr___init___py -.-> examples_tutorial_flaskr_auth_py
  examples_tutorial_flaskr___init___py -.-> examples_tutorial_flaskr_blog_py
  examples_tutorial_flaskr___init___py -.-> examples_tutorial_flaskr_db_py
  examples_tutorial_flaskr_auth_py --> examples_tutorial_flaskr_db_py
  examples_tutorial_flaskr_blog_py --> examples_tutorial_flaskr_auth_py
  examples_tutorial_flaskr_blog_py --> examples_tutorial_flaskr_db_py
```

> Dotted arrows: imports that do not run when the module loads.

## `examples/celery/src/task_app` (3 files)

```mermaid
flowchart TD
  examples_celery_src_task_app___init___py["examples/celery/src/task_app/__init__.py"]
  examples_celery_src_task_app_tasks_py["examples/celery/src/task_app/tasks.py"]
  examples_celery_src_task_app_views_py["examples/celery/src/task_app/views.py"]
  examples_celery_src_task_app___init___py -.-> examples_celery_src_task_app_views_py
  examples_celery_src_task_app_views_py --> examples_celery_src_task_app___init___py
  examples_celery_src_task_app_views_py --> examples_celery_src_task_app_tasks_py
  linkStyle 0 stroke:#f57c00,stroke-width:2px
  linkStyle 1 stroke:#f57c00,stroke-width:2px
```

> Orange arrows (dotted when the import itself is deferred): circular dependencies that only close through an import inside a function, a type-only import or a dynamic import.

## `src/flask/json` (3 files)

```mermaid
flowchart TD
  src_flask_json___init___py["src/flask/json/__init__.py"]
  src_flask_json_provider_py["src/flask/json/provider.py"]
  src_flask_json_tag_py["src/flask/json/tag.py"]
  src_flask_json___init___py --> src_flask_json_provider_py
  src_flask_json_tag_py --> src_flask_json___init___py
  linkStyle 0,1 stroke:#f57c00,stroke-width:2px
```

> Orange arrows (dotted when the import itself is deferred): circular dependencies that only close through an import inside a function, a type-only import or a dynamic import.

## `src/flask/sansio` (3 files)

```mermaid
flowchart TD
  src_flask_sansio_app_py["src/flask/sansio/app.py"]
  src_flask_sansio_blueprints_py["src/flask/sansio/blueprints.py"]
  src_flask_sansio_scaffold_py["src/flask/sansio/scaffold.py"]
  src_flask_sansio_app_py -.-> src_flask_sansio_blueprints_py
  src_flask_sansio_app_py ==> src_flask_sansio_scaffold_py
  src_flask_sansio_blueprints_py -.-> src_flask_sansio_app_py
  src_flask_sansio_blueprints_py ==> src_flask_sansio_scaffold_py
  linkStyle 0,2 stroke:#f57c00,stroke-width:2px
  linkStyle 1,3 stroke:#d32f2f,stroke-width:3px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class src_flask_sansio_app_py,src_flask_sansio_blueprints_py,src_flask_sansio_scaffold_py cycle
```

> Thick red arrows: circular imports that happen as modules load.
> Orange arrows (dotted when the import itself is deferred): circular dependencies that only close through an import inside a function, a type-only import or a dynamic import.

## `examples/javascript/js_example` (2 files)

```mermaid
flowchart TD
  examples_javascript_js_example___init___py["examples/javascript/js_example/__init__.py"]
  examples_javascript_js_example_views_py["examples/javascript/js_example/views.py"]
  examples_javascript_js_example___init___py ==> examples_javascript_js_example_views_py
  examples_javascript_js_example_views_py ==> examples_javascript_js_example___init___py
  linkStyle 0,1 stroke:#d32f2f,stroke-width:3px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class examples_javascript_js_example___init___py,examples_javascript_js_example_views_py cycle
```

> Thick red arrows: circular imports that happen as modules load.

> ℹ️ This file renders the complete Mermaid diagram on GitHub.
> For raw Mermaid source, see [**FLOW-full.mmd**](./FLOW-full.mmd). Every file and import, ungrouped and nothing omitted: [**flow-complete.mmd**](./flow-complete.mmd)

---

<sub>Generated by [GNOST](https://gnost.readthedocs.io) 0.6.0. Try it on your own code: `uvx gnost onboard .`</sub>
