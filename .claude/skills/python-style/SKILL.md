---
name: python-style
description: Python code style conventions for this project — docstring length/format for modules, classes, and methods, comment brevity, and mandatory type hints on function signatures. Apply this whenever writing or editing any Python file (.py), including new modules, new classes, new functions/methods, and edits to existing code. Always follow this skill for Python code in this project, not just when explicitly asked about style.
---

# Python Style

Style conventions for all Python code written or edited in this project. Apply automatically — do not wait to be asked.

## Type hints — mandatory

Every function and method signature includes type hints for **all parameters and the return type**, with no exceptions (including `-> None`).

```python
def get_user_profile(user_id: UUID, include_facts: bool = False) -> UserProfile | None:
    ...

async def save_turn(self, chat_id: UUID, user_message: str) -> ChatTurn:
    ...

def log_event(self, name: str, data: dict | None = None) -> None:
    ...
```

## Comments — short, not narrative

Inline comments are brief — a phrase, not a sentence, and only where the *why* isn't obvious from the code itself. Never comment what the code already says.

```python
# Good
retries = 3  # API occasionally rate-limits on cold start

# Bad — restates the obvious
retries = 3  # set retries to 3

# Bad — too long, reads like a paragraph
retries = 3  # We set this to 3 because in our testing we found that the API
             # tends to rate-limit us when the connection is cold, and 3 retries
             # was generally enough to get through without excessive delay.
```

Skip comments entirely when the code is self-explanatory. Prefer a clear variable/function name over a comment explaining an unclear one.

## Module docstrings — 4-5 lines

Every `.py` file starts with a module-level docstring, 4-5 lines: what the module contains, and its role in the system. No more, no less — trim to fit, don't pad to fit.

```python
"""Repository layer for chat turns and their embedded child chunks.

Handles persistence of ChatTurn (parent) and ChatMemoryChunk (child) records,
including the parent-child chunking flow used for semantic memory search.
Used by the memory tools and the profile extraction pipeline.
"""
```

## Class docstrings — 3-4 lines

Every class has a docstring, 3-4 lines: what it represents/does and any non-obvious responsibility it owns.

```python
class MemoryRepository(BaseRepository[ChatMemoryChunk]):
    """Persists and searches chat memory chunks scoped by user_id.

    Owns the chunk/embed/store flow on write, and the over-fetch-then-
    deduplicate pattern on similarity search to avoid duplicate parent turns.
    """
```

## Method/function docstrings — 2-3 lines

Every method and function has a docstring, 2-3 lines: what it does and anything a caller needs to know (side effects, non-obvious params, when it returns None/raises).

```python
def resolve_expiry(duration_hint: str, created_at: datetime) -> datetime | None:
    """Convert a duration hint into an expires_at timestamp.

    Returns None for "long_term" facts, which never expire on their own.
    """
```

**Exception**: trivial one-line accessors, `__init__` methods that just assign params, and dunder methods don't need a docstring unless they do something non-obvious.

## Length discipline

If a docstring is running longer than the line counts above, that's a signal the function is doing too much — consider splitting it, rather than writing a longer docstring to explain it.

## Applying this to existing code

When editing an existing file that doesn't yet follow these conventions, bring the function/class/module you're touching into compliance as part of the edit. Don't do a drive-by reformat of the whole file for an unrelated change — only the code you're already modifying.
