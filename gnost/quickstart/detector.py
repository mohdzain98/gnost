"""Runs the readers over a project folder and merges what they find into one Quickstart.

`QuickstartDetector` never raises: a reader that fails on an odd file is skipped, so a strange
`package.json` cannot stop `gnost onboard`. The readers are injectable for tests.
"""

from __future__ import annotations

from typing import Optional, Sequence

from gnost.quickstart.models import GROUPS, Quickstart
from gnost.quickstart.readers import SourceReader, default_readers
from gnost.utils.logger import AppLogger

logger = AppLogger.get_logger(__name__)


class QuickstartDetector:
    """Collects install, build, run and test steps from the project's own files."""

    def __init__(self, readers: Optional[Sequence[SourceReader]] = None) -> None:
        self.readers = tuple(readers if readers is not None else default_readers())

    def detect(self, root: str) -> Quickstart:
        """The merged steps of every reader, in reader order."""
        merged = Quickstart()
        for reader in self.readers:
            try:
                found = reader.read(root)
                if reader.fallback:
                    found = self._only_empty_groups(found, merged)
                merged.merge(found)
            except Exception as exc:  # one odd file must not stop onboarding
                logger.debug(f"quickstart: {type(reader).__name__} skipped: {exc}")
        return merged

    @staticmethod
    def _only_empty_groups(found: Quickstart, merged: Quickstart) -> Quickstart:
        """`found` without the groups that `merged` already has steps for."""
        kept = Quickstart()
        for group in GROUPS:
            if not getattr(merged, group):
                setattr(kept, group, list(getattr(found, group)))
        return kept
