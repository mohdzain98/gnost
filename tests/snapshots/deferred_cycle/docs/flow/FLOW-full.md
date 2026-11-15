# Full Execution Flow

```mermaid
flowchart TD
  main_py["main.py"]
  svc_a_py["svc/a.py"]
  svc_b_py["svc/b.py"]
  main_py --> svc_a_py
  svc_a_py --> svc_b_py
  svc_b_py -.-> svc_a_py
  linkStyle 1 stroke:#f57c00,stroke-width:2px
  linkStyle 2 stroke:#f57c00,stroke-width:2px
```

> Orange arrows (dotted when the import itself is deferred): circular dependencies that only close through an import inside a function, a type-only import or a dynamic import.

> ℹ️ This file renders the complete Mermaid diagram on GitHub.
> For raw Mermaid source, see [**FLOW-full.mmd**](./FLOW-full.mmd). Every file and import, ungrouped and nothing omitted: [**flow-complete.mmd**](./flow-complete.mmd)
