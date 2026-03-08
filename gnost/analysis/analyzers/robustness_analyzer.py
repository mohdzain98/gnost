# Flake8: noqa: E501
"""
Robustness Analyzer for checking Python code robustness using multiple tools.
Integrates Bandit, MyPy, and custom dictionary access pattern checking.
"""

import os
import json
import re
import asyncio
import ast
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter
from gnost.utils.logger import AppLogger
from gnost.analysis.utils.df_handling import collect_pandas_info, is_dataframe_expr
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

logger = AppLogger.get_logger(__name__)


class RobustnessAnalyzer(QualityAnalyzer):
    """
    Analyzer for checking Python code robustness using multiple tools.
    Covers security patterns, type safety, file handling, and dictionary access patterns.
    """

    def __init__(self):
        super().__init__("robustness", "1.0.0")
        self.supported_tools = ["bandit", "mypy"]
        self.quality_categories = [
            "security_patterns",
            "type_safety",
            "error_handling",
            "safe_patterns",
        ]

    def get_supported_file_types(self) -> List[str]:
        """Return supported file types."""
        return [".py"]

    def get_quality_categories(self) -> List[str]:
        """Get quality categories this analyzer covers."""
        return self.quality_categories

    def get_quality_metrics(self) -> List[str]:
        """Get quality metrics this analyzer can provide."""
        return [
            "security_patterns",
            "type_safety_score",
            "error_handling_coverage",
            "safe_patterns_usage",
            "bandit_issues",
            "mypy_errors",
            "dict_access_issues",
        ]

    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for this analyzer."""
        return {
            "enable_bandit": True,
            "enable_mypy": True,
            "enable_dict_check": True,
            "bandit_security_level": "medium",  # low, medium, high
            "mypy_strict_mode": True,
            "max_file_size_mb": 5,
        }

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate analyzer-specific configuration."""
        required_keys = [
            "enable_bandit",
            "enable_mypy",
            "enable_dict_check",
        ]
        return all(key in config for key in required_keys)

    def get_config(self) -> Dict[str, str]:
        """
        Return tool config. Source order:
        1) self.finding_mode (if class sets it)
        2) default "brief", accepts expanded also
        if brief is set then it combines same prefix dictionaries into one findings else different pref into different findings
        """
        # pull from env or instance, normalize typos like "breif"
        raw = "brief"  # expanded
        val = (raw or "brief").strip().lower()
        if val in {"breif", "short"}:
            val = "brief"
        if val not in {"brief", "expanded"}:
            val = "brief"

        return {"set_config": val}

    async def analyze(self, config: AnalysisConfiguration) -> AnalysisResult:
        """
        Perform robustness analysis using multiple tools.

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
                f"Starting robustness analysis of {os.path.basename(config.target_path)}"
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

            # Run different checks based on configuration
            analyzer_config = config.analyzer_configs.get(
                self.name, self.get_default_config()
            )

            if analyzer_config.get("enable_bandit", True):
                bandit_findings = await self._run_bandit_check(python_files)
                findings.extend(bandit_findings)

            if analyzer_config.get("enable_mypy", True):
                mypy_findings = await self._run_mypy_check(python_files)
                findings.extend(mypy_findings)

            if analyzer_config.get("enable_dict_check", True):
                dict_findings = await self._run_dict_access_check(python_files)
                clubbed_dict_findings = self.club_dict_access_findings(dict_findings)
                findings.extend(clubbed_dict_findings)

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
                f"Robustness analysis completed: {len(findings)} findings in {execution_time:.2f}s"
            )

            return AnalysisResult(
                findings=findings,
                metrics=metrics,
                metadata={
                    "python_files_count": len(python_files),
                    "tools_used": [
                        tool
                        for tool, enabled in [
                            ("bandit", analyzer_config.get("enable_bandit", True)),
                            ("mypy", analyzer_config.get("enable_mypy", True)),
                            (
                                "dict_check",
                                analyzer_config.get("enable_dict_check", True),
                            ),
                        ]
                        if enabled
                    ],
                },
            )

        except Exception as e:
            logger.error(f"Robustness analysis failed: {str(e)}")
            error_count = 1
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

    def club_dict_access_findings(self, unified_findings):
        """Group 'dict-access-without-get' findings by file into one unified entry."""

        grouped = defaultdict(list)
        findings = []

        # 1️⃣ Group by file path
        for f in unified_findings:
            grouped[(f.location.file_path, f.title)].append(f)

        # 2️⃣ Create one combined finding per file
        for (file_path, title), group in grouped.items():
            clubbed = {"prefix": [], "suffix_count": [], "lines": []}

            for item in group:
                # Extract prefix (like data_trimmed[*])
                prefix_line = next(
                    (d for d in item.details if "prefix:" in d.lower()), None
                )
                prefix = (
                    re.search(r"`(.+?)`", prefix_line).group(1)
                    if prefix_line
                    else "unknown"
                )

                # Extract suffix count
                suffix_line = next(
                    (d for d in item.details if "suffix" in d.lower()), ""
                )
                match_suffix = re.search(r"Found\s+(\d+)", suffix_line)
                suffix_count = int(match_suffix.group(1)) if match_suffix else 0

                # Extract all line numbers from code_snippet and join them
                line_matches = re.findall(r"-\s*(\d+)", item.code_snippet or "")
                line_str = ", ".join(sorted(set(line_matches), key=int))

                # Append one row per prefix
                clubbed["prefix"].append(prefix)
                clubbed["suffix_count"].append(suffix_count)
                clubbed["lines"].append(line_str)

            # 3️⃣ Create one unified finding for this file
            finding = UnifiedFinding(
                title=title,
                description=group[0].description,
                clubbed=clubbed,
                category=group[0].category,
                severity=group[0].severity,
                confidence_score=0.7,
                location=CodeLocation(file_path=file_path),
                rule_id="DICT-ACCESS-WITHOUT-GET",
                remediation_guidance=group[0].remediation_guidance,
                remediation_complexity=group[0].remediation_complexity,
                source_analyzer=group[0].source_analyzer,
                tags=group[0].tags,
            )
            findings.append(finding)
        return findings

    def _find_python_files(self, path: str) -> List[str]:
        """Find all Python files under the given path, excluding virtual environments."""
        return find_python_files(path, exclude_test_files=False)

    async def _run_bandit_check(self, files: List[str]) -> List[UnifiedFinding]:
        """Run Bandit security checks and return findings for B110 and B113 test IDs."""
        findings = []

        for file_path in files:
            try:
                result = await asyncio.create_subprocess_exec(
                    "bandit",
                    "-f",
                    "json",
                    "-q",
                    file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await result.communicate()

                output = stdout.decode() if stdout else stderr.decode()

                if not output:
                    continue

                try:
                    data = json.loads(output)
                    results = data.get("results", [])
                    for issue in results:
                        test_id = issue.get("test_id", "")
                        if test_id in ["B110", "B113"]:
                            finding = self._create_bandit_finding(issue, file_path)
                            if finding:
                                findings.append(finding)

                except json.JSONDecodeError:
                    if "B110" in output or "B113" in output:
                        finding = self._create_generic_bandit_finding(file_path, output)
                        if finding:
                            findings.append(finding)

            except FileNotFoundError:
                logger.error(
                    "Bandit not found. Please install with: pip install bandit"
                )
                break
            except Exception as e:
                logger.warning(f"Bandit error for {file_path}: {str(e)}")

        return findings

    def _get_mypy_severity_mapping(self, code: str) -> SeverityLevel:
        severity_map = {
            # 🔴 High — likely to break or misbehave at runtime
            "return-value": SeverityLevel.HIGH,  # wrong return type → runtime errors
            "arg-type": SeverityLevel.HIGH,  # invalid argument type
            "call-arg": SeverityLevel.HIGH,  # mismatched call arguments
            "name-defined": SeverityLevel.HIGH,  # undefined name
            "attr-defined": SeverityLevel.HIGH,  # missing attribute
            "import-not-found": SeverityLevel.HIGH,  # missing dependency
            "assignment": SeverityLevel.HIGH,  # invalid assignment type
            "return": SeverityLevel.HIGH,  # invalid return statement/type
            "has-type": SeverityLevel.HIGH,
            # 🟠 Medium — unsafe, but not immediate runtime breakage
            "no-redef": SeverityLevel.MEDIUM,  # redefinition may shadow variables
            "operator": SeverityLevel.MEDIUM,  # wrong operator types
            "type-arg": SeverityLevel.MEDIUM,  # missing/invalid type argument
            "import-untyped": SeverityLevel.MEDIUM,  # imported module lacks typing
            "union-attr": SeverityLevel.MEDIUM,  # unsafe attribute access on Union
            "annotation-unchecked": SeverityLevel.MEDIUM,  # unchecked annotations may hide issues
            "misc": SeverityLevel.MEDIUM,  # generic issues (potentially unsafe)
            # 🟢 Low — style / completeness / type coverage
            "no-untyped-def": SeverityLevel.LOW,  # missing function annotations
            "no-untyped-call": SeverityLevel.LOW,  # call to untyped function
        }
        return severity_map.get(code, SeverityLevel.INFO)

    def get_mypy_code_mapping(self, code: str) -> str:
        """Return a mapping of MyPy error codes to short labels."""
        code_mapping = {
            "no-untyped-def": "Missing Function Annotations",
            "return-value": "Return type mismatch",
            "no-untyped-call": "Call to untyped function",
            "attr-defined": "Attribute not defined",
            "type-arg": "Bad/missing type arguments",
            "operator": "Invalid operator types",
            "arg-type": "Invalid argument type",
            "import-not-found": "Import error (module not found)",
            "import-untyped": "Import without type hints",
            "name-defined": "Undefined name",
            "no-redef": "Name redefined",
            "call-arg": "Invalid function call arguments",
            "return": "Invalid Return Statement or Type",
            "assignment": "Invalid Assignment Type",
            "misc": "Miscellaneous Type Checking Issue",
            "union-attr": "Invalid Union Attribute Access",
            "annotation-unchecked": "Unchecked Type Annotation",
            "has-type": "Unknown or Unresolved Type Reference",
        }
        return code_mapping.get(code, "Type Checking Issue")

    async def _run_mypy_check(self, files: List[str]) -> List[UnifiedFinding]:
        """Run mypy in strict mode and parse output for type checking issues."""
        findings = []

        if not files:
            return findings

        try:
            cmd = ["mypy", "--config-file", "mypy.ini"] + files
            result = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            output = stdout.decode()
            pattern = (
                r"^(?P<file>.+\.py):(?P<line>\d+):\s*"
                r"(?P<level>error|warning|note):\s*"
                r"(?P<msg>.+?)(?:\s+\[(?P<code>[^\]]+)\])?$"
            )
            grouped = defaultdict(
                lambda: {
                    "levels": set(),
                    "lines_list": [],  # keeps order; same length as messages_list
                    "messages_list": [],  # keeps order; same length as lines_list
                    "codes": set(),
                }
            )

            seen = set()
            code_counts = Counter()

            def _norm_code(code: str | None) -> str:
                return (code or "<unknown>").strip().lower()

            for raw_line in output.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                m = re.match(pattern, line)
                if not m:
                    continue

                fpath = m.group("file")
                lnum = int(m.group("line"))
                level = m.group("level")
                msg = m.group("msg").strip()
                code = m.group("code")

                if level == "note":
                    continue

                norm_code = _norm_code(code)
                code_counts[norm_code] += 1

                # exact duplicate guard
                dup_key = (fpath, lnum, level, msg, norm_code)
                if dup_key in seen:
                    continue
                seen.add(dup_key)

                bucket = grouped[(fpath, norm_code)]
                bucket["levels"].add(level)
                bucket["lines_list"].append(lnum)  # CHANGED: append to list
                bucket["messages_list"].append(msg)
                if code:
                    bucket["codes"].add(code)

            severity_order = {"error": 2, "warning": 1, "note": 0}

            for (fpath, norm_code), data in grouped.items():
                level = max(data["levels"], key=lambda x: severity_order.get(x, 0))

                # For header/preview we can use distinct lines, but keep clubbed lines as full list
                # distinct_lines_sorted = sorted(set(data["lines_list"]))
                hits = len(data["lines_list"])

                combined_code = (
                    None
                    if norm_code == "<unknown>"
                    else (", ".join(sorted(data["codes"])) or norm_code)
                )
                hits = len(data["lines_list"])
                combined_msg = f"{self.get_mypy_code_mapping(combined_code)} -- {hits} occurrence(s)"

                # Representative anchor line for the finding (first occurrence)
                rep_line = data["lines_list"][0] if data["lines_list"] else 1

                finding = self._create_mypy_finding(
                    fpath,
                    rep_line,
                    level,
                    combined_msg,
                    combined_code,
                )
                if finding:
                    clubbed_payload = {
                        # CHANGED: lists are equal length → safe for DataFrame
                        "lines": data["lines_list"],
                        "messages": data["messages_list"],
                    }
                    try:
                        setattr(finding, "clubbed", clubbed_payload)
                    except Exception:
                        try:
                            finding["clubbed"] = clubbed_payload
                        except Exception:
                            pass

                    if combined_code:
                        try:
                            setattr(
                                finding, "rule_id", combined_code.split(",")[0].strip()
                            )
                        except Exception:
                            try:
                                finding["rule_id"] = combined_code.split(",")[0].strip()
                            except Exception:
                                pass

                    findings.append(finding)
        except FileNotFoundError:
            logger.error("MyPy not found. Please install with: pip install mypy")
        except Exception as e:
            logger.warning(f"MyPy error: {str(e)}")

        return findings

    def _extract_chain(self, node: ast.AST) -> Optional[Tuple[str, List[str]]]:
        """
        If node is a subscript chain like params["ewb"]["data_management"]["levels"]["lvl1"],
        return ("params", ["ewb", "data_management", "levels", "lvl1"]).
        Only supports string literal keys.
        """
        keys: List[str] = []
        cur = node
        while isinstance(cur, ast.Subscript):
            # Python 3.9+ uses ast.Constant for string literal slice
            slc = cur.slice
            if isinstance(slc, ast.Constant) and isinstance(slc.value, str):
                keys.insert(0, slc.value)
            else:
                return None  # dynamic key; skip
            cur = cur.value

        if isinstance(cur, ast.Name):
            base = cur.id
        elif isinstance(cur, ast.Attribute):
            # support obj.attr[...] chains: take the root name
            root = cur
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name):
                base = root.id
            else:
                return None
        else:
            return None

        return base, keys

    def _line_has_get_call(self, src_line: str) -> bool:
        # quick filter to skip obvious .get( usage on the same line
        return ".get(" in src_line

    async def _run_dict_access_check(self, files: List[str]) -> List[UnifiedFinding]:
        """Find dictionary access patterns like mydict["key"] without .get() usage."""
        findings = []
        prefix_map = defaultdict(set)
        cfg = self.get_config()

        for file_path in files:
            try:
                if cfg.get("set_config", "expanded") == "expanded":
                    dict_access_pattern = r'\w+\s*\[\s*["\'][^"\']*["\']\s*\]'
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    for line_num, line in enumerate(lines, 1):
                        line_content = line.strip()

                        if not line_content or line_content.startswith("#"):
                            continue

                        if re.search(dict_access_pattern, line_content):
                            if ".get(" not in line_content:
                                finding = self._create_dict_access_finding(
                                    file_path,
                                    line_num,
                                    line_content,
                                    details="no details",
                                )
                                if finding:
                                    findings.append(finding)
                else:
                    src = open(file_path, "r", encoding="utf-8").read()
                    tree = ast.parse(src)
                    env = collect_pandas_info(tree)
                    lines = src.splitlines()

                    for parent in ast.walk(tree):
                        for child in ast.iter_child_nodes(parent):
                            setattr(child, "parent", parent)

                    # 2) Collect only OUTERMOST Subscript nodes
                    prefix_map = defaultdict(set)
                    df_map = dict()

                    for node in ast.walk(tree):
                        if not isinstance(node, ast.Subscript):
                            continue

                        # Skip if this Subscript is part of a larger chain (its parent is also a Subscript)
                        parent = getattr(node, "parent", None)
                        if isinstance(parent, ast.Subscript):
                            continue

                        # Extract full chain from the outermost node only
                        chain = self._extract_chain(node)
                        base_expr = node.value  # the object before the [...]
                        base_is_df = is_dataframe_expr(env, base_expr)
                        if chain is None:
                            continue
                        base, keys = chain
                        if not keys:
                            continue

                        # immediate parent prefix + leaf suffix
                        prefix = tuple(
                            keys[:-1]
                        )  # e.g. ("ewb","data_management","levels")
                        raw_suffix = keys[-1]  # e.g. "lvl1"
                        suffix = str(raw_suffix)

                        line_num = getattr(node, "lineno", None) or 1
                        src_line = (
                            lines[line_num - 1] if 1 <= line_num <= len(lines) else ""
                        )

                        # optional: skip lines that already use .get(
                        if self._line_has_get_call(src_line):
                            continue

                        key_tuple = (file_path, base, prefix)
                        prefix_map[key_tuple].add((suffix, line_num))
                        df_map[key_tuple] = base_is_df

                    for (fp, base, prefix), suffix_items in prefix_map.items():
                        # Sort by line number, then suffix for stable output
                        suffix_items_sorted = sorted(
                            suffix_items, key=lambda x: (x[1], x[0])
                        )

                        prefix_display = "".join(f'["{k}"]' for k in prefix)
                        display = f"`{base}{prefix_display}[*]`"

                        # Multiline reconstructed accesses
                        reconstructed_lines = [
                            f'{base}{prefix_display}["{sfx}"] - {ln}'
                            for (sfx, ln) in suffix_items_sorted
                        ]
                        line_content = "\n".join(reconstructed_lines)

                        # Anchor at first occurrence
                        anchor_line = (
                            suffix_items_sorted[0][1] if suffix_items_sorted else 1
                        )
                        short_fp = "/".join(fp.split("/")[-2:])
                        finding = self._create_dict_access_finding(
                            file_path=short_fp,
                            line_num=anchor_line,
                            line_content=line_content,
                            details=[
                                f"Bracket access on prefix: {display}",
                                f"Found {len(suffix_items_sorted)} suffix(es)",
                            ],
                            is_df=df_map[(fp, base, prefix)],
                        )
                        if finding:
                            findings.append(finding)

            except UnicodeDecodeError:
                logger.error(f"File encoding error - could not read {file_path}")
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {str(e)}")

        return findings

    def _create_bandit_finding(
        self, issue: Dict[str, Any], file_path: str
    ) -> Optional[UnifiedFinding]:
        """Create a UnifiedFinding from a Bandit issue."""
        test_id = issue.get("test_id", "")
        test_name = issue.get("test_name", "Security issue")
        line_number = issue.get("line_number", 0)
        confidence = issue.get("confidence", "MEDIUM").lower()
        severity = issue.get("severity", "MEDIUM").lower()

        return UnifiedFinding(
            title=f"{test_id}: {test_name}",
            description=issue.get("issue_text", test_name),
            category=FindingCategory.SECURITY,
            severity=self._map_bandit_severity(severity),
            confidence_score=self._map_bandit_confidence(confidence),
            location=CodeLocation(
                file_path="/".join(file_path.split("/")[-2:]),
                line_number=line_number,
                column=issue.get("col_offset", 0),
            ),
            rule_id=test_id,
            cwe_id=self._map_bandit_to_cwe(test_id),
            code_snippet=issue.get("code", ""),
            remediation_guidance=self._get_bandit_remediation(test_id),
            remediation_complexity=ComplexityLevel.MODERATE,
            source_analyzer=self.name,
            extra_data={"bandit_issue": issue, "priority_score": 0.7},
        )

    def _create_mypy_finding(
        self,
        filepath: str,
        line_num: int,
        level: str,
        message: str,
        error_code: Optional[str],
    ) -> Optional[UnifiedFinding]:
        """Create a UnifiedFinding from a MyPy issue."""
        formatted_msg = re.sub(r'"([^"]+)"', r"`\1`", message)
        # if error_code:
        #     formatted_msg += f" [{error_code}]"

        normalized_code = (error_code or "").strip()
        code_labels = [c.strip() for c in normalized_code.split(",") if c.strip()]
        codes = code_labels if code_labels else ["<unknown>"]
        error = []

        for x in codes:
            error.append(self.get_mypy_code_mapping(x))
            formatted_msg = re.sub(rf"\s*\[{re.escape(x)}\](?=\s|$)", "", formatted_msg)

        return UnifiedFinding(
            title=f"{', '.join(error)}",
            description=formatted_msg,
            details=self._get_mypy_detail(error_code),
            category=FindingCategory.QUALITY,
            severity=self._get_mypy_severity_mapping(codes[0]),
            confidence_score=0.9,  # MyPy is quite reliable
            location=CodeLocation(
                file_path="/".join(filepath.split("/")[-2:]),
                line_number=line_num,
            ),
            rule_id=(normalized_code.split(",")[0].strip() if normalized_code else None),
            remediation_guidance=self._get_mypy_remediation(codes[0]),
            remediation_complexity=self._get_mypy_complexity(codes[0]),
            source_analyzer=self.name,
            tags={"type_safety", "static_analysis"},
            extra_data={
                "mypy_level": level,
                "error_code": error_code,
                "priority_score": 0.7,
            },
        )

    def _create_dict_access_finding(
        self,
        file_path: str,
        line_num: int,
        line_content: str,
        details: Optional[list],
        is_df: bool,
    ) -> Optional[UnifiedFinding]:
        """Create a UnifiedFinding for dictionary access without .get()."""
        return UnifiedFinding(
            title=(
                "Dictionary access without .get() method"
                if not is_df
                else "Dataframe Column Access "
            ),
            description=(
                "Dictionary access using [] notation without .get() method may raise KeyError"
                if not is_df
                else (
                    "DataFrame column access using [] is valid. "
                    "To avoid KeyError on missing columns, check `col in df.columns` or use a guard."
                )
            ),
            details=details,
            category=FindingCategory.QUALITY,
            severity=SeverityLevel.LOW if not is_df else SeverityLevel.INFO,
            confidence_score=0.7,  # Could be intentional
            location=CodeLocation(
                file_path="/".join(file_path.split("/")[-2:]),
                line_number=line_num,
            ),
            rule_id="dict-access-without-get".upper(),
            code_snippet=line_content.strip(),
            remediation_guidance=(
                "Consider using dict.get() method with default values to prevent KeyError exceptions."
                if not is_df
                else "If a column may be missing, first check with "
                "`if 'col' in df.columns:` or use a try/except KeyError "
                "to handle safely."
            ),
            remediation_complexity=ComplexityLevel.SIMPLE,
            source_analyzer=self.name,
            tags={"safe_patterns", "error_prevention"},
            extra_data={"line_content": line_content.strip(), "priority_score": 0.7},
        )

    def _create_generic_bandit_finding(
        self, file_path: str, output: str
    ) -> Optional[UnifiedFinding]:
        """Create a generic Bandit finding when JSON parsing fails."""
        return UnifiedFinding(
            title="Bandit security issue detected",
            description="Security issue detected by Bandit (details in output)",
            category=FindingCategory.SECURITY,
            severity=SeverityLevel.MEDIUM,
            confidence_score=0.6,
            location=CodeLocation(file_path="/".join(file_path.split("/")[-2:])),
            source_analyzer=self.name,
            extra_data={"bandit_output": output},
        )

    def _map_bandit_severity(self, severity: str) -> SeverityLevel:
        """Map Bandit severity to our SeverityLevel."""
        mapping = {
            "low": SeverityLevel.LOW,
            "medium": SeverityLevel.MEDIUM,
            "high": SeverityLevel.HIGH,
        }
        return mapping.get(severity.lower(), SeverityLevel.MEDIUM)

    def _map_bandit_confidence(self, confidence: str) -> float:
        """Map Bandit confidence to a float score."""
        mapping = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.9,
        }
        return mapping.get(confidence.lower(), 0.6)

    # Removed because mypy mostly gives error to most of the findings
    # def _map_mypy_severity(self, level: str) -> SeverityLevel:
    #     """Map MyPy level to our SeverityLevel."""
    #     mapping = {
    #         "error": SeverityLevel.HIGH,
    #         "warning": SeverityLevel.MEDIUM,
    #         "note": SeverityLevel.LOW,
    #     }
    #     return mapping.get(level.lower(), SeverityLevel.MEDIUM)

    def _map_bandit_to_cwe(self, test_id: str) -> Optional[str]:
        """Map Bandit test IDs to CWE identifiers."""
        mapping = {
            "B110": "CWE-703",  # Improper Check or Handling of Exceptional Conditions
            "B113": "CWE-400",  # Uncontrolled Resource Consumption
        }
        return mapping.get(test_id)

    def _get_bandit_remediation(self, test_id: str) -> str:
        """Get remediation guidance for Bandit test IDs."""
        guidance = {
            "B110": "Ensure proper exception handling and avoid bare except clauses.",
            "B113": "Implement proper timeout handling for network requests and resource usage.",
        }
        return guidance.get(
            test_id, "Review and address the security issue identified by Bandit."
        )

    def _get_mypy_remediation(self, error_code: Optional[str]) -> str:
        """Get remediation guidance for MyPy error codes."""
        if not error_code:
            return "Review and fix the type annotation issue."

        guidance = {
            "no-untyped-def": "Add type annotations for all function parameters and return types.",
            "return-value": "Ensure the function's return value matches its declared return type.",
            "no-untyped-call": "Add type hints to the called function or use a properly typed version.",
            "attr-defined": "Verify the attribute exists on the object or update the type definition.",
            "type-arg": "Provide valid type arguments for generic types (e.g., List[str] instead of List).",
            "operator": "Use operators with compatible types or cast values to appropriate types.",
            "arg-type": "Ensure argument types match the expected parameter types.",
            "import-not-found": "Check that the module is installed and available in the environment. Try with `pip install types-module_name`",
            "import-untyped": "Install or add type stubs for the module, or mark it as typed (py.typed).",
            "assignment": "Ensure assigned values match the declared type of the variable.",
            "name-defined": "Define or import the name before use; fix scope/order of definitions.",
            "no-redef": "Use a unique name or remove the duplicate definition.",
            "call-arg": "Ensure the function call matches the declared parameters and does not provide extra or missing arguments.",
            "return": "Make all return statements conform to the declared return type; either change the annotation or convert the returned value accordingly.",
            "union-attr": "Only access attributes present on every member of the Union. Narrow the type first via isinstance/None checks or match/case; then access or use typing.cast after the guard.",
            "annotation-unchecked": "Provide concrete, checkable annotations (avoid Any/dynamic constructs). Add missing stubs/plugins if needed, and annotate decorated/overloaded functions explicitly so MyPy can check them.",
            "misc": "Inspect the full error text and add precise type annotations or refactor dynamic code to be type-safe. If from third-party libs, add type stubs or pin versions. Use reveal_type to locate the mismatch.",
            "has-type": "Add explicit type annotations to the variable or attribute, or reorder code to ensure the type is defined before use. If caused by cyclic imports, use 'from typing import TYPE_CHECKING' guards or refactor imports.",
        }
        return guidance.get(error_code, "Review and fix the type checking issue.")

    def _get_mypy_detail(self, error_code: Optional[str]) -> str:
        """Get detailed explanation for MyPy error codes."""
        if not error_code:
            return "Analyzer detected a type-checking issue, but no specific error code was provided."

        details = {
            "no-untyped-def": "This function does not declare parameter or return type annotations. "
            "Without them, Analyzer cannot enforce type safety.",
            "return-value": "The return type of this function does not match the declared annotation. "
            "It may be returning an unexpected type or returning a value when None is expected.",
            "no-untyped-call": "You are calling a function that has no type hints. "
            "Analyzer cannot verify if the arguments or return values are correct.",
            "attr-defined": "An attribute is being accessed that Analyzer does not recognize as existing on this object. "
            "This may indicate a typo, missing initialization, or missing type hints.",
            "type-arg": "A generic type (like List, Dict, Optional) is being used without proper type arguments "
            "or with invalid ones (e.g., List instead of List[str]).",
            "operator": "An operator (like +, -, ==) is being used with incompatible types "
            "(e.g., adding an int and a str). It can give TypeError",
            "arg-type": "A function argument was passed with the wrong type. "
            "The type checker expected a different type than what was provided.",
            "import-not-found": "Analyzer could not find the specified module. "
            "It may not be installed in your environment.",
            "import-untyped": "The imported module exists but has no type information available "
            "(no .pyi stubs or py.typed marker). Analyzer treats it as untyped.",
            "assignment": "A variable is being assigned a value that does not match its type annotation.",
            "name-defined": (
                "A variable, function, class, or module is referenced before it's defined or imported. "
                "Common causes: missing import, typo, wrong scope, or using a symbol before its definition."
            ),
            "no-redef": (
                "The same name has been defined more than once in the same scope "
                "(e.g., a function or variable redeclared). "
                "This can shadow the previous definition and cause confusion."
            ),
            "call-arg": (
                "The function call does not match the target function’s signature. "
                "This usually means too many arguments, missing required arguments, "
                "or mismatched keyword arguments."
            ),
            "return": (
                "A value returned from the function does not match the declared return type."
            ),
            "union-attr": ("Invalid attribute access on a Union type. "),
            "annotation-unchecked": ("Unchecked type annotation detected."),
            "misc": (
                "Miscellaneous type checking issue. "
                "The analyzer encountered a type inconsistency that does not fit a specific category."
            ),
            "has-type": "Cannot determine the type of a variable, attribute, or reference. This often occurs when a symbol is used before its type is known, such as in cyclic imports or class attributes without explicit type annotations.",
        }
        return details.get(
            error_code, "Analyzer reported a type-checking issue with this code."
        )

    def _get_mypy_complexity(self, error_code: Optional[str]) -> ComplexityLevel:
        """Get remediation complexity for MyPy error codes."""
        if not error_code:
            return ComplexityLevel.MODERATE

        simple_fixes = {"assignment", "arg-type"}
        complex_fixes = {"attr-defined", "return-value"}

        if error_code in simple_fixes:
            return ComplexityLevel.SIMPLE
        elif error_code in complex_fixes:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.MODERATE

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
