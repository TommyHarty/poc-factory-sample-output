#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> Setting up poc-starter"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Created .env from .env.example"
fi

if command -v docker &>/dev/null; then
  echo "==> Building Docker image with Docker Compose"
  docker compose build
  echo "==> Done. Run scripts/run.sh to start the app."
else
  echo "==> Docker not found, falling back to local setup"
  if command -v uv &>/dev/null; then
    echo "==> Using uv"
    uv venv .venv
    uv pip install -e ".[dev]"
  else
    echo "==> Using python -m venv + pip"
    python -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -e ".[dev]"
  fi
  echo "==> Done. Run scripts/run.sh to start the app."
fi
