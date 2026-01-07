#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# PAC-OCC-P16-HW: Heartbeat Keeper Script
# Physical Sovereignty Layer - Human Anchor
# ═══════════════════════════════════════════════════════════════════════════════
#
# This script maintains the heartbeat lockfile that keeps the ChainBridge
# relay alive. Run this in a separate terminal before starting the relay.
#
# Usage:
#   ./scripts/dev/heartbeat_keeper.sh
#   ./scripts/dev/heartbeat_keeper.sh --interval 0.25  # Faster heartbeat
#
# To kill the relay, simply stop this script (Ctrl+C) or:
#   rm ~/.chainbridge/heartbeat.lock
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Configuration
LOCKFILE="${HOME}/.chainbridge/heartbeat.lock"
INTERVAL="${1:-0.5}"  # Default: 500ms

# Parse arguments
if [ "$1" = "--interval" ]; then
    INTERVAL="$2"
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "═══════════════════════════════════════════════════════════════════════════════"
echo -e "${GREEN}⚡ CHAINBRIDGE HEARTBEAT KEEPER (P16-HW)${NC}"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "Lockfile:  ${LOCKFILE}"
echo "Interval:  ${INTERVAL}s"
echo ""
echo -e "${YELLOW}The circuit is the law.${NC}"
echo -e "${YELLOW}Stop this script to break the circuit and terminate the relay.${NC}"
echo "═══════════════════════════════════════════════════════════════════════════════"

# Create directory if needed
mkdir -p "$(dirname "$LOCKFILE")"

# Cleanup on exit
cleanup() {
    echo ""
    echo -e "${RED}☠️  HEARTBEAT STOPPED${NC}"
    echo "Removing lockfile: ${LOCKFILE}"
    rm -f "$LOCKFILE"
    echo "The circuit is broken. The relay will die within 2 seconds."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Initial creation
touch "$LOCKFILE"
echo -e "${GREEN}✓ Heartbeat lockfile created${NC}"

# Counter for status display
count=0

# Main heartbeat loop
while true; do
    touch "$LOCKFILE"
    
    # Show status every 10 beats
    count=$((count + 1))
    if [ $((count % 10)) -eq 0 ]; then
        echo -e "${GREEN}♥${NC} Heartbeat #${count} @ $(date '+%H:%M:%S')"
    fi
    
    sleep "$INTERVAL"
done
