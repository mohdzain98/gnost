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
