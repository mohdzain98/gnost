# Full Execution Flow

```mermaid
flowchart TD
  src_App_tsx["src/App.tsx"]
  src_components_ui_button_tsx["src/components/ui/button.tsx"]
  src_components_ui_index_ts["src/components/ui/index.ts"]
  src_hooks_useThing_ts["src/hooks/useThing.ts"]
  src_lib_helper_ts["src/lib/helper.ts"]
  src_lib_index_ts["src/lib/index.ts"]
  src_main_tsx["src/main.tsx"]
  src_pages_About_tsx["src/pages/About.tsx"]
  src_pages_Home_tsx["src/pages/Home.tsx"]
  src_App_tsx --> src_components_ui_button_tsx
  src_App_tsx --> src_hooks_useThing_ts
  src_App_tsx -.-> src_pages_About_tsx
  src_App_tsx -.-> src_pages_Home_tsx
  src_components_ui_index_ts --> src_components_ui_button_tsx
  src_lib_index_ts --> src_lib_helper_ts
  src_main_tsx --> src_App_tsx
  src_pages_About_tsx --> src_components_ui_index_ts
  src_pages_Home_tsx --> src_lib_index_ts
```

> Dotted arrows: imports that do not run when the module loads.

> ℹ️ This file renders the complete Mermaid diagram on GitHub.
> For raw Mermaid source, see [**FLOW-full.mmd**](./FLOW-full.mmd). Every file and import, ungrouped and nothing omitted: [**flow-complete.mmd**](./flow-complete.mmd)
