# ChainPay Overview

## Why It Matters

ChainPay is how ChainBridge translates visibility into cash. It provides milestone tracking, settlement verification, and payment orchestration—critical for proving that the platform shortens days sales outstanding for shippers and carriers.

## Capabilities

- **Settlement Plans:** Model contract milestones, tolerances, and approval rules.
- **Payment State Tracking:** Surfaces where cash is blocked and who needs to act.
- **Exception Routing:** Sends high-risk settlements back into ChainBoard for resolution.
- **Audit Trail:** Maintains immutable logs for finance and compliance teams.

## Code Location

- Backend service: `chainpay-service/`
- Shared domain logic: `core/`
- API gateway & routes: `api/`

## Service Interfaces

- **Inbound:** All customer/API requests arrive via `services/api-gateway` at `/chainpay/*`.
- **Outbound:** Emits settlement events to ChainBoard and optionally external ERPs.

## Local Development

1. Start the FastAPI backend (see root `README.md` for `api/server.py`).
2. Use the ChainPay routes under `/chainpay/*` via `http://localhost:8001`.

## Where to Go in the Repo

- Backend services: `api/`, `chainiq-service/`, `chainpay-service/`
- Frontend (ChainBoard / OC): `chainboard-ui/`
- Agent framework: `AGENTS 2/`
- Architecture diagrams: `docs/architecture/`

## Testing

- Unit & integration tests: `tests/services/chainpay/`
- Gateway contracts: `tests/api/chainpay/`
- E2E cash flow scenarios: `tests/e2e/settlements/`

## Roadmap Hooks

- Integrate Ripple + bank partner APIs for real disbursements.
- Add machine learning driven risk scoring before release events.
- Publish settlement SLAs in `docs/flows/settlement_lifecycle.md` (stub).
