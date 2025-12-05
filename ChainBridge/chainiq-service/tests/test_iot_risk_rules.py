"""Deprecated engine-level IoT risk tests.

The authoritative IoT risk rule tests now live at:

    tests/test_iq_iot_risk_rules_api.py

and exercise the behavior via the unified FastAPI app and the
/iq/score-shipment endpoint. This placeholder is kept to avoid
confusion when scanning the chainiq-service tests directory.
"""

import pytest


@pytest.mark.skip("Superseded by API-level IoT risk tests in tests/test_iq_iot_risk_rules_api.py")
def test_engine_level_iot_rules_placeholder() -> None:
    assert True
