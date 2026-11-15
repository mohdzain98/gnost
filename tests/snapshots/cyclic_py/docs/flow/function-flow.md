# Function-level Flow

What each entry point calls, function by function (Python only). Dotted arrows lead to a function already drawn elsewhere in the same diagram. Calls through other objects (`self.client.send()`) are not followed.

## `main.py` → `<main>`

`main.py:4` · 3 functions

```mermaid
flowchart LR
  main_py___main_["<main><br/>main.py"]
  pkg_a_py__run["run<br/>pkg/a.py"]
  pkg_b_py__helper["helper<br/>pkg/b.py"]
  main_py___main_ --> pkg_a_py__run
  pkg_a_py__run --> pkg_b_py__helper
```

