# gnost/scanner/models.py

from typing import TYPE_CHECKING, Dict, List, Optional
from dataclasses import dataclass, field

from gnost.languages.base import EntryPoint, ImportEdge

if TYPE_CHECKING:
    from gnost.routes.models import Route


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
    # HTTP endpoints and their handlers; filled in after the scan (gnost.routes).
    routes: List["Route"] = field(default_factory=list)
