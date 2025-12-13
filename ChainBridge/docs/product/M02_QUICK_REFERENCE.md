# 🚀 ChainBridge Quick Reference Card

## M02 At a Glance

```
CURRENT STATE (Nov 19, 2025)
├─ M01: ✅ COMPLETE – API up, UI connected, snapshot exports wired
├─ M02: 🔥 IN PROGRESS – Seeding, enrichment, workers, enrichment
├─ M03: ⬜ BLOCKED – Awaiting M02 completion
└─ M04: ⬜ BLOCKED – Awaiting M03

BACKEND STATUS
├─ API: ✅ http://localhost:8001 (FastAPI)
├─ Health: ✅ /health endpoint
├─ At-Risk: ✅ /chainiq/shipments/at_risk (needs seeding)
├─ Exports: ✅ POST/GET /chainiq/admin/snapshot_exports
├─ CORS: ✅ localhost:5173 allowed
└─ Logs: ✅ /tmp/api.log

FRONTEND STATUS
├─ Base URL: ✅ http://localhost:8001
├─ Cockpit: ✅ ShipmentRiskTable.tsx (filters, pagination, export)
├─ Timeline: ✅ SnapshotTimelineDrawer.tsx (5s polling)
├─ Health: ✅ APIHealthIndicator.tsx (45s polling)
└─ Build: ✅ npm run build passes

DATA STATUS
├─ Seed Script: ⬜ TODO (Cody)
├─ Enrichment: ⬜ TODO (Cody)
├─ Worker Lifecycle: ⬜ TODO (Cody)
└─ Worker Runner: ⬜ TODO (Cody)

UI TODO (M02)
├─ Empty States: ⬜ TODO (Sonny)
├─ Risk Filter Pills: ⬜ TODO (Sonny)
└─ Timeline Polish: ⬜ TODO (Sonny)
```

---

## Core Workflows

### Create & Export Snapshot (Current ✅)

```
1. User clicks "Export" button on at-risk shipment
2. Frontend calls POST /chainiq/admin/snapshot_exports
3. Backend creates SnapshotExportEvent (PENDING status)
4. Button disables, spinner shows
5. Frontend polls table (15s) → snapshot status updates
6. User clicks Timeline button
7. Timeline drawer opens → shows event history
8. Drawer polls (5s) → shows events updating (still PENDING)
```

### Process Snapshot with Worker (M02 🔥)

```
1. Seed data: 50 at-risk shipments inserted
2. Backend enriches /chainiq/shipments/at_risk with latest snapshot status
3. User clicks Export → event created (PENDING)
4. Worker running: python -m scripts.run_snapshot_worker
5. Worker claims event → status = IN_PROGRESS
6. Worker simulates processing (1-3s)
7. Worker marks SUCCESS → status = SUCCESS
8. Timeline shows: PENDING → IN_PROGRESS → SUCCESS
9. Table snapshot status badge updates to "Exported"
```

---

## M02 Task Breakdown

### Cody (Backend)

```
🔥 Priority 1: Seed Data Script
  └─ scripts/seed_chainiq_demo.py
     • Generates 50 realistic shipments
     • Multiple corridors, modes, incoterms, risk levels
     • Idempotent (re-run safe)
     • Status: 0%

🔥 Priority 2: At-Risk Enrichment
  └─ Add to GET /chainiq/shipments/at_risk response:
     • latest_snapshot_status (SUCCESS|FAILED|IN_PROGRESS|PENDING|null)
     • latest_snapshot_updated_at (ISO timestamp)
     • Single query (no N+1)
     • Status: 0%

🔥 Priority 3: Worker Lifecycle
  └─ Service methods in api/services/snapshot_worker.py
     • claim_next_pending_event(worker_id) → atomic, concurrent-safe
     • mark_event_success(event_id)
     • mark_event_failed(event_id, reason, retryable)
     • State machine: PENDING → IN_PROGRESS → SUCCESS/FAILED
     • Retry logic: MAX_EXPORT_RETRIES = 3
     • Status: 0%

🔥 Priority 4: Worker Runner Script
  └─ scripts/run_snapshot_worker.py
     • Infinite loop: claim → process → mark result
     • Graceful shutdown (Ctrl+C)
     • Logs to /tmp/snapshot_worker.log
     • Usage: python -m scripts.run_snapshot_worker --worker-id=worker-001
     • Status: 0%
```

### Sonny (Frontend)

```
🔥 Priority 1: Empty States
  └─ ShipmentRiskTable.tsx
     • Show message if data array empty
     • "Load Demo Data" button (callback)
     • Status: 0%

🔥 Priority 2: Risk Filter Pills
  └─ Horizontal pill bar: All | Critical | High | Moderate | Low
     • Clicking pill updates filter → refetch table
     • Show selected state
     • Reset pagination to page 1
     • Status: 0%

🔥 Priority 3: Timeline Polish
  └─ SnapshotTimelineDrawer.tsx
     • Group events by day (sticky headers)
     • Show absolute + relative time
     • Icons per status (check, X, clock)
     • Smooth scrolling
     • Status: 0%
```

### Logistics SME

```
✅ Review & Validate
  └─ Seed data schema (realistic attributes)
     └─ Verify: corridor_code, mode, incoterm, risk scores, ETAs

  └─ Worker event status workflow
     └─ Validate: PENDING → IN_PROGRESS → SUCCESS matches ops

  └─ Retry strategy
     └─ Confirm: 3 retries, SLA compliance

  └─ Timeline visibility
     └─ Test: ops can track full lifecycle in UI
```

---

## Key Endpoints

| Method | Endpoint | Status | Notes |
|--------|----------|--------|-------|
| GET | `/health` | ✅ | Health check (45s polling) |
| GET | `/chainiq/shipments/at_risk` | ✅ | Returns empty until seeded; M02 adds enrichment |
| POST | `/chainiq/admin/snapshot_exports` | ✅ | Creates export event |
| GET | `/chainiq/admin/snapshot_exports?shipment_id=...` | ✅ | Fetch export history |

---

## File Locations

```
docs/product/PROJECT_CHECKLIST.md ........................ Master checklist (all M01-M04)
docs/product/PROJECT_STATUS_SUMMARY.md .................. Quick status overview
AGENTS 2/LOGISTICS_OPS_SME/checklist.md ... Ops validation checklist

api/server.py ............................ FastAPI entrypoint
api/services/snapshot_worker.py ........... Worker service (TBD)
scripts/seed_chainiq_demo.py ............. Seed data (TBD)
scripts/run_snapshot_worker.py ........... Worker runner (TBD)

chainboard-ui/src/components/settlements/
  ├─ ShipmentRiskTable.tsx ............... Fleet Cockpit
  ├─ SnapshotTimelineDrawer.tsx ......... Timeline drawer
  └─ APIHealthIndicator.tsx ............ Health indicator

tests/test_chainiq_api.py ............... API tests
tests/test_snapshot_worker.py ........... Worker tests (TBD)
```

---

## Dev Environment Setup

```bash
# Backend
cd /Users/johnbozza/Documents/Projects/ChainBridge-local-repo/ChainBridge
source .venv/bin/activate
python -m api.server
# → http://localhost:8001

# Frontend
cd chainboard-ui
npm run dev
# → http://localhost:5173

# Logs
tail -f /tmp/api.log
tail -f /tmp/snapshot_worker.log (after M02)
```

---

## M02 Success Criteria

- [ ] 50 realistic shipments visible in Cockpit
- [ ] At-risk endpoint returns latest_snapshot_status
- [ ] Export button triggers snapshot creation
- [ ] Worker processes events (PENDING → SUCCESS)
- [ ] Timeline shows real status transitions
- [ ] Table updates with latest snapshot status (15s polling)
- [ ] Ops can monitor full lifecycle in UI
- [ ] No race conditions with concurrent workers
- [ ] Retry logic tested and working
- [ ] All commands documented in README

---

## Next Sprint (M03 Preview)

- [ ] ChainPay integration: payment holds UX
- [ ] ChainDocs integration: document timeline
- [ ] ProofPack wiring: proof flow integration
- [ ] Observability: metrics & monitoring dashboard
- [ ] Full "Risk → Snapshot → Hold → Proof → Release" demo

---

**Questions?** See `docs/product/PROJECT_CHECKLIST.md` for comprehensive details.
**Status Updates?** Check `docs/product/PROJECT_STATUS_SUMMARY.md`.
