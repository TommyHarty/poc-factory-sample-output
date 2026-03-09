#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if command -v docker &>/dev/null; then
  echo "==> Running tests in Docker"
  docker compose run --rm app pytest tests/
else
  echo "==> Docker not found, falling back to local pytest"
  if [ ! -d .venv ]; then
    echo "ERROR: .venv not found. Run scripts/setup.sh first." >&2
    exit 1
  fi
  if ! .venv/bin/python -c "import pytest" &>/dev/null; then
    echo "ERROR: pytest not installed in .venv. Run scripts/setup.sh first." >&2
    exit 1
  fi
  .venv/bin/pytest tests/
fi
