import subprocess
import json
import re


class MIDiagnose:
    @staticmethod
    def run_command(cmd):
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip()

    @staticmethod
    def analyze_file(file_path):
        # Maintainability Index
        mi_json = MIDiagnose.run_command(["radon", "mi", "--json", file_path])
        mi_score = json.loads(mi_json).get(file_path, {}).get("mi", 100)

        # Cyclomatic Complexity
        cc_json = MIDiagnose.run_command(["radon", "cc", "--json", file_path])
        cc_data = json.loads(cc_json).get(file_path, [])
        cc_avg = sum(f["complexity"] for f in cc_data) / len(cc_data) if cc_data else 0
        high_complex_funcs = [f for f in cc_data if f["complexity"] > 10]
        high_complex_funcs_name = [f["name"] for f in cc_data if f["complexity"] > 10]

        # Raw metrics
        raw_output = MIDiagnose.run_command(["radon", "raw", file_path])
        hv_raw_output = MIDiagnose.run_command(["radon", "hal", file_path])
        loc = sloc = comments = scomments = blank = 0

        for line in raw_output.splitlines():
            line = line.strip()
            if re.match(r"^LOC:\s+\d+", line):
                loc = int(re.search(r"LOC:\s+(\d+)", line).group(1))
            elif re.match(r"^SLOC:\s+\d+", line):
                sloc = int(re.search(r"SLOC:\s+(\d+)", line).group(1))
            elif re.match(r"^Comments:\s+\d+", line):
                comments = int(re.search(r"Comments:\s+(\d+)", line).group(1))
            elif re.match(r"^Single comments:\s+\d+", line):
                scomments = int(re.search(r"Single comments:\s+(\d+)", line).group(1))
            elif re.match(r"^Multi:\s+\d+", line):
                multi = int(re.search(r"Multi:\s+(\d+)", line).group(1))
            elif re.match(r"^Blank:\s+\d+", line):
                blank = int(re.search(r"Blank:\s+(\d+)", line).group(1))

        # Diagnostic Report
        comment_density = round(((scomments + multi) / loc) * 100, 2) if loc else 0
        metrics = [
            "h1",
            "h2",
            "N1",
            "N2",
            "vocabulary",
            "length",
            "calculated_length",
            "volume",
            "difficulty",
            "effort",
            "time",
            "bugs",
        ]

        halstead_data = {}
        for metric in metrics:
            match = re.search(rf"{metric}:\s+([0-9.]+)", hv_raw_output)
            if match:
                value = match.group(1)
                halstead_data[metric] = float(value) if "." in value else int(value)
        stats = {
            "maintainability_index": mi_score,
            "loc": loc,
            "source_loc": sloc,
            # "comments": comments,
            "single_line_comments": scomments,
            "multi_line_commnets": multi,
            "blank_lines": blank,
            "difficulty": round(halstead_data["difficulty"], 2),
            "bugs": round(halstead_data["bugs"], 2),
            "time": f"{round(halstead_data['time'], 2)} sec",
        }
        # Suggestions
        suggestions = []

        if loc > 1000:
            suggestions.append("Reduce file length. Consider breaking into modules.")
        if cc_avg > 8:
            suggestions.append(
                "Many functions have high decision logic. Refactor complex functions."
            )
        if len(high_complex_funcs) > 0:
            suggestions.append(
                f"{len(high_complex_funcs)} functions have complexity > 10. Split them."
            )

        if comments < sloc * 0.1:
            suggestions.append(
                "Consider adding more comments and docstrings for clarity."
            )
        if halstead_data["volume"] > 8000:
            suggestions.append(
                f"Halstead volume is high ({halstead_data['volume']:.0f}). Refactor to reduce complexity and improve maintainability."
            )

        # High Halstead Difficulty
        if halstead_data["difficulty"] > 15:
            suggestions.append(
                f"Halstead difficulty is {halstead_data['difficulty']:.1f}. Consider simplifying logic and reducing nested structures."
            )

        # High Estimated Bugs
        if halstead_data["bugs"] >= 3:
            suggestions.append(
                f"Estimated bugs ≈ {halstead_data['bugs']:.2f}. Add tests and refactor complex parts to improve reliability."
            )
        time_in_m = halstead_data["time"] / 60
        time_in_h = time_in_m / 60
        suggestions.append(
            f"Time requires to program is {time_in_m:.2f} Minutes or {time_in_h:.2f} Hours"
        )
        final_suggestion = " ".join(suggestions)
        response = {}
        response["stats"] = stats
        response["comment_density"] = comment_density
        response["suggestions"] = final_suggestion
        response["hcf"] = high_complex_funcs_name
        response["cc_avg"] = cc_avg

        return response
