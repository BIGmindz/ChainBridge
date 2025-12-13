#!/usr/bin/env bash

# ============================================================================
# PHASE 3 - DOCKER STARTUP & GOD MODE TESTING GUIDE
# ============================================================================
# Complete startup sequence for ChainBridge with Ticking Timebomb
# ============================================================================

cat << 'EOF'

╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║        🚀 PHASE 3: TICKING TIMEBOMB - DOCKER STARTUP GUIDE                  ║
║                                                                              ║
║                   Dutch Auction UI with Price Decay Animation                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

📋 PRE-FLIGHT CHECKLIST
═══════════════════════════════════════════════════════════════════════════════

Before starting the system, verify:

✓ Docker Desktop is installed and running
✓ Port 3000 (frontend) is available
✓ Port 8000 (API) is available
✓ Port 5432 (PostgreSQL) is available
✓ Port 6379 (Redis) is available

Command to check ports:
  lsof -i :3000 :8000 :5432 :6379

═══════════════════════════════════════════════════════════════════════════════

🚀 STEP 1: IGNITE THE ENGINES
═══════════════════════════════════════════════════════════════════════════════

Navigate to the ChainBridge root directory:

  cd /Users/johnbozza/Documents/Projects/ChainBridge-local-repo/ChainBridge

Build and start all services:

  docker-compose up --build -d

This will:
  ✓ Build the backend API container
  ✓ Build the frontend React container
  ✓ Start PostgreSQL database
  ✓ Start Redis cache
  ✓ Start API server (port 8000)
  ✓ Start React frontend (port 3000)

⏱️ Wait ~2 minutes for all services to start and become healthy.

Monitor container status:

  docker-compose ps

Expected output:
  NAME                  STATUS          PORTS
  chainbridge-api       Up (healthy)    0.0.0.0:8000->8000/tcp
  chainbridge-frontend  Up (healthy)    0.0.0.0:3000->3000/tcp
  chainbridge-db        Up (healthy)    0.0.0.0:5432->5432/tcp
  chainbridge-cache     Up (healthy)    0.0.0.0:6379->6379/tcp

═══════════════════════════════════════════════════════════════════════════════

💾 STEP 2: INITIALIZE THE DATABASE
═══════════════════════════════════════════════════════════════════════════════

Run database migrations:

  docker-compose exec api alembic upgrade head

Expected output:
  INFO [alembic.migration] Running upgrade -> xxxx (description)
  ...
  (If already applied, will show: "Target database is up to date")

Seed demo data (optional):

  docker-compose exec api python scripts/seed_demo_data.py

═══════════════════════════════════════════════════════════════════════════════

🎯 STEP 3: ACCESS THE WAR ROOM
═══════════════════════════════════════════════════════════════════════════════

Open your browser to the following URLs:

FRONTEND (Sonny - React Dashboard):
  URL: http://localhost:3000

  What you'll see:
  ┌─ Chainboard navigation
  ├─ Operator Console (god mode access point)
  ├─ ChainSalvage Marketplace
  ├─ Shipment tracking
  └─ Financial dashboards

API DOCUMENTATION (Cody - FastAPI):
  URL: http://localhost:8000/docs

  What you'll see:
  ├─ Interactive API explorer
  ├─ All available endpoints
  ├─ Real-time marketplace data
  ├─ Auction pricing endpoints
  └─ Demo control endpoints

Database Admin (PgAdmin - optional):
  URL: http://localhost:5050 (if pgadmin enabled)

═══════════════════════════════════════════════════════════════════════════════

⚡ STEP 4: TEST "GOD MODE" IMMEDIATELY
═══════════════════════════════════════════════════════════════════════════════

Once frontend is live at http://localhost:3000:

ACTIVATE GOD MODE:
  1. Navigate to: Operator Console (or any page with listings)
  2. Press hotkey: Cmd + Shift + . (period)
     └─ Mac: Command (⌘) + Shift + .
     └─ Windows/Linux: Ctrl + Shift + .
  3. Observe: Floating HUD appears in bottom-right corner
     └─ With 4 demo control buttons
     └─ With semi-transparent backdrop blur

TEST SEQUENCE:

  ┌─ [RESET WORLD] Button
  │  └─ Effect: Marketplace restores to initial state
  │  └─ Watch: Shipment list populates with "Golden Path" data
  │  └─ Verify: All prices reset to start price
  │  └─ Feedback: "✓ World reset to initial state"
  │
  ├─ [📉 CRASH MARKET] Button
  │  └─ Effect: Triggers CRITICAL breach on all listings
  │  └─ Watch: "Breach Protocol" modal fires in operator console
  │  └─ Verify: All listings show red status indicators
  │  └─ Feedback: "📉 Market crashed: CRITICAL breach detected"
  │
  ├─ [⏩ FF +1h] Button
  │  └─ Effect: Fast-forwards auction by 1 hour
  │  └─ Watch: Dutch Auction price ticker decays rapidly
  │  └─ Verify: Price drops by 1 hour of decay
  │  └─ Feedback: "⏩ Time warped +1h"
  │
  └─ [⏩ FF +6h] Button
     └─ Effect: Fast-forwards auction by 6 hours
     └─ Watch: Larger price drop, red flash animation
     └─ Verify: Price approaches reserve
     └─ Feedback: "⏩ Time warped +6h"

═══════════════════════════════════════════════════════════════════════════════

🎬 PHASE 3 FEATURES TO TEST
═══════════════════════════════════════════════════════════════════════════════

TICKING TIMEBOMB (Dutch Auction):
  □ Navigate to marketplace listing detail page
  □ Watch DutchAuctionCard animate price smoothly
  □ See red flash when price drops > $1
  □ Watch countdown timer count down
  □ Check discount depth bar filling up
  □ Observe PriceDecayGraph updating in real-time

PRICE ANIMATION (60fps, no jitter):
  □ Open DevTools (F12) → Console tab
  □ Watch for any animation warnings
  □ Check frame rate remains at ~60fps
  □ Verify smooth price decay (not jumpy)
  □ Every 30 seconds: price updates from server

VISUAL URGENCY:
  □ Red flash plays when price drops
  □ Reserve reached: price turns amber
  □ All red/amber changes smooth with motion.span
  □ Buy button changes green when reserve reached

GOD MODE DEMO CONTROLS:
  □ Hotkey activation: Cmd+Shift+.
  □ Floating HUD appearance
  □ Demo control responsiveness
  □ Feedback message delivery
  □ Time warp effect on price
  □ Market crash effect on all listings

═══════════════════════════════════════════════════════════════════════════════

🔧 COMMON ISSUES & TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════════

❌ "docker-compose: command not found"
→ Solution: Use "docker compose" instead (newer Docker versions)
   Command: docker compose up --build -d

❌ Port 3000 or 8000 already in use
→ Solution: Kill existing process or change port in docker-compose.yml
   Command: lsof -i :3000 | grep LISTEN | awk '{print $2}' | xargs kill -9

❌ Container exits immediately
→ Solution: Check logs
   Command: docker-compose logs api
            docker-compose logs frontend

❌ Database connection timeout
→ Solution: Verify db container is healthy
   Command: docker-compose ps
            docker-compose logs db

❌ Frontend blank/not loading
→ Solution: Check React build output
   Command: docker-compose logs frontend
            npm run build (in chainboard-ui folder)

❌ God Mode hotkey not working
→ Solution: Ensure you're on the right page, try different key
   Alternative: Use Ctrl+Shift+. on Linux/Windows

═══════════════════════════════════════════════════════════════════════════════

🛑 STEP 5: STOP THE SYSTEM
═══════════════════════════════════════════════════════════════════════════════

To stop all services:

  docker-compose down

To stop and remove volumes (WARNING: deletes database):

  docker-compose down -v

To view logs for debugging:

  docker-compose logs -f api
  docker-compose logs -f frontend
  docker-compose logs -f db

═══════════════════════════════════════════════════════════════════════════════

📊 VERIFICATION CHECKLIST
═══════════════════════════════════════════════════════════════════════════════

After starting, verify:

✓ Frontend loads at http://localhost:3000
✓ API docs accessible at http://localhost:8000/docs
✓ No console errors in DevTools
✓ Containers show "Up (healthy)" in docker-compose ps
✓ God Mode hotkey (Cmd+Shift+.) opens floating HUD
✓ All four demo buttons visible and responsive
✓ Price animation smooth (no jitter)
✓ Red flash visible when price drops

═══════════════════════════════════════════════════════════════════════════════

🎯 LIVE SYSTEM STATUS
═══════════════════════════════════════════════════════════════════════════════

Your system is now running as a **Live Financial Operating System**.

Core Components Running:
  ✓ PostgreSQL Database (port 5432)
  ✓ Redis Cache (port 6379)
  ✓ FastAPI Backend (port 8000) - API, WebSockets, Auctions
  ✓ React Frontend (port 3000) - Chainboard, God Mode, Marketplace
  ✓ Dutch Auctions - Ticking Timebomb with price decay
  ✓ Demo Controls - God Mode with reset/crash/time-warp

Ready to:
  ✓ Trade financial instruments
  ✓ Track shipments in real-time
  ✓ Run live auctions with price animations
  ✓ Test system with God Mode controls
  ✓ Demo to stakeholders with time warp effects

═══════════════════════════════════════════════════════════════════════════════

Next Steps:
  1. Open http://localhost:3000 in browser
  2. Navigate to Operator Console or Marketplace
  3. Press Cmd+Shift+. to activate God Mode
  4. Click demo buttons to test system
  5. Watch price animations and market effects

Go break things! 🚀

═══════════════════════════════════════════════════════════════════════════════

EOF
