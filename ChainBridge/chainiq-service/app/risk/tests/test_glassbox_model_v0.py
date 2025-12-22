# app/risk/tests/test_glassbox_model_v0.py
from __future__ import annotations

from app.risk.glassbox_model_v0 import score_shipment_risk


def test_score_shipment_risk_returns_expected_structure():
    shipment = {
        "origin_country": "US",
        "destination_country": "CA",
        "amount": 50000,
    }
    context = {
        "has_disputes": False,
        "has_late_deliveries": True,
    }

    result = score_shipment_risk(shipment, context)

    assert "risk_score" in result
    assert "risk_band" in result
    assert "input_snapshot" in result
    assert "rules_fired" in result
    assert "explanation" in result

    assert isinstance(result["risk_score"], int)
    assert result["risk_band"] in {"LOW", "MEDIUM", "HIGH"}
    assert isinstance(result["rules_fired"], list)
    assert result["input_snapshot"]["amount"] == 50000
    assert result["input_snapshot"]["has_late_deliveries"] is True


def test_score_shipment_risk_is_deterministic():
    shipment = {
        "origin_country": "US",
        "destination_country": "CA",
        "amount": 50000,
    }
    context = {
        "has_disputes": True,
        "has_late_deliveries": False,
    }

    r1 = score_shipment_risk(shipment, context)
    r2 = score_shipment_risk(shipment, context)

    assert r1["risk_score"] == r2["risk_score"]
    assert r1["risk_band"] == r2["risk_band"]
    assert r1["rules_fired"] == r2["rules_fired"]
