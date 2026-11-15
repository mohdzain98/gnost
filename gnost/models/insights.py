from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum


class CautionType(Enum):
    HIGH_IMPACT = "high_impact"
    LARGE_FILE = "large_file"
    TIGHT_COUPLING = "tight_coupling"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    HIGH_COMPLEXITY = "high_complexity"
    LOW_OBSERVABILITY = "low_observability"


@dataclass
class FileInsight:
    path: str
    reason: str
    score: float


@dataclass
class ArchitectureLayers:
    entry: List[str]
    core: List[str]
    leaf: List[str]


@dataclass
class LayerDetail:
    name: str
    description: str
    files: List[str]


@dataclass
class CautionFactor:
    name: str
    value: float
    contribution: float  # 0..1, how much of the score this signal explains
    estimated: bool = False


@dataclass
class CautionInsight:
    path: str
    category: "CautionType"
    severity: int  # 1–5
    description: str
    metrics: Dict[str, float]
    score: float = 0.0  # 0..100
    partial: bool = False  # some signals are not measurable for this language
    factors: List[CautionFactor] = field(default_factory=list)


@dataclass
class CycleInsight:
    files: List[str]
    example: List[str]
    kind: str  # "import-time" or "deferred"


@dataclass
class OnboardingInsights:
    first_files: List[FileInsight]
    layers: ArchitectureLayers
    caution_areas: List[CautionInsight]
    cycles: List[CycleInsight] = field(default_factory=list)
