import subprocess
import json
import os
import tempfile


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
