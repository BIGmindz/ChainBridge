# 🚀 M02 SPRINT LAUNCH KIT
## Quick Reference for All Roles (Nov 19, 2025)

---

## 📍 Start Here (Everyone)

### 1. Understand Status (2 min)
```bash
cat docs/product/PROJECT_STATUS_SUMMARY.md | head -60
```

### 2. Pick Your Role (Read Relevant Section Below)
- **Cody** → "Backend Tasks (M02)"
- **Sonny** → "Frontend Tasks (M02)"
- **SME** → "Ops Validation (M02)"
- **Manager** → "Tracking Progress"

### 3. Execute & Report Daily
```bash
# Update: docs/product/PROJECT_STATUS_SUMMARY.md task percentages
# Reference: docs/product/M02_QUICK_REFERENCE.md for commands
# Validate: AGENTS 2/LOGISTICS_OPS_SME/checklist.md for SME
```

---

## 🔴 CRITICAL PATH – DO FIRST (Cody)

### 1. Seed Data Script (`scripts/seed_chainiq_demo.py`)
**Why:** Without data, nothing works. This unblocks Sonny and SME.

**What to Build:**
- Function: `seed_demo_shipments(count=50, clear=False)`
- Generates: shipment_id, corridor_code, mode, incoterm, risk_score, risk_level, origin, destination, eta_days
- Schema: `AtRiskShipment` database model
- Idempotent: Safe to re-run with `--clear` flag

**Success Criteria:**
```bash
python -m scripts.seed_chainiq_demo --count=50 --clear
# Output: "✅ Seeded 50 demo shipments"

curl http://127.0.0.1:8001/chainiq/shipments/at_risk?max_results=10 | jq
# Output: Array with 10 shipments
```

**Estimate:** 2–3 hours

---

### 2. At-Risk Enrichment
**Why:** Frontend table needs to show latest snapshot status.

**What to Build:**
- Add to response: `latest_snapshot_status`, `latest_snapshot_updated_at`
- Use single query (LEFT JOIN or subquery) – no N+1
- Returns: "SUCCESS" | "FAILED" | "IN_PROGRESS" | "PENDING" | null

**Success Criteria:**
```bash
curl http://127.0.0.1:8001/chainiq/shipments/at_risk?max_results=1 | jq '.[0] | {id, latest_snapshot_status, latest_snapshot_updated_at}'
# Output: Shows snapshot status + timestamp
```

**Estimate:** 1–2 hours

---

### 3. Worker Lifecycle (Worker Service)
**Why:** Without worker logic, no status transitions. This is the core M02 feature.

**What to Build:**
```python
# api/services/snapshot_worker.py
class SnapshotWorkerService:
    def claim_next_pending_event(self, worker_id: str) -> SnapshotExportEvent | None:
        # Atomically claim next PENDING event
        # Set status=IN_PROGRESS, claimed_by=worker_id
        # Return event or None if no work

    def mark_event_success(self, event_id: str) -> SnapshotExportEvent:
        # Set status=SUCCESS, completed_at=now
        # Return updated event

    def mark_event_failed(self, event_id: str, reason: str, retryable: bool) -> SnapshotExportEvent:
        # If retryable AND retry_count < MAX:
        #   Increment retry_count, set status=PENDING, claimed_by=None
        # Else:
        #   Set status=FAILED, failure_reason=reason
        # Return updated event
```

**Success Criteria:**
```bash
# Test state machine
1. Create event (PENDING)
2. Claim event → status=IN_PROGRESS
3. Mark success → status=SUCCESS
4. Timeline shows all transitions

# Test retry logic
1. Create event (PENDING)
2. Mark failed, retryable=True, retry_count=0 → status=PENDING
3. Repeat until retry_count=3
4. Mark failed, retryable=True, retry_count=3 → status=FAILED (permanent)
```

**Estimate:** 3–4 hours + testing

---

### 4. Worker Runner Script (`scripts/run_snapshot_worker.py`)
**Why:** Actually processes snapshot exports in a loop.

**What to Build:**
```python
# scripts/run_snapshot_worker.py
import argparse
import signal
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/snapshot_worker.log'), logging.StreamHandler()]
)

def signal_handler(sig, frame):
    print("\n🛑 Worker shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

worker_service = SnapshotWorkerService()

while True:
    # 1. Claim next pending event
    event = worker_service.claim_next_pending_event(worker_id=args.worker_id)

    if not event:
        # No work, sleep and retry
        time.sleep(args.interval)
        continue

    try:
        # 2. Simulate processing
        logging.info(f"Processing event {event.event_id}")
        time.sleep(random.uniform(1, 3))  # Simulate work

        # 3. Randomly succeed/fail (80% success for demo)
        if random.random() < 0.8:
            worker_service.mark_event_success(event.event_id)
            logging.info(f"✅ Event {event.event_id} succeeded")
        else:
            worker_service.mark_event_failed(
                event.event_id,
                "Simulated failure (demo)",
                retryable=True
            )
            logging.info(f"❌ Event {event.event_id} failed (retryable)")

    except Exception as e:
        logging.error(f"Error processing {event.event_id}: {e}")
        worker_service.mark_event_failed(event.event_id, str(e), retryable=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-id", default=socket.gethostname())
    parser.add_argument("--interval", type=int, default=2)
    args = parser.parse_args()

    logging.info(f"🚀 Worker {args.worker_id} starting (interval={args.interval}s)")
    main()
```

**Success Criteria:**
```bash
# Terminal 1
python -m scripts.run_snapshot_worker --worker-id=worker-001

# Terminal 2
python -m scripts.run_snapshot_worker --worker-id=worker-002

# Terminal 3
python -m scripts.seed_chainiq_demo --count=5
curl -X POST http://127.0.0.1:8001/chainiq/admin/snapshot_exports \
  -d '{"shipment_id": "SHP-001"}' -H "Content-Type: application/json"

# Verify: Both workers process events, no conflicts
tail -f /tmp/snapshot_worker.log
```

**Estimate:** 2–3 hours

---

## 🟢 FRONTEND TASKS – DO AFTER (Sonny)

### 1. Empty States
**When Cockpit has no data:**
```tsx
// In ShipmentRiskTable.tsx
{data?.length === 0 && (
  <div className="text-center py-12">
    <AlertTriangle className="h-12 w-12 text-slate-500 mx-auto mb-4" />
    <h3 className="text-lg font-semibold text-slate-300 mb-2">No At-Risk Shipments</h3>
    <p className="text-slate-400 mb-4">Try adjusting filters or load demo data</p>
    <button onClick={() => onLoadDemoData?.()}>
      Load Demo Data
    </button>
  </div>
)}
```

**Estimate:** 30 min

---

### 2. Risk Filter Pills
**Replace existing filter with pills:**
```tsx
const pills = ["All", "Critical", "High", "Moderate", "Low"]
<div className="flex gap-2">
  {pills.map(pill => (
    <button
      key={pill}
      onClick={() => {
        setSelectedRiskLevel(pill === "All" ? null : pill)
        setPage(1) // Reset pagination
      }}
      className={`px-4 py-1 rounded-full ${
        selectedRiskLevel === pill ? "bg-blue-600" : "bg-slate-700"
      }`}
    >
      {pill}
    </button>
  ))}
</div>
```

**Estimate:** 45 min

---

### 3. Timeline Polish
**Group by day, show relative time:**
```tsx
// In TimelineItem
const getRelativeTime = (isoString: string) => {
  const now = new Date()
  const then = new Date(isoString)
  const seconds = Math.floor((now.getTime() - then.getTime()) / 1000)

  if (seconds < 60) return "Just now"
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}

// Show both absolute + relative
<span className="text-xs text-slate-400">{absoluteTime}</span>
<span className="text-xs text-slate-500">{getRelativeTime(timestamp)}</span>
```

**Estimate:** 1–2 hours

---

## 🔵 OPS VALIDATION – IN PARALLEL (SME)

### Pre-M02 Validation (Today)
- [ ] Review seed data schema with Cody
- [ ] Approve shipment attributes (corridor_code, mode, incoterm, risk levels)
- [ ] Confirm risk score thresholds
- [ ] Validate ETAs are realistic per corridor

### M02 Validation (As Implemented)
- [ ] Verify 50 shipments visible in Cockpit
- [ ] Test snapshot export (PENDING → SUCCESS flow)
- [ ] Run concurrent workers (test no race conditions)
- [ ] Verify Timeline shows real status transitions
- [ ] Test retry logic (fail → retry → success)
- [ ] Validate SLAs (processing time, failure rate, E2E time)

### Run Verification Commands
```bash
# Seed & verify
python -m scripts.seed_chainiq_demo --count=50 --clear
curl http://127.0.0.1:8001/chainiq/shipments/at_risk?max_results=50 | jq '.[] | {id, corridor: .corridor_code, risk: .risk_level, eta: .eta_days}' | head -20

# Start 2 workers
python -m scripts.run_snapshot_worker --worker-id=worker-001 &
python -m scripts.run_snapshot_worker --worker-id=worker-002 &

# Create exports & monitor
for i in {1..10}; do
  curl -X POST http://127.0.0.1:8001/chainiq/admin/snapshot_exports \
    -d "{\"shipment_id\": \"SHP-$(printf '%03d' $i)\"}" \
    -H "Content-Type: application/json"
done

# Watch workers process
tail -f /tmp/snapshot_worker.log
```

---

## 📊 TRACKING PROGRESS

### Daily Update Template
```markdown
### Day X (Date)

**Backend (Cody)**
- [x] Seed script implemented
- [ ] At-risk enrichment (25% – schema done, query pending)
- [ ] Worker lifecycle (0%)
- [ ] Worker runner (0%)

**Frontend (Sonny)**
- [ ] Empty states (0%)
- [ ] Filter pills (0%)
- [ ] Timeline polish (0%)

**Ops (SME)**
- [x] Seed data schema validated
- [ ] Running verification tests

**Blockers:**
- None yet

**Next (Tomorrow):**
- Cody to complete seed script
- Sonny to review empty state UI
```

### Update: `docs/product/PROJECT_STATUS_SUMMARY.md`
```markdown
| Task | % | Owner | Notes |
|------|---|-------|-------|
| Seed Script | 50% | Cody | Generated data, testing insert |
| Enrichment | 0% | Cody | Waiting for schema |
| Worker Lifecycle | 0% | Cody | Starting tomorrow |
| Empty States | 0% | Sonny | Pending seed data |
```

---

## 🎯 M02 Success Criteria (Quality Gates)

- [ ] 50+ realistic shipments in database
- [ ] Cockpit shows all shipments with filters working
- [ ] Snapshot export button creates event (PENDING)
- [ ] Worker claims event (→ IN_PROGRESS)
- [ ] Worker marks success (→ SUCCESS)
- [ ] Timeline shows all transitions with timestamps
- [ ] No race conditions (test with 2+ concurrent workers)
- [ ] Retry logic tested (3 max retries)
- [ ] Empty states display when no data
- [ ] Filter pills update data
- [ ] Timeline shows relative + absolute times
- [ ] All tests passing
- [ ] npm run build passes
- [ ] ops team has validated workflow

---

## 📞 Questions?

| Question | Answer |
|----------|--------|
| What do I work on? | See your role section above |
| What are commands? | `docs/product/M02_QUICK_REFERENCE.md` |
| How do I test? | `AGENTS 2/LOGISTICS_OPS_SME/checklist.md` |
| What's my priority? | Backend ← Cody. Frontend after backend complete. Ops in parallel. |
| When is M02 done? | All quality gates passing + ops sign-off |

---

## ✅ Checklist (Print & Post on Wall)

```
M02 Sprint Launch
├─ [ ] Cody: Seed script done & tested
├─ [ ] Cody: Enrichment done & tested
├─ [ ] Cody: Worker lifecycle done & tested
├─ [ ] Cody: Worker runner script done & tested
├─ [ ] Sonny: Empty states done
├─ [ ] Sonny: Filter pills done
├─ [ ] Sonny: Timeline polish done
├─ [ ] SME: Seed data validated
├─ [ ] SME: Full workflow tested
├─ [ ] All: Quality gates passing
├─ [ ] All: Tests passing
├─ [ ] All: npm run build passes
└─ [ ] All: M02 sign-off & celebration 🎉
```

---

**Sprint Starts:** Now
**Sprint Goal:** M02 Complete (Live Risk & Worker Pipeline)
**Sprint Duration:** 1 week
**Success Condition:** All quality gates passing + ops sign-off

**Let's build!** 🚀
