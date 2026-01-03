from gnost.scanner.models import ScanResult
from gnost.core.flow import FlowResult
from gnost.core.graph import DependencyGraph
from gnost.utils.printer import Printer
from gnost.core.ranker import HotspotRanker
from gnost.models.insights import OnboardingInsights


class SummaryReporter:
    """
    Generates a human-readable onboarding summary.
    """

    def __init__(
        self,
        scan: ScanResult,
        flow: FlowResult,
        graph: DependencyGraph,
        printer: Printer | None = None,
        insights: OnboardingInsights = None,
    ):
        self.scan = scan
        self.flow = flow
        self.graph = graph
        self.insights = insights
        self.printer = printer or Printer()

    # -------------------------
    # Public API
    # -------------------------

    def render(self):
        self._header()
        self._project_overview()
        self._entry_points()
        self._execution_flow()
        self._hotspots()
        self._reading_guide()

        if self.insights:
            self._first_files()
            self._caution_areas()

    # -------------------------
    # Sections
    # -------------------------

    def _header(self):
        self.printer.title("GNOST — Project Onboarding Summary")

    def _project_overview(self):
        self.printer.section("Project Overview")

        languages = ", ".join(
            f"{lang} ({count})" for lang, count in self.scan.languages.items()
        )

        self.printer.kv("Root", self.scan.root)
        self.printer.kv("Languages", languages or "Unknown")
        self.printer.kv("Framework", self.scan.framework or "Not detected")
        self.printer.newline()

    def _entry_points(self):
        self.printer.section("Entry Points")

        if not self.flow.entry_points:
            self.printer.text("No explicit entry point detected.")
            self.printer.newline()
            return

        for ep in self.flow.entry_points:
            self.printer.bullet(f"{ep.file}  ({ep.reason})")

        self.printer.newline()

    def _execution_flow(self):
        self.printer.section("Execution Flow (High Level)")

        if not self.flow.paths:
            self.printer.text("Unable to infer execution flow.")
            self.printer.newline()
            return

        # Show only top N paths (avoid noise)
        MAX_PATHS = 3

        for i, path in enumerate(self.flow.paths[:MAX_PATHS], start=1):
            chain = " → ".join(self._shorten(p) for p in path.path)
            self.printer.bullet(chain)

        if len(self.flow.paths) > MAX_PATHS:
            self.printer.text(f"... and {len(self.flow.paths) - MAX_PATHS} more paths")

        self.printer.newline()

    def _reading_guide(self):
        self.printer.section("Recommended Reading Order")

        layers = self.flow.layers

        if layers.get("entry"):
            self.printer.subsection("Start Here")
            for f in sorted(layers["entry"]):
                self.printer.bullet(self._shorten(f))

        if layers.get("core"):
            self.printer.subsection("Core Logic")
            for f in sorted(layers["core"]):
                self.printer.bullet(self._shorten(f))

        if layers.get("leaf"):
            self.printer.subsection("Supporting / Leaf Code")
            for f in sorted(layers["leaf"]):
                self.printer.bullet(self._shorten(f))

        self.printer.newline()

    def _hotspots(self):
        self.printer.section("Hotspots (Most Important Files)")

        # Build ranking
        ranker = HotspotRanker(
            graph=self.graph,
            flow=self.flow,
        )

        # If graph is not directly available, pass it explicitly (see note below)
        hotspots = ranker.rank(top=5)

        if not hotspots:
            self.printer.text("No significant hotspots detected.")
            self.printer.newline()
            return

        for h in hotspots:
            self.printer.bullet(
                f"{self._shorten(h.file)} "
                f"(score={h.score}, layer={h.layer}, fan-in={h.fan_in})"
            )

        self.printer.newline()

    def _first_files(self):
        self.printer.section("First Files to Read")

        for item in self.insights.first_files[:5]:
            short = self._short_path(item.path, depth=3)
            self.printer.bullet(f"{short} — {item.reason}")

        self.printer.newline()

    def _short_path(self, path: str, depth: int = 2) -> str:
        """
        Shorten a file path to the last `depth` components.
        Example:
        gnost/core/flow.py  → core/flow.py
        """
        parts = path.replace("\\", "/").split("/")
        return "/".join(parts[-depth:])

    def _caution_areas(self):
        if not self.insights.caution_areas:
            return

        self.printer.section("Caution Areas")

        for c in self.insights.caution_areas[:5]:
            short = self._short_path(c.path, depth=3)
            sev = c.severity
            self.printer.bullet(f"{short} [{c.category.value}] severity: {sev}")
            self.printer.text(f"  {c.description}")

        self.printer.newline()

    # -------------------------
    # Helpers
    # -------------------------

    def _shorten(self, path: str) -> str:
        """
        Shorten long paths for readability.
        """
        return path.replace(self.scan.root + "/", "")
