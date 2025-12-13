import re

import pytest
from app.services.ledger.hedera_engine import log_audit_event, mint_rwa_token

pytestmark = pytest.mark.phase2


def test_mint_rwa_token_returns_token_id() -> None:
    token_id = mint_rwa_token("demo-metadata-hash", amount=1)
    assert re.match(r"^0\.0\.\d+$", token_id)


def test_log_audit_event_returns_receipt() -> None:
    receipt = log_audit_event("SHIP-DEMO-1", {"fuzzy_score": 99})
    assert "message_id" in receipt
    assert receipt["message_id"]
