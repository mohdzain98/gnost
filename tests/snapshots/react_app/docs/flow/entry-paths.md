# Entry-based Execution Paths

These diagrams show individual execution paths starting from application entry points. Each path represents one possible flow through the system.

## Path 1 — `src/main.tsx`

```mermaid
flowchart LR
  src_App_tsx["src/App.tsx"]
  src_lib_helper_ts["src/lib/helper.ts"]
  src_lib_index_ts["src/lib/index.ts"]
  src_main_tsx["src/main.tsx"]
  src_pages_Home_tsx["src/pages/Home.tsx"]
  src_App_tsx -.-> src_pages_Home_tsx
  src_lib_index_ts --> src_lib_helper_ts
  src_main_tsx --> src_App_tsx
  src_pages_Home_tsx --> src_lib_index_ts
```

**Execution chain:** src/main.tsx → src/App.tsx → src/pages/Home.tsx → src/lib/index.ts → src/lib/helper.ts

## Path 2 — `src/main.tsx`

```mermaid
flowchart LR
  src_App_tsx["src/App.tsx"]
  src_components_ui_index_ts["src/components/ui/index.ts"]
  src_main_tsx["src/main.tsx"]
  src_pages_About_tsx["src/pages/About.tsx"]
  src_App_tsx -.-> src_pages_About_tsx
  src_main_tsx --> src_App_tsx
  src_pages_About_tsx --> src_components_ui_index_ts
```

**Execution chain:** src/main.tsx → src/App.tsx → src/pages/About.tsx → src/components/ui/index.ts

## Path 3 — `src/main.tsx`

```mermaid
flowchart LR
  src_App_tsx["src/App.tsx"]
  src_components_ui_button_tsx["src/components/ui/button.tsx"]
  src_main_tsx["src/main.tsx"]
  src_App_tsx --> src_components_ui_button_tsx
  src_main_tsx --> src_App_tsx
```

**Execution chain:** src/main.tsx → src/App.tsx → src/components/ui/button.tsx
