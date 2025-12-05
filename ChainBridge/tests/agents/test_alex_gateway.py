from __future__ import annotations

import pytest

from api.agents.alex_gateway import AlexGovernanceError, alex_gateway

pytestmark = pytest.mark.core

GOOD_RESPONSE = """
BLUF: OK
Issues: OK
Applicable Frameworks: OK
Governance Checks: OK
Analysis: OK
Risk Classification: LOW
Required Controls: OK
RACI: OK
Final Determination: APPROVED
"""


def test_gateway_passes_on_valid_input():
    payload = {
        "proof": True,
        "pipes": True,
        "cash": True,
        "wrapper": "ACTIVE",
        "supremacy": "COMPLIANT",
        "kill": "SAFE",
    }
    result = alex_gateway(payload, GOOD_RESPONSE)
    assert result["status"] == "APPROVED"


@pytest.mark.parametrize(
    "proof,pipes,cash",
    [
        (False, True, True),
        (True, False, True),
        (True, True, False),
    ],
)
def test_mantra_failures(proof, pipes, cash):
    payload = {
        "proof": proof,
        "pipes": pipes,
        "cash": cash,
    }
    with pytest.raises(AlexGovernanceError):
        alex_gateway(payload, GOOD_RESPONSE)
