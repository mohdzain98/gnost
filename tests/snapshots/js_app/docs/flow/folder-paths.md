# Keyword-based Execution Paths

These diagrams show execution flows related to key features, auto-detected from the project structure.

## Feature: `user`

### Representative Paths

#### Path Group 1

```mermaid
flowchart LR
  src_index_js["src/index.js"]
  src_routes_users_js["src/routes/users.js"]
  src_index_js --> src_routes_users_js
```
**Execution chain:** src/index.js → src/routes/users.js

### Combined Flow (All `user` Paths)

```mermaid
flowchart LR
  src_index_js["src/index.js"]
  src_routes_users_js["src/routes/users.js"]
  src_index_js --> src_routes_users_js
```
