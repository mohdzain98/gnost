"""Rule-based "caution" score: files that are risky to change.

Each file gets up to six signals, normalised to 0..1:

    cycles         import-time cycle = 1.0, deferred cycle = 0.35
    size           lines of code
    impact         how many files import it (fan-in)
    coupling       how many files it imports (fan-out)
    complexity     highest cyclomatic complexity of a function (Python, via radon),
                   or branch keywords in the file (other languages, an estimate)
    observability  `except` blocks that neither log nor re-raise (Python only)

Signals combine like independent risks (noisy-OR): one strong signal is enough to
flag a file, several moderate ones add up, and a signal that cannot be measured
for a language is simply left out (the score is then marked `partial`).
"""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from gnost.core.cycles import IMPORT_TIME, Cycle
from gnost.core.graph import DependencyGraph
from gnost.scanner.models import ScanResult

try:  # radon is a dependency, but never let a parsing hiccup stop an onboarding run
    from radon.complexity import cc_visit
except Exception:  # pragma: no cover
    cc_visit = None

SIGNALS = ("cycles", "size", "impact", "coupling", "complexity", "observability")

# Largest share of the final score each signal can claim on its own.
DEFAULT_WEIGHTS: Dict[str, float] = {
    "cycles": 0.9,
    "impact": 0.8,
    "size": 0.7,
    "complexity": 0.7,
    "coupling": 0.5,
    "observability": 0.4,
}
# (value that counts as 0, value that counts as 1)
DEFAULT_RANGES: Dict[str, Tuple[float, float]] = {
    "size": (200, 1000),
    "impact": (4, 30),
    "coupling": (8, 25),
    "complexity": (10, 30),
    "estimated_complexity": (60, 250),
    "observability": (1, 6),
}
DEFERRED_CYCLE_STRENGTH = 0.35
HIGH_SCORE = 70.0
DEFAULT_THRESHOLD = 40.0
DEFAULT_LIMIT = 10

_BRANCH_RE = re.compile(
    r"\b(?:if|for|while|case|catch|except|elif)\b|&&|\|\||\?(?![.?])"
)
_LOG_NAMES = {
    "debug",
    "info",
    "warning",
    "warn",
    "error",
    "exception",
    "critical",
    "log",
}


@dataclass(frozen=True)
class CautionSettings:
    weights: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    ranges: Dict[str, Tuple[float, float]] = field(
        default_factory=lambda: dict(DEFAULT_RANGES)
    )
    threshold: float = DEFAULT_THRESHOLD  # lowest score that is reported
    limit: int = DEFAULT_LIMIT  # most files reported


@dataclass
class FileMetrics:
    path: str
    language: str
    loc: int
    fan_in: int
    fan_out: int
    cycle: Optional[str] = None  # "import-time", "deferred" or None
    complexity: Optional[float] = None
    complexity_estimated: bool = False
    silent_handlers: Optional[int] = None
    generated: bool = False  # machine-written: nobody edits it by hand


@dataclass
class Factor:
    name: str
    value: float  # raw measurement (lines, files, ...)
    strength: float  # normalised 0..1
    contribution: float  # share of the score this signal explains, 0..1
    estimated: bool = False


@dataclass
class CautionScore:
    path: str
    score: float  # 0..100
    level: str  # "high", "medium" or "low"
    partial: bool  # some signals could not be measured for this language
    factors: List[Factor]  # signals that contributed, strongest first

    @property
    def severity(self) -> int:
        return max(1, min(5, math.ceil(self.score / 20)))


def normalize(value: float, low: float, high: float) -> float:
    if high <= low:
        return 1.0 if value >= high else 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def score_file(m: FileMetrics, settings: CautionSettings) -> CautionScore:
    strengths: Dict[
        str, Tuple[float, float, bool]
    ] = {}  # name -> (value, strength, est)

    if m.cycle:
        strength = 1.0 if m.cycle == IMPORT_TIME else DEFERRED_CYCLE_STRENGTH
        strengths["cycles"] = (1.0, strength, False)
    for name, value in (("size", m.loc), ("impact", m.fan_in), ("coupling", m.fan_out)):
        low, high = settings.ranges[name]
        strengths[name] = (value, normalize(value, low, high), False)
    if m.complexity is not None:
        key = "estimated_complexity" if m.complexity_estimated else "complexity"
        low, high = settings.ranges[key]
        strengths["complexity"] = (
            m.complexity,
            normalize(m.complexity, low, high),
            m.complexity_estimated,
        )
    if m.silent_handlers is not None:
        low, high = settings.ranges["observability"]
        strengths["observability"] = (
            m.silent_handlers,
            normalize(m.silent_handlers, low, high),
            False,
        )

    shares = {
        name: settings.weights.get(name, 0.0) * strength
        for name, (_, strength, _) in strengths.items()
    }
    quiet = 1.0
    for share in shares.values():
        quiet *= 1.0 - min(1.0, share)
    score = round(100.0 * (1.0 - quiet), 1)

    factors = [
        Factor(name, value, round(strength, 3), round(shares[name], 3), est)
        for name, (value, strength, est) in strengths.items()
        if shares[name] > 0
    ]
    factors.sort(key=lambda f: (-f.contribution, f.name))

    measurable = {"cycles", "size", "impact", "coupling"}
    if m.complexity is not None:
        measurable.add("complexity")
    if m.silent_handlers is not None:
        measurable.add("observability")
    partial = any(
        settings.weights.get(s, 0) > 0
        for s in SIGNALS
        if s not in measurable and s != "cycles"
    )

    level = (
        "high"
        if score >= HIGH_SCORE
        else "medium"
        if score >= settings.threshold
        else "low"
    )
    return CautionScore(m.path, score, level, partial, factors)


# -------------------------
# Measuring files
# -------------------------


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def _python_measures(content: str) -> Tuple[Optional[float], Optional[int]]:
    """(highest function complexity, silent except blocks) of a Python file."""
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError):
        return None, None

    complexity: Optional[float] = None
    if cc_visit is not None:
        try:
            blocks = cc_visit(content)
            complexity = float(max((b.complexity for b in blocks), default=1))
        except Exception:
            complexity = None

    silent = sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler) and not _handler_reports(node)
    )
    return complexity, silent


def _handler_reports(handler: ast.ExceptHandler) -> bool:
    """True when an except block logs, prints or re-raises."""
    for node in ast.walk(handler):
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in _LOG_NAMES:
                return True
            if isinstance(func, ast.Name) and func.id in {"print", "warn"}:
                return True
    return False


_GENERATED_DIRS = {"generated", "__generated__", "gen"}
_GENERATED_MARKERS = (
    "@generated",
    "auto-generated",
    "autogenerated",
    "do not edit",
    "code generated",
)


def is_generated(path: str, content: str) -> bool:
    """Generated code (by directory name or a marker in its first lines)."""
    parts = set(path.replace("\\", "/").split("/")[:-1])
    if parts & _GENERATED_DIRS:
        return True
    head = "\n".join(content.splitlines()[:5]).lower()
    return any(marker in head for marker in _GENERATED_MARKERS)


def _estimated_complexity(content: str) -> float:
    return float(len(_BRANCH_RE.findall(content)))


def collect_metrics(
    scan: ScanResult, graph: DependencyGraph, cycles: List[Cycle]
) -> List[FileMetrics]:
    cycle_of: Dict[str, str] = {}
    for cycle in cycles:  # import-time cycles come first and win
        for f in cycle.files:
            cycle_of.setdefault(f, cycle.kind)

    metrics: List[FileMetrics] = []
    for info in sorted(scan.files, key=lambda f: f.path):
        content = _read(info.path)
        loc = sum(1 for line in content.splitlines() if line.strip())

        complexity: Optional[float] = None
        estimated = False
        silent: Optional[int] = None
        if info.language == "python":
            complexity, silent = _python_measures(content)
        if complexity is None:
            complexity, estimated = _estimated_complexity(content), True

        metrics.append(
            FileMetrics(
                path=info.path,
                language=info.language,
                loc=loc,
                fan_in=graph.fan_in(info.path),
                fan_out=graph.fan_out(info.path),
                cycle=cycle_of.get(info.path),
                complexity=complexity,
                complexity_estimated=estimated,
                silent_handlers=silent,
                generated=is_generated(info.path, content),
            )
        )
    return metrics


def rank_files(
    scan: ScanResult,
    graph: DependencyGraph,
    cycles: List[Cycle],
    settings: Optional[CautionSettings] = None,
) -> List[CautionScore]:
    """Caution score of every hand-written file, highest first."""
    settings = settings or CautionSettings()
    scores = [
        score_file(m, settings)
        for m in collect_metrics(scan, graph, cycles)
        if not m.generated
    ]
    return sorted(scores, key=lambda s: (-s.score, s.path))
