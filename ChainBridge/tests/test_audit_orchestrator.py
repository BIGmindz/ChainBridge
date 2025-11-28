from api.audit.orchestrator import _emit_audit_recommended, is_high_risk_band


def test_emit_audit_recommended_does_not_raise():
    _emit_audit_recommended("SET-1", ["rule1", "rule2"])


def test_is_high_risk_band():
    assert is_high_risk_band("HIGH") is True
    assert is_high_risk_band("LOW") is False
