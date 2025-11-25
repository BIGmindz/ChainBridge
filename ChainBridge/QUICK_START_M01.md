# ChainBridge Vertical Slice – Quick Start Guide

**Last Updated:** 2025-11-19

---

## ⚡ 30-Second Start

```bash
# Terminal 1: Start Backend
cd ~/Documents/Projects/ChainBridge-local-repo/ChainBridge
source .venv/bin/activate
uvicorn api.server:app --host 0.0.0.0 --port 8001

# Terminal 2: Start Frontend
cd chainboard-ui
npm run dev

# Open browser to http://localhost:5173
# Go to Settlements > Fleet Risk Overview
```

---

## 🎯 What You Can Do Right Now

- ✅ See the Fleet Risk table (empty, waiting for data)
- ✅ Click a row to open Snapshot Timeline Drawer
- ✅ Click Export button to trigger snapshot creation
- ✅ Watch real-time polling (table every 15s, drawer every 5s)
- ✅ See export status update as it progresses

---

## 🔗 Key Endpoints

| Endpoint | Purpose | Status |
|----------|---------|--------|
| `GET /health` | API health check | ✅ Working |
| `GET /chainiq/shipments/at_risk` | List at-risk shipments | ✅ Working (empty) |
| `POST /chainiq/admin/snapshot_exports` | Create export event | ✅ Wired |
| `GET /chainiq/admin/snapshot_exports?shipment_id=...` | Get export history | ✅ Wired |

---

## 📊 Frontend Configuration

**File:** `chainboard-ui/.env.local`

```dotenv
VITE_API_BASE_URL="http://localhost:8001"
VITE_DEMO_MODE="true"
```

---

## 🧪 Quick Tests

```bash
# Test backend is running
curl http://127.0.0.1:8001/health

# Test at-risk endpoint
curl "http://127.0.0.1:8001/chainiq/shipments/at_risk?max_results=3"

# Expected: 200 OK with JSON
```

---

## 📝 Architecture Files

| File | Purpose | Owner |
|------|---------|-------|
| `api/server.py` | FastAPI app entry point | Cody |
| `api/routes/chainboard.py` | ChainBoard routes | Cody |
| `api/chainiq_service/router.py` | At-risk + snapshot routes | Cody |
| `chainboard-ui/src/components/settlements/ShipmentRiskTable.tsx` | Fleet table | Sonny |
| `chainboard-ui/src/components/settlements/SnapshotTimelineDrawer.tsx` | Timeline drawer | Sonny |
| `chainboard-ui/src/hooks/useAtRiskShipments.ts` | Auto-polling hook | Sonny |
| `chainboard-ui/src/services/apiClient.ts` | HTTP client | Sonny |

---

## ⚠️ Known Limitations

- No seed data (at-risk table is empty)
- Export events created but not processed by worker
- No ChainPay integration yet
- No ChainDocs integration yet

---

## 🚀 Next Steps (Milestone 02)

1. Seed realistic shipment data (~100 shipments)
2. Implement export worker (processes PENDING → SUCCESS/FAILED)
3. Add ChainPay integration (holds + releases)
4. Full end-to-end demo with real data flow

---

## 📞 Support

- **Backend Issues:** Check `/tmp/api.log`
- **Frontend Issues:** Check browser console (F12)
- **Connection Issues:** Verify `VITE_API_BASE_URL` in `.env.local`

---

## 🎓 Learning Path

1. **First:** Run both servers, navigate to Fleet Risk
2. **Second:** Open browser DevTools Network tab, click Export
3. **Third:** Watch network requests go to http://127.0.0.1:8001
4. **Fourth:** Read MILESTONE_01_VERTICAL_SLICE.md for full details
