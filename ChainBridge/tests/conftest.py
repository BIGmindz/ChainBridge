"""Pytest Configuration for ChainBridge Tests.

╔══════════════════════════════════════════════════════════════════════╗
║ EXECUTING AGENT: Cody (GID-01) — Senior Backend Engineer             ║
║ EXECUTING COLOR: 🟢 BLUE                                             ║
║ PAC: PAC-CODY-A6-ARCHITECTURE-ENFORCEMENT-WIRING-01                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""
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

# Use the repo root directly; the app modules (e.g., api.server) live there.
if ROOT_DIR.is_dir():
    if str(ROOT_DIR) in sys.path:
        sys.path.remove(str(ROOT_DIR))
    sys.path.insert(0, str(ROOT_DIR))

# Also add monorepo root for core.* modules (e.g., core.proof.validation)
# PAC-CODY-A6-ARCHITECTURE-ENFORCEMENT-WIRING-01: Allow importing core modules
# NOTE: Insert AFTER ROOT_DIR to not shadow api.* imports
MONOREPO_ROOT = ROOT_DIR.parent
if MONOREPO_ROOT.is_dir() and (MONOREPO_ROOT / "core").exists():
    if str(MONOREPO_ROOT) not in sys.path:
        # Append rather than insert to preserve priority of ChainBridge modules
        sys.path.append(str(MONOREPO_ROOT))

# ---------------------------------------------------------------------------
# NAMESPACE ISOLATION: Pre-load monorepo app.* modules BEFORE api.server
# ---------------------------------------------------------------------------
# The api.server module loads chainiq-service, which has its own 'app' package.
# To prevent namespace collision, we pre-load all monorepo app modules here.
# This ensures they're saved and restored properly by _load_chainiq_router().
#
# Monorepo modules: app.services.*, app.api.endpoints.*, app.models.*, etc.
# ChainIQ modules:  app.risk.*, app.api (router), app.schemas
# These namespaces are disjoint and can coexist once properly registered.
# ---------------------------------------------------------------------------
def _preload_monorepo_app_modules() -> None:
    """Pre-load monorepo app.* modules to ensure namespace isolation."""
    # Import submodules that tests need. These will be saved by
    # _load_chainiq_router() before it loads chainiq-service.
    try:
        # Core config needed by many modules
        import app.core.config  # noqa: F401

        # Marketplace modules (Phase 2 tests)
        import app.models.marketplace  # noqa: F401
        import app.services.marketplace.dutch_engine  # noqa: F401
        import app.services.marketplace.auctioneer  # noqa: F401
        import app.services.marketplace.buy_intents  # noqa: F401
        import app.services.marketplace.price_proof  # noqa: F401

        # Ledger/Hedera modules (Phase 2 tests)
        import app.services.ledger.hedera_engine  # noqa: F401

        # Pricing/fuzzy modules (Phase 2 tests)
        import app.services.chain_audit.fuzzy_engine  # noqa: F401
        import app.services.pricing.adjuster  # noqa: F401

        # API endpoints (Phase 2 tests)
        import app.api.api  # noqa: F401
        import app.api.endpoints.stake  # noqa: F401
        import app.api.endpoints.marketplace  # noqa: F401

        # Schemas (Phase 2 tests)
        import app.schemas.marketplace  # noqa: F401
        import app.schemas.stake  # noqa: F401

        # Worker modules (Phase 2 tests)
        import app.worker.settlement  # noqa: F401

        # PDO enforcement modules (PDO Enforcement Gates)
        import app.services.pdo.validator  # noqa: F401
        import app.middleware.pdo_enforcement  # noqa: F401

        # PDO signature verification (PDO Signing)
        import app.services.pdo.signing  # noqa: F401

        # Risk interface modules (PDO Risk Integration)
        import app.services.risk.interface  # noqa: F401
    except ImportError:
        # Some modules may not exist; that's fine, they'll be skipped anyway
        pass


_preload_monorepo_app_modules()

# Note: chainiq-service path is added by api/server.py when it imports the ChainIQ router.
# We don't add it here to avoid shadowing the monorepo 'app' package.

from api.server import app  # now resolves via injected path
from api.core.config import settings

# Force demo mode for deterministic intel responses
settings.DEMO_MODE = True  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Shared TestClient for API tests."""
    with TestClient(app) as c:
        yield c


# ═══════════════════════════════════════════════════════════════════════════
# END — Cody (GID-01) — 🔵
# ═══════════════════════════════════════════════════════════════════════════
