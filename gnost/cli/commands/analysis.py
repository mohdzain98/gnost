import asyncio
import json
import os
import tempfile
import logging
from pathlib import Path
from termcolor import colored
from gnost.analysis.core.interfaces import AnalyzerRegistry
from gnost.analysis.utils.extract import Extract
from gnost.analysis.core.models import AnalysisConfiguration
from gnost.analysis.core.engine import (
    UnifiedAnalysisEngine as Engine,
)
from gnost.analysis.analyzers import (
    MaintainabilityAnalyzer,
    RobustnessAnalyzer,
    ObservabilityAnalyzer,
    ReadabilityAnalyzer,
)
from gnost.utils.logger import AppLogger

logger = AppLogger.get_logger(__name__)


class TqdmProgress:
    """Simple textual progress showing completed analyzers out of total."""

    def __init__(self, show: bool, desc: str = "Analyzing"):
        self.show = show
        self.total = 0
        self.completed = 0
        self.current_stage = desc
        self.total_known = False

    def __call__(self, increment=1, stage=None, total_analyzers=None):
        if total_analyzers is not None and not self.total_known:
            self.total = max(1, int(total_analyzers))
            self.total_known = True

        if stage:
            if "finished" in stage:
                color = "green"
            elif "running" in stage:
                color = "yellow"
            else:
                color = "cyan"
            self.current_stage = colored(f"[{stage}]", color, attrs=["bold"])

        if increment:
            next_count = self.completed + increment
            self.completed = min(next_count, self.total or next_count)

        if self.show:
            total_display = self.total if self.total else "?"
            print(
                f"{self.current_stage} {self.completed}/{total_display} analyzers completed",
                flush=True,
            )

    def close(self):
        if self.show:
            print()


class Analysis:
    def __init__(self):
        self.analyzer_registry = AnalyzerRegistry()
        self.engine = Engine(self.analyzer_registry)

    def initialize_analyzers(self) -> None:
        """Register all analyzers in the global registry."""
        if not self.analyzer_registry.list_analyzer_names():
            self.analyzer_registry.register(RobustnessAnalyzer())
            self.analyzer_registry.register(MaintainabilityAnalyzer())
            self.analyzer_registry.register(ObservabilityAnalyzer())
            self.analyzer_registry.register(ReadabilityAnalyzer())

    def get_analyzer_registry(
        self,
    ):
        return self.analyzer_registry

    def _json_default(self, o):
        """Fallback converter for non-serializable types."""
        import datetime
        import pathlib
        import enum
        import dataclasses

        if isinstance(o, datetime.datetime):
            return o.isoformat()
        if isinstance(o, datetime.date):
            return o.isoformat()
        if isinstance(o, (pathlib.Path,)):
            return str(o)
        if isinstance(o, (set, frozenset)):
            return list(o)
        if isinstance(o, enum.Enum):
            return o.value
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)

        # Try model_dump, to_dict, dict, json (Pydantic, etc.)
        for attr in ("to_dict", "dict", "model_dump", "json"):
            if hasattr(o, attr) and callable(getattr(o, attr)):
                try:
                    v = getattr(o, attr)()
                    if isinstance(v, str):
                        return json.loads(v)
                    return v
                except Exception:
                    pass

        return str(o)

    def write_json_file(self, path: str, data: dict, *, compact: bool) -> None:
        out_dir = os.path.dirname(os.path.abspath(path)) or "."
        os.makedirs(out_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", delete=False, dir=out_dir, encoding="utf-8"
        ) as tf:
            tmp = tf.name
            if compact:
                json.dump(
                    data,
                    tf,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    default=self._json_default,
                )
            else:
                json.dump(
                    data, tf, ensure_ascii=False, indent=2, default=self._json_default
                )
                tf.write("\n")
        os.replace(tmp, path)

    def collect_code_files(
        self, target_path: str, *, exts: set[str] | None = None
    ) -> list[str]:
        """Return a list of code files under target_path using Extract's filters."""
        exts = exts or set(Extract.CODE_EXTS)
        root = Path(target_path).resolve()

        # Let Extract decide the best project root (handles wrapper dirs)
        project_root = Extract.find_best_project_root(root, exts)
        count = Extract.count_code_files(project_root, exts)

        files: list[str] = []
        # Manual stack walk so we can prune hidden/excluded dirs eagerly
        stack: list[Path] = [project_root]
        while stack:
            d = stack.pop()
            try:
                for entry in d.iterdir():
                    if entry.is_dir():
                        if not Extract.is_hidden_dir(entry):
                            stack.append(entry)
                    else:
                        if Extract.is_code_file(entry, exts):
                            files.append(str(entry))
            except PermissionError:
                # ignore unreadable dirs
                continue
        return files, count

    def set_quiet_logging(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.WARNING)
        for handler in root_logger.handlers:
            handler.setLevel(logging.WARNING)

    async def run_async(self, cfg: AnalysisConfiguration, show_progress: bool):
        tprog = TqdmProgress(show_progress, desc=colored("[starting]", "cyan"))
        try:
            report = await self.engine.analyze(cfg, progress_cb=tprog)
        except asyncio.CancelledError:
            logger.info("Analysis cancelled by user.")
            raise
        finally:
            tprog.close()
        return report
