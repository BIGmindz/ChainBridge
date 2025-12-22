# ChainPay CI Notes (DAN-004)

## Scope
- Ensure ChainPay backend tests (including settlement API) run in CI.
- Ensure ChainBoard UI builds in CI.
- Provide a minimal smoke check for the settlement endpoint using FastAPI `TestClient`.

## Workflows
- **`ChainBridge/.github/workflows/chainpay-iq-ui-ci.yml`**
  - Triggers: push/PR to `main`, `develop`, `feature/*`.
  - Python 3.11 backend job:
    - Creates `.venv`, installs `requirements.txt`, `requirements-dev.txt`, and `chainpay-service/requirements.txt` (guarded with `|| true`).
    - Runs IQ + ML tests (legacy from combined workflow):
      - `make iq-tests`
      - `pytest -vv tests/ml/test_context_ledger_risk_model.py`
    - Runs ChainPay tests:
      - `cd chainpay-service && ../.venv/bin/python -m pytest -p pytest_cov -vv tests`
    - Smoke check (new):
      - FastAPI `TestClient` request to `/api/chainpay/settlements/SHIP-12345`, asserts `shipment_id` matches.
  - Frontend job:
    - Node 20 with npm cache.
    - `cd chainboard-ui && npm ci && npm run build`.

## How to reproduce locally
```bash
# Backend (from ChainBridge root)
cd ChainBridge
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt -r chainpay-service/requirements.txt
make iq-tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -vv tests/ml/test_context_ledger_risk_model.py
cd chainpay-service
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.. VIRTUAL_ENV=../.venv ../.venv/bin/python -m pytest -p pytest_cov -vv tests
python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app
resp = TestClient(app).get("/api/chainpay/settlements/SHIP-12345")
resp.raise_for_status()
print(resp.json())
PY

# Frontend
cd ../chainboard-ui
npm ci
npm run build
```

## Future improvements
- Split IQ/ChainPay into separate jobs if runtime grows.
- Add `npm run lint` or `npm test` when stable.
- Add coverage thresholds for ChainPay tests.
- Convert smoke to a lightweight live server probe if we add Dockerized services later.
- Align with ALEX governance once the CI/deploy policy is finalized.
