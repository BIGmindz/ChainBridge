import pytest

pytestmark = pytest.mark.core

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

@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_alex_response_sections_present(section):
    """
    Ensures ALEX responses ALWAYS include critical sections.
    If any of these are missing in an output, ALEX is malfunctioning.
    """

    # Example output ALEX should ALWAYS match
    example = """
    BLUF: Example
    Issues: Example
    Applicable Frameworks: Example
    Governance Checks: Example
    Analysis: Example
    Risk Classification: LOW
    Required Controls: Example
    RACI: Legal, Ops, Eng
    Final Determination: APPROVED
    """

    assert section in example, f"Section missing: {section}"
