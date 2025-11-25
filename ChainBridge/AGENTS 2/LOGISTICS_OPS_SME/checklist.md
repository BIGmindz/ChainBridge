# Logistics Operations SME – ChainBridge M02 Checklist

## Your Role in ChainBridge

As the Logistics Operations Subject Matter Expert, you oversee the **operational readiness** of ChainBridge's risk & settlement pipeline. You ensure that:

1. **At-Risk Shipment Data** reflects real logistics scenarios
2. **Snapshot Export Events** map to actual operational events
3. **Worker Pipeline** processes exports in compliance with logistics SLAs
4. **Timeline Visibility** enables ops teams to track shipment risk evolution

---

## M02 Logistics Deliverables

### 1. ✅ At-Risk Data Model & Seeding

**Status:** In Progress

**What You Need to Validate:**

- [ ] **Shipment Attributes** are logistics-accurate:
  - `corridor_code` (e.g., IN_US, CN_EU) – real trade lanes
  - `mode` (FCL, LCL, Partial Container Load) – matches carrier options
  - `incoterm` (CIF, FOB, DAP, DDP) – valid per Incoterms 2020
  - `risk_score` (0–100) – based on real risk factors (delays, port congestion, currency)
  - `risk_level` (LOW, MODERATE, HIGH) – maps to ops severity
  - `origin`, `destination` – valid port/airport codes
  - `eta_days` – realistic transit times per corridor

- [ ] **Demo Data Volume:** 20–50 shipments covering:
  - All risk levels (LOW, MODERATE, HIGH)
  - Multiple corridors (IN_US, CN_EU, JP_US, etc.)
  - Multiple modes (FCL, LCL)
  - Multiple incoterms (CIF, FOB, DAP)
  - Realistic ETA ranges (7–60 days depending on corridor)

**Verify:**
```bash
# After seed script runs:
curl "http://127.0.0.1:8001/chainiq/shipments/at_risk?max_results=50" | jq '.[] | {id: .shipment_id, corridor: .corridor_code, risk: .risk_level, eta: .eta_days}'
```

**Expected Output:**
```
{
  "id": "SHP-001",
  "corridor": "IN_US",
  "risk": "HIGH",
  "eta": 35
}
```

---

### 2. 🔥 Snapshot Export Events – Operational Mapping

**Status:** In Progress

**What You Need to Validate:**

- [ ] **Event Status Transitions** map to real ops workflows:
  - `PENDING` → Export created, awaiting processing (e.g., doc verification)
  - `IN_PROGRESS` → Worker claiming and processing (e.g., compiling shipment docs)
  - `SUCCESS` → Export complete, ready for hold/proof (e.g., all docs verified)
  - `FAILED` → Export failed (e.g., missing BOL, invalid incoterm)
  - `RETRY` → Temporary failure, will re-attempt (e.g., transient API error)

- [ ] **Failure Reasons** are operationally meaningful:
  - "Missing Bill of Lading"
  - "Invalid Incoterm for corridor"
  - "Port congestion delay (retry in 5m)"
  - "Customs hold – requires documentation review"
  - etc.

- [ ] **Retry Logic** respects SLA:
  - `MAX_EXPORT_RETRIES = 3`
  - Retry wait time (if applicable): 5–30 seconds for demo, configurable
  - After max retries: escalate to ops team (mark FAILED permanently)

**Verify Timeline:**
```bash
# Click Timeline button on any at-risk shipment:
# Expected to show event history with statuses:
# 1. PENDING (created 5 min ago)
# 2. IN_PROGRESS (claimed by worker-001, 4 min ago)
# 3. SUCCESS (completed 2 min ago)
```

---

### 3. 🔥 Worker Pipeline – Processing & Reliability

**Status:** In Progress

**What You Need to Validate:**

- [ ] **Worker Lifecycle** is robust:
  - [ ] No duplicate claims (only one worker processes one event)
  - [ ] Graceful handling of worker crashes (events revert to PENDING after timeout)
  - [ ] Claim timestamp recorded for audit trail
  - [ ] Processing time tracked (duration = completed_at - started_at)

- [ ] **Concurrency Safety:**
  - [ ] Run 2+ workers simultaneously; verify no race conditions
  - [ ] Events are claimed by exactly one worker
  - [ ] No "phantom" SUCCESS events without proper claim

- [ ] **Retry Strategy:**
  - [ ] Transient failures (e.g., network timeout) trigger retry
  - [ ] Permanent failures (e.g., invalid incoterm) fail immediately
  - [ ] Retry count incremented correctly
  - [ ] Max retries enforced

**Verification Test:**
```bash
# Terminal 1: Start worker
python -m scripts.run_snapshot_worker --worker-id=worker-001 --interval=2

# Terminal 2: Start second worker
python -m scripts.run_snapshot_worker --worker-id=worker-002 --interval=2

# Terminal 3: Seed data and create export
python -m scripts.seed_chainiq_demo --count=10
curl -X POST http://127.0.0.1:8001/chainiq/admin/snapshot_exports \
  -H "Content-Type: application/json" \
  -d '{"shipment_id": "SHP-001", "include_related": true}'

# Monitor: Both workers should process events without conflicts
tail -f /tmp/snapshot_worker.log
```

---

### 4. ✅ Snapshot Export → At-Risk Enrichment

**Status:** Pending Backend Implementation

**What You Need to Validate:**

- [ ] **Latest Snapshot Status** appears in at-risk table:
  - New column: "Snapshot Status"
  - Values: "Exported" (SUCCESS), "Exporting…" (IN_PROGRESS), "Failed" (FAILED), "—" (no export)
  - Updates in real-time as table polls

- [ ] **Oldest-First Ordering:** Shipments with oldest exports appear first (or configurable)

- [ ] **Color Coding:**
  - Green badge: SUCCESS ("Exported")
  - Yellow badge: IN_PROGRESS ("Exporting…")
  - Red badge: FAILED ("Failed")
  - Gray badge: None ("—")

**Verification:**
```
ChainBoard UI → Fleet Cockpit
Look for: "Snapshot Status" column with badges
Verify: Export button creates event → column updates within 15 seconds
```

---

## M02 Ops Checklist

### Data Preparation

- [ ] Identify real trade lane data sources (TBD with ops)
- [ ] Map risk factors to risk_score calculation:
  - [ ] Days delay vs ETA
  - [ ] Port congestion index
  - [ ] Currency volatility
  - [ ] Carrier reliability score
  - [ ] Customs clearance time
- [ ] Define risk_level thresholds:
  - HIGH: risk_score ≥ 70
  - MODERATE: 40 ≤ risk_score < 70
  - LOW: risk_score < 40

### Operational SLA Validation

- [ ] **Processing SLA:** Worker should process export within X seconds (target: 3–5s for demo)
- [ ] **Failure Rate:** Acceptable failure % before escalation (target: <5% in demo)
- [ ] **Retry SLA:** Maximum time to retry failed export (target: 30s per retry)
- [ ] **E2E SLA:** From "at-risk" detection to "export success" (target: <60s)

### Documentation

- [ ] Seed data schema documented (what each field means operationally)
- [ ] Worker event status workflow diagram (PENDING → SUCCESS/FAILED)
- [ ] Retry strategy documented (when/why retries happen)
- [ ] Failure scenarios documented (common failure reasons)

---

## Integration Touchpoints

### With Cody (Backend)

- [ ] Review seed data schema with Cody
- [ ] Approve at-risk enrichment response format
- [ ] Define worker processing simulation parameters (success rate, processing time)
- [ ] Review failure scenarios and retry logic

### With Sonny (Frontend)

- [ ] Review UI column labels and terminology
- [ ] Verify color coding matches ops conventions
- [ ] Test polling intervals (table 15s, drawer 5s) for ops visibility
- [ ] Validate Timeline Drawer event display for ops ease-of-use

### With Investor/Stakeholder

- [ ] Review demo data set (is it representative?)
- [ ] Validate SLA targets (are they realistic?)
- [ ] Confirm workflow (PENDING → SUCCESS) matches their expectations

---

## Success Criteria (M02 – Logistics Phase)

- [ ] **50 realistic at-risk shipments** visible in ChainBoard
- [ ] **Snapshot export events** process through full lifecycle (PENDING → SUCCESS)
- [ ] **Timeline Drawer** shows real event history with statuses
- [ ] **Worker pipeline** is reliable, concurrent, and well-logged
- [ ] **At-risk table** enriched with latest snapshot status in real-time
- [ ] **Ops team can monitor** full export lifecycle in UI
- [ ] **SLAs validated** (processing time, failure rate, E2E time)

---

## Commands You'll Use (M02)

```bash
# Seed demo shipments
python -m scripts.seed_chainiq_demo --count=50 --clear

# Start worker (in background or separate terminal)
python -m scripts.run_snapshot_worker --worker-id=ops-worker-01 --interval=2 &

# Monitor worker logs
tail -f /tmp/snapshot_worker.log

# Query at-risk endpoint
curl "http://127.0.0.1:8001/chainiq/shipments/at_risk?max_results=50" | jq

# Check export history
curl "http://127.0.0.1:8001/chainiq/admin/snapshot_exports?shipment_id=SHP-001" | jq

# Verify worker health
curl http://127.0.0.1:8001/health | jq '.active_pipelines'
```

---

## Known Ops Considerations

- **Demo Processing:** Workers will simulate 1–3s processing; real workers may vary
- **Failure Simulation:** Demo will inject random failures (20% rate) for testing; production will use real error detection
- **Data Lifecycle:** Demo data persists across runs; use `--clear` flag to reset
- **Timezone:** All timestamps in UTC; ensure ops team dashboard also uses UTC

---

**Next Steps:**
1. ✅ Review at-risk data model (Cody & You)
2. 🔥 Implement seed script (Cody)
3. 🔥 Validate worker lifecycle (You & Cody)
4. 🔥 Test UI enrichment (Sonny)
5. 📊 Create ops monitoring dashboard (future M03)
