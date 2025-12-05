# ALEX Governance Rules — AT-02 Accessorial Fraud Engine

## 1. BLUF

This document defines the **ALEX governance rules** for the AT-02 Accessorial Fraud Detection Engine. The rules map model outputs (fraud score, confidence, data quality) to governance actions and ensure that every decision is auditable, reproducible, and regulator-safe.

---

## 2. Key Concepts

- **Fraud Score (p):** Calibrated probability \( p = P(\text{fraud} | x) \).
- **Confidence (c):** 0–1 measure based on ensemble variance and data completeness.
- **Data Completeness Score (d):** 0–1 measure summarizing missing features and signal quality.
- **ALEX Gate:** Governance decision: `pass` or `fail`.
- **Recommended Action:** `approve | hold | deny | review`.

ALEX evaluates both **model outputs** and **contextual rules** (contract terms, legal constraints, ProofPack validation state).

---

## 3. Scoring Tiers & Actions

Baseline tiering based on **fraud_score (p)**:

- **Tier 1: Low Risk (0.0 ≤ p < 0.3)**
  - Default: `approve`
  - ALEX Gate: `pass`
  - Notes: Eligible for auto-approval if **confidence high** and **data completeness adequate**.

- **Tier 2: Medium Risk (0.3 ≤ p < 0.6)**
  - Default: `review`
  - ALEX Gate: `pass` if routed to manual review queue.
  - Notes: Human review recommended; provide full explanations and top features.

- **Tier 3: High Risk (0.6 ≤ p < 0.8)**
  - Default: `hold`
  - ALEX Gate: `fail` unless additional validation supplied.
  - Notes: Requires ALEX governance check and SxT ProofPack verification.

- **Tier 4: Very High Risk (0.8 ≤ p ≤ 1.0)**
  - Default: `deny`
  - ALEX Gate: `fail`
  - Notes: Strong evidence of fraud; accessorial likely rejected pending any override.

These tiers can be **carrier-, lane-, or facility-specific** after sufficient data, but defaults above apply globally at launch.

---

## 4. Confidence & Data Quality Modifiers

ALEX gates are conditioned on **confidence (c)** and **data completeness (d)**.

### 4.1. Confidence Thresholds

- **High confidence:** c ≥ 0.8
- **Medium confidence:** 0.5 ≤ c < 0.8
- **Low confidence:** c < 0.5

### 4.2. Data Completeness Thresholds

- **Good data:** d ≥ 0.8 and `num_critical_features_missing = 0`
- **Degraded data:** 0.5 ≤ d < 0.8 or some non-critical features missing
- **Poor data:** d < 0.5 or any critical feature missing

### 4.3. Governance Adjustments

- If **Tier 1** but **low confidence or poor data**:
  - Recommended Action: downgrade to `review`.
  - ALEX Gate: `pass` only if SxT ProofPack or human reviewer confirms.

- If **Tier 3/4** but **low confidence or poor data**:
  - Recommended Action: `hold` instead of `deny`.
  - ALEX Gate: `fail` until further validation.
  - Rationale: Do not deny on weak evidence; require stronger proof.

---

## 5. ALEX Rule Matrix (Simplified)

Let `p` = fraud_score, `c` = confidence, `d` = data_completeness.

### 5.1. Base Matrix (ignoring modifiers)

| Tier | Range of p        | Recommended | ALEX Gate |
|------|-------------------|------------|-----------|
| 1    | 0.0 ≤ p < 0.3     | approve    | pass      |
| 2    | 0.3 ≤ p < 0.6     | review     | pass      |
| 3    | 0.6 ≤ p < 0.8     | hold       | fail      |
| 4    | 0.8 ≤ p ≤ 1.0     | deny       | fail      |

### 5.2. Modifiers

- If `c < 0.5` or `d < 0.5`:
  - Escalate one action level toward `review/hold`.
- If `p` is very close to boundaries (e.g., within ±0.02 of 0.3, 0.6, 0.8):
  - Mark as **borderline**, require manual review regardless of tier.

---

## 6. ProofPack Integration

ALEX never acts solely on the ML score for high-value or contentious claims.

- **Proof-first principle:**
  - For Tier 3 or 4 claims, ALEX checks SxT ProofPack state:
    - If proof **supports** the claim (e.g., cryptographically verified IoT data, signed documents), ALEX may downgrade the recommended action.
    - If proof **contradicts** the claim, ALEX may auto-deny.

- **Signals consumed from ProofPack:**
  - Integrity of IoT streams (no tampering, signatures valid).
  - Document integrity (hash matches, no post-fact changes outside allowed workflow).
  - Time-sync / chronology checks.

---

## 7. Override & Auditability

- **Override Rules:**
  - Human reviewers can override `deny` or `hold` decisions.
  - Override requires:
    - Reason code (from a predefined set).
    - Free-text explanation.
    - User identity and timestamp.

- **Audit Log Contents:**
  - Original Fraud Assessment Object.
  - ALEX tier and decision.
  - Any ProofPack checks and results.
  - Any human overrides, including before/after states.

---

## 8. Fairness & Bias Controls

- ALEX must ensure that AT-02 does not unfairly penalize:
  - Specific carriers without evidence.
  - Particular regions, facility types, or shipment modes.

Controls:
- Periodic fairness audits on model outputs segmented by carrier tier, geography, mode.
- Alert if a carrier’s average fraud_score drifts significantly without corresponding behavior change.
- Governance rule: **no hard-coded per-carrier penalties**; all differences must arise from data and be justifiable.

---

## 9. Deployment & Versioning

- Each deployed model version has:
  - `model_version_id`
  - Training data period
  - Feature schema version
  - Calibration report
  - Governance approval record (ALEX decision ID)

- ALEX will **block**:
  - Any model without completed calibration.
  - Any model failing monotonicity checks on key features.
  - Any model with degraded performance < governance thresholds on validation.

---

## 10. Regulator-Safe Summary (For CFO / Legal)

- AT-02 assigns each accessorial a **fraud risk probability** and **confidence**.
- ALEX uses clear, documented **thresholds** to decide whether to approve, hold, deny, or review.
- All decisions are:
  - **Traceable** (who/what decided and when)
  - **Explainable** (why, based on which features)
  - **Reproducible** (same inputs → same outputs)
- No purely black-box logic is used; every output is backed by:
  - Documented model architecture
  - Measurable performance
  - Governance sign-off.
