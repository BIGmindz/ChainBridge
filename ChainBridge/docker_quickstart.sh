#!/usr/bin/env bash

# ============================================================================
# PHASE 3 QUICK START - One-Command System Startup
# ============================================================================

set -e

cd "$(dirname "$0")" || exit 1

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                          ║"
echo "║        🚀 PHASE 3: TICKING TIMEBOMB - QUICK START                        ║"
echo "║                                                                          ║"
echo "║              Initializing ChainBridge Financial OS...                    ║"
echo "║                                                                          ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Create data directory
echo "📂 Step 1: Setting up data directory..."
mkdir -p data
echo "   ✓ Data directory ready"

# Step 2: Build and start containers
echo ""
echo "🐳 Step 2: Building and starting Docker containers..."
echo "   This may take 1-2 minutes on first run..."
echo ""

if ! docker-compose up --build -d 2>&1 | tail -20; then
    echo ""
    echo "❌ Docker startup failed!"
    echo ""
    echo "Troubleshooting:"
    echo "  • Is Docker Desktop running?"
    echo "  • Are ports 3000, 8000, 5432, 6379 available?"
    echo "  • Check: docker-compose logs"
    exit 1
fi

echo ""
echo "✓ Containers started successfully"
echo ""

# Step 3: Wait for services to be healthy
echo "⏳ Step 3: Waiting for services to become healthy..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if docker-compose ps | grep -q "Up.*healthy"; then
        echo "   ✓ Services are healthy"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo -n "."
    sleep 2
done

if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
    echo ""
    echo "⚠️  Services took longer to start. Continuing anyway..."
fi

echo ""

# Step 4: Run migrations
echo "💾 Step 4: Running database migrations..."
if docker-compose exec -T api alembic upgrade head 2>/dev/null; then
    echo "   ✓ Migrations completed"
else
    echo "   ⓘ Migrations skipped (may already be applied)"
fi

echo ""

# Step 5: Display URLs and next steps
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                          ║"
echo "║                    ✅ SYSTEM STARTUP COMPLETE                            ║"
echo "║                                                                          ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

echo "📌 SERVICE ENDPOINTS:"
echo ""
echo "  🌐 Frontend (Chainboard):"
echo "     http://localhost:3000"
echo ""
echo "  📚 API Documentation:"
echo "     http://localhost:8000/docs"
echo ""
echo "  🗄️  Database:"
echo "     host: localhost:5432"
echo "     db: chainbridge_dev"
echo ""

echo "🎮 GOD MODE ACTIVATION:"
echo ""
echo "  1. Open http://localhost:3000"
echo "  2. Navigate to Operator Console or Marketplace"
echo "  3. Press: Cmd+Shift+. (or Ctrl+Shift+. on Windows/Linux)"
echo "  4. Floating HUD appears → Click demo buttons"
echo ""

echo "🧪 TEST SEQUENCE:"
echo ""
echo "  [RESET WORLD]      → Market restores to initial state"
echo "  [📉 CRASH MARKET]  → All listings show breach"
echo "  [⏩ FF +1h]        → Price decays by 1 hour"
echo "  [⏩ FF +6h]        → Price decays by 6 hours"
echo ""

echo "🛑 TO STOP THE SYSTEM:"
echo ""
echo "  docker-compose down"
echo ""

echo "📖 FULL DOCUMENTATION:"
echo ""
echo "  bash DOCKER_STARTUP_GUIDE.sh"
echo ""

echo "✨ System is running! Go break things. 🚀"
echo ""
