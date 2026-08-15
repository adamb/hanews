#!/usr/bin/env bash
# Run the hai CLI with the backup-disk venv. Never uses the ESPHome venv.
set -euo pipefail

export PATH="/home/adam/.local/bin:/usr/bin:/bin"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-/mnt/backup/hanews/.venv}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-/mnt/backup/hanews/.cache/uv}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec uv run hai "$@"
