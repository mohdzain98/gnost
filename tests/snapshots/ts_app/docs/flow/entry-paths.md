# Entry-based Execution Paths

These diagrams show individual execution paths starting from application entry points. Each path represents one possible flow through the system.

## Path 1 — `src/index.ts`

```mermaid
flowchart LR
  src_index_ts["src/index.ts"]
  src_math_ts["src/math.ts"]
  src_index_ts --> src_math_ts
```

**Execution chain:** src/index.ts → src/math.ts

## Path 2 — `src/index.ts`

```mermaid
flowchart LR
  src_index_ts["src/index.ts"]
  src_view_tsx["src/view.tsx"]
  src_index_ts --> src_view_tsx
```

**Execution chain:** src/index.ts → src/view.tsx
