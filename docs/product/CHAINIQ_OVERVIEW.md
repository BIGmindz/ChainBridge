# ChainIQ Overview

## Why It Matters

ChainIQ is the intelligence layer that proves ChainBridge knows more about a shipper's freight network than they do. It fuses documents, telemetry, and external signals into a live risk posture—this is what convinces enterprise buyers that ChainBridge can de-risk their operations immediately.

## Core Responsibilities

- **Shipment Health Engine:** Calculates corridor, lane, and shipment-level health scores.
- **Exception Detection:** Flags anomalies and pushes them into ChainBoard queues.
- **Insight Feeds:** Generates the metrics that power dashboards and outbound notifications.
- **Data Contracts:** Owns the canonical models used by other services and the UI.
- **Glass-Box Risk Brain (v0.1):** ML-driven risk scoring with full explainability via SHAP factors.

## Code Location

- Backend service: `chainiq-service/`
- **Risk Brain (v0.1):** `chainiq-service/app/` — schemas, features, models, scoring, explain, evaluation
- **Spec Document:** `chainiq-service/docs/CHAINIQ_V0_SPEC.md`
- Shared domain logic: `core/`
- API gateway & routes: `api/`

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
3. Hit `http://localhost:8001/health` or exercise the ChainIQ routes under `/chainiq/*`.

## Where to Go in the Repo

- Backend services: `api/`, `chainiq-service/`, `chainpay-service/`
- Frontend (ChainBoard / OC): `chainboard-ui/`
- Agent framework: `AGENTS 2/`
- Architecture diagrams: `docs/architecture/`

## Testing

- Unit tests live under `tests/services/chainiq/`.
- API contract tests live under `tests/api/chainiq/` and run via `pytest`.
- End-to-end flows run from `tests/e2e/control_tower/` and require the gateway + UI.

## Roadmap Hooks

- Integrate ChainSense anomaly detections as first-class events.
- Add predictive ETA scoring to the Shipment Health engine.
- Publish health scoring methodology in `docs/product/CHAINIQ_SCORING.md` (WIP).

## ChainIQ v0.1 Risk Brain (Maggie PAC)

**Spec:** `chainiq-service/docs/CHAINIQ_V0_SPEC.md`

Key components delivered:

| Module | Purpose |
|--------|---------|
| `schemas.py` | Pydantic input/output contracts (ShipmentRiskContext, ShipmentRiskAssessment) |
| `features.py` | Feature engineering from raw context to model-ready vectors |
| `models.py` | XGBoost, Logistic Regression, and Heuristic risk models |
| `scoring.py` | End-to-end scoring pipeline (ChainIQScorer) |
| `explain.py` | SHAP-based explanation generation (TopFactor, summary_reason) |
| `evaluation.py` | Retrospective pilot tools for customer historical data |
| `main.py` | FastAPI service exposing `/api/v1/risk/score` and `/api/v1/risk/simulation` |

**API Endpoints:**

- `POST /api/v1/risk/score` — Score 1-100 shipments, returns assessments with factors
- `POST /api/v1/risk/simulation` — What-if analysis comparing carriers/routes/timing
- `GET /api/v1/risk/health` — Model health check
- `GET /api/v1/risk/model/info` — Model metadata and feature list

**Decision Mapping:**

| Risk Score | Decision |
|------------|----------|
| 0-30 | APPROVE |
| 30-50 | APPROVE (monitored) |
| 50-70 | TIGHTEN_TERMS |
| 70-85 | TIGHTEN_TERMS / HOLD |
| 85-100 | HOLD / ESCALATE |
