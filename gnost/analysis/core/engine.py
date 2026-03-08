"""
Unified Analysis Engine - Core orchestration system for all analysis modules.
"""

# Flake8: noqa: E501
import os
import time
import asyncio
import traceback
from typing import List, Dict, Any, Optional

from gnost.analysis.core.models import (
    ConsolidatedReport,
    AnalysisConfiguration,
    UnifiedFinding,
    AnalysisMetrics,
    SeverityLevel,
)
from gnost.analysis.core.interfaces import (
    BaseAnalyzer,
    AnalysisResult,
    AnalyzerRegistry,
)
from gnost.analysis.core.aggregator import ResultAggregator
from gnost.analysis.core.transformers import DataTransformer
from gnost.utils.logger import AppLogger

logger = AppLogger.get_logger(__name__)


class UnifiedAnalysisEngine:
    """
    Central orchestration system for running multiple analysis modules
    and consolidating their results.
    """

    def __init__(self, analyzer_registry: Optional[AnalyzerRegistry] = None):
        self.aggregator = ResultAggregator()
        self.transformer = DataTransformer()
        self._analysis_history: List[ConsolidatedReport] = []
        self.analyzer_registry = analyzer_registry or AnalyzerRegistry()

    async def analyze(
        self, config: AnalysisConfiguration, progress_cb=None
    ) -> ConsolidatedReport:
        """
        Run comprehensive analysis using all enabled analyzers.

        Args:
            config: Analysis configuration

        Returns:
            Consolidated report with all findings
        """
        start_time = time.time()

        logger.info(
            f"Starting unified analysis of {os.path.basename(config.target_path)}"
        )

        # Initialize report
        report = ConsolidatedReport(
            target_path=config.target_path, analysis_config=self._config_to_dict(config)
        )

        try:
            # Get enabled analyzers
            analyzers = self._get_analyzers_for_config(config)

            if not analyzers:
                logger.warning("No analyzers enabled for analysis")
                return report

            logger.info(
                f"Running {len(analyzers)} analyzers: {[a.get_name() for a in analyzers]}"
            )
            logger.info(f"Parallel Execution:{config.parallel_execution}")
            if progress_cb:
                progress_cb(increment=0, total_analyzers=len(analyzers))
            # Run analysis modules
            if config.parallel_execution:
                analysis_results = await self._run_parallel_analysis(
                    analyzers, config, progress_cb
                )
            else:
                analysis_results = await self._run_sequential_analysis(
                    analyzers, config, progress_cb
                )

            # Aggregate results
            report = await self._aggregate_results(analysis_results, report, config)

            # Calculate total execution time
            report.total_execution_time = time.time() - start_time

            # Store in history
            self._analysis_history.append(report)

            logger.info(f"Analysis completed in {report.total_execution_time:.2f}s")
            logger.info(f"Found {len(report.findings)} total findings")

            return report

        except asyncio.CancelledError:
            logger.info("Analysis cancelled by user.")
            raise
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Analysis failed: {str(e)}")
            # Return partial report with error information
            report.total_execution_time = time.time() - start_time
            report.summary["error"] = str(e)
            return report

    async def analyze_file(
        self, file_path: str, config: Optional[AnalysisConfiguration] = None
    ) -> ConsolidatedReport:
        """
        Analyze a single file.

        Args:
            file_path: Path to the file to analyze
            config: Optional analysis configuration

        Returns:
            Consolidated report for the file
        """
        if config is None:
            config = AnalysisConfiguration()

        config.target_path = file_path
        return await self.analyze(config)

    async def analyze_directory(
        self, directory_path: str, config: Optional[AnalysisConfiguration] = None
    ) -> ConsolidatedReport:
        """
        Analyze all files in a directory.

        Args:
            directory_path: Path to the directory to analyze
            config: Optional analysis configuration

        Returns:
            Consolidated report for the directory
        """
        if config is None:
            config = AnalysisConfiguration()

        config.target_path = directory_path
        return await self.analyze(config)

    def get_analysis_history(self) -> List[ConsolidatedReport]:
        """Get history of previous analyses."""
        return self._analysis_history.copy()

    def get_latest_report(self) -> Optional[ConsolidatedReport]:
        """Get the most recent analysis report."""
        return self._analysis_history[-1] if self._analysis_history else None

    def clear_history(self) -> None:
        """Clear analysis history."""
        self._analysis_history.clear()

    async def _run_parallel_analysis(
        self,
        analyzers: List[BaseAnalyzer],
        config: AnalysisConfiguration,
        progress_cb=None,
    ) -> List[AnalysisResult]:
        """Run analyzers in parallel."""
        tasks = []
        for analyzer in analyzers:
            task = asyncio.create_task(
                self._run_single_analyzer(analyzer, config, progress_cb),
                name=f"analyzer_{analyzer.get_name()}",
            )
            tasks.append(task)

        # Wait for all tasks with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=config.timeout_seconds,
            )

            # Filter out exceptions and log them
            valid_results = []
            for i, result in enumerate(results):
                analyzer_name = analyzers[i].get_name()
                if isinstance(result, Exception):
                    traceback.print_exc()
                    logger.error(f"Analyzer {analyzer_name} failed: {str(result)}")

                    # Create error metrics
                    error_metrics = AnalysisMetrics(
                        analyzer_name=analyzer_name,
                        execution_time_seconds=0.0,
                        files_analyzed=0,
                        findings_count=0,
                        error_count=1,
                        success=False,
                        error_message=str(result),
                    )

                    valid_results.append(
                        AnalysisResult(
                            findings=[],
                            metrics=error_metrics,
                            metadata={"error": str(result)},
                        )
                    )
                else:
                    valid_results.append(result)

            return valid_results

        except asyncio.TimeoutError:
            logger.error(f"Analysis timed out after {config.timeout_seconds} seconds")
            # Cancel remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()

            # Return partial results
            return [
                task.result() for task in tasks if task.done() and not task.exception()
            ]
        except asyncio.CancelledError:
            # Propagate cancellation but make sure tasks are cleaned up
            logger.error("Analysis interrupted by user.")
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

    async def _run_sequential_analysis(
        self,
        analyzers: List[BaseAnalyzer],
        config: AnalysisConfiguration,
        progress_cb=None,
    ) -> List[AnalysisResult]:
        """Run analyzers sequentially."""
        results = []
        for analyzer in analyzers:
            try:
                result = await self._run_single_analyzer(analyzer, config, progress_cb)
                results.append(result)
            except Exception as e:
                traceback.print_exc()
                logger.error(f"Analyzer {analyzer.get_name()} failed: {str(e)}")

                # Create error result
                error_metrics = AnalysisMetrics(
                    analyzer_name=analyzer.get_name(),
                    execution_time_seconds=0.0,
                    files_analyzed=0,
                    findings_count=0,
                    error_count=1,
                    success=False,
                    error_message=str(e),
                )

                results.append(
                    AnalysisResult(
                        findings=[], metrics=error_metrics, metadata={"error": str(e)}
                    )
                )

        return results

    async def _run_single_analyzer(
        self, analyzer: BaseAnalyzer, config: AnalysisConfiguration, progress_cb=None
    ) -> AnalysisResult:
        """Run a single analyzer with error handling and timeout."""
        start_time = time.time()
        analyzer_name = analyzer.get_name()

        logger.debug(f"Starting analyzer: {analyzer_name}")

        try:
            # Check if analyzer is enabled
            if not analyzer.is_enabled():
                logger.debug(f"Analyzer {analyzer_name} is disabled, skipping")
                return AnalysisResult(
                    findings=[],
                    metrics=AnalysisMetrics(
                        analyzer_name=analyzer_name,
                        execution_time_seconds=0.0,
                        files_analyzed=0,
                        findings_count=0,
                        success=True,
                    ),
                    metadata={"skipped": "disabled"},
                )

            # Run the analyzer
            if progress_cb:
                progress_cb(increment=0, stage=f"{analyzer_name} running")
            result = await analyzer.analyze(config)

            # Apply filters and transformations
            filtered_findings = self._apply_filters(result.findings, config)

            # Update metrics
            result.metrics.execution_time_seconds = time.time() - start_time
            result.metrics.findings_count = len(filtered_findings)

            logger.debug(
                f"Analyzer {analyzer_name} completed in {result.metrics.execution_time_seconds:.2f}s"
            )
            logger.debug(f"Found {len(filtered_findings)} findings")

            return AnalysisResult(
                findings=filtered_findings,
                metrics=result.metrics,
                metadata=result.metadata,
            )

        except Exception as e:
            traceback.print_exc()
            execution_time = time.time() - start_time
            logger.error(
                f"Analyzer {analyzer_name} failed after {execution_time:.2f}s: {str(e)}"
            )
            raise
        finally:
            if progress_cb:
                progress_cb(increment=1, stage=f"{analyzer_name} finished")

    def _apply_filters(
        self, findings: List[UnifiedFinding], config: AnalysisConfiguration
    ) -> List[UnifiedFinding]:
        """Apply filtering based on configuration."""
        filtered = findings

        # Apply severity threshold
        if config.severity_threshold != SeverityLevel.INFO:
            severity_order = [
                SeverityLevel.CRITICAL,
                SeverityLevel.HIGH,
                SeverityLevel.MEDIUM,
                SeverityLevel.LOW,
                SeverityLevel.INFO,
            ]
            threshold_index = severity_order.index(config.severity_threshold)
            allowed_severities = set(severity_order[: threshold_index + 1])
            filtered = [f for f in filtered if f.severity in allowed_severities]

        # Apply confidence filter
        if not config.include_low_confidence:
            filtered = [f for f in filtered if f.confidence_score >= 0.7]

        # Apply max findings limit
        if config.max_findings_per_analyzer > 0:
            # Sort by severity and confidence, then take top N
            filtered = sorted(
                filtered,
                key=lambda f: (
                    [
                        SeverityLevel.CRITICAL,
                        SeverityLevel.HIGH,
                        SeverityLevel.MEDIUM,
                        SeverityLevel.LOW,
                        SeverityLevel.INFO,
                    ].index(f.severity),
                    -f.confidence_score,
                ),
            )[: config.max_findings_per_analyzer]

        return filtered

    def _get_analyzers_for_config(
        self, config: AnalysisConfiguration
    ) -> List[BaseAnalyzer]:
        """Get analyzers based on configuration."""
        if self.analyzer_registry is None:
            return []

        if config.enabled_analyzers:
            # Use specific analyzers from config
            analyzers = []
            for analyzer_name in config.enabled_analyzers:
                analyzer = self.analyzer_registry.get_analyzer(analyzer_name)
                if analyzer:
                    analyzers.append(analyzer)
                else:
                    logger.warning(f"Analyzer '{analyzer_name}' not found in registry")
            return analyzers
        else:
            # Use all enabled analyzers
            return self.analyzer_registry.get_enabled_analyzers()

    async def _aggregate_results(
        self,
        results: List[AnalysisResult],
        report: ConsolidatedReport,
        config: AnalysisConfiguration,
    ) -> ConsolidatedReport:
        """Aggregate analysis results into consolidated report."""
        all_findings = []
        all_metrics = []

        for result in results:
            all_findings.extend(result.findings)
            all_metrics.append(result.metrics)

        # Use aggregator to process findings
        report.findings = await self.aggregator.aggregate_findings(all_findings)
        report.analysis_metrics = all_metrics

        # Generate summary
        report.summary = await self.aggregator.generate_summary(report)

        return report

    def _config_to_dict(self, config: AnalysisConfiguration) -> Dict[str, Any]:
        """Convert configuration to dictionary for storage."""
        return {
            "target_path": config.target_path,
            "file_patterns": config.file_patterns,
            "exclude_patterns": config.exclude_patterns,
            "enabled_analyzers": list(config.enabled_analyzers),
            "severity_threshold": config.severity_threshold.value,
            "parallel_execution": config.parallel_execution,
            "timeout_seconds": config.timeout_seconds,
            "include_low_confidence": config.include_low_confidence,
            "max_findings_per_analyzer": config.max_findings_per_analyzer,
        }
