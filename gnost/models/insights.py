from dataclasses import dataclass
from typing import List, Dict
from enum import Enum


class CautionType(Enum):
    HIGH_IMPACT = "high_impact"
    LARGE_FILE = "large_file"
    TIGHT_COUPLING = "tight_coupling"
    CIRCULAR_DEPENDENCY = "circular_dependency"


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
class CautionInsight:
    path: str
    category: "CautionType"
    severity: int  # 1–5
    description: str
    metrics: Dict[str, float]


@dataclass
class OnboardingInsights:
    first_files: List[FileInsight]
    layers: ArchitectureLayers
    caution_areas: List[CautionInsight]
