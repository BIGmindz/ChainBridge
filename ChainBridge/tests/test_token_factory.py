"""Token creation validation tests."""

import pytest

from chainbridge.tokens.at02 import AT02Token
from chainbridge.tokens.base_token import RelationValidationError, TokenValidationError
from chainbridge.tokens.it01 import IT01Token


def test_missing_required_field_triggers_validation():
    with pytest.raises(TokenValidationError):
        AT02Token(
            parent_shipment_id="SHP-100",
            metadata={
                "accessorial_type": "DETENTION",
                "amount": 150.0,
                "timestamp": "2025-01-01T00:00:00Z",
                "currency": "USD",
            },
            relations={"mt01_id": "MT-1"},
        )


def test_it01_requires_relations():
    with pytest.raises(RelationValidationError):
        IT01Token(
            parent_shipment_id="SHP-1",
            metadata={
                "invoice_number": "INV-1",
                "currency": "USD",
                "total": 1000.0,
                "line_items": [{"code": "LH", "amount": 800.0}],
                "due_date": "2025-01-05",
            },
            relations={"qt01_id": "QT-1"},
        )
