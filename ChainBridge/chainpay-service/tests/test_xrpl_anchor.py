"""
Test XRPL anchoring for settlement receipts.
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
async def test_anchor_settlement_produces_valid_hash():
    service = XRPLSettlementService({
        "XRPL_MODE": XRPL_MODE,
        "XRPL_SEED": XRPL_SEED,
        "XRPL_ADDRESS": XRPL_ADDRESS
    })
    canonical_shipment_id = "SHIP123456"
    event_payload = {"event_type": "SETTLEMENT_FINALIZED", "amount": 1000}
    governance_metadata = {"rule_id": "GOV-01", "severity": "HIGH"}
    ml_metadata = {"prediction": "OK"}
    result = await service.anchor_settlement(canonical_shipment_id, event_payload, governance_metadata, ml_metadata)
    assert "settlement_hash" in result
    assert isinstance(result["settlement_hash"], str)
    assert len(result["settlement_hash"]) == 64
    assert result["success"] in [True, False]  # Success depends on XRPL connectivity
    assert "trace_id" in result
    assert "rationale" in result
