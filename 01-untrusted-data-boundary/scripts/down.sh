#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if command -v docker &>/dev/null; then
  echo "==> Stopping and removing containers, networks, and volumes"
  docker compose down --volumes --remove-orphans

  echo "==> Removing built image"
  docker compose images -q | xargs -r docker rmi -f 2>/dev/null || true

  echo "==> Pruning dangling images"
  docker image prune -f
else
  echo "==> Docker not found, nothing to tear down"
fi

echo "==> Done"
