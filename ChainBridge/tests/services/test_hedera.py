"""Phase 2: Hedera ledger integration tests.

These tests validate the Hedera Hashgraph integration for audit logging and RWA minting.
Due to sys.path conflicts between the monorepo 'app' package and chainiq-service 'app',
these imports fail when conftest.py loads api.server first.

Status: Deferred to Phase 2 (module exists but import path conflicts with ChainIQ)
"""
import re

import pytest

# Phase 2: Import guard due to sys.path conflict with chainiq-service
try:
    from app.services.ledger.hedera_engine import log_audit_event, mint_rwa_token
    _HEDERA_ENGINE_AVAILABLE = True
except ImportError:
    _HEDERA_ENGINE_AVAILABLE = False
    log_audit_event = mint_rwa_token = None

pytestmark = [
    pytest.mark.phase2,
    pytest.mark.skipif(not _HEDERA_ENGINE_AVAILABLE, reason="Hedera engine module unavailable (sys.path conflict with ChainIQ)"),
]


def test_mint_rwa_token_returns_token_id() -> None:
    token_id = mint_rwa_token("demo-metadata-hash", amount=1)
    assert re.match(r"^0\.0\.\d+$", token_id)


def test_log_audit_event_returns_receipt() -> None:
    receipt = log_audit_event("SHIP-DEMO-1", {"fuzzy_score": 99})
    assert "message_id" in receipt
    assert receipt["message_id"]
