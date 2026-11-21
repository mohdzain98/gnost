# Keyword-based Execution Paths

These diagrams show execution flows related to key features, auto-detected from the project structure.

## Feature: `auth`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_tutorial_flaskr___init___py["examples/tutorial/flaskr/__init__.py"]
  examples_tutorial_flaskr_auth_py["examples/tutorial/flaskr/auth.py"]
  examples_tutorial_flaskr___init___py -.-> examples_tutorial_flaskr_auth_py
```
**Execution chain:** examples/tutorial/flaskr/__init__.py → examples/tutorial/flaskr/auth.py

### Combined Flow (All `auth` Paths)

```mermaid
flowchart LR
  examples_tutorial_flaskr___init___py["examples/tutorial/flaskr/__init__.py"]
  examples_tutorial_flaskr_auth_py["examples/tutorial/flaskr/auth.py"]
  examples_tutorial_flaskr___init___py -.-> examples_tutorial_flaskr_auth_py
```

## Feature: `celery`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_celery_src_task_app___init___py["examples/celery/src/task_app/__init__.py"]
  src_flask___init___py["src/flask/__init__.py"]
  src_flask_app_py["src/flask/app.py"]
  src_flask_blueprints_py["src/flask/blueprints.py"]
  src_flask_cli_py["src/flask/cli.py"]
  src_flask_config_py["src/flask/config.py"]
  src_flask_ctx_py["src/flask/ctx.py"]
  src_flask_debughelpers_py["src/flask/debughelpers.py"]
  src_flask_globals_py["src/flask/globals.py"]
  src_flask_helpers_py["src/flask/helpers.py"]
  src_flask_json___init___py["src/flask/json/__init__.py"]
  src_flask_json_provider_py["src/flask/json/provider.py"]
  src_flask_json_tag_py["src/flask/json/tag.py"]
  src_flask_logging_py["src/flask/logging.py"]
  src_flask_sansio_app_py["src/flask/sansio/app.py"]
  src_flask_sansio_blueprints_py["src/flask/sansio/blueprints.py"]
  src_flask_sansio_scaffold_py["src/flask/sansio/scaffold.py"]
  src_flask_sessions_py["src/flask/sessions.py"]
  src_flask_signals_py["src/flask/signals.py"]
  src_flask_templating_py["src/flask/templating.py"]
  src_flask_testing_py["src/flask/testing.py"]
  src_flask_typing_py["src/flask/typing.py"]
  src_flask_wrappers_py["src/flask/wrappers.py"]
  examples_celery_src_task_app___init___py --> src_flask___init___py
  src_flask___init___py ==> src_flask_app_py
  src_flask___init___py ==> src_flask_blueprints_py
  src_flask___init___py --> src_flask_config_py
  src_flask___init___py ==> src_flask_ctx_py
  src_flask___init___py --> src_flask_globals_py
  src_flask___init___py --> src_flask_helpers_py
  src_flask___init___py --> src_flask_json___init___py
  src_flask___init___py --> src_flask_signals_py
  src_flask___init___py ==> src_flask_templating_py
  src_flask___init___py ==> src_flask_wrappers_py
  src_flask_app_py --> src_flask_cli_py
  src_flask_app_py -.-> src_flask_debughelpers_py
  src_flask_app_py ==> src_flask_sansio_app_py
  src_flask_app_py --> src_flask_sessions_py
  src_flask_app_py -.-> src_flask_testing_py
  src_flask_app_py --> src_flask_typing_py
  src_flask_blueprints_py ==> src_flask_sansio_blueprints_py
  src_flask_blueprints_py ==> src_flask_sansio_scaffold_py
  src_flask_json___init___py --> src_flask_json_provider_py
  src_flask_sansio_app_py --> src_flask_logging_py
  src_flask_sessions_py --> src_flask_json_tag_py
  linkStyle 1,2,4,9,10,13,17,18 stroke:#d32f2f,stroke-width:3px
  linkStyle 3,5,6,7,11,14,19,20,21 stroke:#f57c00,stroke-width:2px
  linkStyle 12,15 stroke:#f57c00,stroke-width:2px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class src_flask___init___py,src_flask_app_py,src_flask_blueprints_py,src_flask_ctx_py,src_flask_sansio_app_py,src_flask_sansio_blueprints_py,src_flask_sansio_scaffold_py,src_flask_templating_py,src_flask_wrappers_py cycle
```
**Execution chain:** examples/celery/src/task_app/__init__.py → src/flask/__init__.py → src/flask/app.py → src/flask/sansio/app.py → src/flask/logging.py

#### Path Group 2

```mermaid
flowchart LR
  examples_celery_src_task_app___init___py["examples/celery/src/task_app/__init__.py"]
  examples_celery_src_task_app_tasks_py["examples/celery/src/task_app/tasks.py"]
  examples_celery_src_task_app_views_py["examples/celery/src/task_app/views.py"]
  examples_celery_src_task_app___init___py -.-> examples_celery_src_task_app_views_py
  examples_celery_src_task_app_views_py --> examples_celery_src_task_app_tasks_py
  linkStyle 0 stroke:#f57c00,stroke-width:2px
```
**Execution chain:** examples/celery/src/task_app/__init__.py → examples/celery/src/task_app/views.py → examples/celery/src/task_app/tasks.py

### Combined Flow (All `celery` Paths)

```mermaid
flowchart LR
  examples_celery_src_task_app___init___py["examples/celery/src/task_app/__init__.py"]
  examples_celery_src_task_app_tasks_py["examples/celery/src/task_app/tasks.py"]
  examples_celery_src_task_app_views_py["examples/celery/src/task_app/views.py"]
  src_flask___init___py["src/flask/__init__.py"]
  src_flask_app_py["src/flask/app.py"]
  src_flask_blueprints_py["src/flask/blueprints.py"]
  src_flask_cli_py["src/flask/cli.py"]
  src_flask_config_py["src/flask/config.py"]
  src_flask_ctx_py["src/flask/ctx.py"]
  src_flask_debughelpers_py["src/flask/debughelpers.py"]
  src_flask_globals_py["src/flask/globals.py"]
  src_flask_helpers_py["src/flask/helpers.py"]
  src_flask_json___init___py["src/flask/json/__init__.py"]
  src_flask_json_provider_py["src/flask/json/provider.py"]
  src_flask_json_tag_py["src/flask/json/tag.py"]
  src_flask_logging_py["src/flask/logging.py"]
  src_flask_sansio_app_py["src/flask/sansio/app.py"]
  src_flask_sansio_blueprints_py["src/flask/sansio/blueprints.py"]
  src_flask_sansio_scaffold_py["src/flask/sansio/scaffold.py"]
  src_flask_sessions_py["src/flask/sessions.py"]
  src_flask_signals_py["src/flask/signals.py"]
  src_flask_templating_py["src/flask/templating.py"]
  src_flask_testing_py["src/flask/testing.py"]
  src_flask_typing_py["src/flask/typing.py"]
  src_flask_wrappers_py["src/flask/wrappers.py"]
  examples_celery_src_task_app___init___py -.-> examples_celery_src_task_app_views_py
  examples_celery_src_task_app___init___py --> src_flask___init___py
  examples_celery_src_task_app_views_py --> examples_celery_src_task_app_tasks_py
  src_flask___init___py ==> src_flask_app_py
  src_flask___init___py ==> src_flask_blueprints_py
  src_flask___init___py --> src_flask_config_py
  src_flask___init___py ==> src_flask_ctx_py
  src_flask___init___py --> src_flask_globals_py
  src_flask___init___py --> src_flask_helpers_py
  src_flask___init___py --> src_flask_json___init___py
  src_flask___init___py --> src_flask_signals_py
  src_flask___init___py ==> src_flask_templating_py
  src_flask___init___py ==> src_flask_wrappers_py
  src_flask_app_py --> src_flask_cli_py
  src_flask_app_py -.-> src_flask_debughelpers_py
  src_flask_app_py ==> src_flask_sansio_app_py
  src_flask_app_py --> src_flask_sessions_py
  src_flask_app_py -.-> src_flask_testing_py
  src_flask_app_py --> src_flask_typing_py
  src_flask_blueprints_py ==> src_flask_sansio_blueprints_py
  src_flask_blueprints_py ==> src_flask_sansio_scaffold_py
  src_flask_json___init___py --> src_flask_json_provider_py
  src_flask_sansio_app_py --> src_flask_logging_py
  src_flask_sessions_py --> src_flask_json_tag_py
  linkStyle 0,14,17 stroke:#f57c00,stroke-width:2px
  linkStyle 3,4,6,11,12,15,19,20 stroke:#d32f2f,stroke-width:3px
  linkStyle 5,7,8,9,13,16,21,22,23 stroke:#f57c00,stroke-width:2px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class src_flask___init___py,src_flask_app_py,src_flask_blueprints_py,src_flask_ctx_py,src_flask_sansio_app_py,src_flask_sansio_blueprints_py,src_flask_sansio_scaffold_py,src_flask_templating_py,src_flask_wrappers_py cycle
```

## Feature: `flaskr`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_tutorial_flaskr___init___py["examples/tutorial/flaskr/__init__.py"]
  src_flask___init___py["src/flask/__init__.py"]
  src_flask_app_py["src/flask/app.py"]
  src_flask_blueprints_py["src/flask/blueprints.py"]
  src_flask_cli_py["src/flask/cli.py"]
  src_flask_config_py["src/flask/config.py"]
  src_flask_ctx_py["src/flask/ctx.py"]
  src_flask_debughelpers_py["src/flask/debughelpers.py"]
  src_flask_globals_py["src/flask/globals.py"]
  src_flask_helpers_py["src/flask/helpers.py"]
  src_flask_json___init___py["src/flask/json/__init__.py"]
  src_flask_json_provider_py["src/flask/json/provider.py"]
  src_flask_json_tag_py["src/flask/json/tag.py"]
  src_flask_logging_py["src/flask/logging.py"]
  src_flask_sansio_app_py["src/flask/sansio/app.py"]
  src_flask_sansio_blueprints_py["src/flask/sansio/blueprints.py"]
  src_flask_sansio_scaffold_py["src/flask/sansio/scaffold.py"]
  src_flask_sessions_py["src/flask/sessions.py"]
  src_flask_signals_py["src/flask/signals.py"]
  src_flask_templating_py["src/flask/templating.py"]
  src_flask_testing_py["src/flask/testing.py"]
  src_flask_typing_py["src/flask/typing.py"]
  src_flask_wrappers_py["src/flask/wrappers.py"]
  examples_tutorial_flaskr___init___py --> src_flask___init___py
  src_flask___init___py ==> src_flask_app_py
  src_flask___init___py ==> src_flask_blueprints_py
  src_flask___init___py --> src_flask_config_py
  src_flask___init___py ==> src_flask_ctx_py
  src_flask___init___py --> src_flask_globals_py
  src_flask___init___py --> src_flask_helpers_py
  src_flask___init___py --> src_flask_json___init___py
  src_flask___init___py --> src_flask_signals_py
  src_flask___init___py ==> src_flask_templating_py
  src_flask___init___py ==> src_flask_wrappers_py
  src_flask_app_py --> src_flask_cli_py
  src_flask_app_py -.-> src_flask_debughelpers_py
  src_flask_app_py ==> src_flask_sansio_app_py
  src_flask_app_py --> src_flask_sessions_py
  src_flask_app_py -.-> src_flask_testing_py
  src_flask_app_py --> src_flask_typing_py
  src_flask_blueprints_py ==> src_flask_sansio_blueprints_py
  src_flask_blueprints_py ==> src_flask_sansio_scaffold_py
  src_flask_json___init___py --> src_flask_json_provider_py
  src_flask_sansio_app_py --> src_flask_logging_py
  src_flask_sessions_py --> src_flask_json_tag_py
  linkStyle 1,2,4,9,10,13,17,18 stroke:#d32f2f,stroke-width:3px
  linkStyle 3,5,6,7,11,14,19,20,21 stroke:#f57c00,stroke-width:2px
  linkStyle 12,15 stroke:#f57c00,stroke-width:2px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class src_flask___init___py,src_flask_app_py,src_flask_blueprints_py,src_flask_ctx_py,src_flask_sansio_app_py,src_flask_sansio_blueprints_py,src_flask_sansio_scaffold_py,src_flask_templating_py,src_flask_wrappers_py cycle
```
**Execution chain:** examples/tutorial/flaskr/__init__.py → src/flask/__init__.py → src/flask/app.py → src/flask/sansio/app.py → src/flask/logging.py

#### Path Group 2

```mermaid
flowchart LR
  examples_tutorial_flaskr___init___py["examples/tutorial/flaskr/__init__.py"]
  examples_tutorial_flaskr_auth_py["examples/tutorial/flaskr/auth.py"]
  examples_tutorial_flaskr___init___py -.-> examples_tutorial_flaskr_auth_py
```
**Execution chain:** examples/tutorial/flaskr/__init__.py → examples/tutorial/flaskr/auth.py

### Combined Flow (All `flaskr` Paths)

```mermaid
flowchart LR
  examples_tutorial_flaskr___init___py["examples/tutorial/flaskr/__init__.py"]
  examples_tutorial_flaskr_auth_py["examples/tutorial/flaskr/auth.py"]
  examples_tutorial_flaskr_blog_py["examples/tutorial/flaskr/blog.py"]
  examples_tutorial_flaskr_db_py["examples/tutorial/flaskr/db.py"]
  src_flask___init___py["src/flask/__init__.py"]
  src_flask_app_py["src/flask/app.py"]
  src_flask_blueprints_py["src/flask/blueprints.py"]
  src_flask_cli_py["src/flask/cli.py"]
  src_flask_config_py["src/flask/config.py"]
  src_flask_ctx_py["src/flask/ctx.py"]
  src_flask_debughelpers_py["src/flask/debughelpers.py"]
  src_flask_globals_py["src/flask/globals.py"]
  src_flask_helpers_py["src/flask/helpers.py"]
  src_flask_json___init___py["src/flask/json/__init__.py"]
  src_flask_json_provider_py["src/flask/json/provider.py"]
  src_flask_json_tag_py["src/flask/json/tag.py"]
  src_flask_logging_py["src/flask/logging.py"]
  src_flask_sansio_app_py["src/flask/sansio/app.py"]
  src_flask_sansio_blueprints_py["src/flask/sansio/blueprints.py"]
  src_flask_sansio_scaffold_py["src/flask/sansio/scaffold.py"]
  src_flask_sessions_py["src/flask/sessions.py"]
  src_flask_signals_py["src/flask/signals.py"]
  src_flask_templating_py["src/flask/templating.py"]
  src_flask_testing_py["src/flask/testing.py"]
  src_flask_typing_py["src/flask/typing.py"]
  src_flask_wrappers_py["src/flask/wrappers.py"]
  examples_tutorial_flaskr___init___py -.-> examples_tutorial_flaskr_auth_py
  examples_tutorial_flaskr___init___py -.-> examples_tutorial_flaskr_blog_py
  examples_tutorial_flaskr___init___py -.-> examples_tutorial_flaskr_db_py
  examples_tutorial_flaskr___init___py --> src_flask___init___py
  src_flask___init___py ==> src_flask_app_py
  src_flask___init___py ==> src_flask_blueprints_py
  src_flask___init___py --> src_flask_config_py
  src_flask___init___py ==> src_flask_ctx_py
  src_flask___init___py --> src_flask_globals_py
  src_flask___init___py --> src_flask_helpers_py
  src_flask___init___py --> src_flask_json___init___py
  src_flask___init___py --> src_flask_signals_py
  src_flask___init___py ==> src_flask_templating_py
  src_flask___init___py ==> src_flask_wrappers_py
  src_flask_app_py --> src_flask_cli_py
  src_flask_app_py -.-> src_flask_debughelpers_py
  src_flask_app_py ==> src_flask_sansio_app_py
  src_flask_app_py --> src_flask_sessions_py
  src_flask_app_py -.-> src_flask_testing_py
  src_flask_app_py --> src_flask_typing_py
  src_flask_blueprints_py ==> src_flask_sansio_blueprints_py
  src_flask_blueprints_py ==> src_flask_sansio_scaffold_py
  src_flask_json___init___py --> src_flask_json_provider_py
  src_flask_sansio_app_py --> src_flask_logging_py
  src_flask_sessions_py --> src_flask_json_tag_py
  linkStyle 4,5,7,12,13,16,20,21 stroke:#d32f2f,stroke-width:3px
  linkStyle 6,8,9,10,14,17,22,23,24 stroke:#f57c00,stroke-width:2px
  linkStyle 15,18 stroke:#f57c00,stroke-width:2px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class src_flask___init___py,src_flask_app_py,src_flask_blueprints_py,src_flask_ctx_py,src_flask_sansio_app_py,src_flask_sansio_blueprints_py,src_flask_sansio_scaffold_py,src_flask_templating_py,src_flask_wrappers_py cycle
```

## Feature: `javascript`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_javascript_js_example___init___py["examples/javascript/js_example/__init__.py"]
  src_flask___init___py["src/flask/__init__.py"]
  src_flask_app_py["src/flask/app.py"]
  src_flask_blueprints_py["src/flask/blueprints.py"]
  src_flask_cli_py["src/flask/cli.py"]
  src_flask_config_py["src/flask/config.py"]
  src_flask_ctx_py["src/flask/ctx.py"]
  src_flask_debughelpers_py["src/flask/debughelpers.py"]
  src_flask_globals_py["src/flask/globals.py"]
  src_flask_helpers_py["src/flask/helpers.py"]
  src_flask_json___init___py["src/flask/json/__init__.py"]
  src_flask_json_provider_py["src/flask/json/provider.py"]
  src_flask_json_tag_py["src/flask/json/tag.py"]
  src_flask_logging_py["src/flask/logging.py"]
  src_flask_sansio_app_py["src/flask/sansio/app.py"]
  src_flask_sansio_blueprints_py["src/flask/sansio/blueprints.py"]
  src_flask_sansio_scaffold_py["src/flask/sansio/scaffold.py"]
  src_flask_sessions_py["src/flask/sessions.py"]
  src_flask_signals_py["src/flask/signals.py"]
  src_flask_templating_py["src/flask/templating.py"]
  src_flask_testing_py["src/flask/testing.py"]
  src_flask_typing_py["src/flask/typing.py"]
  src_flask_wrappers_py["src/flask/wrappers.py"]
  examples_javascript_js_example___init___py --> src_flask___init___py
  src_flask___init___py ==> src_flask_app_py
  src_flask___init___py ==> src_flask_blueprints_py
  src_flask___init___py --> src_flask_config_py
  src_flask___init___py ==> src_flask_ctx_py
  src_flask___init___py --> src_flask_globals_py
  src_flask___init___py --> src_flask_helpers_py
  src_flask___init___py --> src_flask_json___init___py
  src_flask___init___py --> src_flask_signals_py
  src_flask___init___py ==> src_flask_templating_py
  src_flask___init___py ==> src_flask_wrappers_py
  src_flask_app_py --> src_flask_cli_py
  src_flask_app_py -.-> src_flask_debughelpers_py
  src_flask_app_py ==> src_flask_sansio_app_py
  src_flask_app_py --> src_flask_sessions_py
  src_flask_app_py -.-> src_flask_testing_py
  src_flask_app_py --> src_flask_typing_py
  src_flask_blueprints_py ==> src_flask_sansio_blueprints_py
  src_flask_blueprints_py ==> src_flask_sansio_scaffold_py
  src_flask_json___init___py --> src_flask_json_provider_py
  src_flask_sansio_app_py --> src_flask_logging_py
  src_flask_sessions_py --> src_flask_json_tag_py
  linkStyle 1,2,4,9,10,13,17,18 stroke:#d32f2f,stroke-width:3px
  linkStyle 3,5,6,7,11,14,19,20,21 stroke:#f57c00,stroke-width:2px
  linkStyle 12,15 stroke:#f57c00,stroke-width:2px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class src_flask___init___py,src_flask_app_py,src_flask_blueprints_py,src_flask_ctx_py,src_flask_sansio_app_py,src_flask_sansio_blueprints_py,src_flask_sansio_scaffold_py,src_flask_templating_py,src_flask_wrappers_py cycle
```
**Execution chain:** examples/javascript/js_example/__init__.py → src/flask/__init__.py → src/flask/app.py → src/flask/sansio/app.py → src/flask/logging.py

#### Path Group 2

```mermaid
flowchart LR
  examples_javascript_js_example___init___py["examples/javascript/js_example/__init__.py"]
  examples_javascript_js_example_views_py["examples/javascript/js_example/views.py"]
  examples_javascript_js_example___init___py ==> examples_javascript_js_example_views_py
  linkStyle 0 stroke:#d32f2f,stroke-width:3px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class examples_javascript_js_example___init___py,examples_javascript_js_example_views_py cycle
```
**Execution chain:** examples/javascript/js_example/__init__.py → examples/javascript/js_example/views.py

### Combined Flow (All `javascript` Paths)

```mermaid
flowchart LR
  examples_javascript_js_example___init___py["examples/javascript/js_example/__init__.py"]
  examples_javascript_js_example_views_py["examples/javascript/js_example/views.py"]
  src_flask___init___py["src/flask/__init__.py"]
  src_flask_app_py["src/flask/app.py"]
  src_flask_blueprints_py["src/flask/blueprints.py"]
  src_flask_cli_py["src/flask/cli.py"]
  src_flask_config_py["src/flask/config.py"]
  src_flask_ctx_py["src/flask/ctx.py"]
  src_flask_debughelpers_py["src/flask/debughelpers.py"]
  src_flask_globals_py["src/flask/globals.py"]
  src_flask_helpers_py["src/flask/helpers.py"]
  src_flask_json___init___py["src/flask/json/__init__.py"]
  src_flask_json_provider_py["src/flask/json/provider.py"]
  src_flask_json_tag_py["src/flask/json/tag.py"]
  src_flask_logging_py["src/flask/logging.py"]
  src_flask_sansio_app_py["src/flask/sansio/app.py"]
  src_flask_sansio_blueprints_py["src/flask/sansio/blueprints.py"]
  src_flask_sansio_scaffold_py["src/flask/sansio/scaffold.py"]
  src_flask_sessions_py["src/flask/sessions.py"]
  src_flask_signals_py["src/flask/signals.py"]
  src_flask_templating_py["src/flask/templating.py"]
  src_flask_testing_py["src/flask/testing.py"]
  src_flask_typing_py["src/flask/typing.py"]
  src_flask_wrappers_py["src/flask/wrappers.py"]
  examples_javascript_js_example___init___py ==> examples_javascript_js_example_views_py
  examples_javascript_js_example___init___py --> src_flask___init___py
  src_flask___init___py ==> src_flask_app_py
  src_flask___init___py ==> src_flask_blueprints_py
  src_flask___init___py --> src_flask_config_py
  src_flask___init___py ==> src_flask_ctx_py
  src_flask___init___py --> src_flask_globals_py
  src_flask___init___py --> src_flask_helpers_py
  src_flask___init___py --> src_flask_json___init___py
  src_flask___init___py --> src_flask_signals_py
  src_flask___init___py ==> src_flask_templating_py
  src_flask___init___py ==> src_flask_wrappers_py
  src_flask_app_py --> src_flask_cli_py
  src_flask_app_py -.-> src_flask_debughelpers_py
  src_flask_app_py ==> src_flask_sansio_app_py
  src_flask_app_py --> src_flask_sessions_py
  src_flask_app_py -.-> src_flask_testing_py
  src_flask_app_py --> src_flask_typing_py
  src_flask_blueprints_py ==> src_flask_sansio_blueprints_py
  src_flask_blueprints_py ==> src_flask_sansio_scaffold_py
  src_flask_json___init___py --> src_flask_json_provider_py
  src_flask_sansio_app_py --> src_flask_logging_py
  src_flask_sessions_py --> src_flask_json_tag_py
  linkStyle 0,2,3,5,10,11,14,18,19 stroke:#d32f2f,stroke-width:3px
  linkStyle 4,6,7,8,12,15,20,21,22 stroke:#f57c00,stroke-width:2px
  linkStyle 13,16 stroke:#f57c00,stroke-width:2px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class examples_javascript_js_example___init___py,examples_javascript_js_example_views_py,src_flask___init___py,src_flask_app_py,src_flask_blueprints_py,src_flask_ctx_py,src_flask_sansio_app_py,src_flask_sansio_blueprints_py,src_flask_sansio_scaffold_py,src_flask_templating_py,src_flask_wrappers_py cycle
```

## Feature: `js_example`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_javascript_js_example___init___py["examples/javascript/js_example/__init__.py"]
  src_flask___init___py["src/flask/__init__.py"]
  src_flask_app_py["src/flask/app.py"]
  src_flask_blueprints_py["src/flask/blueprints.py"]
  src_flask_cli_py["src/flask/cli.py"]
  src_flask_config_py["src/flask/config.py"]
  src_flask_ctx_py["src/flask/ctx.py"]
  src_flask_debughelpers_py["src/flask/debughelpers.py"]
  src_flask_globals_py["src/flask/globals.py"]
  src_flask_helpers_py["src/flask/helpers.py"]
  src_flask_json___init___py["src/flask/json/__init__.py"]
  src_flask_json_provider_py["src/flask/json/provider.py"]
  src_flask_json_tag_py["src/flask/json/tag.py"]
  src_flask_logging_py["src/flask/logging.py"]
  src_flask_sansio_app_py["src/flask/sansio/app.py"]
  src_flask_sansio_blueprints_py["src/flask/sansio/blueprints.py"]
  src_flask_sansio_scaffold_py["src/flask/sansio/scaffold.py"]
  src_flask_sessions_py["src/flask/sessions.py"]
  src_flask_signals_py["src/flask/signals.py"]
  src_flask_templating_py["src/flask/templating.py"]
  src_flask_testing_py["src/flask/testing.py"]
  src_flask_typing_py["src/flask/typing.py"]
  src_flask_wrappers_py["src/flask/wrappers.py"]
  examples_javascript_js_example___init___py --> src_flask___init___py
  src_flask___init___py ==> src_flask_app_py
  src_flask___init___py ==> src_flask_blueprints_py
  src_flask___init___py --> src_flask_config_py
  src_flask___init___py ==> src_flask_ctx_py
  src_flask___init___py --> src_flask_globals_py
  src_flask___init___py --> src_flask_helpers_py
  src_flask___init___py --> src_flask_json___init___py
  src_flask___init___py --> src_flask_signals_py
  src_flask___init___py ==> src_flask_templating_py
  src_flask___init___py ==> src_flask_wrappers_py
  src_flask_app_py --> src_flask_cli_py
  src_flask_app_py -.-> src_flask_debughelpers_py
  src_flask_app_py ==> src_flask_sansio_app_py
  src_flask_app_py --> src_flask_sessions_py
  src_flask_app_py -.-> src_flask_testing_py
  src_flask_app_py --> src_flask_typing_py
  src_flask_blueprints_py ==> src_flask_sansio_blueprints_py
  src_flask_blueprints_py ==> src_flask_sansio_scaffold_py
  src_flask_json___init___py --> src_flask_json_provider_py
  src_flask_sansio_app_py --> src_flask_logging_py
  src_flask_sessions_py --> src_flask_json_tag_py
  linkStyle 1,2,4,9,10,13,17,18 stroke:#d32f2f,stroke-width:3px
  linkStyle 3,5,6,7,11,14,19,20,21 stroke:#f57c00,stroke-width:2px
  linkStyle 12,15 stroke:#f57c00,stroke-width:2px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class src_flask___init___py,src_flask_app_py,src_flask_blueprints_py,src_flask_ctx_py,src_flask_sansio_app_py,src_flask_sansio_blueprints_py,src_flask_sansio_scaffold_py,src_flask_templating_py,src_flask_wrappers_py cycle
```
**Execution chain:** examples/javascript/js_example/__init__.py → src/flask/__init__.py → src/flask/app.py → src/flask/sansio/app.py → src/flask/logging.py

#### Path Group 2

```mermaid
flowchart LR
  examples_javascript_js_example___init___py["examples/javascript/js_example/__init__.py"]
  examples_javascript_js_example_views_py["examples/javascript/js_example/views.py"]
  examples_javascript_js_example___init___py ==> examples_javascript_js_example_views_py
  linkStyle 0 stroke:#d32f2f,stroke-width:3px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class examples_javascript_js_example___init___py,examples_javascript_js_example_views_py cycle
```
**Execution chain:** examples/javascript/js_example/__init__.py → examples/javascript/js_example/views.py

### Combined Flow (All `js_example` Paths)

```mermaid
flowchart LR
  examples_javascript_js_example___init___py["examples/javascript/js_example/__init__.py"]
  examples_javascript_js_example_views_py["examples/javascript/js_example/views.py"]
  src_flask___init___py["src/flask/__init__.py"]
  src_flask_app_py["src/flask/app.py"]
  src_flask_blueprints_py["src/flask/blueprints.py"]
  src_flask_cli_py["src/flask/cli.py"]
  src_flask_config_py["src/flask/config.py"]
  src_flask_ctx_py["src/flask/ctx.py"]
  src_flask_debughelpers_py["src/flask/debughelpers.py"]
  src_flask_globals_py["src/flask/globals.py"]
  src_flask_helpers_py["src/flask/helpers.py"]
  src_flask_json___init___py["src/flask/json/__init__.py"]
  src_flask_json_provider_py["src/flask/json/provider.py"]
  src_flask_json_tag_py["src/flask/json/tag.py"]
  src_flask_logging_py["src/flask/logging.py"]
  src_flask_sansio_app_py["src/flask/sansio/app.py"]
  src_flask_sansio_blueprints_py["src/flask/sansio/blueprints.py"]
  src_flask_sansio_scaffold_py["src/flask/sansio/scaffold.py"]
  src_flask_sessions_py["src/flask/sessions.py"]
  src_flask_signals_py["src/flask/signals.py"]
  src_flask_templating_py["src/flask/templating.py"]
  src_flask_testing_py["src/flask/testing.py"]
  src_flask_typing_py["src/flask/typing.py"]
  src_flask_wrappers_py["src/flask/wrappers.py"]
  examples_javascript_js_example___init___py ==> examples_javascript_js_example_views_py
  examples_javascript_js_example___init___py --> src_flask___init___py
  src_flask___init___py ==> src_flask_app_py
  src_flask___init___py ==> src_flask_blueprints_py
  src_flask___init___py --> src_flask_config_py
  src_flask___init___py ==> src_flask_ctx_py
  src_flask___init___py --> src_flask_globals_py
  src_flask___init___py --> src_flask_helpers_py
  src_flask___init___py --> src_flask_json___init___py
  src_flask___init___py --> src_flask_signals_py
  src_flask___init___py ==> src_flask_templating_py
  src_flask___init___py ==> src_flask_wrappers_py
  src_flask_app_py --> src_flask_cli_py
  src_flask_app_py -.-> src_flask_debughelpers_py
  src_flask_app_py ==> src_flask_sansio_app_py
  src_flask_app_py --> src_flask_sessions_py
  src_flask_app_py -.-> src_flask_testing_py
  src_flask_app_py --> src_flask_typing_py
  src_flask_blueprints_py ==> src_flask_sansio_blueprints_py
  src_flask_blueprints_py ==> src_flask_sansio_scaffold_py
  src_flask_json___init___py --> src_flask_json_provider_py
  src_flask_sansio_app_py --> src_flask_logging_py
  src_flask_sessions_py --> src_flask_json_tag_py
  linkStyle 0,2,3,5,10,11,14,18,19 stroke:#d32f2f,stroke-width:3px
  linkStyle 4,6,7,8,12,15,20,21,22 stroke:#f57c00,stroke-width:2px
  linkStyle 13,16 stroke:#f57c00,stroke-width:2px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class examples_javascript_js_example___init___py,examples_javascript_js_example_views_py,src_flask___init___py,src_flask_app_py,src_flask_blueprints_py,src_flask_ctx_py,src_flask_sansio_app_py,src_flask_sansio_blueprints_py,src_flask_sansio_scaffold_py,src_flask_templating_py,src_flask_wrappers_py cycle
```

## Feature: `tutorial`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  examples_tutorial_flaskr___init___py["examples/tutorial/flaskr/__init__.py"]
  src_flask___init___py["src/flask/__init__.py"]
  src_flask_app_py["src/flask/app.py"]
  src_flask_blueprints_py["src/flask/blueprints.py"]
  src_flask_cli_py["src/flask/cli.py"]
  src_flask_config_py["src/flask/config.py"]
  src_flask_ctx_py["src/flask/ctx.py"]
  src_flask_debughelpers_py["src/flask/debughelpers.py"]
  src_flask_globals_py["src/flask/globals.py"]
  src_flask_helpers_py["src/flask/helpers.py"]
  src_flask_json___init___py["src/flask/json/__init__.py"]
  src_flask_json_provider_py["src/flask/json/provider.py"]
  src_flask_json_tag_py["src/flask/json/tag.py"]
  src_flask_logging_py["src/flask/logging.py"]
  src_flask_sansio_app_py["src/flask/sansio/app.py"]
  src_flask_sansio_blueprints_py["src/flask/sansio/blueprints.py"]
  src_flask_sansio_scaffold_py["src/flask/sansio/scaffold.py"]
  src_flask_sessions_py["src/flask/sessions.py"]
  src_flask_signals_py["src/flask/signals.py"]
  src_flask_templating_py["src/flask/templating.py"]
  src_flask_testing_py["src/flask/testing.py"]
  src_flask_typing_py["src/flask/typing.py"]
  src_flask_wrappers_py["src/flask/wrappers.py"]
  examples_tutorial_flaskr___init___py --> src_flask___init___py
  src_flask___init___py ==> src_flask_app_py
  src_flask___init___py ==> src_flask_blueprints_py
  src_flask___init___py --> src_flask_config_py
  src_flask___init___py ==> src_flask_ctx_py
  src_flask___init___py --> src_flask_globals_py
  src_flask___init___py --> src_flask_helpers_py
  src_flask___init___py --> src_flask_json___init___py
  src_flask___init___py --> src_flask_signals_py
  src_flask___init___py ==> src_flask_templating_py
  src_flask___init___py ==> src_flask_wrappers_py
  src_flask_app_py --> src_flask_cli_py
  src_flask_app_py -.-> src_flask_debughelpers_py
  src_flask_app_py ==> src_flask_sansio_app_py
  src_flask_app_py --> src_flask_sessions_py
  src_flask_app_py -.-> src_flask_testing_py
  src_flask_app_py --> src_flask_typing_py
  src_flask_blueprints_py ==> src_flask_sansio_blueprints_py
  src_flask_blueprints_py ==> src_flask_sansio_scaffold_py
  src_flask_json___init___py --> src_flask_json_provider_py
  src_flask_sansio_app_py --> src_flask_logging_py
  src_flask_sessions_py --> src_flask_json_tag_py
  linkStyle 1,2,4,9,10,13,17,18 stroke:#d32f2f,stroke-width:3px
  linkStyle 3,5,6,7,11,14,19,20,21 stroke:#f57c00,stroke-width:2px
  linkStyle 12,15 stroke:#f57c00,stroke-width:2px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class src_flask___init___py,src_flask_app_py,src_flask_blueprints_py,src_flask_ctx_py,src_flask_sansio_app_py,src_flask_sansio_blueprints_py,src_flask_sansio_scaffold_py,src_flask_templating_py,src_flask_wrappers_py cycle
```
**Execution chain:** examples/tutorial/flaskr/__init__.py → src/flask/__init__.py → src/flask/app.py → src/flask/sansio/app.py → src/flask/logging.py

#### Path Group 2

```mermaid
flowchart LR
  examples_tutorial_flaskr___init___py["examples/tutorial/flaskr/__init__.py"]
  examples_tutorial_flaskr_auth_py["examples/tutorial/flaskr/auth.py"]
  examples_tutorial_flaskr___init___py -.-> examples_tutorial_flaskr_auth_py
```
**Execution chain:** examples/tutorial/flaskr/__init__.py → examples/tutorial/flaskr/auth.py

### Combined Flow (All `tutorial` Paths)

```mermaid
flowchart LR
  examples_tutorial_flaskr___init___py["examples/tutorial/flaskr/__init__.py"]
  examples_tutorial_flaskr_auth_py["examples/tutorial/flaskr/auth.py"]
  examples_tutorial_flaskr_blog_py["examples/tutorial/flaskr/blog.py"]
  examples_tutorial_flaskr_db_py["examples/tutorial/flaskr/db.py"]
  src_flask___init___py["src/flask/__init__.py"]
  src_flask_app_py["src/flask/app.py"]
  src_flask_blueprints_py["src/flask/blueprints.py"]
  src_flask_cli_py["src/flask/cli.py"]
  src_flask_config_py["src/flask/config.py"]
  src_flask_ctx_py["src/flask/ctx.py"]
  src_flask_debughelpers_py["src/flask/debughelpers.py"]
  src_flask_globals_py["src/flask/globals.py"]
  src_flask_helpers_py["src/flask/helpers.py"]
  src_flask_json___init___py["src/flask/json/__init__.py"]
  src_flask_json_provider_py["src/flask/json/provider.py"]
  src_flask_json_tag_py["src/flask/json/tag.py"]
  src_flask_logging_py["src/flask/logging.py"]
  src_flask_sansio_app_py["src/flask/sansio/app.py"]
  src_flask_sansio_blueprints_py["src/flask/sansio/blueprints.py"]
  src_flask_sansio_scaffold_py["src/flask/sansio/scaffold.py"]
  src_flask_sessions_py["src/flask/sessions.py"]
  src_flask_signals_py["src/flask/signals.py"]
  src_flask_templating_py["src/flask/templating.py"]
  src_flask_testing_py["src/flask/testing.py"]
  src_flask_typing_py["src/flask/typing.py"]
  src_flask_wrappers_py["src/flask/wrappers.py"]
  examples_tutorial_flaskr___init___py -.-> examples_tutorial_flaskr_auth_py
  examples_tutorial_flaskr___init___py -.-> examples_tutorial_flaskr_blog_py
  examples_tutorial_flaskr___init___py -.-> examples_tutorial_flaskr_db_py
  examples_tutorial_flaskr___init___py --> src_flask___init___py
  src_flask___init___py ==> src_flask_app_py
  src_flask___init___py ==> src_flask_blueprints_py
  src_flask___init___py --> src_flask_config_py
  src_flask___init___py ==> src_flask_ctx_py
  src_flask___init___py --> src_flask_globals_py
  src_flask___init___py --> src_flask_helpers_py
  src_flask___init___py --> src_flask_json___init___py
  src_flask___init___py --> src_flask_signals_py
  src_flask___init___py ==> src_flask_templating_py
  src_flask___init___py ==> src_flask_wrappers_py
  src_flask_app_py --> src_flask_cli_py
  src_flask_app_py -.-> src_flask_debughelpers_py
  src_flask_app_py ==> src_flask_sansio_app_py
  src_flask_app_py --> src_flask_sessions_py
  src_flask_app_py -.-> src_flask_testing_py
  src_flask_app_py --> src_flask_typing_py
  src_flask_blueprints_py ==> src_flask_sansio_blueprints_py
  src_flask_blueprints_py ==> src_flask_sansio_scaffold_py
  src_flask_json___init___py --> src_flask_json_provider_py
  src_flask_sansio_app_py --> src_flask_logging_py
  src_flask_sessions_py --> src_flask_json_tag_py
  linkStyle 4,5,7,12,13,16,20,21 stroke:#d32f2f,stroke-width:3px
  linkStyle 6,8,9,10,14,17,22,23,24 stroke:#f57c00,stroke-width:2px
  linkStyle 15,18 stroke:#f57c00,stroke-width:2px
  classDef cycle stroke:#d32f2f,stroke-width:3px
  class src_flask___init___py,src_flask_app_py,src_flask_blueprints_py,src_flask_ctx_py,src_flask_sansio_app_py,src_flask_sansio_blueprints_py,src_flask_sansio_scaffold_py,src_flask_templating_py,src_flask_wrappers_py cycle
```

---

<sub>Generated by [GNOST](https://gnost.readthedocs.io) 0.6.0. Try it on your own code: `uvx gnost onboard .`</sub>
