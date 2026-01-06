#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# CHAINBRIDGE V1 LAUNCHPAD
# PAC-OCC-P25: Single-Command Startup Script
# 
# Usage: ./start_chainbridge.sh
# 
# This script:
#   1. Checks if Kill Switch is active (Safety First)
#   2. Activates Python virtual environment
#   3. Starts Backend API (Uvicorn on port 8000)
#   4. Starts Frontend UI (Vite on port 5173)
#   5. Opens ChainBoard Dashboard in browser
#   6. Provides clean shutdown on Ctrl+C
#
# Authors: DAN (GID-07) DevOps, BENSON (GID-00) Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Process tracking
API_PID=""
UI_PID=""

# ═══════════════════════════════════════════════════════════════════════════════
# CLEANUP FUNCTION (Trap Handler)
# ═══════════════════════════════════════════════════════════════════════════════
cleanup() {
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}   SHUTTING DOWN CHAINBRIDGE${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
    
    if [ -n "$API_PID" ] && kill -0 "$API_PID" 2>/dev/null; then
        echo -e "${CYAN}🔌 Stopping API Server (PID: $API_PID)...${NC}"
        kill "$API_PID" 2>/dev/null || true
        wait "$API_PID" 2>/dev/null || true
        echo -e "${GREEN}   ✓ API Server stopped${NC}"
    fi
    
    if [ -n "$UI_PID" ] && kill -0 "$UI_PID" 2>/dev/null; then
        echo -e "${CYAN}🔌 Stopping UI Server (PID: $UI_PID)...${NC}"
        kill "$UI_PID" 2>/dev/null || true
        wait "$UI_PID" 2>/dev/null || true
        echo -e "${GREEN}   ✓ UI Server stopped${NC}"
    fi
    
    # Kill any remaining uvicorn or vite processes for this project
    pkill -f "uvicorn api.server:app" 2>/dev/null || true
    pkill -f "vite.*chainboard-ui" 2>/dev/null || true
    
    echo ""
    echo -e "${GREEN}✅ ChainBridge shutdown complete. No zombie processes.${NC}"
    echo -e "${PURPLE}   DAN (GID-07): Clean Start, Clean Stop.${NC}"
    echo ""
    exit 0
}

# Set trap for clean shutdown
trap cleanup SIGINT SIGTERM EXIT

# ═══════════════════════════════════════════════════════════════════════════════
# BANNER
# ═══════════════════════════════════════════════════════════════════════════════
clear
echo -e "${PURPLE}"
echo "   ╔═══════════════════════════════════════════════════════════════════════════╗"
echo "   ║                                                                           ║"
echo "   ║     ██████╗██╗  ██╗ █████╗ ██╗███╗   ██╗██████╗ ██████╗ ██╗██████╗  ██████╗███████╗    ║"
echo "   ║    ██╔════╝██║  ██║██╔══██╗██║████╗  ██║██╔══██╗██╔══██╗██║██╔══██╗██╔════╝██╔════╝    ║"
echo "   ║    ██║     ███████║███████║██║██╔██╗ ██║██████╔╝██████╔╝██║██║  ██║██║  ███║█████╗      ║"
echo "   ║    ██║     ██╔══██║██╔══██║██║██║╚██╗██║██╔══██╗██╔══██╗██║██║  ██║██║   ██║██╔══╝      ║"
echo "   ║    ╚██████╗██║  ██║██║  ██║██║██║ ╚████║██████╔╝██║  ██║██║██████╔╝╚██████╔╝███████╗    ║"
echo "   ║     ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝  ╚═════╝ ╚══════╝    ║"
echo "   ║                                                                           ║"
echo "   ║                    V1 Constitutional Control Plane                        ║"
echo "   ║                                                                           ║"
echo "   ╚═══════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# SAFETY CHECK: Kill Switch
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   PREFLIGHT SAFETY CHECK${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

if [ -f "$SCRIPT_DIR/KILL_SWITCH.lock" ]; then
    echo -e "${RED}🔴 ABORT: Kill Switch is ACTIVE${NC}"
    echo -e "${RED}   File: $SCRIPT_DIR/KILL_SWITCH.lock${NC}"
    echo ""
    echo -e "${YELLOW}   To resume operations, remove the lock file:${NC}"
    echo -e "${YELLOW}   rm $SCRIPT_DIR/KILL_SWITCH.lock${NC}"
    echo ""
    echo -e "${RED}   Or use the API endpoint:${NC}"
    echo -e "${RED}   curl -X POST http://localhost:8000/occ/emergency/resume${NC}"
    echo ""
    exit 1
fi
echo -e "${GREEN}✓ Kill Switch: CLEAR${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT CHECK
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}Checking environment...${NC}"

# Check for virtual environment
if [ -d "$SCRIPT_DIR/.venv" ]; then
    echo -e "${GREEN}✓ Python venv found${NC}"
    source "$SCRIPT_DIR/.venv/bin/activate"
    echo -e "${GREEN}✓ Python venv activated${NC}"
else
    echo -e "${RED}✗ Python venv not found at $SCRIPT_DIR/.venv${NC}"
    echo -e "${YELLOW}  Run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt${NC}"
    exit 1
fi

# Check for node_modules in chainboard-ui
if [ -d "$SCRIPT_DIR/chainboard-ui/node_modules" ]; then
    echo -e "${GREEN}✓ UI dependencies found${NC}"
else
    echo -e "${YELLOW}⚠ UI dependencies not found. Installing...${NC}"
    cd "$SCRIPT_DIR/chainboard-ui"
    npm install
    cd "$SCRIPT_DIR"
    echo -e "${GREEN}✓ UI dependencies installed${NC}"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# KILL EXISTING PROCESSES
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}Cleaning up any existing processes...${NC}"
pkill -f "uvicorn api.server:app" 2>/dev/null || true
pkill -f "vite.*chainboard-ui" 2>/dev/null || true
sleep 1
echo -e "${GREEN}✓ Clean slate${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# START BACKEND API
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   STARTING SERVICES${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}🚀 Starting API Server (Port 8000)...${NC}"
cd "$SCRIPT_DIR"
uvicorn api.server:app --host 127.0.0.1 --port 8000 > /tmp/chainbridge_api.log 2>&1 &
API_PID=$!
sleep 2

# Verify API is running
if kill -0 "$API_PID" 2>/dev/null; then
    echo -e "${GREEN}✓ API Server started (PID: $API_PID)${NC}"
else
    echo -e "${RED}✗ API Server failed to start. Check /tmp/chainbridge_api.log${NC}"
    exit 1
fi

# ═══════════════════════════════════════════════════════════════════════════════
# START FRONTEND UI
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}🎨 Starting UI Server (Port 5173)...${NC}"
cd "$SCRIPT_DIR/chainboard-ui"
npm run dev > /tmp/chainbridge_ui.log 2>&1 &
UI_PID=$!
sleep 3

# Verify UI is running
if kill -0 "$UI_PID" 2>/dev/null; then
    echo -e "${GREEN}✓ UI Server started (PID: $UI_PID)${NC}"
else
    echo -e "${RED}✗ UI Server failed to start. Check /tmp/chainbridge_ui.log${NC}"
    exit 1
fi

cd "$SCRIPT_DIR"

# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}🏥 Running health checks...${NC}"
sleep 2

# Check API health
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
if [ "$API_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ API Health: OK${NC}"
else
    echo -e "${YELLOW}⚠ API Health: Status $API_STATUS (may still be starting)${NC}"
fi

# Check God-View endpoint
GODVIEW=$(curl -s http://localhost:8000/occ/dashboard 2>/dev/null || echo "{}")
SYSTEM_STATUS=$(echo "$GODVIEW" | python3 -c "import sys,json; print(json.load(sys.stdin).get('system_status','UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
AGENT_COUNT=$(echo "$GODVIEW" | python3 -c "import sys,json; print(json.load(sys.stdin).get('active_agents',0))" 2>/dev/null || echo "0")

echo -e "${GREEN}✓ System Status: $SYSTEM_STATUS${NC}"
echo -e "${GREEN}✓ Active Agents: $AGENT_COUNT${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# OPEN BROWSER
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}🌐 Opening ChainBoard Dashboard...${NC}"
sleep 1

# Open browser (macOS)
if command -v open &> /dev/null; then
    open "http://localhost:5173"
    echo -e "${GREEN}✓ Browser opened${NC}"
# Open browser (Linux)
elif command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:5173"
    echo -e "${GREEN}✓ Browser opened${NC}"
else
    echo -e "${YELLOW}⚠ Could not auto-open browser. Navigate to: http://localhost:5173${NC}"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# RUNNING STATUS
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   CHAINBRIDGE V1 IS RUNNING${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "   ${CYAN}API Server:${NC}    http://localhost:8000"
echo -e "   ${CYAN}UI Dashboard:${NC}  http://localhost:5173"
echo -e "   ${CYAN}God-View API:${NC}  http://localhost:8000/occ/dashboard"
echo ""
echo -e "   ${PURPLE}API Logs:${NC}      /tmp/chainbridge_api.log"
echo -e "   ${PURPLE}UI Logs:${NC}       /tmp/chainbridge_ui.log"
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}   Press Ctrl+C to shutdown ChainBridge${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Keep script running and wait for interrupt
while true; do
    # Check if processes are still running
    if ! kill -0 "$API_PID" 2>/dev/null; then
        echo -e "${RED}⚠ API Server died unexpectedly. Check /tmp/chainbridge_api.log${NC}"
        break
    fi
    if ! kill -0 "$UI_PID" 2>/dev/null; then
        echo -e "${RED}⚠ UI Server died unexpectedly. Check /tmp/chainbridge_ui.log${NC}"
        break
    fi
    sleep 5
done
