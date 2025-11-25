#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_SCRIPT="$ROOT_DIR/scripts/dev/run_api_gateway.sh"
UI_SCRIPT="$ROOT_DIR/scripts/dev/run_chainboard.sh"

if [ ! -x "$API_SCRIPT" ]; then
  echo "[run_stack] Missing executable: $API_SCRIPT" >&2
  exit 1
fi

if [ ! -x "$UI_SCRIPT" ]; then
  echo "[run_stack] Missing executable: $UI_SCRIPT" >&2
  exit 1
fi

"$API_SCRIPT" &
API_PID=$!

echo "[run_stack] API Gateway PID $API_PID"

sleep 2

"$UI_SCRIPT" &
UI_PID=$!

echo "[run_stack] ChainBoard UI PID $UI_PID"

cleanup() {
  echo "[run_stack] Shutting down stack"
  kill "$API_PID" "$UI_PID" 2>/dev/null || true
  wait "$API_PID" 2>/dev/null || true
  wait "$UI_PID" 2>/dev/null || true
}

trap cleanup EXIT

wait -n "$API_PID" "$UI_PID"
EXIT_CODE=$?
exit "$EXIT_CODE"
