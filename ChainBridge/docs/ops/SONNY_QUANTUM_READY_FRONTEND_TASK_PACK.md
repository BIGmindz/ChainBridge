SONNY — QUANTUM-READY FRONTEND TASK PACK
========================================

Mission:
Make ChainBoard and The OC a future-proof, CIA-grade visualization layer
with zero business logic, perfect alignment with backend contracts, and
full readiness for AI/quantum data streams.

You own:
The OC (Operator Console), Shipment Journey, IoT/ChainSense panels,
ChainBoard UI/UX, TypeScript schema consistency.

--------------------------------------
1. ALIGN TS TYPES WITH BACKEND ENUMS
--------------------------------------
After Cody finalizes canonical enums:
- Update src/types/chainbridge.ts to match EXACTLY.
- Replace ALL hard-coded string literals.

Definition of Done:
- No UI logic uses rogue strings. All enums come from a single TS type set.

--------------------------------------
2. THE OC — BACKEND-DRIVEN LOGIC ONLY
--------------------------------------
Ensure The OC:
- Uses backend ordering for queue (no custom sort).
- Uses backend flags (is_critical, needs_snapshot).
- Never computes risk or status locally.
- Snapshot export triggers React Query invalidations correctly.

Definition of Done:
- Backend can change policies and The OC updates instantly without code edits.

--------------------------------------
3. SHIPMENT JOURNEY — API-FIRST VISUALIZATION
--------------------------------------
Visualize:
- Event history (ShipmentEvent, RiskEvent, PaymentEvent, ScoreEvent)
- IoT streams (temp, shocks, GPS)
- ChainScore badges
- Timeline + map path (truck → rail → vessel → air transitions)

No local inference or business logic.

Definition of Done:
- Journey view is pure visualization: no logic, just reading API data.

--------------------------------------
4. CHAINSENSE: IOT PANEL
--------------------------------------
Implement IoTHealthPanel that:
- Reads backend-provided flags:
  - is_safe
  - is_at_risk
  - is_anomalous
- Shows charts, maps, gauges based on API data.

Definition of Done:
- UI never decides risk — backend does.

--------------------------------------
5. CHAINSCORE BADGES & HUDs
--------------------------------------
Implement:
- Bronze / Silver / Gold / Platinum badges
- Tooltip showing:
  - On-time %
  - Claims %
  - Data Quality %
  - Responsiveness %

Definition of Done:
- Badges reflect backend-calculated tier/score ONLY.

--------------------------------------
6. CINEMATIC MAP VISUALIZATION (The OC)
--------------------------------------
Prepare mapping layer for:
- Mode transitions animations
- Real-time geo movement (truck icon → vessel icon → rail icon → aircraft)
- Risk overlays (storms, port congestion)
- Event markers (gate-in, gate-out, POD)
- Ready for VR expansion in future

Definition of Done:
- Map consumes normalized coordinates + events in chronological order.

--------------------------------------
7. ERROR HANDLING & TRACEABILITY
--------------------------------------
For all API calls:
- Clear error surfaces
- Log shipment_id + request_id for failures
- UI can explain what broke and why

Definition of Done:
- Every UI issue maps back to backend via canonical IDs.

--------------------------------------
8. UI OBSERVABILITY & EXPERIENCE
--------------------------------------
Implement:
- Loading skeletons
- Retry patterns
- Operator-friendly alerts
- High-performance updates for fast polling feeds

Definition of Done:
- The OC feels like a CIA ops center: instant, responsive, authoritative.

--------------------------------------
SONNY COMPLETION CRITERIA
--------------------------------------
Frontend becomes a thin, perfect mirror of backend intelligence,
zero duplicated logic, and delivers a cinematic, enterprise-grade
experience through The OC, Journey, IoT, and ChainScore views.

---

## Implementation Notes

**Current State (Post-M02 Sprint):**
- ✅ The OC foundation complete with backend API integration
- ✅ React Query polling configured for real-time updates
- ✅ TypeScript types aligned with backend schemas
- 🚧 Shipment Journey visualization pending
- 🚧 ChainSense IoT panels pending
- 🚧 ChainScore badges pending
- 🚧 Cinematic mapping layer pending

**Priority Order:**
1. Complete The OC refinements (error handling, performance)
2. Build Shipment Journey event timeline
3. Implement ChainSense IoT health panels
4. Add ChainScore visualization components
5. Create cinematic mapping infrastructure
6. Polish observability and user experience

**Technical Dependencies:**
- Canonical enums from Cody's backend work
- Event log API endpoints
- IoT data streaming endpoints
- ChainScore calculation APIs
- Geospatial event data with coordinates

---

**Last Updated:** 2025-11-19
**Version:** 1.0
**Status:** Ready for Implementation
