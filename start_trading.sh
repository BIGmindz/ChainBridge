#!/bin/bash
#
# Benson Multi-Signal Automated Trading System
# This script sets up and runs the complete trading system
#

# Set up colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================${NC}"
echo -e "${GREEN}BENSON MULTI-SIGNAL AUTOMATED TRADING SYSTEM${NC}"
echo -e "${BLUE}=================================================${NC}"
echo

# Create directories if they don't exist
mkdir -p logs
mkdir -p reports

# Parse command line arguments
REFRESH_HOURS=12
RUN_ONCE=false
TEST_MODE=false
ANALYZE_ONLY=false

while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --refresh)
      REFRESH_HOURS="$2"
      shift
      shift
      ;;
    --once)
      RUN_ONCE=true
      shift
      ;;
    --test)
      TEST_MODE=true
      shift
      ;;
    --analyze)
      ANALYZE_ONLY=true
      shift
      ;;
    *)
      echo -e "${RED}Unknown option: $key${NC}"
      echo "Usage: $0 [--refresh HOURS] [--once] [--test] [--analyze]"
      exit 1
      ;;
  esac
done

# Display settings
echo -e "${YELLOW}Settings:${NC}"
echo -e "  Refresh interval: ${GREEN}$REFRESH_HOURS hours${NC}"
echo -e "  Run once: ${GREEN}$RUN_ONCE${NC}"
echo -e "  Test mode: ${GREEN}$TEST_MODE${NC}"
echo -e "  Analyze only: ${GREEN}$ANALYZE_ONLY${NC}"
echo

# If analyze only, just run the analysis script
if [ "$ANALYZE_ONLY" = true ]; then
  echo -e "${YELLOW}Running performance analysis...${NC}"
  python3 analyze_trading_performance.py
  echo -e "${GREEN}Analysis complete!${NC}"
  echo -e "Performance reports saved in ${BLUE}reports/${NC} directory."
  exit 0
fi

# If test mode, run tests
if [ "$TEST_MODE" = true ]; then
  echo -e "${YELLOW}Running in test mode...${NC}"

  echo -e "${BLUE}Testing dynamic crypto selector...${NC}"
  python3 dynamic_crypto_selector.py

  echo -e "${BLUE}Testing multi-signal bot (single cycle)...${NC}"
  python3 multi_signal_bot.py --once

  echo -e "${GREEN}Tests completed!${NC}"
  exit 0
fi

# Start the automated trader
echo -e "${YELLOW}Starting automated trading system...${NC}"
if [ "$RUN_ONCE" = true ]; then
  python3 automated_trader.py --once --refresh "$REFRESH_HOURS"
else
  python3 automated_trader.py --refresh "$REFRESH_HOURS"
fi

echo -e "${GREEN}Trading system has completed.${NC}"
