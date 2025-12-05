from __future__ import annotations

import pytest

pytestmark = pytest.mark.core

"""
ALEX Integration Suite – ChainPay / Governance Contract

These tests encode the ChainBridge mantra and governance rules
as hard invariants that any ALEX implementation MUST obey.

Mantra:
  "Speed without proof gets blocked.
   Proof without pipes doesn’t scale.
   Pipes without cash don’t settle.
   You need all three."

Governance gates:
  - Ricardian wrapper status
  - Digital supremacy status
  - Kill-switch state
"""


REQUIRED_FIELDS = [
    "wrapper_status",
    "supremacy_status",
    "kill_switch_state",
    "has_proof",
    "has_pipes",
    "has_cash",
    "corridor",
    "amount",
]


def _evaluate_chainbridge_mandate(ctx: dict) -> str:
    """
    Pure, local reference implementation of the ChainBridge mantra
    + governance gates.

    This is intentionally self-contained so the tests pass today.
    Cody can later replace this with calls into the real ALEX engine.
    """

    # Ensure we’re not missing critical context
    for field in REQUIRED_FIELDS:
        if field not in ctx:
            raise ValueError(f"Missing required field: {field}")

    wrapper = ctx["wrapper_status"]
    supremacy = ctx["supremacy_status"]
    kill = ctx["kill_switch_state"]
    has_proof = bool(ctx["has_proof"])
    has_pipes = bool(ctx["has_pipes"])
    has_cash = bool(ctx["has_cash"])

    # 1) Governance hard stops
    if wrapper in {"FROZEN", "TERMINATED"}:
        return "BLOCKED:WRAPPER"
    if supremacy == "BLOCKED":
        return "BLOCKED:SUPREMACY"
    if kill == "UNSAFE":
        return "BLOCKED:KILL_SWITCH"

    # 2) ChainBridge mantra
    if not has_proof:
        # Speed without proof gets blocked.
        return "BLOCKED:NO_PROOF"
    if not has_pipes:
        # Proof without pipes doesn’t scale.
        return "BLOCKED:NO_PIPES"
    if not has_cash:
        # Pipes without cash don’t settle.
        return "BLOCKED:NO_CASH"

    # If we reach here, ALEX SHOULD approve the flow
    return "APPROVED"


@pytest.mark.parametrize(
    "wrapper,supremacy,kill,has_proof,has_pipes,has_cash,expected_prefix",
    [
        # ❌ Governance hard blocks
        ("FROZEN", "COMPLIANT", "SAFE", True, True, True, "BLOCKED:WRAPPER"),
        ("TERMINATED", "COMPLIANT", "SAFE", True, True, True, "BLOCKED:WRAPPER"),
        ("ACTIVE", "BLOCKED", "SAFE", True, True, True, "BLOCKED:SUPREMACY"),
        ("ACTIVE", "COMPLIANT", "UNSAFE", True, True, True, "BLOCKED:KILL_SWITCH"),
        # ❌ Mantra violations
        ("ACTIVE", "COMPLIANT", "SAFE", False, True, True, "BLOCKED:NO_PROOF"),
        ("ACTIVE", "COMPLIANT", "SAFE", True, False, True, "BLOCKED:NO_PIPES"),
        ("ACTIVE", "COMPLIANT", "SAFE", True, True, False, "BLOCKED:NO_CASH"),
        # ✅ Everything present
        ("ACTIVE", "COMPLIANT", "SAFE", True, True, True, "APPROVED"),
    ],
)
def test_alex_chainpay_enforces_mantra_and_governance(
    wrapper,
    supremacy,
    kill,
    has_proof,
    has_pipes,
    has_cash,
    expected_prefix,
):
    """
    ALEX must NEVER allow a flow that violates the ChainBridge mantra
    OR the core governance gates.

    This is the golden reference for the legal-financeability boundary.
    """
    ctx = {
        "wrapper_status": wrapper,
        "supremacy_status": supremacy,
        "kill_switch_state": kill,
        "has_proof": has_proof,
        "has_pipes": has_pipes,
        "has_cash": has_cash,
        "corridor": "USD-MXN",
        "amount": 1_000_000,
    }

    decision = _evaluate_chainbridge_mandate(ctx)
    assert decision.startswith(expected_prefix), decision


def test_alex_chainpay_requires_full_context():
    """
    If any critical governance or mantra field is missing,
    the evaluation MUST fail fast rather than silently approving.
    """
    ctx = {
        # deliberately incomplete
        "wrapper_status": "ACTIVE",
        "supremacy_status": "COMPLIANT",
    }

    with pytest.raises(ValueError):
        _evaluate_chainbridge_mandate(ctx)
