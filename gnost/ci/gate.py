"""The quality gate: decide from the score and the new findings whether a CI run passes.

`QualityGate` holds the two optional rules (`--fail-under`, `--fail-on-new`) and returns a
`GateResult` with a message per broken rule, ready to print and to turn into an exit code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GateResult:
    """Whether the run passed, and one sentence for each rule it broke."""

    passed: bool
    messages: List[str] = field(default_factory=list)


class QualityGate:
    """Fails a run when the score is under a threshold or findings are new against a baseline."""

    def __init__(
        self, fail_under: Optional[float] = None, fail_on_new: bool = False
    ) -> None:
        self.fail_under = fail_under
        self.fail_on_new = fail_on_new

    def evaluate(self, score: float, new_findings: Optional[int]) -> GateResult:
        """Check the final score (0 to 10) and the number of new findings (None without a baseline)."""
        messages: List[str] = []
        if self.fail_under is not None and score < self.fail_under:
            messages.append(
                f"score {score:.2f} is below the required {self.fail_under:.2f} (--fail-under)"
            )
        if self.fail_on_new and new_findings:
            noun = "finding" if new_findings == 1 else "findings"
            messages.append(
                f"{new_findings} new {noun} not in the baseline (--fail-on-new)"
            )
        return GateResult(passed=not messages, messages=messages)
