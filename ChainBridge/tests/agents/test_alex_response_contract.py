from __future__ import annotations

import pytest

pytestmark = pytest.mark.core

"""
ALEX Response Contract

Any ALEX response that leaves the agent layer must conform to a
strict, parseable structure, so downstream services (ChainPay,
ChainIQ, OC) can treat it as a machine-consumable decision.

This test suite defines the MINIMUM JSON contract.
"""


REQUIRED_TOP_LEVEL_KEYS = [
    "bluf",
    "issues",
    "applicable_frameworks",
    "governance_checks",
    "analysis",
    "risk_classification",
    "required_controls",
    "raci",
    "final_determination",
]


def validate_alex_payload(payload: dict) -> None:
    """
    Reference validator for ALEX outputs.

    This is intentionally minimal and self-contained:
    Cody can later delegate to a shared schema / Pydantic model.
    """
    missing = [k for k in REQUIRED_TOP_LEVEL_KEYS if k not in payload]
    if missing:
        raise ValueError(f"Missing required keys: {', '.join(missing)}")

    if payload["final_determination"] not in {"APPROVED", "BLOCKED", "ESCALATE"}:
        raise ValueError("final_determination must be APPROVED | BLOCKED | ESCALATE")

    if payload["risk_classification"] not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        raise ValueError("risk_classification must be LOW | MEDIUM | HIGH | CRITICAL")

    raci = payload["raci"]
    if not isinstance(raci, dict):
        raise ValueError("raci must be an object mapping roles → owners")

    for required_role in ["Legal", "Operations", "Engineering"]:
        if required_role not in raci:
            raise ValueError(f"raci must include role: {required_role}")


def test_alex_payload_happy_path():
    payload = {
        "bluf": "This flow is acceptable with standard controls.",
        "issues": ["No prior breach on this corridor.", "Wrapper ACTIVE."],
        "applicable_frameworks": ["Ricardian", "OFAC-lite", "SOX-lite"],
        "governance_checks": {
            "wrapper_status": "ACTIVE",
            "supremacy_status": "COMPLIANT",
            "kill_switch_state": "SAFE",
        },
        "analysis": "Sample narrative.",
        "risk_classification": "LOW",
        "required_controls": ["Standard KYC", "Standard AML screening"],
        "raci": {
            "Legal": "ALEX",
            "Operations": "ChainBridge Ops",
            "Engineering": "ChainBridge Core",
        },
        "final_determination": "APPROVED",
    }

    validate_alex_payload(payload)  # should NOT raise


def test_alex_payload_missing_keys_is_invalid():
    payload = {
        "bluf": "Example only",
        # missing many required keys
    }

    with pytest.raises(ValueError):
        validate_alex_payload(payload)


@pytest.mark.parametrize("bad_value", ["OK", "ALLOW", "DENY", "PENDING"])
def test_alex_payload_invalid_final_determination_rejected(bad_value):
    base = {
        "bluf": "x",
        "issues": [],
        "applicable_frameworks": [],
        "governance_checks": {
            "wrapper_status": "ACTIVE",
            "supremacy_status": "COMPLIANT",
            "kill_switch_state": "SAFE",
        },
        "analysis": "x",
        "risk_classification": "LOW",
        "required_controls": [],
        "raci": {
            "Legal": "ALEX",
            "Operations": "Ops",
            "Engineering": "Eng",
        },
        "final_determination": bad_value,
    }

    with pytest.raises(ValueError):
        validate_alex_payload(base)


@pytest.mark.parametrize("risk", ["OK", "NONE", "SEVERE"])
def test_alex_payload_invalid_risk_classification_rejected(risk):
    base = {
        "bluf": "x",
        "issues": [],
        "applicable_frameworks": [],
        "governance_checks": {
            "wrapper_status": "ACTIVE",
            "supremacy_status": "COMPLIANT",
            "kill_switch_state": "SAFE",
        },
        "analysis": "x",
        "risk_classification": risk,
        "required_controls": [],
        "raci": {
            "Legal": "ALEX",
            "Operations": "Ops",
            "Engineering": "Eng",
        },
        "final_determination": "APPROVED",
    }

    with pytest.raises(ValueError):
        validate_alex_payload(base)
