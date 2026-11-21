"""SARIF 2.1.0 output, the format GitHub code scanning (and many other tools) reads.

`SarifWriter` turns findings into one run with a rule per kind of finding and a result per
finding. Locations are repository-relative; each result carries the GNOST fingerprint so
tools can match the same problem across runs instead of reopening it.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Sequence

from gnost import __version__
from gnost.analysis.core.models import SeverityLevel, UnifiedFinding
from gnost.ci.fingerprint import FindingFingerprint
from gnost.ci.paths import PathResolver

SCHEMA_URL = "https://json.schemastore.org/sarif-2.1.0.json"
INFO_URL = "https://gnost.readthedocs.io"


class SarifWriter:
    """Builds and writes a SARIF log for a list of findings."""

    # Change a level here to change how a severity is reported.
    LEVELS: Dict[SeverityLevel, str] = {
        SeverityLevel.CRITICAL: "error",
        SeverityLevel.HIGH: "error",
        SeverityLevel.MEDIUM: "warning",
        SeverityLevel.LOW: "note",
        SeverityLevel.INFO: "note",
    }
    MESSAGE_LIMIT = 500

    def __init__(self, resolver: PathResolver, fingerprint: FindingFingerprint) -> None:
        self.resolver = resolver
        self.fingerprint = fingerprint

    def build(self, findings: Sequence[UnifiedFinding]) -> Dict[str, Any]:
        """The SARIF log as a dict."""
        rules: Dict[str, Dict[str, Any]] = {}
        results = []
        for finding in sorted(findings, key=self._sort_key):
            rule_id = self.rule_id(finding)
            rules.setdefault(rule_id, self._rule(rule_id, finding))
            results.append(self._result(rule_id, list(rules).index(rule_id), finding))
        return {
            "$schema": SCHEMA_URL,
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "GNOST",
                            "version": __version__,
                            "informationUri": INFO_URL,
                            "rules": list(rules.values()),
                        }
                    },
                    "results": results,
                }
            ],
        }

    def write(self, path: str, findings: Sequence[UnifiedFinding]) -> None:
        """Write the SARIF log to path (creating its folder)."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.build(findings), f, indent=2)
            f.write("\n")

    @staticmethod
    def rule_id(finding: UnifiedFinding) -> str:
        """analyzer/rule, or analyzer/title-slug for findings without a rule id."""
        name = finding.rule_id or re.sub(
            r"[^a-z0-9]+", "-", finding.title.lower()
        ).strip("-")
        return f"{finding.source_analyzer or 'gnost'}/{name or 'finding'}"

    def _level(self, finding: UnifiedFinding) -> str:
        return self.LEVELS.get(finding.severity, "warning")

    def _rule(self, rule_id: str, finding: UnifiedFinding) -> Dict[str, Any]:
        rule: Dict[str, Any] = {
            "id": rule_id,
            "name": finding.title or rule_id,
            "shortDescription": {"text": finding.title or rule_id},
            "defaultConfiguration": {"level": self._level(finding)},
            "properties": {
                "tags": sorted({finding.category.value, finding.source_analyzer} - {""})
            },
        }
        if finding.description:
            rule["fullDescription"] = {
                "text": finding.description[: self.MESSAGE_LIMIT]
            }
        if finding.remediation_guidance:
            rule["help"] = {"text": finding.remediation_guidance[: self.MESSAGE_LIMIT]}
        return rule

    def _result(
        self, rule_id: str, index: int, finding: UnifiedFinding
    ) -> Dict[str, Any]:
        text = finding.title
        if finding.description and finding.description != finding.title:
            text = f"{finding.title}: {finding.description}"
        result: Dict[str, Any] = {
            "ruleId": rule_id,
            "ruleIndex": index,
            "level": self._level(finding),
            "message": {"text": text[: self.MESSAGE_LIMIT]},
            "partialFingerprints": {
                f"gnostFingerprint/{FindingFingerprint.VERSION}": self.fingerprint.of(
                    finding
                )
            },
        }
        location = self._location(finding)
        if location:
            result["locations"] = [location]
        return result

    def _location(self, finding: UnifiedFinding) -> Dict[str, Any]:
        """The physical location, or {} when the path is not a file in the repository."""
        path = self.resolver.resolve(finding.location.file_path)
        if not path or not self.resolver.exists(path):
            return {}
        region: Dict[str, int] = {
            "startLine": max(1, finding.location.line_number or 1)
        }
        if finding.location.end_line_number:
            region["endLine"] = max(
                region["startLine"], finding.location.end_line_number
            )
        return {
            "physicalLocation": {
                "artifactLocation": {"uri": path, "uriBaseId": "%SRCROOT%"},
                "region": region,
            }
        }

    def _sort_key(self, finding: UnifiedFinding) -> List[Any]:
        return [
            self.resolver.resolve(finding.location.file_path),
            finding.location.line_number or 0,
            self.rule_id(finding),
        ]
