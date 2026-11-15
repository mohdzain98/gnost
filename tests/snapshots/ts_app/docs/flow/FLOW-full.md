# Full Execution Flow

```mermaid
flowchart TD
  src_index_ts["src/index.ts"]
  src_math_ts["src/math.ts"]
  src_view_tsx["src/view.tsx"]
  src_index_ts --> src_math_ts
  src_index_ts --> src_view_tsx
  src_view_tsx --> src_math_ts
```

> ℹ️ This file renders the complete Mermaid diagram on GitHub.
> For raw Mermaid source, see [**FLOW-full.mmd**](./FLOW-full.mmd). Every file and import, ungrouped and nothing omitted: [**flow-complete.mmd**](./flow-complete.mmd)
