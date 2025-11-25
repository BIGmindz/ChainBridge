from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.server import app
from api.core.config import settings

# Force demo mode for deterministic intel responses
settings.DEMO_MODE = True  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Shared TestClient for API tests."""
    with TestClient(app) as c:
        yield c
