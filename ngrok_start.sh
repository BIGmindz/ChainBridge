#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# PAC-STRAT-P26-FULL-IGNITION — ChainBridge Ignition Sequence
# Launches Sovereign Relay + Ngrok Tunnel + Live Monitor
# Governance Tier: INFRASTRUCTURE_GO_LIVE
# ═══════════════════════════════════════════════════════════════════════════════
#
# "The machine is listening. Speak the Law."
#
# Usage: bash ngrok_start.sh
#
# Prerequisites:
#   - ngrok installed and authenticated (ngrok config add-authtoken <token>)
#   - ARCHITECT_PUB_KEY_HEX environment variable set
#   - Python virtual environment at .venv/
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "🔥 CHAINBRIDGE FULL IGNITION SEQUENCE - P26"
echo "═══════════════════════════════════════════════════════════════════"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: CLEANUP
# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "🧹 PHASE 1: Cleaning up old processes..."

# Kill any existing relay or ngrok processes
pkill -f bridge_relay.py 2>/dev/null || true
pkill -f ngrok 2>/dev/null || true
lsof -ti:8080 | xargs kill -9 2>/dev/null || true

sleep 2

echo "   ✅ Old processes terminated"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: ENVIRONMENT CHECK
# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "🔑 PHASE 2: Verifying environment..."

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "   ✅ Virtual environment activated"
else
    echo "   ❌ ERROR: .venv not found. Run 'make venv && make install' first."
    exit 1
fi

# Check for ARCHITECT_PUB_KEY_HEX
if [ -z "$ARCHITECT_PUB_KEY_HEX" ]; then
    echo "   ⚠️  WARNING: ARCHITECT_PUB_KEY_HEX not set!"
    echo "   Generating ephemeral key pair for testing..."
    
    # Generate ephemeral key pair
    KEY_OUTPUT=$(python3 -c "
from nacl.signing import SigningKey
sk = SigningKey.generate()
pk = sk.verify_key.encode().hex()
print(f'PUBLIC:{pk}')
print(f'PRIVATE:{sk.encode().hex()}')
")
    
    export ARCHITECT_PUB_KEY_HEX=$(echo "$KEY_OUTPUT" | grep "PUBLIC:" | cut -d: -f2)
    EPHEMERAL_PRIVATE=$(echo "$KEY_OUTPUT" | grep "PRIVATE:" | cut -d: -f2)
    
    echo "   🔑 Ephemeral Public Key: ${ARCHITECT_PUB_KEY_HEX:0:16}..."
    echo "   🔑 Ephemeral Private Key: ${EPHEMERAL_PRIVATE:0:16}... (save this for signing!)"
    echo ""
    echo "   To make permanent, run:"
    echo "   export ARCHITECT_PUB_KEY_HEX=$ARCHITECT_PUB_KEY_HEX"
    echo ""
else
    echo "   ✅ ARCHITECT_PUB_KEY_HEX is set: ${ARCHITECT_PUB_KEY_HEX:0:16}..."
fi

# Check for ngrok
if ! command -v ngrok &> /dev/null; then
    echo "   ❌ ERROR: ngrok not installed."
    echo "   Install with: brew install ngrok"
    exit 1
fi
echo "   ✅ ngrok found"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: LAUNCH RELAY
# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "🚀 PHASE 3: Launching Sovereign Relay v2.2.1..."

# Create logs directory
mkdir -p logs

# Launch relay in background, logging to file
nohup python3 bridge_relay.py > logs/bridge_relay_stdout.log 2>&1 &
RELAY_PID=$!

echo "   Relay PID: $RELAY_PID"
sleep 3

# Verify relay started
if ! kill -0 $RELAY_PID 2>/dev/null; then
    echo "   ❌ ERROR: Relay failed to start. Check logs/bridge_relay_stdout.log"
    tail -20 logs/bridge_relay_stdout.log
    exit 1
fi

# Verify health endpoint
HEALTH=$(curl -s http://localhost:8080/health 2>/dev/null || echo "FAILED")
if echo "$HEALTH" | grep -q "2.2.1"; then
    echo "   ✅ Relay v2.2.1 ACTIVE on http://localhost:8080"
else
    echo "   ⚠️  Relay health check unclear: $HEALTH"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: LAUNCH NGROK TUNNEL
# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "🌍 PHASE 4: Establishing Ngrok tunnel..."

# Launch ngrok in background
ngrok http 8080 --log=stdout > logs/ngrok.log 2>&1 &
NGROK_PID=$!

echo "   Ngrok PID: $NGROK_PID"
sleep 3

# Get the public URL from ngrok API
NGROK_URL=""
for i in {1..10}; do
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    tunnels = data.get('tunnels', [])
    for t in tunnels:
        if 'https' in t.get('public_url', ''):
            print(t['public_url'])
            break
    else:
        if tunnels:
            print(tunnels[0]['public_url'])
except:
    pass
" 2>/dev/null)
    
    if [ -n "$NGROK_URL" ]; then
        break
    fi
    sleep 1
done

if [ -z "$NGROK_URL" ]; then
    echo "   ❌ ERROR: Could not retrieve Ngrok URL"
    echo "   Check logs/ngrok.log for details"
    exit 1
fi

echo "   ✅ Tunnel established!"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: IGNITION COMPLETE
# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "🔥 FULL IGNITION COMPLETE"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "   🌍 PUBLIC URL:  $NGROK_URL"
echo "   🏠 LOCAL URL:   http://localhost:8080"
echo "   📊 NGROK DASH:  http://localhost:4040"
echo ""
echo "   Endpoints:"
echo "   ├── $NGROK_URL/health"
echo "   └── $NGROK_URL/pac-ingress"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "   The machine is listening. Speak the Law."
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Save the URL to a file for easy access
echo "$NGROK_URL" > logs/ngrok_url.txt
echo "   URL saved to logs/ngrok_url.txt"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: LAUNCH MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

echo "🔵 Starting Live Monitor (Ctrl+C to stop)..."
echo ""

python3 bridge_monitor.py
