#!/usr/bin/env bash
# Smoke-test an unpacked gnost bundle: scripts/smoke_binary.sh <bundle-dir> <expected-version>
set -euo pipefail
BUNDLE="$(cd "$1" && pwd)"
EXPECTED="$2"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$BUNDLE/gnost"
[ -x "$BIN" ] || BIN="$BUNDLE/gnost.exe"
WORK="$(mktemp -d)"
cp -r "$REPO/tests/fixtures/python_app" "$WORK/app"
cd "$WORK/app"
OUT="$("$BIN" version)"
echo "$OUT"
[ "$OUT" = "gnost $EXPECTED" ] || { echo "version mismatch: want gnost $EXPECTED"; exit 1; }
"$BIN" onboard .
# Everything GNOST writes goes into the .gnost folder.
for f in README.md ONBOARD.md insights.json flow.html flow/FLOW-full.mmd; do
  test -f ".gnost/$f" || { echo "missing .gnost/$f"; exit 1; }
done
cp -r "$REPO/tests/fixtures/react_app" "$WORK/react"
(cd "$WORK/react" && "$BIN" onboard .)
# The progress bar once made the binary relaunch itself and print a usage error.
(cd "$WORK/react" && "$BIN" onboard . --progress 2> "$WORK/progress.err")
if grep -qE "resource_tracker|invalid choice|usage:" "$WORK/progress.err"; then
  cat "$WORK/progress.err"; echo "progress bar relaunched the binary"; exit 1
fi
grep -q "Scanning files" "$WORK/progress.err" || { echo "progress bar shows no step names"; exit 1; }
# The "Get it running" section comes from the project's own files (package.json here).
grep -q "## Get it running" "$WORK/react/.gnost/ONBOARD.md" || { echo "missing Get it running"; exit 1; }
grep -q '"quickstart"' "$WORK/react/.gnost/insights.json" || { echo "missing quickstart in the JSON"; exit 1; }
# JavaScript, TypeScript and Java files are read with tree-sitter inside the frozen binary too.
JAVA_APP="$WORK/javaapp"; cp -r "$REPO/tests/fixtures/java_app" "$JAVA_APP"
(cd "$JAVA_APP" && "$BIN" onboard . > /dev/null)
grep -q '"java": "tree-sitter"' "$JAVA_APP/.gnost/insights.json" || { echo "Java is not read with tree-sitter in the binary"; exit 1; }
grep -q '"typescript": "tree-sitter"\|"javascript": "tree-sitter"' "$WORK/react/.gnost/insights.json" || { echo "JS/TS is not read with tree-sitter in the binary"; exit 1; }
# `analyze` checks JavaScript, TypeScript and Java with the built-in rules (no Node or JDK needed).
RULES="$WORK/rules"; mkdir -p "$RULES/src"
printf 'function f(a) {\n  try { eval(a); } catch (e) {}\n  return a == 1;\n}\n' > "$RULES/src/app.js"
printf 'class A {\n  void m() {\n    try { run(); } catch (Exception e) {}\n    System.out.println("x");\n  }\n}\n' > "$RULES/src/A.java"
(cd "$RULES" && git init -q . && "$BIN" analyze . --no-progress --quiet -o > /dev/null)
grep -q 'ROB-UNSAFE-EVAL' "$RULES/.gnost/analysis/analysis.json" || { echo "no JavaScript findings from the binary"; exit 1; }
grep -q 'ROB-CATCH-GENERIC' "$RULES/.gnost/analysis/analysis.json" || { echo "no Java findings from the binary"; exit 1; }
# gnost init writes a complete config (and --print shows it without writing).
"$BIN" init --print | grep -q "output_dir"
INIT_DIR="$WORK/initcheck"; mkdir "$INIT_DIR"
(cd "$INIT_DIR" && git init -q . && "$BIN" init && test -f .gnost.toml)
# Change hotspots come from git history; the frozen binary uses the git on the machine.
HIST="$WORK/history"; cp -r "$REPO/tests/fixtures/python_app" "$HIST"
(
  cd "$HIST"
  git init -q .
  git add -A
  git -c user.name=Ada -c user.email=ada@example.com commit -q -m one
  echo "# more" >> main.py
  git -c user.name=Grace -c user.email=grace@example.com commit -q -am two
  echo "# again" >> main.py
  git -c user.name=Ada -c user.email=ada@example.com commit -q -am three
  "$BIN" onboard . > /dev/null
  grep -q "## Change Hotspots" .gnost/ONBOARD.md
  grep -q '"change_history"' .gnost/insights.json
  # gnost changes: compares with the commit before, writes the report, exits 2 for an unknown ref.
  "$BIN" changes HEAD~1 --format json | grep -q '"schema_version"'
  test -f .gnost/changes/changes.md
  set +e; "$BIN" changes no-such-ref > /dev/null 2>&1; BAD=$?; set -e
  [ "$BAD" = "2" ] || { echo "expected exit code 2 for an unknown ref, got $BAD"; exit 1; }
)
"$BIN" analyze . | tee analyze.out
grep -q "final score" analyze.out
grep -q "robustness" analyze.out
# CI features: SARIF output, and the quality gate exits with code 3.
"$BIN" analyze . --no-progress --sarif > /dev/null
test -f .gnost/analysis/analysis.sarif || { echo "missing the SARIF file"; exit 1; }
"$BIN" analyze . --no-progress --write-baseline > /dev/null
"$BIN" analyze . --no-progress --baseline --fail-on-new > /dev/null  # nothing new: passes
set +e
"$BIN" analyze . --no-progress --fail-under 10.01 > /dev/null 2>&1
GATE_CODE=$?
set -e
[ "$GATE_CODE" = "3" ] || { echo "expected exit code 3 from the quality gate, got $GATE_CODE"; exit 1; }
"$BIN" open flow --no-open
echo "smoke ok"
