# ChainIQ Overview

## Why It Matters

ChainIQ is the intelligence layer that proves ChainBridge knows more about a shipper's freight network than they do. It fuses documents, telemetry, and external signals into a live risk posture—this is what convinces enterprise buyers that ChainBridge can de-risk their operations immediately.

## Core Responsibilities

- **Shipment Health Engine:** Calculates corridor, lane, and shipment-level health scores.
- **Exception Detection:** Flags anomalies and pushes them into ChainBoard queues.
- **Insight Feeds:** Generates the metrics that power dashboards and outbound notifications.
- **Data Contracts:** Owns the canonical models used by other services and the UI.

## Code Location

- Service entrypoint: `services/chainiq-service/`
- Shared data contracts: `platform/data-model/`
- Intelligence utilities and analyzers: `platform/common-lib/iq/`
- Proof packs & sample datasets: `platform/proofpack/chainiq/`

## Service Interfaces

- **Inbound:**
  - `api-gateway` routes `/chainiq/*` requests here.
  - ChainSense streams push anomalous events via the internal event bus.
- **Outbound:**
  - Persists summaries in the data warehouse.
  - Emits notifications to ChainBoard and ChainPay via the gateway.

## Local Development

1. Ensure the platform virtual environment is active (see root `README.md`).
2. Start ChainIQ with hot reload:
   ```bash
   uvicorn services.chainiq_service.app.main:app --reload --port 8102
   ```
3. Hit `http://localhost:8102/health` or exercise the gateway: `http://localhost:8001/chainiq/metrics`.

## Testing

- Unit tests live under `tests/services/chainiq/`.
- API contract tests live under `tests/api/chainiq/` and run via `pytest`.
- End-to-end flows run from `tests/e2e/control_tower/` and require the gateway + UI.

## Roadmap Hooks

- Integrate ChainSense anomaly detections as first-class events.
- Add predictive ETA scoring to the Shipment Health engine.
- Publish health scoring methodology in `docs/product/CHAINIQ_SCORING.md` (WIP).
