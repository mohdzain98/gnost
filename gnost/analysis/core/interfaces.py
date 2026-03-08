"""
Common interfaces for analysis modules.
Defines the contract that all analysis modules must implement.
"""

# Flake8: noqa: E501

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass
from gnost.analysis.core.models import (
    UnifiedFinding,
    AnalysisMetrics,
    AnalysisConfiguration,
)


@dataclass
class AnalysisResult:
    """Result from an individual analysis module."""

    findings: List[UnifiedFinding]
    metrics: AnalysisMetrics
    metadata: Dict[str, Any]


class BaseAnalyzer(ABC):
    """Base class for all code analysis modules."""

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.enabled = True

    @abstractmethod
    async def analyze(self, config: AnalysisConfiguration) -> AnalysisResult:
        """
        Perform analysis on the given target.

        Args:
            config: Analysis configuration including target path and options

        Returns:
            AnalysisResult containing findings and metrics
        """
        pass

    @abstractmethod
    def get_supported_file_types(self) -> List[str]:
        """
        Return list of file extensions this analyzer supports.

        Returns:
            List of file extensions (e.g., ['.py', '.js'])
        """
        pass

    def can_analyze(self, file_path: str) -> bool:
        """
        Check if this analyzer can analyze the given file.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the analyzer can handle this file type
        """
        supported_types = self.get_supported_file_types()
        return any(file_path.lower().endswith(ext.lower()) for ext in supported_types)

    def get_name(self) -> str:
        """Get the analyzer name."""
        return self.name

    def get_version(self) -> str:
        """Get the analyzer version."""
        return self.version

    def is_enabled(self) -> bool:
        """Check if the analyzer is enabled."""
        return self.enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the analyzer."""
        self.enabled = enabled

    @abstractmethod
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration for this analyzer.

        Returns:
            Dictionary of default configuration options
        """
        pass

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate analyzer-specific configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if configuration is valid
        """
        # Default implementation - can be overridden
        return True


class StreamingAnalyzer(BaseAnalyzer):
    """Base class for analyzers that support streaming results."""

    @abstractmethod
    async def analyze_streaming(
        self, config: AnalysisConfiguration
    ) -> AsyncIterator[UnifiedFinding]:
        """
        Perform analysis with streaming results.

        Args:
            config: Analysis configuration

        Yields:
            Individual findings as they are discovered
        """
        pass


class SecurityAnalyzer(BaseAnalyzer):
    """Base class for security-focused analyzers."""

    @abstractmethod
    def get_security_categories(self) -> List[str]:
        """
        Get list of security categories this analyzer covers.

        Returns:
            List of security categories (e.g., ['injection', 'secrets'])
        """
        pass

    @abstractmethod
    def get_cwe_mappings(self) -> Dict[str, str]:
        """
        Get mapping of rules to CWE identifiers.

        Returns:
            Dictionary mapping rule IDs to CWE IDs
        """
        pass


class QualityAnalyzer(BaseAnalyzer):
    """Base class for code quality analyzers."""

    @abstractmethod
    def get_quality_metrics(self) -> List[str]:
        """
        Get list of quality metrics this analyzer provides.

        Returns:
            List of quality metrics (e.g., ['complexity', 'maintainability'])
        """
        pass


class ComplianceAnalyzer(BaseAnalyzer):
    """Base class for compliance-focused analyzers."""

    # @abstractmethod
    # def get_compliance_frameworks(self) -> List[str]:
    #     """
    #     Get list of compliance frameworks this analyzer supports.

    #     Returns:
    #         List of frameworks (e.g., ['GDPR', 'HIPAA', 'PCI-DSS'])
    #     """
    #     pass

    @abstractmethod
    def check_compliance(self, config: AnalysisConfiguration) -> Dict[str, bool]:
        """
        Check compliance against supported frameworks.

        Args:
            config: Analysis configuration

        Returns:
            Dictionary mapping framework names to compliance status
        """
        pass


class AnalyzerRegistry:
    """Registry for managing analysis modules."""

    def __init__(self):
        self._analyzers: Dict[str, BaseAnalyzer] = {}
        self._categories: Dict[str, List[str]] = {
            "security": [],
            "quality": [],
            "compliance": [],
            "performance": [],
            "all": [],
        }

    def register(self, analyzer: BaseAnalyzer) -> None:
        """
        Register an analyzer.

        Args:
            analyzer: Analyzer instance to register
        """
        name = analyzer.get_name()
        self._analyzers[name] = analyzer
        self._categories["all"].append(name)

        # Categorize analyzers
        if isinstance(analyzer, SecurityAnalyzer):
            self._categories["security"].append(name)
        elif isinstance(analyzer, QualityAnalyzer):
            self._categories["quality"].append(name)
        elif isinstance(analyzer, ComplianceAnalyzer):
            self._categories["compliance"].append(name)

    def get_analyzer(self, name: str) -> Optional[BaseAnalyzer]:
        """
        Get analyzer by name.

        Args:
            name: Name of the analyzer

        Returns:
            Analyzer instance or None if not found
        """
        return self._analyzers.get(name)

    def get_analyzers_by_category(self, category: str) -> List[BaseAnalyzer]:
        """
        Get all analyzers in a category.

        Args:
            category: Category name ('security', 'quality', 'compliance', 'all')

        Returns:
            List of analyzer instances
        """
        analyzer_names = self._categories.get(category, [])
        return [
            self._analyzers[name] for name in analyzer_names if name in self._analyzers
        ]

    def get_all_analyzers(self) -> List[BaseAnalyzer]:
        """Get all registered analyzers."""
        return list(self._analyzers.values())

    def get_enabled_analyzers(self) -> List[BaseAnalyzer]:
        """Get all enabled analyzers."""
        return [
            analyzer for analyzer in self._analyzers.values() if analyzer.is_enabled()
        ]

    def list_analyzer_names(self) -> List[str]:
        """Get list of all registered analyzer names."""
        return list(self._analyzers.keys())

    def enable_analyzer(self, name: str) -> bool:
        """
        Enable an analyzer.

        Args:
            name: Name of the analyzer to enable

        Returns:
            True if analyzer was found and enabled
        """
        analyzer = self.get_analyzer(name)
        if analyzer:
            analyzer.set_enabled(True)
            return True
        return False

    def disable_analyzer(self, name: str) -> bool:
        """
        Disable an analyzer.

        Args:
            name: Name of the analyzer to disable

        Returns:
            True if analyzer was found and disabled
        """
        analyzer = self.get_analyzer(name)
        if analyzer:
            analyzer.set_enabled(False)
            return True
        return False

    def get_analyzers_for_file(self, file_path: str) -> List[BaseAnalyzer]:
        """
        Get all analyzers that can handle the given file.

        Args:
            file_path: Path to the file

        Returns:
            List of compatible analyzers
        """
        compatible = []
        for analyzer in self.get_enabled_analyzers():
            if analyzer.can_analyze(file_path):
                compatible.append(analyzer)
        return compatible
