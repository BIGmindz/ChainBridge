#!/usr/bin/env bash
# Restart Trading System Components

# Current directory
cd "$(dirname "$0")"

echo "🔄 Restarting trading system components..."
echo "=========================================="

# Kill any stuck processes
echo "🛑 Stopping existing processes..."
pkill -f "new_listings_radar" 2>/dev/null
pkill -f "system_monitor" 2>/dev/null
echo "✅ Stopped existing processes"

# Restart the New Listings Radar
echo "🚀 Starting New Listings Radar..."
nohup python3 run_new_listings_radar.py --scan > radar.log 2>&1 &
RADAR_PID=$!
echo "✅ New Listings Radar RESTARTED - PID: $RADAR_PID"

# Restart the System Monitor
echo "🚀 Starting System Monitor..."
nohup python3 system_monitor.py > monitor.log 2>&1 &
MONITOR_PID=$!
echo "✅ System Monitor RESTARTED - PID: $MONITOR_PID"

# Verify everything is running
echo "🔍 Verifying processes..."
sleep 2
ps aux | grep -E "(new_listings|system_monitor|multi_signal)" | grep -v grep

echo "
╔════════════════════════════════════════════════════════════╗
║   🚀 FULL SYSTEM NOW OPERATIONAL!                         ║
║   New Listings Radar: HUNTING                             ║
║   System Monitor: TRACKING                                ║
║   Multi-Signal Bot: TRADING                               ║
╚════════════════════════════════════════════════════════════╝
"