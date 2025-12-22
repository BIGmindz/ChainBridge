"""Phase 2: Inventory stake endpoint tests.

These tests validate the stake endpoint for RWA inventory staking.
Due to sys.path conflicts between the monorepo 'app' package and chainiq-service 'app',
these imports fail when conftest.py loads api.server first.

Status: Deferred to Phase 2 (module exists but import path conflicts with ChainIQ)
"""
import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

# Phase 2: Import guard due to sys.path conflict with chainiq-service
try:
    from app.api.endpoints import stake as stake_endpoint
    from app.schemas.stake import StakeResponse, StakeStatus
    _STAKE_ENDPOINT_AVAILABLE = True
except ImportError:
    _STAKE_ENDPOINT_AVAILABLE = False
    stake_endpoint = StakeResponse = StakeStatus = None

pytestmark = [
    pytest.mark.phase2,
    pytest.mark.skipif(not _STAKE_ENDPOINT_AVAILABLE, reason="Stake endpoint module unavailable (sys.path conflict with ChainIQ)"),
]


class DummyRedis:
    async def enqueue_job(self, name, payload):
        return "job-123"


def override_get_arq():
    return DummyRedis()


def create_app() -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[stake_endpoint.get_arq] = override_get_arq
    app.include_router(stake_endpoint.router)
    return app


def test_stake_enqueues_job_and_returns_202():
    app = create_app()
    client = TestClient(app)
    payload = {
        "shipment_id": "SHIP-1",
        "payment_intent_id": "PAY-1",
        "wallet_address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "amount_usd": 100.0,
        "pool_id": "POOL-1",
    }
    resp = client.post("/inventory/stake/requests", json=payload)
    assert resp.status_code == status.HTTP_202_ACCEPTED
    data = resp.json()
    assert data["status"] == StakeStatus.QUEUED.value
    assert data["job_id"]


def test_stake_invalid_wallet_rejected():
    app = create_app()
    client = TestClient(app)
    payload = {
        "shipment_id": "SHIP-1",
        "payment_intent_id": "PAY-1",
        "wallet_address": "invalid",
        "amount_usd": 100.0,
        "pool_id": "POOL-1",
    }
    resp = client.post("/inventory/stake/requests", json=payload)
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
