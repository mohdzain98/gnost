"""
Readability Analyzer for evaluating code readability and style.
Analyzes naming conventions, documentation, formatting, and code clarity.
"""

import os
import json
import asyncio
import traceback
import statistics
from collections import Counter
from collections import defaultdict
from typing import List, Dict, Any, Tuple

from gnost.analysis.core.interfaces import QualityAnalyzer
from gnost.analysis.core.file_utils import find_python_files
from gnost.analysis.core.models import (
    AnalysisConfiguration,
    AnalysisResult,
    AnalysisMetrics,
    UnifiedFinding,
    FindingCategory,
    SeverityLevel,
    ComplexityLevel,
    CodeLocation,
)
from gnost.utils.logger import AppLogger

logger = AppLogger.get_logger(__name__)


class ReadabilityAnalyzer(QualityAnalyzer):
    """
    Analyzer for evaluating code readability through Ruff and custom checks.
    """

    def __init__(self):
        super().__init__("readability", "1.0.0")
        self.quality_categories = ["naming", "documentation", "formatting", "clarity"]
        self._initialize_readability_patterns()

    def get_supported_file_types(self) -> List[str]:
        """Return supported file types."""
        return [".py"]

    def get_quality_categories(self) -> List[str]:
        """Get quality categories this analyzer covers."""
        return self.quality_categories

    def get_quality_metrics(self) -> List[str]:
        """Get quality metrics this analyzer can provide."""
        return [
            "readability_score",
            "naming_issues_count",
            "documentation_issues_count",
            "formatting_issues_count",
            "clarity_issues_count",
            "total_readability_issues",
            "readability_coverage_percentage",
        ]

    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for this analyzer."""
        return {
            "enable_ruff": True,
            "ruff_timeout": 60,
            "focus_on_readability": True,
            "include_naming_conventions": True,
            "include_documentation_checks": True,
            "include_formatting_checks": True,
            "minimum_readability_score": 75.0,
            "exclude_test_files": False,
        }

    def _get_issues_to_report(self):
        issues = [
            "D100",
            "D101",
            "D102",
            "D103",
            "D105",
            "D107",
            "D200",
            "D201",
            "D205",
            "D206",
            "D211",
            "D212",
            "D300",
            "D400",
            "D401",
            "D403",
            "E501",
            "E111",
            "E112",
            "E117",
            "W191",
            "W291",
            "W293",
            "W391",
            "W505",
            "F401",
            "F841",
            "N802",
            "N803",
            "N806",
            "N816",
            "PLR0913",
            "PLR0914",
            "PLR0915",
        ]
        return issues

    async def analyze(self, config: AnalysisConfiguration) -> AnalysisResult:
        """
        Perform readability analysis on the target files.

        Args:
            config: Analysis configuration

        Returns:
            Analysis result with findings and metrics
        """
        findings = []
        error_count = 0
        start_time = asyncio.get_event_loop().time()

        try:
            logger.info(
                f"Starting readability analysis of {os.path.basename(config.target_path)}"
            )

            # Find Python files
            # python_files = self._find_python_files(config.target_path)
            if getattr(config, "files", None):
                # Use the explicit file list passed from CLI
                python_files = config.files
            else:
                # Fallback: discover files automatically
                python_files = self._find_python_files(config.target_path)

            if not python_files:
                logger.warning(
                    f"No Python files found in {os.path.basename(config.target_path)}"
                )
                return self._create_empty_result()

            logger.info(f"Found {len(python_files)} Python files to analyze")

            # Get analyzer configuration
            analyzer_config = config.analyzer_configs.get(
                self.name, self.get_default_config()
            )
            active = await self._check_ruff_status()
            if not active:
                logger.error(
                    "Aborting Readability analysis, ruff not found in the environment"
                )
                execution_time = asyncio.get_event_loop().time() - start_time
                metrics = AnalysisMetrics(
                    analyzer_name=self.name,
                    execution_time_seconds=execution_time,
                    files_analyzed=0,
                    findings_count=0,
                    error_count=1,
                    success=False,
                    error_message="Ruff is not installed. Please install it with `pip install ruff`.",
                )
                return AnalysisResult(
                    findings=[],
                    metrics=metrics,
                    metadata={"error": "Ruff not available"},
                )

            # Perform readability analysis
            analysis_results = await self._perform_readability_analysis(
                python_files, analyzer_config
            )
            clubbed_findings = await self._club_analysis_results(analysis_results)
            # Generate findings based on analysis
            findings = await self._generate_findings(
                clubbed_findings, config.target_path, analyzer_config
            )

            execution_time = asyncio.get_event_loop().time() - start_time

            metrics = AnalysisMetrics(
                analyzer_name=self.name,
                execution_time_seconds=execution_time,
                files_analyzed=len(python_files),
                findings_count=len(findings),
                error_count=error_count,
                success=True,
            )

            logger.info(
                f"Readability analysis completed: {len(findings)} findings in {execution_time:.2f}s"
            )

            return AnalysisResult(
                findings=findings,
                metrics=metrics,
                metadata={
                    "python_files_count": len(python_files),
                    "readability_score": analysis_results.get(
                        "overall_readability_score", 0.0
                    ),
                    "total_readability_issues": analysis_results.get("total_issues", 0),
                    "issues_by_category": analysis_results.get(
                        "issues_by_category", {}
                    ),
                },
            )

        except Exception as e:
            traceback.print_exc()
            logger.error(f"Readability analysis failed: {str(e)}")
            error_count += 1
            execution_time = asyncio.get_event_loop().time() - start_time

            metrics = AnalysisMetrics(
                analyzer_name=self.name,
                execution_time_seconds=execution_time,
                files_analyzed=0,
                findings_count=0,
                error_count=error_count,
                success=False,
                error_message=str(e),
            )

            return AnalysisResult(
                findings=[], metrics=metrics, metadata={"error": str(e)}
            )

    async def _check_ruff_status(self) -> bool:
        #  Check if ruff is available
        try:
            proc = await asyncio.create_subprocess_exec(
                "ruff",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.warning("ruff not found. Install with: pip install ruff")
                if stderr:
                    logger.debug(
                        f"ruff --version stderr: {stderr.decode(errors='ignore')}"
                    )
                if stdout:
                    logger.debug(
                        f"ruff --version stdout: {stdout.decode(errors='ignore')}"
                    )
                return False
            return True
        except FileNotFoundError:
            logger.warning("ruff not found. Install with: pip install ruff")
            return False

    def _initialize_readability_patterns(self):
        """Initialize readability issue patterns and mappings."""
        self.readability_issue_mapping = {
            "E999": {
                "category": "formatting",
                "title": "Parsing failed",
                "severity": SeverityLevel.HIGH,
                "complexity": ComplexityLevel.COMPLEX,
            },
            "D105": {
                "category": "documentation",
                "title": "Missing Magic Method Docstring",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "D107": {
                "category": "documentation",
                "title": "Missing __init__ Docstring",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "N802": {
                "category": "naming",
                "title": "Invalid Function Naming",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "N803": {
                "category": "naming",
                "title": "Invalid Function Argument Name",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "N806": {
                "category": "naming",
                "title": "Variable in Class Scope Not Lowercase",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "N816": {
                "category": "naming",
                "title": "Mixed-Case Variable in Class Scope",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "D100": {
                "category": "documentation",
                "title": "Missing Module Documentation",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "D101": {
                "category": "documentation",
                "title": "Missing Class Documentation",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "D102": {
                "category": "documentation",
                "title": "Missing Magic Method Docstring",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "D103": {
                "category": "documentation",
                "title": "Missing Function Documentation",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "D200": {
                "category": "documentation",
                "title": "One-line Docstring",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "D201": {
                "category": "documentation",
                "title": "Blank Line Before Function Body",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "D205": {
                "category": "documentation",
                "title": "1 Blank Line After Summary",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "D206": {
                "category": "documentation",
                "title": "Docstring Quotes",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "D211": {
                "category": "documentation",
                "title": "No Blank Line Before Class Docstring",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "D212": {
                "category": "documentation",
                "title": "Multi-line Docstring Summary",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "D300": {
                "category": "documentation",
                "title": "Use Triple Double Quotes",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "D400": {
                "category": "documentation",
                "title": "First Line Ends with Period",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "D401": {
                "category": "documentation",
                "title": "Imperative Mood in Summary",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "D403": {
                "category": "documentation",
                "title": "Use imperative verb in first line",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "E111": {
                "category": "formatting",
                "title": "Bad Indentation",
                "severity": SeverityLevel.MEDIUM,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "E112": {
                "category": "formatting",
                "title": "Indentation is not a multiple of four",
                "severity": SeverityLevel.MEDIUM,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "E117": {
                "category": "formatting",
                "title": "Over-indented",
                "severity": SeverityLevel.MEDIUM,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "W191": {
                "category": "formatting",
                "title": "Tab Indentation",
                "severity": SeverityLevel.MEDIUM,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "W291": {
                "category": "formatting",
                "title": "Trailing Whitespace",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.TRIVIAL,
            },
            "W293": {
                "category": "formatting",
                "title": "Blank Line Contains Whitespace",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.TRIVIAL,
            },
            "W391": {
                "category": "formatting",
                "title": "Blank Line at End of File",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.TRIVIAL,
            },
            "W505": {
                "category": "formatting",
                "title": "Doc Line Too Long",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.TRIVIAL,
            },
            "E501": {
                "category": "formatting",
                "title": "Line Too Long",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "F401": {
                "category": "clarity",
                "title": "Unused Import",
                "severity": SeverityLevel.MEDIUM,
                "complexity": ComplexityLevel.TRIVIAL,
            },
            "F841": {
                "category": "clarity",
                "title": "Unused Variable",
                "severity": SeverityLevel.MEDIUM,
                "complexity": ComplexityLevel.SIMPLE,
            },
            "PLR0913": {
                "category": "clarity",
                "title": "Too Many Function Arguments",
                "severity": SeverityLevel.MEDIUM,
                "complexity": ComplexityLevel.MODERATE,
            },
            "PLR0914": {
                "category": "clarity",
                "title": "Too Many Local Variables",
                "severity": SeverityLevel.MEDIUM,
                "complexity": ComplexityLevel.MODERATE,
            },
            "PLR0915": {
                "category": "clarity",
                "title": "Too Many Statements",
                "severity": SeverityLevel.LOW,
                "complexity": ComplexityLevel.MODERATE,
            },
        }

    def get_issue_detail(self, symbol: str) -> str:
        """Return detail text for a Ruff issue symbol."""
        ISSUE_DETAILS = {
            "E999": (
                "The code has a syntax error. "
                "Fix invalid punctuation, indentation, or Python grammar issues before lint checks."
            ),
            "D100": (
                "The module is missing a top-level docstring. "
                "Add a descriptive docstring at the top of the file to explain its purpose."
            ),
            "D101": (
                "The class is missing a class-level docstring. "
                "Add documentation for class usage and purpose."
            ),
            "D102": "Magic methods should include a docstring.",
            "D105": "Add a docstring for this magic method.",
            "D107": "Add docstring for this __init__ method.",
            "D103": (
                "The function does not have a docstring. "
                "Add a docstring describing its parameters and return value."
            ),
            "N802": "Use snake_case for function names.",
            "N803": "Use snake_case for function arguments.",
            "N806": "Use snake_case variable names in class scope.",
            "N816": "Use lowercase variable names in class scope with underscores.",
            "E111": "Use consistent 4-space indentation.",
            "E112": "Use proper indentation with spaces at block level.",
            "E117": "Over-indented line. Adjust indentation to match nearby blocks.",
            "W191": "Tabs used for indentation; replace tabs with spaces.",
            "W291": "Remove trailing whitespace.",
            "W293": "Remove trailing whitespace from blank lines.",
            "W391": "Remove extra blank lines at the end of file.",
            "W505": "Line length exceeds readability settings.",
            "E501": "Line length exceeds configured maximum.",
            "F401": "Unused import found.",
            "F841": "Local variable assigned but never used.",
            "PLR0913": "This function has too many arguments.",
            "PLR0914": "Function has too many local variables.",
            "PLR0915": "Function has too many statements.",
            "D200": "Improve docstring formatting.",
            "D205": "Add summary line and blank line in docstring.",
            "D206": "Use `'''` triple quotes for docstrings.",
            "D211": "No blank line before class docstring.",
            "D212": "Summary line should be on first line.",
            "D300": "Use triple double quotes for docstrings.",
            "D400": "First line should end with period.",
            "D401": "First line should be in imperative mood.",
            "D403": "First word of first line should be an imperative verb.",
        }
        return ISSUE_DETAILS.get(symbol, f"No details available for symbol: {symbol}")

    def _find_python_files(self, path: str) -> List[str]:
        """Find all Python files under the given path, excluding virtual environments."""
        return find_python_files(path, exclude_test_files=False)

    async def _perform_readability_analysis(
        self, python_files: List[str], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform comprehensive readability analysis."""

        all_issues = []
        scores = []
        overall_details = Counter()
        issues_by_category = {
            "naming": 0,
            "documentation": 0,
            "formatting": 0,
            "clarity": 0,
        }

        if config.get("enable_ruff", True):
            for file_path in python_files:
                # Skip test files if configured
                if config.get("exclude_test_files", False) and self._is_test_file(
                    file_path
                ):
                    continue

                ruff_data = await self._run_ruff_analysis(file_path, config)
                scores.append(ruff_data.get("score", 100.0))
                overall_details.update(ruff_data.get("counts", {}))
                file_issues = ruff_data.get("issues", [])
                spf = "/".join(file_path.split("/")[-2:])
                for issue in file_issues:
                    issue["file_path"] = spf or file_path
                    all_issues.append(issue)

                    # Count by category
                    category = issue.get("category", "clarity")
                    if category in issues_by_category:
                        issues_by_category[category] += 1

        # Calculate overall readability score
        total_issues = len(all_issues)
        analyzed_files = sum(
            1
            for path in python_files
            if not (
                config.get("exclude_test_files", False) and self._is_test_file(path)
            )
        )

        # # Simple scoring algorithm: fewer issues = higher score
        # if total_files > 1:
        #     issues_per_file = total_issues / total_files
        #     # Scale: 0 issues = 100%, 10+ issues per file = 0%
        #     overall_score = max(0, min(100, 100 - (issues_per_file * 10)))
        # else:
        #     overall_score = 100 / total_issues
        overall_result = dict(overall_details)
        total = sum(overall_result.values()) or 1
        overall_result["total_issues"] = total
        # Keep score bounded and deterministic when no issues are found.
        if not scores:
            overall_score = 100.0
        else:
            overall_score = max(0.0, min(100.0, round(statistics.mean(scores), 2)))

        return {
            "all_issues": all_issues,
            "total_issues": total_issues,
            "issues_by_category": issues_by_category,
            "overall_readability_score": overall_score,
            "overall_readability_details": overall_result,
            "files_analyzed": analyzed_files,
        }

    async def _run_ruff_analysis(
        self, file_path: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run Ruff analysis on a single file."""
        try:
            timeout = config.get("ruff_timeout", 60)
            selected = self._get_issues_to_report()

            # Run Ruff with JSON output
            proc = await asyncio.create_subprocess_exec(
                "ruff",
                "check",
                os.fspath(file_path),
                "--select",
                ",".join(selected),
                "--output-format",
                "json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            output_text = (stdout or b"").decode(errors="ignore")
            error_text = (stderr or b"").decode(errors="ignore").strip()

            if output_text:
                try:
                    ruff_output = json.loads(output_text)
                    if not isinstance(ruff_output, list):
                        logger.warning(
                            f"Unexpected Ruff output format for {file_path}: {type(ruff_output)}"
                        )
                        return {"issues": [], "score": 100.0, "counts": {}}

                    issues = self._process_ruff_output(ruff_output, file_path)
                    return {
                        "issues": issues,
                        "score": max(0.0, 100.0 - (len(issues) * 2.5)),
                        "counts": dict(
                            Counter(
                                issue.get("symbol")
                                for issue in issues
                                if issue.get("symbol")
                            )
                        ),
                    }
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Failed to parse Ruff JSON output for {file_path}: {e}"
                    )
                    return {"issues": [], "score": 100.0, "counts": {}}
            elif proc.returncode == 0:
                # No issues found
                return {"issues": [], "score": 100.0, "counts": {}}
            elif error_text:
                logger.warning(
                    f"Ruff returned diagnostics for {file_path}: {error_text}"
                )
                return {"issues": [], "score": 100.0, "counts": {}}
            else:
                # No issues found
                return {"issues": [], "score": 100.0, "counts": {}}

        except asyncio.TimeoutError:
            logger.warning(f"Ruff analysis timed out for {file_path}")
            return {"issues": [], "score": 100.0, "counts": {}}
        except FileNotFoundError:
            logger.warning("Ruff not found. Install with: pip install ruff")
            return {"issues": [], "score": 100.0, "counts": {}}
        except Exception as e:
            traceback.print_exc()
            logger.warning(f"Error running Ruff on {file_path}: {str(e)}")
            return {"issues": [], "score": 100.0, "counts": {}}

    def _process_ruff_output(
        self, ruff_output: List[Dict], file_path: str
    ) -> List[Dict[str, Any]]:
        """Process Ruff JSON output into our format."""
        processed_issues = []

        for issue in ruff_output:
            if not isinstance(issue, dict):
                continue
            symbol = issue.get("code", "")
            message = issue.get("message", "")
            location = issue.get("location", {})
            if not isinstance(location, dict):
                location = {}

            line_number = location.get("row", 0)
            if line_number in (None, ""):
                line_number = 0
            column = location.get("column", 0)
            if column in (None, ""):
                column = 0

            issue_info = self.readability_issue_mapping.get(
                symbol,
                {
                    "category": "clarity",
                    "title": f"Code Quality Issue: {symbol}",
                    "severity": SeverityLevel.LOW,
                    "complexity": ComplexityLevel.SIMPLE,
                },
            )
            spf = "/".join(file_path.split("/")[-2:])
            processed_issue = {
                "symbol": symbol,
                "message_id": symbol,
                "object": issue.get("name", ""),
                "message": message,
                "line_number": line_number,
                "column": column,
                "category": issue_info["category"],
                "title": issue_info["title"],
                "severity": issue_info["severity"],
                "complexity": issue_info["complexity"],
                "file_path": spf or file_path,
                "details": self.get_issue_detail(symbol),
            }

            processed_issues.append(processed_issue)
        return processed_issues

    def _is_test_file(self, file_path: str) -> bool:
        """Check if a file is a test file."""
        filename = os.path.basename(file_path).lower()
        return (
            filename.startswith("test_")
            or filename.endswith("_test.py")
            or "test" in filename
            or "/test" in file_path.lower()
        )

    def _get_object_mapping(self, symbol: str) -> str:
        OBJECT_SYMBOLS = {
            "D103": "Function",
            "PLR0913": "Function",
            "D101": "Class",
            "PLR0914": "Function",
            "F841": "Variable",
            "F401": "Import",
        }

        return OBJECT_SYMBOLS.get(symbol, "In")

    async def _club_analysis_results(
        self, analysis_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Club recurring rule codes per file into a single finding each, adding a `clubbed`
        dict with 'lines' and 'messages'. Non-recurring rules are returned unchanged.
        Updates total_issues and issues_by_category.
        """

        src_issues: List[Dict[str, Any]] = analysis_results.get("all_issues", [])

        # Fallback normalization via title → symbol (covers tools that set only title)
        TITLE_TO_SYMBOL = {
            "line too long": "E501",
            "documentation too long": "E501",
            "missing class docstring": "D101",
            "missing function docstring": "D103",
            "too many function arguments": "PLR0913",
            "too many local variables": "PLR0914",
            "too many statements": "PLR0915",
            "unused variable": "F841",
            "unused import": "F401",
            "trailing whitespace": "W291",
            "blank line contains whitespace": "W293",
            "tab indentation": "W191",
            "bad indentation": "E111",
        }

        # Keyed by (file_path, normalized_symbol)
        grouped_issues: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        grouped_keys: List[Tuple[str, str]] = []

        out: List[Dict[str, Any]] = []

        def normalize_symbol(issue: Dict[str, Any]) -> str:
            s = (issue.get("symbol") or "").strip().upper()
            if s:
                return s
            # fallback via title
            t = (issue.get("title") or "").strip().lower()
            return TITLE_TO_SYMBOL.get(t, "")

        for issue in src_issues:
            file_path = issue.get("file_path")
            sym = normalize_symbol(issue)
            # Only group when both file and rule code can be identified
            if file_path and sym:
                key = (file_path, sym)
                if key not in grouped_issues:
                    grouped_issues[key] = []
                    grouped_keys.append(key)
                grouped_issues[key].append(issue)
            else:
                # pass-through for non-clubbed or missing file_path
                out.append(issue)

        # Emit one merged finding per (file, symbol) when repeated
        for key in grouped_keys:
            issues = grouped_issues.get(key, [])
            if len(issues) > 1:
                merged = dict(issues[0])
                lines = []
                messages: List[str] = []
                for issue in issues:
                    line_number = issue.get("line_number")
                    if isinstance(line_number, int):
                        lines.append(line_number)
                    message = issue.get("message") or ""
                    if not message:
                        continue
                    obj = issue.get("object")
                    if obj:
                        messages.append(
                            f"{self._get_object_mapping(key[1])} `{obj}` | {message}"
                        )
                    else:
                        messages.append(message)

                merged["message"] = merged["title"]
                merged["clubbed"] = {
                    "lines": sorted(list(x for x in lines if isinstance(x, int))),
                    "messages": messages,
                }
                merged["line_number"] = None
                merged["column"] = None
                out.append(merged)
            else:
                out.append(issues[0])

        # --- Update summary ---
        new_total = len(out)
        by_cat: Dict[str, int] = defaultdict(int)
        for f in out:
            by_cat[f.get("category", "uncategorized")] += 1

        updated = dict(analysis_results)
        updated["all_issues"] = out
        updated["total_issues"] = new_total
        updated["issues_by_category"] = dict(by_cat)
        # keep overall_readability_score and files_analyzed unchanged
        return updated

    async def _generate_findings(
        self, analysis_results: Dict[str, Any], target_path: str, config: Dict[str, Any]
    ) -> List[UnifiedFinding]:
        """Generate findings based on readability analysis results."""
        findings = []

        # Check overall readability score
        overall_score = analysis_results["overall_readability_score"]
        overall_details = analysis_results["overall_readability_details"]
        minimum_threshold = config.get("minimum_readability_score", 75.0)
        target_path = str(target_path)
        spf = "/".join(target_path.split("/")[-2:])

        if overall_score < minimum_threshold:
            severity = (
                SeverityLevel.HIGH if overall_score < 50 else SeverityLevel.MEDIUM
            )
            finding = UnifiedFinding(
                title="Poor Code Readability",
                description=f"Code readability score is {overall_score:.1f}%, below recommended {minimum_threshold}%",
                details=overall_details,
                category=FindingCategory.QUALITY,
                severity=severity,
                confidence_score=0.8,
                location=CodeLocation(file_path=spf or target_path),
                rule_id="LOW_READABILITY_SCORE",
                remediation_guidance=f"Improve code readability to reach {minimum_threshold}% score",
                remediation_complexity=ComplexityLevel.MODERATE,
                source_analyzer=self.name,
                tags={"readability", "code_quality", "maintainability"},
                extra_data={
                    "readability_score": overall_score,
                    "minimum_threshold": minimum_threshold,
                    "issues_by_category": analysis_results["issues_by_category"],
                },
            )
            findings.append(finding)

        # Generate findings for individual readability issues
        for issue in analysis_results["all_issues"]:
            finding = UnifiedFinding(
                title=issue["title"],
                description=issue["message"],
                details=issue["details"],
                clubbed=issue.get("clubbed", None),
                category=FindingCategory.QUALITY,
                severity=issue["severity"],
                confidence_score=0.8,
                location=CodeLocation(
                    file_path=issue["file_path"],
                    line_number=issue["line_number"],
                    column=issue["column"],
                ),
                rule_id=issue["symbol"],
                remediation_guidance=self._get_remediation_guidance(issue["symbol"]),
                remediation_complexity=issue["complexity"],
                source_analyzer=self.name,
                tags={"readability", issue["category"], "ruff"},
                extra_data={
                    "ruff_rule_id": issue["message_id"],
                    "readability_category": issue["category"],
                },
            )
            findings.append(finding)

        return findings

    def _get_remediation_guidance(self, symbol: str) -> str:
        """Get specific remediation guidance for Ruff rules."""
        remediation_mapping = {
            "D100": "Add a module-level docstring explaining the purpose of this module",
            "D101": "Add a class docstring explaining purpose and usage of the class",
            "D102": "Add a docstring for special methods where useful",
            "D103": "Add a function docstring with parameters and return values",
            "D105": "Add a docstring for this special method",
            "D107": "Add a docstring to __init__",
            "D200": "Put the closing triple quote on a line of its own",
            "D201": "Add a blank line after the docstring",
            "D205": "Add a blank line after the first line of the docstring",
            "D206": "Use triple double quotes for docstrings if consistent with project style",
            "D211": "Add a blank line before the class docstring",
            "D212": "Put summary line at first line of docstring",
            "D300": "Use triple double quotes for multiline docstrings",
            "D400": "End the first line of docstring with a period",
            "D401": "Use imperative mood in docstring summary line",
            "D403": "Use an imperative verb in the first word of the docstring summary",
            "N802": "Use snake_case for function names",
            "N803": "Use snake_case for function arguments",
            "N806": "Use snake_case for class-level variable names",
            "N816": "Use lowercase with underscores for class-scoped names",
            "E111": "Fix indentation to use 4 spaces per level",
            "E112": "Use spaces for indentation, aligned to blocks",
            "E117": "Normalize indentation to avoid over-indentation",
            "W191": "Replace tab indentation with spaces",
            "W291": "Remove trailing whitespace",
            "W293": "Remove trailing whitespace on blank lines",
            "W391": "Remove extra blank lines at file end",
            "W505": "Break long lines into smaller chunks",
            "E501": "Break long lines into multiple lines",
            "F401": "Remove unused imports",
            "F841": "Remove unused local variables",
            "PLR0913": "Reduce function arguments by grouping related values",
            "PLR0914": "Split large local state into smaller helper functions",
            "PLR0915": "Split the function to reduce statements",
            "E999": "Fix parse errors first so style checks can continue",
        }

        return remediation_mapping.get(
            symbol, "Follow Python style guidelines and best practices"
        )

    def _create_empty_result(self) -> AnalysisResult:
        """Create an empty analysis result."""
        metrics = AnalysisMetrics(
            analyzer_name=self.name,
            execution_time_seconds=0.0,
            files_analyzed=0,
            findings_count=0,
            error_count=0,
            success=True,
        )
        return AnalysisResult(findings=[], metrics=metrics, metadata={})
