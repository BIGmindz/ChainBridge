# ChainSense IoT Integration Overview

**Cross-refs:** [ChainBridge Reality Baseline](CHAINBRIDGE_REALITY_BASELINE.md) · [ChainBridge Executive Summary](CHAINBRIDGE_EXEC_SUMMARY.md) · [ChainBridge PAC Standard](PAC_STANDARD.md) · [ChainBridge Agent Registry](AGENT_REGISTRY.md)

---

## 1. Purpose & Scope

This document outlines the current ChainSense IoT integration path that powers the Operator Console (ChainBoard) during the internal pilot. It captures the mock data flows, API endpoints, and UI touchpoints so DevOps, backend, and frontend agents can reason about responsibilities without inferring missing production features. The scope is limited to the repository state as of the Engineering Hardening phase.

## 2. API Surface

ChainSense exposes IoT health metrics to ChainBoard through the FastAPI application in `ChainBridge/api/`.

Primary endpoints:
- `GET /api/chainboard/iot/health-summary` → UI-facing alias that proxies to the core health route.
- `GET /api/chainboard/iot/health` → Returns `IoTHealthSummaryResponse` with fleet-level sensor coverage and alert counts.
- `GET /api/chainboard/metrics/iot/summary` → Aggregated metrics re-used by other ChainBoard dashboards.
- `GET /api/chainboard/metrics/iot/shipments` → Lists shipment snapshots with filtering.
- `GET /api/chainboard/metrics/iot/shipments/{shipment_id}` → Retrieves the latest readings and alerts for a specific shipment.

These routes are backed by `api/routes/chainboard_iot.py` and `api/routes/chainboard.py`, with data contracts defined in `api/schemas/chainboard.py`. The IoT provider currently defaults to `MockIoTDataProvider`, controlled via the `CHAINBOARD_USE_MOCK_IOT` environment variable.

## 3. Data Model Summary

The `IoTHealthSummaryResponse` schema encapsulates:
- `shipments_with_iot`: integer count of monitored shipments.
- `active_sensors`: total number of sensors in mock operation.
- `alerts_last_24h` / `critical_alerts_last_24h`: alert volume metrics.
- `coverage_percent`: fleet coverage expressed as a percentage.
- `generated_at`: UTC timestamp when the snapshot was produced.

Per-shipment snapshots (`ShipmentIoTSnapshotResponse`) include:
- `snapshot.shipment_id`
- `snapshot.latest_readings`: sensor type/value/status tuples sorted by recency.
- `snapshot.alert_count_24h` and `snapshot.critical_alerts_24h`

All records originate from deterministic fixtures housed under `api/chainsense/fixtures/`, ensuring stable automated test runs (see `api/tests/test_chainboard_iot.py`).

## 4. Operator Console Integration

The React front-end (`ChainBridge/chainboard-ui/`) consumes the health summary through `src/services/realApiClient.ts` and renders it in `src/components/iot/IoTHealthPanel.tsx`. The panel appears on `src/pages/OverviewPage.tsx`, providing operators with fleet telemetry at a glance. During local development, Vite proxies `/api` requests to the FastAPI server, preserving consistent routes between backend and frontend.

Smoke validation commands (maintained in `docs/AGENT_ORG_MAP.md`):
```
cd ~/Documents/Projects/ChainBridge-local-repo/ChainBridge && pytest api/tests/test_chainboard_iot.py
cd ~/Documents/Projects/ChainBridge-local-repo/ChainBridge/chainboard-ui && npm test -- IoTHealthPanel
```

## 5. Future Work (Roadmap)

Planned enhancements, aligned with the Reality Baseline:
1. Replace `MockIoTDataProvider` with a real telemetry ingestion service (e.g., Samsara or proprietary gateway) once partnerships are secured.
2. Extend schema coverage for sensor anomalies, location trails, and device health diagnostics.
3. Add alert subscription workflows within ChainBoard (operator acknowledgments, escalation paths).
4. Instrument end-to-end observability for IoT pipelines within GitHub Actions and runtime dashboards.

This document intentionally remains a lightweight reference. Agents must continue to consult PACs for task-level execution details and avoid claiming production readiness beyond the constraints listed above.
