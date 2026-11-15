# Keyword-based Execution Paths

These diagrams show execution flows related to key features, auto-detected from the project structure.

## Feature: `app`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  app_services_db_py["app/services/db.py"]
  app_services_users_py["app/services/users.py"]
  main_py["main.py"]
  app_services_users_py --> app_services_db_py
  main_py --> app_services_users_py
```
**Execution chain:** main.py → app/services/users.py → app/services/db.py

#### Path Group 2

```mermaid
flowchart LR
  app_api_py["app/api.py"]
  main_py["main.py"]
  main_py --> app_api_py
```
**Execution chain:** main.py → app/api.py

### Combined Flow (All `app` Paths)

```mermaid
flowchart LR
  app_api_py["app/api.py"]
  app_services_db_py["app/services/db.py"]
  app_services_users_py["app/services/users.py"]
  main_py["main.py"]
  app_services_users_py --> app_services_db_py
  main_py --> app_api_py
  main_py --> app_services_users_py
```

## Feature: `services`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  app_services_db_py["app/services/db.py"]
  app_services_users_py["app/services/users.py"]
  main_py["main.py"]
  app_services_users_py --> app_services_db_py
  main_py --> app_services_users_py
```
**Execution chain:** main.py → app/services/users.py → app/services/db.py

### Combined Flow (All `services` Paths)

```mermaid
flowchart LR
  app_services_db_py["app/services/db.py"]
  app_services_users_py["app/services/users.py"]
  main_py["main.py"]
  app_services_users_py --> app_services_db_py
  main_py --> app_services_users_py
```

## Feature: `user`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  app_services_db_py["app/services/db.py"]
  app_services_users_py["app/services/users.py"]
  main_py["main.py"]
  app_services_users_py --> app_services_db_py
  main_py --> app_services_users_py
```
**Execution chain:** main.py → app/services/users.py → app/services/db.py

### Combined Flow (All `user` Paths)

```mermaid
flowchart LR
  app_services_db_py["app/services/db.py"]
  app_services_users_py["app/services/users.py"]
  main_py["main.py"]
  app_services_users_py --> app_services_db_py
  main_py --> app_services_users_py
```
