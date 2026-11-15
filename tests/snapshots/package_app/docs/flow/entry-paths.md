# Entry-based Execution Paths

These diagrams show individual execution paths starting from application entry points. Each path represents one possible flow through the system.

## Path 1 — `app/main.py`

```mermaid
flowchart LR
  app_api_v1_chat_py["app/api/v1/chat.py"]
  app_main_py["app/main.py"]
  app_services_store_py["app/services/store.py"]
  app_api_v1_chat_py --> app_services_store_py
  app_main_py --> app_api_v1_chat_py
```

**Execution chain:** app/main.py → app/api/v1/chat.py → app/services/store.py

## Path 2 — `app/main.py`

```mermaid
flowchart LR
  app_api_v1_notes_py["app/api/v1/notes.py"]
  app_main_py["app/main.py"]
  app_models_py["app/models.py"]
  app_api_v1_notes_py --> app_models_py
  app_main_py --> app_api_v1_notes_py
```

**Execution chain:** app/main.py → app/api/v1/notes.py → app/models.py

## Path 3 — `app/main.py`

```mermaid
flowchart LR
  app_api_v1___init___py["app/api/v1/__init__.py"]
  app_main_py["app/main.py"]
  app_main_py --> app_api_v1___init___py
```

**Execution chain:** app/main.py → app/api/v1/__init__.py
