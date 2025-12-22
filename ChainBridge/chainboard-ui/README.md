# ChainBoard Operator Console

ChainBoard is the enterprise Operator Console for the ChainBridge platform. This React + Vite front-end fuses ChainIQ intelligence, ChainPay settlements, and ChainSense telemetry flows into one cockpit for operators and execs.

## What Lives Here

- `src/pages/` – Route-level screens for the OC, Global Intel, Settlements, ShadowPilot, demos
- `src/components/` – Shared UI primitives (OC tables, intel widgets, map overlays, debug tools)
- `src/core/` – Typed API client, route registry, caching utilities, event streams
- `src/services/` – Higher-level service facades (real API + mock adapters)
- `src/types/` – Canonical TypeScript contracts that mirror backend Pydantic models

## Quickstart

### Frontend Only

```bash
cd chainboard-ui
npm install
cp .env.example .env.local    # optional overrides
npm run dev
```

Visit `http://localhost:5173`. The UI targets the API gateway at `http://localhost:8001` by default (set `VITE_API_BASE_URL` to change).

### Full Stack (Gateway + UI)

From repo root:

```bash
./scripts/dev/run_api_gateway.sh   # FastAPI gateway on :8001
./scripts/dev/run_chainboard.sh    # ChainBoard UI on :5173
```

You can also run the VS Code task **Start ChainBridge Stack** to launch both.

## Environment Variables

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8001` | Base URL for all real API requests |
| `VITE_USE_MOCKS` | `false` | Force legacy mock services (bypasses gateway) |
| `VITE_ENVIRONMENT_LABEL` | auto | Badge in UI header to signal environment |
| `VITE_RISK_API_MODE` | `mock` | Risk Console data source ('mock' or 'live') |
| `VITE_CHAINIQ_API_BASE_URL` | - | Base URL for ChainIQ Risk API (required for live mode) |

All env access flows through `src/config/env.ts`, which logs the active configuration in development mode.

## Page & Module Map

| Route | Page Component | Supporting Modules | Key Endpoints |
| ----- | -------------- | ------------------ | ------------- |
| `/overview` | `src/pages/OverviewPage.tsx` | `components/dashboard/*`, `core/api/client` | `GET /api/chainboard/metrics/*`, `GET /api/chainboard/exceptions` |
| `/oc`, `/operator` | `src/pages/OperatorConsolePage.tsx` | `components/oc/*`, `components/GlobalOpsMap`, `hooks/useEventStream` | `GET /api/chainboard/shipments`, `GET /api/chainboard/metrics/iot/*`, SSE stream |
| `/intelligence` | `src/pages/IntelligencePage.tsx`, `src/pages/GlobalIntelPage.tsx` | `components/intel/*`, `services/realApiClient` | `GET /api/chainboard/risk/overview`, `GET /api/chainboard/iq/risk-stories` |
| `/shipments` | `src/pages/ShipmentsPage.tsx` | `components/tables/ShipmentsTable`, `hooks/useShipments` | `GET /api/chainboard/shipments` |
| `/exceptions` | `src/pages/ExceptionsPage.tsx` | `components/oc/OCQueueTable`, `core/api/client` | `GET /api/chainboard/exceptions` |
| `/chainpay`, `/settlements` | `src/pages/ChainPayPage.tsx`, `src/pages/SettlementsPage.tsx` | `components/settlements/*`, `services/operatorApi` | `GET /api/chainboard/pay/queue`, `GET /api/chainboard/settlements/*` |
| `/shadow-pilot` | `src/pages/ShadowPilotPage.tsx` | `components/shadowPilot/*`, `services/operatorApi` | `GET /api/chainboard/shadow-pilot/*` |
| `/sandbox` | `src/pages/SandboxPage.tsx` | Demo widgets, mocks | Primarily mock data |

API paths are centralized in `src/core/api/routes.ts`; update that file first if backend routes change.

## API Access Pattern

1. `src/core/api/http.ts` – Fetch wrapper with timeout, headers, and error handling.
2. `src/core/api/client.ts` – Primary ChainBoard API surface (ChainIQ, ChainPay, ChainSense, alerts).
3. `src/services/operatorApi.ts` – Operator Console / settlement-specific endpoints.
4. `src/services/realApiClient.ts` – Transitional client for legacy areas still lifting data from the gateway.

Use the `@/` alias from `tsconfig.json` instead of long relative paths when importing these modules.

## Developer Workflow

| Task | Command |
| ---- | ------- |
| Start dev server | `npm run dev`
| Type check | `npm run type-check`
| Lint | `npm run lint`
| Unit tests | `npm run test`
| Format | `npm run format`

Vitest suites live in `src/__tests__/` and component-specific folders. Keep them green before shipping.

## DX Notes

- Keep TypeScript types in `src/types/` aligned with backend Pydantic schemas whenever Cody updates service contracts.
- Document new operator flows in `docs/product/` and link them from the repo root README when appropriate.
- Legacy trading artifacts stay in `legacy/bensonbot/`; do not reintroduce them here.
- If you add new API endpoints, wire them through `src/core/api/routes.ts` and `src/core/api/client.ts` so future refactors stay centralized.

The Operator Console is the single source of truth for ChainBridge—make it fast, reliable, and demo-ready.
