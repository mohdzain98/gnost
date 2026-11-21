#!/usr/bin/env bash
# One-time developer setup: creates .venv and installs the git pre-commit hook.
# Run it with `make setup` (then `make install` for the dependencies).
# Works on macOS, Linux, and Windows with Git Bash or WSL.
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON:-python3}"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || PYTHON_BIN=python
command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "Python 3.9 or newer is required (not found)." >&2; exit 1; }
"$PYTHON_BIN" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' \
  || { echo "Python 3.9 or newer is required (found $("$PYTHON_BIN" -V))." >&2; exit 1; }

if [ ! -d .venv ]; then
  echo "Creating .venv with $("$PYTHON_BIN" -V) ..."
  "$PYTHON_BIN" -m venv .venv
else
  echo ".venv already exists, keeping it."
fi

if [ -x .venv/bin/python ]; then VENV_PY=.venv/bin/python; ACTIVATE="source .venv/bin/activate"
else VENV_PY=.venv/Scripts/python.exe; ACTIVATE=".venv\\Scripts\\activate"; fi

"$VENV_PY" -m pip install --quiet --upgrade pip
"$VENV_PY" -m pip install --quiet pre-commit

if git rev-parse --git-dir >/dev/null 2>&1; then
  "$VENV_PY" -m pre_commit install
  echo "Pre-commit hook installed: style checks now run on every commit."
else
  echo "Not inside a git repository, so the pre-commit hook was skipped (run 'make hooks' later)." >&2
fi

cat <<MSG

Setup done. Next:
  1. make install          # install GNOST and the development tools into .venv
  2. $ACTIVATE   # optional: use the environment in your shell
  3. make check            # lint, formatting and tests, same as CI
Run 'make help' to see every command.
MSG
