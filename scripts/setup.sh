#!/usr/bin/env bash
# Create isolated venv + cache on the backup disk. No system packages.
set -euo pipefail

export PATH="/home/adam/.local/bin:/usr/bin:/bin"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-/mnt/backup/hanews/.venv}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-/mnt/backup/hanews/.cache/uv}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p /mnt/backup/hanews/{data,cache,.cache/uv}

cd "$ROOT"
exec uv sync --extra dev
