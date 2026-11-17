from __future__ import annotations

from gnost.utils.paths import shorten
from gnost.scanner.models import ScanResult
from gnost.core.flow import FlowResult
from gnost.core.graph import DependencyGraph
from gnost.utils.printer import Printer
from gnost.core.ranker import HotspotRanker
from gnost.models.insights import OnboardingInsights
from typing import Optional


class SummaryReporter:
    """
    Generates a human-readable onboarding summary.
    """

    def __init__(
        self,
        scan: ScanResult,
        flow: FlowResult,
        graph: DependencyGraph,
        printer: Optional[Printer] = None,
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
        self._routes()
        self._execution_flow()
        self._hotspots()
        self._reading_guide()

        if self.insights:
            self._first_files()
            self._caution_areas()
            self._cycles()

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
            self.printer.bullet(f"{self._shorten(ep.file)}  ({ep.reason})")

        self.printer.newline()

    ROUTE_LIMIT = 10

    def _routes(self):
        routes = self.scan.routes
        if not routes:
            return

        self.printer.section("Routes")
        for route in routes[: self.ROUTE_LIMIT]:
            self.printer.bullet(
                f"{route.method} {route.path} → {route.handler} "
                f"({self._shorten(route.file)}:{route.line})"
            )
        if len(routes) > self.ROUTE_LIMIT:
            self.printer.text(f"... and {len(routes) - self.ROUTE_LIMIT} more routes")
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

    READING_LIMIT = 15

    def _reading_guide(self):
        self.printer.section("Recommended Reading Order")

        sections = [
            ("entry", "Start Here"),
            ("core", "Core Logic"),
            ("leaf", "Supporting / Leaf Code"),
        ]
        for layer, title in sections:
            files = self.flow.ordered_layer(layer)
            if not files:
                continue
            self.printer.subsection(title)
            for f in files[: self.READING_LIMIT]:
                self.printer.bullet(self._shorten(f))
            if len(files) > self.READING_LIMIT:
                self.printer.text(
                    f"... and {len(files) - self.READING_LIMIT} more "
                    "(closest to an entry point listed first)"
                )

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
            short = self._shorten(item.path)
            self.printer.bullet(f"{short} — {item.reason}")

        self.printer.newline()

    def _caution_areas(self):
        if not self.insights.caution_areas:
            return

        self.printer.section("Caution Areas")

        for c in self.insights.caution_areas[:5]:
            short = self._shorten(c.path)
            sev = c.severity
            score = f" score {c.score:g}" if c.score else ""
            self.printer.bullet(f"{short} [{c.category.value}] severity: {sev}{score}")
            self.printer.text(f"  {c.description}")

        self.printer.newline()

    def _cycles(self):
        cycles = self.insights.cycles
        self.printer.section("Circular Dependencies")

        if not cycles:
            self.printer.text("None detected.")
            self.printer.newline()
            return

        eager = [c for c in cycles if c.kind == "import-time"]
        self.printer.text(
            f"{len(eager)} import-time, {len(cycles) - len(eager)} deferred "
            "(imports inside functions or type-only)"
        )
        for cycle in cycles[:5]:
            chain = " → ".join(self._shorten(f) for f in cycle.example)
            self.printer.bullet(f"[{cycle.kind}] {chain}")
        if len(cycles) > 5:
            self.printer.text(f"... and {len(cycles) - 5} more")

        self.printer.newline()

    # -------------------------
    # Helpers
    # -------------------------

    def _shorten(self, path: str) -> str:
        """
        Shorten long paths for readability.
        """
        return shorten(path, self.scan.root)
