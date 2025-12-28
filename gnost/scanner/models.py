# gnost/scanner/models.py

from typing import Dict, List, Optional
from dataclasses import dataclass

from gnost.languages.base import EntryPoint, ImportEdge


@dataclass
class FileInfo:
    path: str
    language: str
    imports: List[ImportEdge]


@dataclass
class ScanResult:
    root: str
    languages: Dict[str, int]
    files: List[FileInfo]
    entry_points: List[EntryPoint]
    framework: Optional[str]
