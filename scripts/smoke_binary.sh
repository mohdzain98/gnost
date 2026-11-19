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
cp -r "$REPO/tests/fixtures/react_app" "$WORK/react"
(cd "$WORK/react" && "$BIN" onboard .)
# The progress bar once made the binary relaunch itself and print a usage error.
(cd "$WORK/react" && "$BIN" onboard . --progress 2> "$WORK/progress.err")
if grep -qE "resource_tracker|invalid choice|usage:" "$WORK/progress.err"; then
  cat "$WORK/progress.err"; echo "progress bar relaunched the binary"; exit 1
fi
"$BIN" analyze . | tee analyze.out
grep -q "final score" analyze.out
grep -q "robustness" analyze.out
"$BIN" open flow --no-open
echo "smoke ok"
