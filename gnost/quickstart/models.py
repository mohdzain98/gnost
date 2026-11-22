"""The data a quickstart is made of: steps grouped by purpose, each naming its source file.

`Step` is one command or note and the file it was read from. `Quickstart` holds the steps in
fixed groups (prerequisites, install, build, run, test, environment) and merges partial results
from several readers, dropping duplicates. Used by the Markdown guide, the JSON export and the summary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

GROUPS = ("prerequisites", "install", "build", "run", "test", "environment")
GROUP_TITLES = {
    "prerequisites": "Prerequisites",
    "install": "Install",
    "build": "Build",
    "run": "Run",
    "test": "Test",
    "environment": "Environment variables",
}
GROUP_LIMIT = 8  # a long list stops being a quickstart


@dataclass(frozen=True)
class Step:
    """One thing to do or know, and the project file it comes from."""

    text: str  # a command, or a plain note such as "Node.js >=18"
    source: str  # file name relative to the project, for example "package.json"
    command: bool = True  # False for notes (prerequisites, variable names)

    def to_dict(self) -> Dict[str, Any]:
        """The JSON form of the step."""
        return {"text": self.text, "source": self.source, "command": self.command}


@dataclass
class Quickstart:
    """Steps to get a project running, grouped; empty groups stay empty."""

    prerequisites: List[Step] = field(default_factory=list)
    install: List[Step] = field(default_factory=list)
    build: List[Step] = field(default_factory=list)
    run: List[Step] = field(default_factory=list)
    test: List[Step] = field(default_factory=list)
    environment: List[Step] = field(default_factory=list)

    def add(self, group: str, step: Step) -> None:
        """Add a step to a group unless the same text is already there or the group is full."""
        steps: List[Step] = getattr(self, group)
        if len(steps) >= GROUP_LIMIT or any(s.text == step.text for s in steps):
            return
        steps.append(step)

    def merge(self, other: "Quickstart") -> None:
        """Add every step of `other` after the ones already here."""
        for group in GROUPS:
            for step in getattr(other, group):
                self.add(group, step)

    @property
    def is_empty(self) -> bool:
        """True when no reader found anything."""
        return not any(getattr(self, g) for g in GROUPS)

    def to_dict(self) -> Dict[str, Any]:
        """The JSON form: every group, each a list of steps."""
        return {g: [s.to_dict() for s in getattr(self, g)] for g in GROUPS}
