# ChainBridge Dev Quickstart

> Internal notes for contributors. For the high-level product overview, see the main `README.md`.

---

## Monorepo Layout

- `ChainBridge/`
  - `chainboard-ui/` – React/Vite frontend (ChainBoard / The OC)
  - `chainiq-service/` – FastAPI-based AI & risk service
  - `chainpay-service/` – payments & settlement service
  - `docs/` – architecture, product, governance, and dev docs

Adjust paths above if your local layout differs.

---

## Prereqs

- Node.js (LTS) + npm
- Python 3.11 (with `venv`)
- Docker (optional, for containerized runs)
- Git + GitHub access

---

## Setup — Frontend (ChainBoard / The OC)

From the repo root:

```bash
cd ChainBridge/chainboard-ui
npm install
npm run dev
```

Default: Vite dev server on http://localhost:5173 (or what Vite prints).

---

## Setup — Backend Services

From the repo root:

```bash
cd ChainBridge

# Activate venv if present
# source .venv/bin/activate

# Install backend deps (example)
# pip install -r requirements.txt
```

### ChainIQ Service (risk/AI)
```bash
cd chainiq-service
# Example dev run (adjust module/path if needed)
# uvicorn app.api:app --reload --port 8001
```

### ChainPay Service (payments/settlement)
```bash
cd ../chainpay-service
# Example dev run
# uvicorn app.api:app --reload --port 8002
```

---

## Testing

From the ChainBridge root (or wherever tests are configured):

```bash
# Using the repo's venv
# source .venv/bin/activate

pytest -vv
```

If tests live under service folders (e.g. chainpay-service/tests, chainiq-service/tests), you can also run:

```bash
cd chainpay-service
pytest -vv tests

cd ../chainiq-service
pytest -vv tests
```

---

## Docs to Read First

Recommended starting points:

- docs/architecture/CHAINBRIDGE_OVERVIEW.md (if present)
- docs/architecture/CHAINPAY_ONCHAIN_SETTLEMENT.md
- docs/product/CHAINPAY_V1_SPEC.md
- docs/governance/AGENT_ACTIVITY_LOG.md

These cover:
- The Sense → Think → Act pattern
- How ChainIQ and ChainPay interact
- How CB-USDx, XRPL, and Chainlink fit into the design
