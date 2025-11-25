from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure ChainBridge app directory is on sys.path when running tests from monorepo root
# Layout:
#   repo root: /.../ChainBridge-local-repo
#   app root:  /.../ChainBridge-local-repo/ChainBridge
ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR / "ChainBridge"

if APP_DIR.is_dir() and str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from api.server import app  # now resolves via injected path
from api.core.config import settings

# Force demo mode for deterministic intel responses
settings.DEMO_MODE = True  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Shared TestClient for API tests."""
    with TestClient(app) as c:
        yield c
