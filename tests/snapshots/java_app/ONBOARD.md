# java_app — Project Onboarding Guide

_Generated automatically by <a href='https://gnost.readthedocs.io'>GNOST</a>._

## Project Overview

- **Root:** `<ROOT>`
- **Languages:** java (3)
- **Framework:** Spring Framework

## Summary Table

| Language | Files | LOC |
|---|---:|---:|
| Java | 3 | 38 |

## Stats Table

| Language | Files | Code | Comments | Blanks | LOC |
|---|---:|---:|---:|---:|---:|
| Java | 3 | 30 | 0 | 8 | 38 |

## Entry Points

- `src/main/java/demo/App.java` — public static void main

## Routes

4 endpoints found. Each row is a URL and the code that handles it.

| Method | Path | Handler | File |
|---|---|---|---|
| POST | `/api/greet/a` | `GreetingController.create` | `src/main/java/demo/GreetingController.java:14` |
| POST | `/api/greet/b` | `GreetingController.create` | `src/main/java/demo/GreetingController.java:14` |
| PUT | `/api/greet/x` | `GreetingController.update` | `src/main/java/demo/GreetingController.java:17` |
| GET | `/api/greet/{name}` | `GreetingController.greet` | `src/main/java/demo/GreetingController.java:9` |

## Execution Flow (High Level)

- `src/main/java/demo/App.java` → `src/main/java/demo/Greeter.java`

## Execution Flow (Overview)

```mermaid
flowchart TD
```

> 📌 This diagram shows the high-level execution flow.<br>For the complete flow, see [**flow/flow-full.md**](./docs/flow/FLOW-full.md)<br>Raw Mermaid: [flow/flow-full.mmd](./docs/flow/FLOW-full.mmd)

## Recommended Reading Order

### Start Here

- `src/main/java/demo/App.java`

### Supporting / Leaf Code

- `src/main/java/demo/Greeter.java`

## 📘 First Files to Read
- **`src/main/java/demo/App.java`**
  - Primary entry point into the application
- **`src/main/java/demo/Greeter.java`**
  - Frequently involved in execution flow
- **`src/main/java/demo/GreetingController.java`**
  - Frequently involved in execution flow

## ⚠️ Caution Areas

## 🔁 Circular Dependencies

_No circular dependencies detected._
## Key Execution Paths

To understand specific scenarios, see the entry-based execution paths:

- 📍 [Entry-based Paths](docs/flow/entry-paths.md)

- 🧭 [folder-based Paths](docs/flow/folder-paths.md)

(Complete system flow: [flow/flow-full.md](docs/flow/FLOW-full.md))
