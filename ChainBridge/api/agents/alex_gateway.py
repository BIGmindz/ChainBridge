"""
ALEX Gateway – Runtime Governance Validator
This enforces:
- ChainBridge mantra (proof/pipes/cash)
- Wrapper/supremacy/kill-switch states
- Required output structure
- Deterministic governance guardrails
"""

from typing import Any, Dict


REQUIRED_SECTIONS = [
    "BLUF",
    "Issues",
    "Applicable Frameworks",
    "Governance Checks",
    "Analysis",
    "Risk Classification",
    "Required Controls",
    "RACI",
    "Final Determination",
]


class AlexGovernanceError(Exception):
    """Raised when ALEX violates any governance rule."""


def enforce_chainbridge_mantra(proof: bool, pipes: bool, cash: bool):
    """
    ChainBridge Mantra:
    Speed without proof gets blocked.
    Proof without pipes doesn’t scale.
    Pipes without cash don’t settle.
    You need all three.
    """
    if not proof or not pipes or not cash:
        raise AlexGovernanceError(
            f"Mantra violation: proof={proof}, pipes={pipes}, cash={cash}"
        )


def enforce_governance_states(wrapper: str, supremacy: str, kill_state: str):
    """
    Governance Enforcement:
    - wrapper cannot be FROZEN or TERMINATED
    - supremacy cannot be BLOCKED
    - kill-switch cannot be UNSAFE
    """
    if wrapper in ("FROZEN", "TERMINATED"):
        raise AlexGovernanceError(f"Wrapper violation: wrapper={wrapper}")

    if supremacy == "BLOCKED":
        raise AlexGovernanceError(f"Supremacy violation: supremacy={supremacy}")

    if kill_state == "UNSAFE":
        raise AlexGovernanceError(f"Kill-switch violation: kill_state={kill_state}")


def enforce_response_structure(response_text: str):
    """
    ALEX responses must include mandatory sections.
    Prevents drift, hallucination, or unstructured output.
    """
    missing = [sec for sec in REQUIRED_SECTIONS if sec not in response_text]
    if missing:
        raise AlexGovernanceError(
            f"ALEX output missing sections: {', '.join(missing)}"
        )


def alex_gateway(input_payload: Dict[str, Any], response_text: str):
    """
    Unified gateway:
    - Validate pre-conditions (mantra + governance)
    - Validate post-conditions (structure)
    """

    enforce_chainbridge_mantra(
        proof=input_payload.get("proof", False),
        pipes=input_payload.get("pipes", False),
        cash=input_payload.get("cash", False),
    )

    enforce_governance_states(
        wrapper=input_payload.get("wrapper", "ACTIVE"),
        supremacy=input_payload.get("supremacy", "COMPLIANT"),
        kill_state=input_payload.get("kill", "SAFE"),
    )

    enforce_response_structure(response_text)

    return {
        "status": "APPROVED",
        "reason": "ALEX governance checks passed",
    }
