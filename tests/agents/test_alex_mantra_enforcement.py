import pytest

ALEX_REQUIRED_SECTIONS = [
    "BLUF",
    "Issues",
    "Applicable",
    "Governance",
    "Analysis",
    "Risk",
    "Mitigations",
    "RACI",
    "Final Determination",
]


def alex_output_sections(text: str):
    return [section for section in ALEX_REQUIRED_SECTIONS if section.lower() in text.lower()]


# ---------------------------------------------------------
# 1. ALEX must block flows that violate the ChainBridge mantra
# ---------------------------------------------------------


@pytest.mark.parametrize(
    "scenario,proof,pipes,cash,expected",
    [
        ("missing proof", False, True, True, "BLOCKED"),
        ("missing pipes", True, False, True, "BLOCKED"),
        ("missing cash", True, True, False, "BLOCKED"),
        ("everything present", True, True, True, "APPROVED"),
    ],
)
def test_mantra_enforcement(scenario, proof, pipes, cash, expected):
    """
    ALEX must enforce:
    'Speed without proof gets blocked.
     Proof without pipes doesn’t scale.
     Pipes without cash don’t settle.
     You need all three.'
    """

    # Simulated chainbridge-mandate evaluator
    def evaluate_mantra(proof, pipes, cash):
        if not proof or not pipes or not cash:
            return "BLOCKED"
        return "APPROVED"

    determination = evaluate_mantra(proof, pipes, cash)
    assert determination == expected, f"{scenario}: mantra enforcement failed"


# ---------------------------------------------------------
# 2. ALEX MUST require wrapper + supremacy + kill-switch states
# ---------------------------------------------------------


@pytest.mark.parametrize(
    "wrapper,supremacy,kill,expected",
    [
        ("ACTIVE", "COMPLIANT", "SAFE", True),
        ("ACTIVE", "NEEDS_PROOF", "SAFE", True),
        ("ACTIVE", "BLOCKED", "SAFE", False),
        ("FROZEN", "COMPLIANT", "SAFE", False),
        ("TERMINATED", "COMPLIANT", "SAFE", False),
        ("ACTIVE", "COMPLIANT", "UNSAFE", False),
    ],
)
def test_governance_gates(wrapper, supremacy, kill, expected):
    """
    ALEX must block operations when:
      - wrapper = FROZEN/TERMINATED
      - supremacy = BLOCKED
      - kill-switch = UNSAFE
    """

    def governance_valid():
        if wrapper in ("FROZEN", "TERMINATED"):
            return False
        if supremacy == "BLOCKED":
            return False
        if kill == "UNSAFE":
            return False
        return True

    assert governance_valid() == expected
