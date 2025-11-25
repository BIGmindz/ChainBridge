# ChainPay Overview

## Why It Matters

ChainPay is how ChainBridge translates visibility into cash. It provides milestone tracking, settlement verification, and payment orchestration—critical for proving that the platform shortens days sales outstanding for shippers and carriers.

## Capabilities

- **Settlement Plans:** Model contract milestones, tolerances, and approval rules.
- **Payment State Tracking:** Surfaces where cash is blocked and who needs to act.
- **Exception Routing:** Sends high-risk settlements back into ChainBoard for resolution.
- **Audit Trail:** Maintains immutable logs for finance and compliance teams.

## Code Location

- Service entrypoint: `services/chainpay-service/`
- Shared payment models: `platform/data-model/payments/`
- Ledger integrations & adapters: `platform/common-lib/payments/`
- Demo datasets: `platform/proofpack/chainpay/`

## Service Interfaces

- **Inbound:** All customer/API requests arrive via `services/api-gateway` at `/chainpay/*`.
- **Outbound:** Emits settlement events to ChainBoard and optionally external ERPs.

## Local Development

1. Boot the API gateway (see `scripts/dev/run_api_gateway.sh`).
2. Run ChainPay locally on a separate port if iterating directly:
   ```bash
   uvicorn services.chainpay_service.app.main:app --reload --port 8103
   ```
3. Use the demo script in `scripts/demo/settlement_story.sh` to seed sample plans.

## Testing

- Unit & integration tests: `tests/services/chainpay/`
- Gateway contracts: `tests/api/chainpay/`
- E2E cash flow scenarios: `tests/e2e/settlements/`

## Roadmap Hooks

- Integrate Ripple + bank partner APIs for real disbursements.
- Add machine learning driven risk scoring before release events.
- Publish settlement SLAs in `docs/flows/settlement_lifecycle.md` (stub).
