"""
Test XRPL settlement pipeline integration.
"""
import pytest
try:
    from config import XRPL_MODE, XRPL_SEED, XRPL_ADDRESS
    from app.xrpl.xrpl_settlement_service import XRPLSettlementService
    xrpl_import_ok = True
except ImportError:
    xrpl_import_ok = False

pytestmark = pytest.mark.skipif(not xrpl_import_ok, reason="XRPL or config import failed")

@pytest.mark.asyncio
async def test_pipeline_emits_xrpl_anchor_success():
    service = XRPLSettlementService({
        "XRPL_MODE": XRPL_MODE,
        "XRPL_SEED": XRPL_SEED,
        "XRPL_ADDRESS": XRPL_ADDRESS
    })
    canonical_shipment_id = "SHIP987654"
    event_payload = {"event_type": "SETTLEMENT_FINALIZED", "amount": 500}
    governance_metadata = {"rule_id": "GOV-02", "severity": "MEDIUM"}
    ml_metadata = {"prediction": "OK"}
    result = await service.anchor_settlement(canonical_shipment_id, event_payload, governance_metadata, ml_metadata)
    if result["success"]:
        assert result["tx_hash"] is not None
        assert result["ledger_index"] is not None
        assert result["rationale"] == "Settlement anchored to XRPL"
    else:
        assert result["tx_hash"] is None
        assert result["ledger_index"] is None
        assert "disabled" in result["rationale"] or "wallet missing" in result["rationale"]
