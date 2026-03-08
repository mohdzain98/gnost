"""
Data transformation utilities for converting findings from different analyzers
to the unified format.
"""

# Flake8: noqa: E501
from gnost.utils.logger import AppLogger
from typing import Dict, Any, Optional, Callable

from gnost.analysis.core.models import (
    UnifiedFinding,
    CodeLocation,
    SeverityLevel,
    FindingCategory,
    ComplexityLevel,
    AnalysisMetrics,
)


logger = AppLogger.get_logger(__name__)


class DataTransformer:
    """
    Transforms findings from different analyzers into unified format.
    """

    def __init__(self):
        # Register transformation functions for different analyzers
        self._transformers: Dict[str, Callable] = {
            "gitleaks": self._transform_gitleaks_finding,
            "bandit": self._transform_bandit_finding,
            "pylint": self._transform_pylint_finding,
            "mypy": self._transform_mypy_finding,
            "semgrep": self._transform_semgrep_finding,
            "pii_scanner": self._transform_pii_finding,
            "testability": self._transform_testability_finding,
            "observability": self._transform_observability_finding,
            "safety": self._transform_safety_finding,
            "robustness": self._transform_robustness_finding,
            "pii_phi": self._transform_pii_phi_finding,
            "readability": self._transform_readability_finding,
            "injection": self._transform_injection_finding,
        }

        # CWE mapping for common security issues
        self._cwe_mapping = {
            # Injection vulnerabilities
            "sql_injection": "CWE-89",
            "command_injection": "CWE-78",
            "code_injection": "CWE-94",
            "ldap_injection": "CWE-90",
            "xpath_injection": "CWE-643",
            # Authentication and session management
            "hardcoded_password": "CWE-259",
            "hardcoded_key": "CWE-798",
            "weak_cryptography": "CWE-327",
            "insecure_random": "CWE-338",
            "session_fixation": "CWE-384",
            # Access control
            "path_traversal": "CWE-22",
            "improper_authorization": "CWE-285",
            "privilege_escalation": "CWE-269",
            # Input validation
            "xss": "CWE-79",
            "buffer_overflow": "CWE-120",
            "integer_overflow": "CWE-190",
            "format_string": "CWE-134",
            # Information disclosure
            "sensitive_data_exposure": "CWE-200",
            "debug_info_leak": "CWE-489",
            "error_message_leak": "CWE-209",
            # Cryptographic issues
            "weak_hash": "CWE-327",
            "insecure_transport": "CWE-319",
            "cert_validation": "CWE-295",
        }

        # Severity mapping from different tools
        self._severity_mapping = {
            "critical": SeverityLevel.CRITICAL,
            "high": SeverityLevel.HIGH,
            "medium": SeverityLevel.MEDIUM,
            "low": SeverityLevel.LOW,
            "info": SeverityLevel.INFO,
            "information": SeverityLevel.INFO,
            "warning": SeverityLevel.MEDIUM,
            "error": SeverityLevel.HIGH,
        }

    def transform_finding(
        self, raw_finding: Dict[str, Any], analyzer_name: str
    ) -> Optional[UnifiedFinding]:
        """
        Transform a raw finding from an analyzer to unified format.

        Args:
            raw_finding: Raw finding data from analyzer
            analyzer_name: Name of the analyzer that produced the finding

        Returns:
            Unified finding or None if transformation fails
        """
        try:
            transformer = self._transformers.get(analyzer_name.lower())
            if transformer:
                return transformer(raw_finding, analyzer_name)
            else:
                logger.warning(f"No transformer found for analyzer: {analyzer_name}")
                return self._transform_generic_finding(raw_finding, analyzer_name)

        except Exception as e:
            logger.error(f"Failed to transform finding from {analyzer_name}: {str(e)}")
            logger.debug(f"Raw finding data: {raw_finding}")
            return None

    def transform_metrics(
        self, raw_metrics: Dict[str, Any], analyzer_name: str
    ) -> AnalysisMetrics:
        """
        Transform raw metrics to unified format.

        Args:
            raw_metrics: Raw metrics from analyzer
            analyzer_name: Name of the analyzer

        Returns:
            Unified analysis metrics
        """
        return AnalysisMetrics(
            analyzer_name=analyzer_name,
            execution_time_seconds=raw_metrics.get("execution_time", 0.0),
            files_analyzed=raw_metrics.get("files_analyzed", 0),
            findings_count=raw_metrics.get("findings_count", 0),
            error_count=raw_metrics.get("error_count", 0),
            warnings_count=raw_metrics.get("warnings_count", 0),
            success=raw_metrics.get("success", True),
            error_message=raw_metrics.get("error_message"),
        )

    def _transform_gitleaks_finding(
        self, raw: Dict[str, Any], analyzer: str
    ) -> UnifiedFinding:
        """Transform Gitleaks (hardcoded secrets) finding."""
        file_path = raw.get("File", "")
        line_number = raw.get("StartLine", raw.get("Line"))

        # Map rule to CWE
        rule_id = raw.get("RuleID", "")
        cwe_id = self._map_gitleaks_rule_to_cwe(rule_id)

        # Determine severity based on rule type
        severity = self._determine_gitleaks_severity(rule_id)

        return UnifiedFinding(
            title=f"Hardcoded Secret: {rule_id}",
            description=raw.get(
                "Description", f"Potential hardcoded secret detected: {rule_id}"
            ),
            category=FindingCategory.SECURITY,
            severity=severity,
            location=CodeLocation(
                file_path=file_path,
                line_number=line_number,
                end_line_number=raw.get("EndLine"),
            ),
            rule_id=rule_id,
            cwe_id=cwe_id,
            code_snippet=(
                raw.get("Secret", "")[:100] + "..." if raw.get("Secret") else None
            ),
            source_analyzer=analyzer,
            compliance_frameworks=["PCI-DSS", "SOX", "GDPR"],
            remediation_complexity=ComplexityLevel.SIMPLE,
            confidence_score=0.9,
            tags={"secrets", "credentials", "security"},
        )

    def _transform_bandit_finding(
        self, raw: Dict[str, Any], analyzer: str
    ) -> UnifiedFinding:
        """Transform Bandit security finding."""
        # Bandit findings typically have test_id, test_name, issue_severity, issue_confidence
        test_id = raw.get("test_id", "")
        test_name = raw.get("test_name", "")

        severity = self._map_bandit_severity(raw.get("issue_severity", "MEDIUM"))
        confidence = self._map_bandit_confidence(raw.get("issue_confidence", "MEDIUM"))

        return UnifiedFinding(
            title=f"Security Issue: {test_name}",
            description=raw.get("issue_text", ""),
            category=FindingCategory.SECURITY,
            severity=severity,
            location=CodeLocation(
                file_path=raw.get("filename", ""),
                line_number=raw.get("line_number"),
                end_line_number=raw.get("line_range", [None])[-1],
            ),
            rule_id=test_id,
            cwe_id=self._map_bandit_test_to_cwe(test_id),
            code_snippet=raw.get("code", ""),
            source_analyzer=analyzer,
            confidence_score=confidence,
            remediation_complexity=self._estimate_remediation_complexity(test_id),
            tags={"security", "static-analysis"},
        )

    def _transform_pylint_finding(
        self, raw: Dict[str, Any], analyzer: str
    ) -> UnifiedFinding:
        """Transform Pylint code quality finding."""
        message_id = raw.get("message-id", "")
        message = raw.get("message", "")

        severity = self._map_pylint_severity(raw.get("type", "convention"))

        return UnifiedFinding(
            title=f"Code Quality: {message_id}",
            description=message,
            category=FindingCategory.QUALITY,
            severity=severity,
            location=CodeLocation(
                file_path=raw.get("path", ""),
                line_number=raw.get("line"),
                column=raw.get("column"),
            ),
            rule_id=message_id,
            source_analyzer=analyzer,
            remediation_complexity=self._estimate_pylint_complexity(message_id),
            confidence_score=0.8,
            tags={"quality", "style", "maintainability"},
        )

    def _transform_mypy_finding(
        self, raw: Dict[str, Any], analyzer: str
    ) -> UnifiedFinding:
        """Transform MyPy type checking finding."""
        return UnifiedFinding(
            title="Type Error",
            description=raw.get("message", ""),
            category=FindingCategory.QUALITY,
            severity=SeverityLevel.MEDIUM,
            location=CodeLocation(
                file_path=raw.get("file", ""),
                line_number=raw.get("line"),
                column=raw.get("column"),
            ),
            source_analyzer=analyzer,
            remediation_complexity=ComplexityLevel.SIMPLE,
            confidence_score=0.9,
            tags={"types", "quality", "static-analysis"},
        )

    def _transform_semgrep_finding(
        self, raw: Dict[str, Any], analyzer: str
    ) -> UnifiedFinding:
        """Transform Semgrep finding."""
        rule_id = raw.get("check_id", "")

        return UnifiedFinding(
            title=f"Pattern Match: {rule_id}",
            description=raw.get("message", ""),
            category=FindingCategory.SECURITY,
            severity=self._map_semgrep_severity(raw.get("severity", "WARNING")),
            location=CodeLocation(
                file_path=raw.get("path", ""),
                line_number=raw.get("start", {}).get("line"),
                end_line_number=raw.get("end", {}).get("line"),
                column=raw.get("start", {}).get("col"),
            ),
            rule_id=rule_id,
            code_snippet=raw.get("extra", {}).get("lines", ""),
            source_analyzer=analyzer,
            confidence_score=0.85,
            tags={"security", "pattern-matching"},
        )

    def _transform_pii_finding(
        self, raw: Dict[str, Any], analyzer: str
    ) -> UnifiedFinding:
        """Transform PII/PHI scanner finding."""
        pattern_type = raw.get("pattern_type", "")

        return UnifiedFinding(
            title=f"PII/PHI Detection: {pattern_type}",
            description=raw.get("description", f"Potential {pattern_type} detected"),
            category=FindingCategory.PRIVACY,
            severity=self._determine_pii_severity(pattern_type),
            location=CodeLocation(
                file_path=raw.get("file_path", ""),
                line_number=raw.get("line_number"),
                function_name=raw.get("function_name"),
            ),
            rule_id=f"PII_{pattern_type.upper()}",
            code_snippet=raw.get("context", ""),
            source_analyzer=analyzer,
            compliance_frameworks=["GDPR", "HIPAA", "CCPA"],
            remediation_complexity=ComplexityLevel.MODERATE,
            confidence_score=raw.get("confidence", 0.8),
            tags={"privacy", "pii", "phi", "compliance"},
        )

    def _transform_testability_finding(
        self, raw: Dict[str, Any], analyzer: str
    ) -> UnifiedFinding:
        """Transform testability analysis finding."""
        issue_type = raw.get("issue_type", "testability")

        return UnifiedFinding(
            title=f"Testability Issue: {issue_type}",
            description=raw.get("description", ""),
            category=FindingCategory.TESTABILITY,
            severity=SeverityLevel.MEDIUM,
            location=CodeLocation(
                file_path=raw.get("file_path", ""),
                line_number=raw.get("line_number"),
                function_name=raw.get("function_name"),
            ),
            source_analyzer=analyzer,
            remediation_complexity=ComplexityLevel.MODERATE,
            confidence_score=0.7,
            tags={"testability", "quality", "maintainability"},
        )

    def _transform_observability_finding(
        self, raw: Dict[str, Any], analyzer: str
    ) -> UnifiedFinding:
        """Transform observability analysis finding."""
        return UnifiedFinding(
            title="Observability Gap",
            description=raw.get("description", "Missing logging or monitoring"),
            category=FindingCategory.OBSERVABILITY,
            severity=SeverityLevel.LOW,
            location=CodeLocation(
                file_path=raw.get("file_path", ""),
                line_number=raw.get("line_number"),
                function_name=raw.get("function_name"),
            ),
            source_analyzer=analyzer,
            remediation_complexity=ComplexityLevel.SIMPLE,
            confidence_score=0.6,
            tags={"observability", "logging", "monitoring"},
        )

    def _transform_safety_finding(
        self, raw: Dict[str, Any], analyzer: str
    ) -> UnifiedFinding:
        """Transform Safety (dependency vulnerability) finding."""
        package_name = raw.get("package", "")
        vulnerability_id = raw.get("vulnerability_id", "")

        return UnifiedFinding(
            title=f"Vulnerable Dependency: {package_name}",
            description=raw.get("advisory", ""),
            category=FindingCategory.DEPENDENCY,
            severity=self._map_safety_severity(raw.get("severity", "medium")),
            location=CodeLocation(
                file_path=raw.get("dependency_file", "requirements.txt")
            ),
            rule_id=vulnerability_id,
            cve_id=raw.get("cve"),
            source_analyzer=analyzer,
            remediation_complexity=ComplexityLevel.SIMPLE,
            confidence_score=0.95,
            tags={"dependency", "vulnerability", "security"},
        )

    def _transform_generic_finding(
        self, raw: Dict[str, Any], analyzer: str
    ) -> UnifiedFinding:
        """Generic transformation for unknown analyzers."""
        return UnifiedFinding(
            title=raw.get("title", raw.get("message", "Unknown Issue")),
            description=raw.get("description", raw.get("message", "")),
            category=FindingCategory.QUALITY,
            severity=self._map_generic_severity(raw.get("severity", "medium")),
            location=CodeLocation(
                file_path=raw.get("file", raw.get("path", raw.get("filename", ""))),
                line_number=raw.get("line", raw.get("line_number")),
            ),
            source_analyzer=analyzer,
            confidence_score=0.5,
            tags={"generic"},
        )

    # Helper methods for specific transformations

    def _map_gitleaks_rule_to_cwe(self, rule_id: str) -> Optional[str]:
        """Map Gitleaks rule to CWE."""
        rule_mappings = {
            "aws-access-token": "CWE-798",
            "aws-secret-key": "CWE-798",
            "github-pat": "CWE-522",
            "private-key": "CWE-321",
            "password": "CWE-259",
            "api-key": "CWE-321",
        }

        for pattern, cwe in rule_mappings.items():
            if pattern in rule_id.lower():
                return cwe

        return "CWE-798"  # Default for hardcoded credentials

    def _determine_gitleaks_severity(self, rule_id: str) -> SeverityLevel:
        """Determine severity for Gitleaks findings."""
        critical_patterns = ["private-key", "secret-key", "aws-secret"]
        high_patterns = ["password", "token", "api-key"]

        rule_lower = rule_id.lower()

        if any(pattern in rule_lower for pattern in critical_patterns):
            return SeverityLevel.CRITICAL
        elif any(pattern in rule_lower for pattern in high_patterns):
            return SeverityLevel.HIGH
        else:
            return SeverityLevel.MEDIUM

    def _map_bandit_severity(self, severity: str) -> SeverityLevel:
        """Map Bandit severity to unified severity."""
        mapping = {
            "HIGH": SeverityLevel.HIGH,
            "MEDIUM": SeverityLevel.MEDIUM,
            "LOW": SeverityLevel.LOW,
        }
        return mapping.get(severity.upper(), SeverityLevel.MEDIUM)

    def _map_bandit_confidence(self, confidence: str) -> float:
        """Map Bandit confidence to numeric value."""
        mapping = {"HIGH": 0.9, "MEDIUM": 0.6, "LOW": 0.3}
        return mapping.get(confidence.upper(), 0.6)

    def _map_bandit_test_to_cwe(self, test_id: str) -> Optional[str]:
        """Map Bandit test ID to CWE."""
        mappings = {
            "B101": "CWE-259",  # assert_used
            "B102": "CWE-78",  # exec_used
            "B103": "CWE-264",  # set_bad_file_permissions
            "B104": "CWE-200",  # hardcoded_bind_all_interfaces
            "B105": "CWE-259",  # hardcoded_password_string
            "B106": "CWE-259",  # hardcoded_password_funcarg
            "B107": "CWE-259",  # hardcoded_password_default
            "B108": "CWE-377",  # hardcoded_tmp_directory
            "B110": "CWE-703",  # try_except_pass
            "B112": "CWE-703",  # try_except_continue
            "B113": "CWE-400",  # request_without_timeout
        }
        return mappings.get(test_id)

    def _map_pylint_severity(self, msg_type: str) -> SeverityLevel:
        """Map Pylint message type to severity."""
        mapping = {
            "error": SeverityLevel.HIGH,
            "warning": SeverityLevel.MEDIUM,
            "refactor": SeverityLevel.LOW,
            "convention": SeverityLevel.LOW,
            "info": SeverityLevel.INFO,
        }
        return mapping.get(msg_type.lower(), SeverityLevel.MEDIUM)

    def _map_semgrep_severity(self, severity: str) -> SeverityLevel:
        """Map Semgrep severity to unified severity."""
        mapping = {
            "ERROR": SeverityLevel.HIGH,
            "WARNING": SeverityLevel.MEDIUM,
            "INFO": SeverityLevel.LOW,
        }
        return mapping.get(severity.upper(), SeverityLevel.MEDIUM)

    def _determine_pii_severity(self, pattern_type: str) -> SeverityLevel:
        """Determine severity for PII findings."""
        critical_patterns = ["ssn", "credit_card", "passport"]
        high_patterns = ["email", "phone", "medical_record"]

        pattern_lower = pattern_type.lower()

        if any(pattern in pattern_lower for pattern in critical_patterns):
            return SeverityLevel.CRITICAL
        elif any(pattern in pattern_lower for pattern in high_patterns):
            return SeverityLevel.HIGH
        else:
            return SeverityLevel.MEDIUM

    def _map_safety_severity(self, severity: str) -> SeverityLevel:
        """Map Safety severity to unified severity."""
        mapping = {
            "critical": SeverityLevel.CRITICAL,
            "high": SeverityLevel.HIGH,
            "medium": SeverityLevel.MEDIUM,
            "low": SeverityLevel.LOW,
        }
        return mapping.get(severity.lower(), SeverityLevel.MEDIUM)

    def _map_generic_severity(self, severity: str) -> SeverityLevel:
        """Generic severity mapping."""
        return self._severity_mapping.get(severity.lower(), SeverityLevel.MEDIUM)

    def _estimate_remediation_complexity(self, rule_id: str) -> ComplexityLevel:
        """Estimate remediation complexity based on rule type."""
        simple_fixes = [
            "B101",
            "B102",
            "B110",
            "B112",
        ]  # Bandit rules with simple fixes
        complex_fixes = ["B105", "B106", "B107"]  # Password-related issues

        if rule_id in simple_fixes:
            return ComplexityLevel.SIMPLE
        elif rule_id in complex_fixes:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.MODERATE

    def _estimate_pylint_complexity(self, message_id: str) -> ComplexityLevel:
        """Estimate remediation complexity for Pylint issues."""
        trivial_fixes = ["C0103", "C0114", "C0115", "C0116"]  # Naming and documentation
        simple_fixes = [
            "W0611",
            "W0612",
            "C0411",
            "C0412",
        ]  # Imports and unused variables

        if message_id in trivial_fixes:
            return ComplexityLevel.TRIVIAL
        elif message_id in simple_fixes:
            return ComplexityLevel.SIMPLE
        else:
            return ComplexityLevel.MODERATE

    def _transform_robustness_finding(
        self, raw: Dict[str, Any], analyzer: str
    ) -> UnifiedFinding:
        """Transform robustness analyzer finding."""
        # The robustness analyzer already creates UnifiedFinding objects,
        # so this method handles any additional transformations if needed

        # If the raw data is already a UnifiedFinding dict, pass it through
        if isinstance(raw, dict) and "id" in raw and "title" in raw:
            # This is likely already a serialized UnifiedFinding
            return UnifiedFinding(
                title=raw.get("title", "Robustness Issue"),
                description=raw.get("description", ""),
                category=FindingCategory(raw.get("category", "quality")),
                severity=SeverityLevel(raw.get("severity", "medium")),
                location=CodeLocation(
                    file_path=raw.get("location", {}).get("file_path", ""),
                    line_number=raw.get("location", {}).get("line_number"),
                ),
                rule_id=raw.get("rule_id"),
                cwe_id=raw.get("cwe_id"),
                code_snippet=raw.get("code_snippet"),
                source_analyzer=analyzer,
                confidence_score=raw.get("confidence_score", 0.8),
                tags=set(raw.get("tags", [])),
            )

        # Handle tool-specific raw findings
        tool_type = raw.get("tool_type", "")

        if tool_type == "bandit":
            return self._transform_bandit_finding(raw, analyzer)
        elif tool_type == "mypy":
            return self._transform_mypy_finding(raw, analyzer)
        elif tool_type == "semgrep":
            return self._transform_semgrep_finding(raw, analyzer)
        elif tool_type == "dict_access":
            return self._transform_dict_access_finding(raw, analyzer)
        else:
            # Generic robustness finding transformation
            return UnifiedFinding(
                title=raw.get("title", "Robustness Issue"),
                description=raw.get("description", raw.get("message", "")),
                category=FindingCategory.QUALITY,
                severity=self._map_generic_severity(raw.get("severity", "medium")),
                location=CodeLocation(
                    file_path=raw.get("file_path", raw.get("filename", "")),
                    line_number=raw.get("line_number", raw.get("line")),
                ),
                rule_id=raw.get("rule_id", raw.get("check_id")),
                source_analyzer=analyzer,
                confidence_score=raw.get("confidence_score", 0.7),
                tags={"robustness", "code_quality"},
            )

    def _transform_dict_access_finding(
        self, raw: Dict[str, Any], analyzer: str
    ) -> UnifiedFinding:
        """Transform dictionary access pattern finding."""
        return UnifiedFinding(
            title="Dictionary Access Pattern",
            description=raw.get(
                "description",
                "Dictionary access without .get() method may raise KeyError",
            ),
            category=FindingCategory.QUALITY,
            severity=SeverityLevel.LOW,
            location=CodeLocation(
                file_path=raw.get("file_path", ""),
                line_number=raw.get("line_number"),
            ),
            rule_id="dict-access-without-get",
            code_snippet=raw.get("line_content", ""),
            source_analyzer=analyzer,
            remediation_guidance="Consider using dict.get() method with default values to prevent KeyError exceptions.",
            remediation_complexity=ComplexityLevel.SIMPLE,
            confidence_score=0.7,
            tags={"safe_patterns", "error_prevention"},
        )

    def _transform_pii_phi_finding(
        self, raw: Dict[str, Any], analyzer: str
    ) -> UnifiedFinding:
        """Transform PII/PHI analyzer finding."""
        # The PII analyzer already creates UnifiedFinding objects,
        # so this method handles any additional transformations if needed

        # If the raw data is already a UnifiedFinding dict, pass it through
        if isinstance(raw, dict) and "id" in raw and "title" in raw:
            # This is likely already a serialized UnifiedFinding
            return UnifiedFinding(
                title=raw.get("title", "PII/PHI Issue"),
                description=raw.get("description", ""),
                category=FindingCategory(raw.get("category", "privacy")),
                severity=SeverityLevel(raw.get("severity", "medium")),
                location=CodeLocation(
                    file_path=raw.get("location", {}).get("file_path", ""),
                    line_number=raw.get("location", {}).get("line_number"),
                ),
                rule_id=raw.get("rule_id"),
                code_snippet=raw.get("code_snippet"),
                source_analyzer=analyzer,
                confidence_score=raw.get("confidence_score", 0.8),
                compliance_frameworks=raw.get("compliance_frameworks", []),
                tags=set(raw.get("tags", [])),
            )

        # Handle different PII types from legacy or raw data
        pii_type = raw.get("pii_type", raw.get("pattern_type", ""))

        return UnifiedFinding(
            title=f"PII/PHI Detection: {pii_type}",
            description=raw.get("description", f"Potential {pii_type} detected"),
            category=FindingCategory.PRIVACY,
            severity=self._determine_pii_severity(pii_type),
            location=CodeLocation(
                file_path=raw.get("file_path", ""),
                line_number=raw.get("line_number"),
                function_name=raw.get("function_name"),
            ),
            rule_id=f"PII_{pii_type.upper().replace(' ', '_')}",
            code_snippet=raw.get("context", raw.get("line_content", "")),
            source_analyzer=analyzer,
            compliance_frameworks=raw.get(
                "compliance_frameworks", ["GDPR", "HIPAA", "CCPA"]
            ),
            remediation_complexity=ComplexityLevel.MODERATE,
            confidence_score=raw.get("confidence", 0.8),
            tags={"privacy", "pii", "phi", "compliance"},
        )

    def _transform_readability_finding(
        self, raw: Dict[str, Any], analyzer: str
    ) -> UnifiedFinding:
        """Transform readability analyzer finding."""
        # The readability analyzer already creates UnifiedFinding objects,
        # so this method handles any additional transformations if needed

        # If the raw data is already a UnifiedFinding dict, pass it through
        if isinstance(raw, dict) and "id" in raw and "title" in raw:
            # This is likely already a serialized UnifiedFinding
            return UnifiedFinding(
                title=raw.get("title", "Readability Issue"),
                description=raw.get("description", ""),
                category=FindingCategory(raw.get("category", "quality")),
                severity=SeverityLevel(raw.get("severity", "low")),
                location=CodeLocation(
                    file_path=raw.get("location", {}).get("file_path", ""),
                    line_number=raw.get("location", {}).get("line_number"),
                ),
                rule_id=raw.get("rule_id"),
                source_analyzer=analyzer,
                confidence_score=raw.get("confidence_score", 0.7),
                tags=set(raw.get("tags", [])),
            )

        # Handle different readability issue types from legacy or raw data
        issue_type = raw.get(
            "issue_type", raw.get("type", raw.get("symbol", "readability"))
        )

        return UnifiedFinding(
            title=f"Readability Issue: {issue_type}",
            description=raw.get(
                "description",
                raw.get("message", f"Readability issue detected: {issue_type}"),
            ),
            category=FindingCategory.QUALITY,
            severity=SeverityLevel.LOW,
            location=CodeLocation(
                file_path=raw.get("file_path", raw.get("path", "")),
                line_number=raw.get("line_number", raw.get("line")),
                column=raw.get("column"),
            ),
            rule_id=f"READABILITY_{issue_type.upper().replace(' ', '_').replace('-', '_')}",
            source_analyzer=analyzer,
            remediation_guidance=raw.get(
                "recommendation", "Improve code readability and style"
            ),
            remediation_complexity=ComplexityLevel.SIMPLE,
            confidence_score=raw.get("confidence", 0.6),
            tags={"readability", "code_style", "maintainability"},
        )

    def _transform_injection_finding(
        self, raw: Dict[str, Any], analyzer: str
    ) -> UnifiedFinding:
        """Transform injection analyzer finding."""
        # The injection analyzer already creates UnifiedFinding objects,
        # so this method handles any additional transformations if needed

        # If the raw data is already a UnifiedFinding dict, pass it through
        if isinstance(raw, dict) and "id" in raw and "title" in raw:
            # This is likely already a serialized UnifiedFinding
            return UnifiedFinding(
                title=raw.get("title", "Injection Vulnerability"),
                description=raw.get("description", ""),
                category=FindingCategory(raw.get("category", "security")),
                severity=SeverityLevel(raw.get("severity", "high")),
                location=CodeLocation(
                    file_path=raw.get("location", {}).get("file_path", ""),
                    line_number=raw.get("location", {}).get("line_number"),
                ),
                rule_id=raw.get("rule_id"),
                cwe_id=raw.get("cwe_id"),
                source_analyzer=analyzer,
                confidence_score=raw.get("confidence_score", 0.7),
                tags=set(raw.get("tags", [])),
            )

        # Handle different injection vulnerability types from legacy or raw data
        vuln_type = raw.get("vulnerability_type", raw.get("type", "injection"))

        # Map vulnerability types to CWE IDs
        cwe_mapping = {
            "sql_injection": "CWE-89",
            "xss": "CWE-79",
            "command_injection": "CWE-78",
            "path_traversal": "CWE-22",
            "ldap_injection": "CWE-90",
            "code_injection": "CWE-94",
            "xpath_injection": "CWE-643",
        }

        return UnifiedFinding(
            title=f"Injection Vulnerability: {vuln_type.replace('_', ' ').title()}",
            description=raw.get(
                "description",
                f"Potential {vuln_type.replace('_', ' ')} vulnerability detected",
            ),
            category=FindingCategory.SECURITY,
            severity=self._map_generic_severity(raw.get("severity", "high")),
            location=CodeLocation(
                file_path=raw.get("file_path", raw.get("file", "")),
                line_number=raw.get("line_number", raw.get("line")),
            ),
            rule_id=f"INJECTION_{vuln_type.upper()}",
            cwe_id=cwe_mapping.get(vuln_type, "CWE-94"),
            code_snippet=raw.get("code_snippet", raw.get("code", "")),
            source_analyzer=analyzer,
            remediation_guidance=raw.get(
                "recommendation", "Review and sanitize user input handling"
            ),
            remediation_complexity=ComplexityLevel.MODERATE,
            confidence_score=raw.get("confidence", 0.7),
            tags={"injection", vuln_type, "security"},
        )
