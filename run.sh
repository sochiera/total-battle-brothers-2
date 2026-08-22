#!/usr/bin/env bash
# Total Battle Brothers launcher.
# Uses the project venv; explains the bootstrap command if it is missing.
set -u

cd "$(dirname "$0")"
PYBIN=".venv/bin/python3"

if [ ! -x "$PYBIN" ]; then
  echo "No project venv found in .venv/."
  echo "Create and fill it with:"
  echo
  echo "    python3 -m venv .venv"
  echo "    .venv/bin/pip install -r requirements.txt"
  echo
  echo "then run this script again (or: make run)."
  exit 1
fi

exec "$PYBIN" -m tbb "$@"