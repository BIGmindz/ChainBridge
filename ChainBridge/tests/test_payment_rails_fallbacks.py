from __future__ import annotations

import pytest

from chainpay_service.app.payment_rails import (
    canonical_milestone_id,
)
from core.payments.identity import canonical_shipment_reference


def test_canonical_milestone_fallback_non_empty():
    result = canonical_milestone_id("SHP-123", 2)
    assert result == "SHP-123-M2"


def test_canonical_shipment_reference_freight_token():
    result = canonical_shipment_reference(shipment_reference=None, freight_token_id=42)
    assert result in {"FTK-42", "SHP-0042"}


def test_canonical_shipment_reference_unknown():
    with pytest.raises(ValueError):
        canonical_shipment_reference(shipment_reference=None, freight_token_id=None)
