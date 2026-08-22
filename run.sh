#!/usr/bin/env bash
# Total Battle Brothers launcher.
# Uses the project venv and bootstraps it unattended when needed.
set -euo pipefail

cd "$(dirname "$0")"
PYBIN=".venv/bin/python3"

if [ ! -x "$PYBIN" ]; then
  if ! python3 -m venv .venv; then
    python3 -m venv --without-pip .venv
  fi
fi

if [ -x .venv/bin/pip ]; then
  .venv/bin/pip install -q -r requirements.txt
else
  pip3 --python .venv install -q -r requirements.txt
fi

exec "$PYBIN" -m tbb "$@"
