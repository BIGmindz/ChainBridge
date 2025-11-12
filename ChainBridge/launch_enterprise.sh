#!/bin/zsh
# BIGmindz Trading Platform Launcher (mutex-free)
set -euo pipefail

echo "🚀 BIGmindz Trading Platform Launcher"
echo "======================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Cleaning environment...${NC}"
# Kill any existing processes
pkill -f "enterprise_multi_signal_bot.py" 2>/dev/null || true
pkill -f "multi_signal_bot.py" 2>/dev/null || true

# Remove lock files and caches
find . -name "*.lock" -delete 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Mutex-free env
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1
export PYTHONPATH=.

echo -e "${GREEN}✅ Environment cleaned${NC}"

MODE="${1:-paper}" # paper|live
CONFIG="${2:-bigmindz_config.yaml}"
EXTRA_ARGS=()

if [[ "${3:-}" == "--once" ]]; then
  EXTRA_ARGS+=(--once)
fi

echo -e "${GREEN}Launching in mode: ${MODE} with config: ${CONFIG}${NC}"

python3 enterprise_multi_signal_bot.py --mode "$MODE" --config "$CONFIG" ${EXTRA_ARGS[@]:-}
