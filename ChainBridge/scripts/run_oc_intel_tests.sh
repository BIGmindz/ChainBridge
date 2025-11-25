#!/usr/bin/env bash
set -euo pipefail

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

python -m pytest -q \
  tests/test_live_positions_api.py \
  tests/test_intel_global_snapshot_api.py
