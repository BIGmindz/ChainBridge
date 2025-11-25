#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVICE_DIR=""

for candidate in "$ROOT_DIR/services/api-gateway" "$ROOT_DIR/api"; do
  if [ -d "$candidate" ]; then
    SERVICE_DIR="$candidate"
    break
  fi
done

if [ -z "$SERVICE_DIR" ]; then
  echo "[run_api_gateway] Unable to locate api-gateway source. Expected services/api-gateway or api/." >&2
  exit 1
fi

if [ -f "$ROOT_DIR/.venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source "$ROOT_DIR/.venv/bin/activate"
fi

export PYTHONPATH="$ROOT_DIR:$ROOT_DIR/services:$ROOT_DIR/platform:${PYTHONPATH:-}"
cd "$ROOT_DIR"

if [ -f "$ROOT_DIR/services/api-gateway/app/main.py" ]; then
  APP_MODULE="services.api_gateway.app.main:app"
elif [ -f "$ROOT_DIR/services/api-gateway/server.py" ]; then
  APP_MODULE="services.api_gateway.server:app"
else
  APP_MODULE="api.server:app"
fi

PORT="${API_GATEWAY_PORT:-8001}"
UVICORN_ARGS=("uvicorn" "$APP_MODULE" "--port" "$PORT")

if [[ "${UVICORN_RELOAD:-1}" != "0" ]]; then
  UVICORN_ARGS+=("--reload")
fi

echo "[run_api_gateway] Starting API Gateway from $APP_MODULE on port $PORT"
exec "${UVICORN_ARGS[@]}"
