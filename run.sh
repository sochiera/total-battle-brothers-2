#!/usr/bin/env bash
# Total Battle Brothers launcher.
# Bootstrap order: normal venv, venv without ensurepip, pip3 --python, then
# an already-capable system python3.  The last path is useful on distro hosts
# where ensurepip is intentionally omitted.
set -euo pipefail

cd "$(dirname "$0")"
PYBIN=""
if [ -x .venv/bin/python3 ]; then
  PYBIN=".venv/bin/python3"
else
  if python3 -m venv .venv >/dev/null 2>&1; then
    PYBIN=".venv/bin/python3"
  elif python3 -m venv --without-pip .venv >/dev/null 2>&1; then
    PYBIN=".venv/bin/python3"
  fi
fi

if [ -n "$PYBIN" ]; then
  if [ -x .venv/bin/pip ]; then
    .venv/bin/pip install -q -r requirements.txt >/dev/null 2>&1 || PYBIN=""
  elif command -v pip3 >/dev/null 2>&1; then
    pip3 --python .venv install -q -r requirements.txt >/dev/null 2>&1 || PYBIN=""
  fi
fi

if [ -z "$PYBIN" ]; then
  if [ "${1:-}" = "--test" ]; then
    if python3 -c 'import pytest' >/dev/null 2>&1; then PYBIN="python3"; fi
  elif [ "${1:-}" = "--save-smoke" ]; then
    # Save smoke is deliberately pygame-free and remains useful on hosts
    # without an audio/display stack.
    PYBIN="python3"
  elif python3 -c 'import pygame' >/dev/null 2>&1; then
    PYBIN="python3"
  fi
fi

if [ -z "$PYBIN" ]; then
  echo "No usable interpreter: install pygame-ce and pytest or provide a venv." >&2
  exit 2
fi
echo "Total Battle Brothers: using $PYBIN (repo on PYTHONPATH)"
export PYTHONPATH="$(pwd)${PYTHONPATH:+:$PYTHONPATH}"
if [ "${1:-}" = "--test" ]; then
  shift
  exec "$PYBIN" -m pytest -q "$@"
fi
exec "$PYBIN" -m tbb "$@"
