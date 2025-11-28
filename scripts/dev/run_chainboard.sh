#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POSSIBLE_PATHS=(
  "$ROOT_DIR/services/chainboard-service"
  "$ROOT_DIR/chainboard-ui"
  "$ROOT_DIR/ChainBridge/chainboard-ui"
)

TARGET_DIR=""
for candidate in "${POSSIBLE_PATHS[@]}"; do
  if [ -d "$candidate" ]; then
    TARGET_DIR="$candidate"
    break
  fi
done

if [ -z "$TARGET_DIR" ]; then
  echo "[run_chainboard] Unable to locate ChainBoard UI. Expected services/chainboard-service." >&2
  exit 1
fi

cd "$TARGET_DIR"

if [ ! -d node_modules ]; then
  echo "[run_chainboard] Installing Node dependencies"
  npm install
fi

echo "[run_chainboard] Starting ChainBoard UI (npm run dev -- --host)"
exec npm run dev -- --host
