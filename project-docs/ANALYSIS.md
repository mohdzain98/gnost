# Analysis rules: calibration results

How GNOST's own rules (JavaScript, TypeScript, Java; added in 0.7.0) were checked against real projects.
Python keeps its external tools (mypy, bandit, radon, ruff). Run date: 2026-11-22, GNOST 0.7.0 development.

## Method
- `gnost analyze -o` on well-known open source projects; final score is out of 10.
- Function statistics (complexity, lines, nesting) decide the thresholds: they should select roughly the worst
  3 % of functions. Kept: complexity 10, function 60 lines, file 500 lines, nesting 4, 5 parameters.
- Every false positive found on a real project became a fixture (`tests/fixtures/rules/<language>/`) and a fix.
- A parity test requires the 12 shared rules to have the same id, analyzer and severity in every language.

## JavaScript and TypeScript
| Project | Files | Time | Findings | Robustness | Maintainability | Observability | Readability | Final |
|---|---|---|---|---|---|---|---|---|
| express (JS) | 50 | 1.1 s | 60 | 10.00 | 8.38 | 9.33 | 9.50 | 8.67 |
| vercel/commerce (Next.js, TS) | ~120 | 0.3 s | 37 | 7.00 | 8.75 | 7.83 | 9.50 | 8.53 |
| vue core (TS) | ~490 | 7.7 s | 1,135 | 7.61 | 7.90 | 8.50 | 9.50 | 7.58 |
| jquery (older JS) | ~150 | 2.6 s | 325 | 6.27 | 7.80 | 7.00 | 9.50 | 7.47 |
| docschat-frontend (React, TS) | ~400 | 3.8 s | 601 | 5.25 | 7.59 | 7.18 | 9.50 | 7.69 |

Complexity p95 was 1 to 7 per project; `> 10` flags 0 to 2.7 % of functions, `> 60` lines 2.5 to 4.5 %, nesting
over 4 under 1 %.

False positives fixed: catch blocks with only a comment or that mention an error/toast/failure state are not
"swallowed"; `eval` / `new Function` and `innerHTML` are not reported in test files; consecutive `//` lines are
judged together by the commented-code rule.

## Java
| Project | Time | Findings | Final |
|---|---|---|---|
| spring-petclinic | 0.3 s | 3 | 8.67 |
| apache commons-lang | 6.2 s | 280 | 8.71 |
| jsoup | 2.3 s | 87 | 8.61 |
| gson | 2.4 s | 129 | 8.06 |

False positives fixed: test classes (`*Test`, `*IT`, `src/test`) are exempt from empty-catch, swallowed-error,
long-file and naming rules; snake_case JUnit test names; Javadoc is not commented-out code; swallowed errors are
LOW severity in every language. `target/` and `.gradle/` are skipped as generated.

## Known limitation
The score is the mean severity of findings, so it ignores how many findings there are or how big the project
is. A messy project (jquery 7.47) lands close to a clean one (express 8.67). A size-aware score is planned for
0.7.1 and will change numbers for everyone, so it comes with a changelog entry.

## Not built yet
`MNT-DUPLICATION` (duplicate code blocks): needs a project-wide rule type; planned for later.


## 0.7.1: size-aware score (run 2026-11-26)
Formula: weight per finding by severity (critical 1.0, high 0.6, medium 0.3, low 0.1, info 0.05), density =
weight per 1,000 non-blank analyzed lines (at least 1,000 lines), score = `10 − 2 × ln(1 + density)`, floored at
0. Analyzers use their own findings over all analyzed lines; the final score uses all findings. Findings over
`max_findings` still count (`analysis_metrics[].capped_by_severity`). Old formula behind
`[analyze] score = "average"` until 0.8.0. Implementation: `gnost/ci/scorecard.py`; docs: `docs/scoring.rst`.

Run with `gnost analyze . -o --max-findings 100000` after the root-detection fix (`analyze` used to pick the
biggest sub-folder, often `tests/`, so the Java table above measured jsoup and commons-lang from `src/test`
only, and flask/fastapi/GNOST from `tests/`). "Old" is the 0.7.0 formula on the same run.

| Project | Files | Lines | Findings | Density | Robustness | Maintainability | Observability | Readability | Final | Old |
|---|---|---|---|---|---|---|---|---|---|---|
| spring-petclinic | 20 | 2,023 | 3 | 0.12 | 9.90 | 9.90 | 10.00 | 9.95 | **9.77** | 8.67 |
| express | 142 | 18,004 | 46 | 0.21 | 10.00 | 9.80 | 9.85 | 9.96 | **9.62** | 8.85 |
| gson | 268 | 52,087 | 145 | 0.39 | 9.95 | 9.45 | 9.96 | 9.95 | **9.34** | 8.15 |
| commons-lang | 647 | 196,517 | 749 | 0.40 | 9.95 | 9.55 | 9.97 | 9.79 | **9.32** | 8.58 |
| jsoup | 216 | 57,081 | 307 | 0.64 | 9.93 | 9.23 | 9.95 | 9.79 | **9.01** | 8.42 |
| vercel/commerce | 66 | 3,527 | 35 | 1.02 | 9.29 | 9.50 | 9.97 | 9.48 | **8.59** | 8.63 |
| vue core | 519 | 156,229 | 972 | 1.08 | 9.64 | 8.76 | 9.99 | 9.95 | **8.53** | 7.84 |
| jquery | 222 | 43,881 | 254 | 1.12 | 9.89 | 8.60 | 9.99 | 9.92 | **8.50** | 7.71 |
| GNOST | 480 | 52,332 | 1,013 | 3.68 | 9.60 | 8.07 | 8.97 | 8.46 | **6.91** | 7.70 |
| fastapi | 1,237 | 117,671 | 3,382 | 3.91 | 9.72 | 8.49 | 9.56 | 7.56 | **6.82** | 8.12 |
| flask | 83 | 14,119 | 323 | 3.93 | 9.55 | 8.55 | 8.70 | 8.02 | **6.81** | 7.85 |
| requests | 37 | 9,841 | 315 | 6.55 | 7.01 | 8.94 | 9.00 | 7.99 | **5.96** | 7.47 |

Curve choice: `10 − 2.5 × ln(1 + d)` put requests at 4.94 and the Python projects near 6.0; `10 × exp(−d / 8)`
and `10 / (1 + sqrt(d) / 3)` were also tried: the first dropped requests to 4.41, the second kept even
petclinic (3 findings) below 9 (8.95). Slope 2
gave the clearest gap between clean and older JS/Java (express 9.62, jquery 8.50) while keeping well-regarded
Python projects at 6 to 7. Python density is 4 to 6 times JS/Java density: mostly mypy findings and ruff
docstring rules (D205, D212, D400, ...), which the JS/TS/Java rules do not have. The React app of the 0.7.0
table (docschat-frontend) was not re-run. fastapi's 1,237 files are 658 tests, 488 `docs_src/` examples and
54 package files; with the default `max_findings = 1000` its readability findings (2,770) are capped but still
counted.
