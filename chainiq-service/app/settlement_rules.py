"""
ChainIQ v0.1 - Settlement Policy Rules

Glass-box, rule-based mapping from risk scores to settlement policy recommendations.
These rules define how ChainIQ risk assessments translate to payment flow suggestions.

Design Philosophy:
- No black-box ML in v0.1 — simple thresholds and lookup tables
- Every decision can be explained to a CFO in < 2 minutes
- ChainIQ **recommends**, ChainPay + governance **decide**

Author: Maggie (GID-10) - ML & Applied AI Lead
Mantra: "Code = Cash. Explain or Perish."
"""

from datetime import datetime
from typing import Any, Dict, List

from .schemas import SettlementMilestoneRecommendation, SettlementPolicyRecommendation, ShipmentRiskAssessment

# =============================================================================
# RISK BAND DEFINITIONS
# =============================================================================

RISK_BANDS = [
    {"name": "LOW", "min": 0, "max": 30, "label": "Low Risk"},
    {"name": "MODERATE", "min": 30, "max": 60, "label": "Moderate Risk"},
    {"name": "HIGH", "min": 60, "max": 80, "label": "High Risk"},
    {"name": "CRITICAL", "min": 80, "max": 100, "label": "Critical Risk"},
]


def get_risk_band(risk_score: float) -> Dict[str, Any]:
    """
    Determine risk band from score.

    Bands:
        LOW:      0-30   → Fast settlement, minimal holds
        MODERATE: 30-60  → Balanced approach
        HIGH:     60-80  → Guarded, shift to claim window
        CRITICAL: 80-100 → Maximum caution, human review

    Args:
        risk_score: Risk score (0-100)

    Returns:
        Risk band dictionary with name, min, max, label
    """
    for band in RISK_BANDS:
        if band["min"] <= risk_score < band["max"]:
            return band
    # Edge case: exactly 100
    return RISK_BANDS[-1]


# =============================================================================
# SETTLEMENT POLICY TEMPLATES
# =============================================================================

# Each policy template defines:
#   - code: Short identifier
#   - name: Human-readable name
#   - description: What this policy does
#   - milestones: List of (name, event_type, percentage, timing_hint)
#   - settlement_delay_hours: Minimum hold before any release
#   - requires_manual_approval: Whether human sign-off is needed

SETTLEMENT_POLICY_TEMPLATES = {
    "LOW_RISK_FAST": {
        "code": "LOW_RISK_FAST",
        "name": "Low Risk - Fast Settlement",
        "description": "Accelerated payment release for trusted, low-risk shipments",
        "milestones": [
            ("PICKUP", "BOL_ISSUED", 20.0, "on_pickup"),
            ("DELIVERY", "POD_RECEIVED", 70.0, "on_delivery"),
            ("CLAIM_WINDOW", "CLAIM_WINDOW_CLOSED", 10.0, "7_days_post_delivery"),
        ],
        "settlement_delay_hours": 0.0,
        "hold_percentage": 10.0,
        "requires_manual_approval": False,
        "tags": ["FAST_SETTLEMENT", "RISK_BAND_LOW"],
    },
    "MODERATE_BALANCED": {
        "code": "MODERATE_BALANCED",
        "name": "Moderate Risk - Balanced Settlement",
        "description": "Standard milestone-based payment with moderate claim window hold",
        "milestones": [
            ("PICKUP", "BOL_ISSUED", 10.0, "on_pickup"),
            ("DELIVERY", "POD_RECEIVED", 60.0, "on_delivery"),
            ("CLAIM_WINDOW", "CLAIM_WINDOW_CLOSED", 30.0, "7_days_post_delivery"),
        ],
        "settlement_delay_hours": 12.0,
        "hold_percentage": 30.0,
        "requires_manual_approval": False,
        "tags": ["BALANCED_SETTLEMENT", "RISK_BAND_MODERATE"],
    },
    "HIGH_RISK_GUARDED": {
        "code": "HIGH_RISK_GUARDED",
        "name": "High Risk - Guarded Settlement",
        "description": "Conservative payment flow with significant claim window protection",
        "milestones": [
            ("PICKUP", "BOL_ISSUED", 0.0, None),
            ("DELIVERY", "POD_RECEIVED", 60.0, "on_delivery"),
            ("CLAIM_WINDOW", "CLAIM_WINDOW_CLOSED", 40.0, "14_days_post_delivery"),
        ],
        "settlement_delay_hours": 24.0,
        "hold_percentage": 40.0,
        "requires_manual_approval": False,
        "tags": ["GUARDED_SETTLEMENT", "RISK_BAND_HIGH", "CLAIM_WINDOW_EXTENDED"],
    },
    "CRITICAL_REVIEW": {
        "code": "CRITICAL_REVIEW",
        "name": "Critical Risk - Manual Review Required",
        "description": "Maximum caution with majority held until claim window and human approval",
        "milestones": [
            ("PICKUP", "BOL_ISSUED", 0.0, None),
            ("DELIVERY", "POD_RECEIVED", 40.0, "on_delivery"),
            ("CLAIM_WINDOW", "CLAIM_WINDOW_CLOSED", 60.0, "21_days_post_delivery"),
        ],
        "settlement_delay_hours": 48.0,
        "hold_percentage": 60.0,
        "requires_manual_approval": True,
        "tags": ["MANUAL_REVIEW_REQUIRED", "RISK_BAND_CRITICAL", "MAXIMUM_HOLD"],
    },
}


# =============================================================================
# RISK BAND → POLICY MAPPING
# =============================================================================

RISK_BAND_TO_POLICY = {
    "LOW": "LOW_RISK_FAST",
    "MODERATE": "MODERATE_BALANCED",
    "HIGH": "HIGH_RISK_GUARDED",
    "CRITICAL": "CRITICAL_REVIEW",
}


# =============================================================================
# MAIN RECOMMENDATION FUNCTION
# =============================================================================


def recommend_settlement_policy(
    assessment: ShipmentRiskAssessment,
) -> SettlementPolicyRecommendation:
    """
    Generate a settlement policy recommendation from a risk assessment.

    This is the **core mapping function** — glass-box, auditable, explainable.

    Logic:
        1. Determine risk band from score
        2. Look up policy template for that band
        3. Build milestones from template
        4. Generate rationale incorporating top risk factors
        5. Return structured recommendation

    Args:
        assessment: ChainIQ risk assessment for a shipment

    Returns:
        SettlementPolicyRecommendation with all details
    """
    # Step 1: Determine risk band
    band = get_risk_band(assessment.risk_score)
    band_name = band["name"]

    # Step 2: Look up policy template
    policy_code = RISK_BAND_TO_POLICY[band_name]
    template = SETTLEMENT_POLICY_TEMPLATES[policy_code]

    # Step 3: Build milestones
    milestones = _build_milestones(template, band_name, assessment)

    # Step 4: Generate rationale
    rationale = _build_rationale(assessment, band, template)

    # Step 5: Build tags
    tags = list(template["tags"])  # Copy base tags
    tags.append(f"DECISION_{assessment.decision}")

    # Add decision-specific tags
    if assessment.decision in ("HOLD", "ESCALATE"):
        tags.append("REQUIRES_ATTENTION")

    return SettlementPolicyRecommendation(
        shipment_id=assessment.shipment_id,
        recommended_at=datetime.utcnow(),
        risk_score=assessment.risk_score,
        risk_band=band_name,
        decision=assessment.decision,
        recommended_policy_code=policy_code,
        milestones=milestones,
        settlement_delay_hours=template["settlement_delay_hours"],
        hold_percentage=template["hold_percentage"],
        requires_manual_approval=template["requires_manual_approval"],
        rationale=rationale,
        top_factors=assessment.top_factors[:3],  # Include top 3 factors
        tags=tags,
    )


def _build_milestones(
    template: Dict[str, Any],
    band_name: str,
    assessment: ShipmentRiskAssessment,
) -> List[SettlementMilestoneRecommendation]:
    """
    Build milestone recommendations from template.

    Future enhancement: dynamically adjust percentages based on
    specific risk factors (e.g., fraud risk → more in claim window).
    """
    milestones = []

    for name, event_type, percentage, timing_hint in template["milestones"]:
        # Build conditions based on milestone type
        conditions = _get_milestone_conditions(name, band_name, assessment)

        milestones.append(
            SettlementMilestoneRecommendation(
                name=name,
                event_type=event_type,
                percentage=percentage,
                timing_hint=timing_hint,
                conditions=conditions,
            )
        )

    return milestones


def _get_milestone_conditions(
    milestone_name: str,
    band_name: str,
    assessment: ShipmentRiskAssessment,
) -> List[str]:
    """
    Generate human-readable conditions for a milestone.

    These are informational — actual enforcement is in ChainPay.
    """
    conditions = []

    if milestone_name == "PICKUP":
        conditions.append("Bill of Lading issued and verified")
        if band_name in ("HIGH", "CRITICAL"):
            conditions.append("Carrier verification completed")

    elif milestone_name == "DELIVERY":
        conditions.append("Proof of Delivery received")
        if band_name in ("MODERATE", "HIGH", "CRITICAL"):
            conditions.append("No damage reported at delivery")
        if assessment.fraud_risk >= 50:
            conditions.append("Documentation authenticity verified")

    elif milestone_name == "CLAIM_WINDOW":
        conditions.append("Claim window period expired")
        conditions.append("No open claims or disputes")
        if band_name == "CRITICAL":
            conditions.append("Manual finance approval obtained")

    return conditions


def _build_rationale(
    assessment: ShipmentRiskAssessment,
    band: Dict[str, Any],
    template: Dict[str, Any],
) -> str:
    """
    Build a human-readable rationale for the recommendation.

    Format: "Risk score X in BAND band; [key adjustment]; [top factor context]."
    """
    parts = [f"Risk score {assessment.risk_score:.0f} in {band['label']} band"]

    # Explain key adjustments
    hold_pct = template["hold_percentage"]
    if hold_pct >= 40:
        parts.append(f"holding {hold_pct:.0f}% until claim window closes")
    elif hold_pct >= 20:
        parts.append(f"reserving {hold_pct:.0f}% for claim window")

    # Add delay context
    delay = template["settlement_delay_hours"]
    if delay >= 24:
        parts.append(f"{delay:.0f}h settlement delay applied")

    # Add top factor context (if available)
    if assessment.top_factors:
        top_factor = assessment.top_factors[0]
        factor_text = top_factor.human_label[:80]  # Truncate if needed
        parts.append(f"primary factor: {factor_text}")

    # Manual approval note
    if template["requires_manual_approval"]:
        parts.append("manual approval required")

    return "; ".join(parts) + "."


# =============================================================================
# BATCH PROCESSING
# =============================================================================


def recommend_settlement_policies(
    assessments: List[ShipmentRiskAssessment],
) -> List[SettlementPolicyRecommendation]:
    """
    Generate settlement recommendations for multiple assessments.

    Args:
        assessments: List of risk assessments

    Returns:
        List of settlement policy recommendations
    """
    return [recommend_settlement_policy(a) for a in assessments]


# =============================================================================
# POLICY LOOKUP UTILITIES
# =============================================================================


def get_policy_template(policy_code: str) -> Dict[str, Any]:
    """
    Get a policy template by code.

    Args:
        policy_code: Policy code (e.g., "LOW_RISK_FAST")

    Returns:
        Policy template dictionary

    Raises:
        KeyError: If policy code not found
    """
    return SETTLEMENT_POLICY_TEMPLATES[policy_code]


def list_policy_codes() -> List[str]:
    """List all available policy codes."""
    return list(SETTLEMENT_POLICY_TEMPLATES.keys())


def list_risk_bands() -> List[Dict[str, Any]]:
    """List all risk bands with their thresholds."""
    return RISK_BANDS.copy()


# =============================================================================
# VALIDATION
# =============================================================================


def validate_policy_template(template: Dict[str, Any]) -> List[str]:
    """
    Validate a policy template for consistency.

    Checks:
        - Milestone percentages sum to 100
        - Required fields present

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check required fields
    required = ["code", "name", "milestones", "settlement_delay_hours", "requires_manual_approval"]
    for field in required:
        if field not in template:
            errors.append(f"Missing required field: {field}")

    # Check milestone percentages
    if "milestones" in template:
        total_pct = sum(m[2] for m in template["milestones"])
        if abs(total_pct - 100.0) > 0.01:
            errors.append(f"Milestone percentages sum to {total_pct}, expected 100")

    return errors


def validate_all_templates() -> Dict[str, List[str]]:
    """
    Validate all policy templates.

    Returns:
        Dict of policy_code → list of errors (empty if valid)
    """
    results = {}
    for code, template in SETTLEMENT_POLICY_TEMPLATES.items():
        errors = validate_policy_template(template)
        if errors:
            results[code] = errors
    return results
