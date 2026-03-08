import subprocess
import json
import os
import tempfile


def find_duplicate_code(path: str, min_tokens: int = 50) -> dict:
    """
    Run jscpd on the given path and return a summary of duplicate code from stdout.
    """
    try:
        result = subprocess.run(
            [
                "jscpd",
                path,
                "--min-tokens",
                str(min_tokens),
                "--reporters",
                "json",
                "--silent",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode not in [0, 1]:
            return {"error": f"JSCPD error: {result.stderr.strip()}"}

        # Parse stdout directly
        report = json.loads(result.stdout)
        summary = {
            "total_files": report.get("statistics", {})
            .get("total", {})
            .get("files", 0),
            "total_lines": report.get("statistics", {})
            .get("total", {})
            .get("lines", 0),
            "duplicated_lines": report.get("statistics", {})
            .get("total", {})
            .get("duplicatedLines", 0),
            "duplicated_percent": report.get("statistics", {})
            .get("total", {})
            .get("percentage", 0),
            "clones_found": len(report.get("duplicates", [])),
            "clones": [
                {
                    "firstFile": dup["firstFile"],
                    "secondFile": dup["secondFile"],
                    "startLine": dup["start"],
                    "endLine": dup["end"],
                    "lines": dup["lines"],
                    "fragment": dup["fragment"],
                }
                for dup in report.get("duplicates", [])
            ],
        }

        return summary

    except json.JSONDecodeError:
        return {"error": "Failed to parse jscpd JSON output"}
    except Exception as e:
        return {"error": str(e)}


def run_jscpd_analysis(path, min_tokens=20):
    """
    Run jscpd to detect duplicate code.

    Args:
        path (str): File or directory path to scan.
        min_tokens (int): Minimum tokens for duplication.

    Returns:
        dict: Parsed jscpd duplication report.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = os.path.join(tmp_dir, "jscpd-report.json")

        cmd = [
            "jscpd",
            path,
            "--min-tokens",
            str(min_tokens),
            "--reporters",
            "json",
            "--output",
            tmp_dir,
            "--silent",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return {"error": result.stderr}

        if not os.path.exists(report_path):
            return {"error": "Report not generated."}

        with open(report_path, "r") as f:
            return json.load(f)
