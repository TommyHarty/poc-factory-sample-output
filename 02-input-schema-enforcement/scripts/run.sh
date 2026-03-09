#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if command -v docker &>/dev/null; then
  echo "==> Starting app with Docker Compose"
  docker compose up
else
  echo "==> Docker not found, falling back to local execution"
  if [ ! -d .venv ]; then
    echo "ERROR: .venv not found. Run scripts/setup.sh first." >&2
    exit 1
  fi
  HOST="${API_HOST:-0.0.0.0}"
  PORT="${API_PORT:-8000}"
  echo "==> Starting uvicorn on ${HOST}:${PORT}"
  .venv/bin/uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
fi
