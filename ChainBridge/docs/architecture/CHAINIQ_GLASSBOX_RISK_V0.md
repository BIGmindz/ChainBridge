# ChainIQ Glass-Box Risk Model v0

## 1. BLUF (Bottom Line Up Front)
*   **What:** A deterministic, rule-based risk scoring engine for shipments (0–100 score, LOW/MEDIUM/HIGH bands).
*   **Why:** Provides immediate "glass-box" interpretability for auditors and ops, replacing opaque or ad-hoc logic.
*   **Audit:** Outputs a structured explanation payload that maps 1:1 to the `DecisionLog` and `ProofPack` specifications, ensuring every score is traceable to specific rules.

## 2. Commercial ROI
*   **Risk Segmentation:** Instantly segments shipments into risk tiers, allowing automated processing for LOW risk and focused manual review for HIGH risk.
*   **Operational Efficiency:** Reduces false positives by using clear, weighted rules rather than black-box guesses.
*   **Audit Readiness:** Every decision comes with a "why," making it trivial to satisfy external auditors or internal compliance checks.

## 3. Glass-Box Model Architecture

### Inputs
The model accepts a standard shipment dictionary and a context dictionary:
*   **Shipment:** `origin_country`, `destination_country`, `amount` (value), `currency`.
*   **Context:** Historical flags like `has_disputes`, `has_late_deliveries`, `customer_tier`.

### Features
*   **Lane Risk:** Derived from origin/destination (e.g., High Risk Regions vs. Safe Zones).
*   **Amount Band:** SMALL (<10k), MEDIUM (<100k), LARGE (>=100k).
*   **History:** Penalties for past bad behavior (disputes, lateness).

### Scoring Logic (Weighted Additive)
1.  **Base Score:** 0.
2.  **Adders:**
    *   Lane Risk: +0 (Low), +15 (Medium), +30 (High).
    *   Amount: +0 (Small), +10 (Medium), +20 (Large).
    *   History: +20 (Disputes), +10 (Late Deliveries).
3.  **Clamp:** Score is clamped to [0, 100].
4.  **Band:**
    *   LOW: < 35
    *   MEDIUM: 35–69
    *   HIGH: >= 70

## 4. Model I/O Contract

```python
def score_shipment_risk(shipment: dict, context: dict) -> dict:
    """
    Returns:
        {
          "risk_score": int,            # 0–100
          "risk_band": str,            # "LOW" | "MEDIUM" | "HIGH"
          "input_snapshot": dict,      # compact view of inputs used
          "rules_fired": list[dict],   # rule_id, description, contribution
          "explanation": dict,         # free-form but structured explanation
        }
    """
```

## 5. Alignment with Audit & ProofPack Spec

This model is designed to populate the `DecisionLog` directly:

| Model Output | DecisionLog Field | ProofPack Component |
| :--- | :--- | :--- |
| `input_snapshot` | `input_snapshot` | `Evidence` (Inputs) |
| `rules_fired` | `rules_fired` | `Logic` (Trace) |
| `explanation` | `explanation` | `Reasoning` (Human-readable) |
| `risk_score` | `result.score` | `Outcome` |
| `risk_band` | `result.band` | `Outcome` |

*Note: `risk_policy_version` and `model_version` are managed by the calling service to ensure version control integrity.*

## 6. Risks & Mitigations

*   **Risk:** v0 is simple and may underfit complex fraud patterns.
    *   **Mitigation:** The interface is designed to be "model-agnostic." We can swap in a v1 ML model later without changing the API contract or audit logs.
*   **Risk:** Static weights may need tuning.
    *   **Mitigation:** Weights are defined in a clear configuration block at the top of the module, allowing for rapid iteration and versioning.
*   **Risk:** Missing data (e.g., unknown lane).
    *   **Mitigation:** Safe defaults (e.g., treat unknown lanes as MEDIUM risk) prevent system failures while flagging potential issues.
