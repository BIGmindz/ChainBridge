#!/usr/bin/env bash

# ============================================================================
# TICKING TIMEBOMB - QUICK START GUIDE
# ============================================================================
# How to test Phase 3 components and features
# ============================================================================

cat << 'EOF'

╔════════════════════════════════════════════════════════════════════════════╗
║          TICKING TIMEBOMB - QUICK REFERENCE GUIDE                         ║
║               Dutch Auction UI with Price Decay Animation                  ║
╚════════════════════════════════════════════════════════════════════════════╝

🎬 HOW TO TEST
══════════════════════════════════════════════════════════════════════════════

1. NAVIGATE TO LISTING DETAIL
   ────────────────────────────
   URL: http://localhost:3000/marketplace/:listingId

   What you'll see:
   ┌─ Header with back button
   ├─ Hero: Asset image (left) + DutchAuctionCard (right)
   ├─ Red flash when price drops
   ├─ Countdown timer
   ├─ Large "Buy Now for $X" button
   ├─ Risk factors section
   ├─ PriceDecayGraph showing price trajectory
   └─ Wallet connection alert (if needed)

2. WATCH PRICE ANIMATION
   ──────────────────────
   • Price updates smoothly every 30 seconds
   • No jitter or jumping
   • When price drops > $1: RED FLASH animation plays for 600ms
   • Watch the PriceDecayGraph update in real-time
   • Discount depth bar fills as price decays

3. TRIGGER GOD MODE DEMO CONTROLS
   ───────────────────────────────
   Hotkey: Cmd+Shift+. (Mac) or Ctrl+Shift+. (Windows/Linux)

   What happens:
   ✓ Floating HUD appears in bottom-right corner
   ✓ Semi-transparent backdrop blur
   ✓ Four buttons visible:
     - [Reset World]
     - [📉 Crash Market]
     - [⏩ FF +1h]
     - [⏩ FF +6h]

4. TEST DEMO CONTROLS
   ──────────────────

   [Reset World]
   └─ Restores marketplace to initial state
   └─ All prices reset to start price
   └─ Show feedback: "✓ World reset to initial state"

   [📉 Crash Market]
   └─ Triggers CRITICAL breach event
   └─ All listings show red status indicators
   └─ Show feedback: "📉 Market crashed: CRITICAL breach detected"

   [⏩ FF +1h]
   └─ Fast-forwards auction by 1 hour
   └─ Price decays by 1 hour worth
   └─ PriceDecayGraph updates immediately
   └─ Show feedback: "⏩ Time warped +1h"

   [⏩ FF +6h]
   └─ Fast-forwards auction by 6 hours
   └─ Price decays by 6 hours worth
   └─ Red flash animation if large drop
   └─ Show feedback: "⏩ Time warped +6h"

5. TEST BUY FLOW (If wallet connected)
   ─────────────────────────────────────
   ✓ Click "Buy Now for $X" button
   ✓ Wallet signing prompt appears
   ✓ Sign the transaction
   ✓ Success animation plays (green checkmark)
   ✓ Redirect to marketplace after 2 seconds

6. KEYBOARD NAVIGATION
   ───────────────────
   • Tab: Focus on buttons
   • Enter: Trigger focused button
   • Cmd+Shift+.: Toggle God Mode
   • Escape: Close dialogs

📊 PRICE ANIMATION VERIFICATION
══════════════════════════════════════════════════════════════════════════════

Check in browser console:
  • Open: Developer Tools (F12)
  • Go to: Console tab
  • Price should update every 30 seconds
  • requestAnimationFrame logs every frame (disable in prod)

Watch for:
  ✓ Smooth price decay (no jumps)
  ✓ Red flash when price drops
  ✓ Countdown timer counting down
  ✓ Discount depth bar filling
  ✓ PriceDecayGraph line moving down

🔧 PERFORMANCE CHECKS
══════════════════════════════════════════════════════════════════════════════

React DevTools (Chrome Extension):
  1. Install "React Developer Tools"
  2. Open DevTools → Components tab
  3. Expand DutchAuctionCard component
  4. Watch props update every 30s (not every frame)
  5. Should see 0 re-renders between price updates

Performance Tab:
  1. DevTools → Performance tab
  2. Start recording
  3. Wait 5 seconds (price animation plays)
  4. Stop recording
  5. Check Frame Rate (should be ~60fps)
  6. Look for animation in "Rendering" section

🌐 API ENDPOINTS TESTED
══════════════════════════════════════════════════════════════════════════════

GET /api/marketplace/listing/:id/live-price
  └─ Returns: { officialPrice, calculatedPrice, decayPerSecond, priceDropped }
  └─ Called every 30 seconds by useDutchPrice hook

GET /api/marketplace/listing/:id
  └─ Returns: Listing with dutchAuction state
  └─ Called on page load and refetch

POST /demo/reset
  └─ Resets marketplace (demo only)
  └─ Returns: { success: true }

POST /demo/trigger-breach
  └─ Triggers breach event (demo only)
  └─ Payload: { listingId, breachType, severity }

POST /demo/warp-time
  └─ Advances auction time (demo only)
  └─ Payload: { listingId, hoursToAdvance }

✅ VALIDATION CHECKLIST
══════════════════════════════════════════════════════════════════════════════

Feature Tests:
  □ Price animates smoothly (no jitter)
  □ Red flash plays when price drops
  □ Countdown timer counts down
  □ Discount depth bar updates
  □ PriceDecayGraph shows correct trajectory
  □ Start/Current/Reserve prices displayed
  □ Risk factors clearly shown
  □ Condition rating shows 0-100

God Mode Tests:
  □ Cmd+Shift+. opens panel
  □ Cmd+Shift+. closes panel (toggle)
  □ Reset World button works
  □ Crash Market button works
  □ Fast Forward buttons work
  □ Feedback messages appear
  □ Floating indicator visible when closed

Performance Tests:
  □ Frame rate stays at 60fps during animation
  □ No layout thrashing
  □ No memory leaks
  □ No excessive re-renders

Accessibility Tests:
  □ All buttons have titles
  □ Keyboard navigation works
  □ Color contrast meets AA standard
  □ No keyboard traps

💡 TROUBLESHOOTING
══════════════════════════════════════════════════════════════════════════════

Price doesn't animate?
  → Check browser console for API errors
  → Verify /api/marketplace/listing/:id/live-price endpoint is responding
  → Check that listing.dutchAuction is populated

Red flash doesn't appear?
  → Check that price is dropping by more than $1
  → Verify motion.div animation in DutchAuctionCard
  → Open DevTools → check for animation warnings

God Mode panel won't open?
  → Make sure you're pressing Cmd (Mac) or Ctrl (Windows)
  → Try Cmd+Shift+/ instead (some keyboards map . differently)
  → Check browser console for hotkey detection logs

Buy button disabled?
  → Check that wallet is connected (if required)
  → Verify listing.status !== "SOLD"
  → Check that wallet.isConnected is true

🚀 NEXT STEPS AFTER TESTING
══════════════════════════════════════════════════════════════════════════════

Phase 6: Web3 Integration
  • Connect useMarketplaceWallet to DutchAuctionCard
  • Test transaction signing and submission
  • Verify gas estimation display

Phase 7: Final Testing
  • Run E2E tests for complete buy flow
  • Test on mobile (one-thumb buying)
  • Cross-browser testing (Safari, Firefox, Chrome)
  • Accessibility audit (WCAG 2.1 Level AA)

Phase 8: Acceptance & Deployment
  • Performance profiling under load
  • Load test with 100+ listings
  • Create stakeholder demo script
  • Deploy to production

═══════════════════════════════════════════════════════════════════════════════
Questions? Check: src/components/marketplace/DutchAuctionCard.tsx
           or: src/pages/ListingDetail/index.tsx
═══════════════════════════════════════════════════════════════════════════════

EOF
