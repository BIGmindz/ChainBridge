# AT-02 Accessorial Fraud Detection — Model Architecture

## 1. BLUF

AT-02 is a **glass-box, token-aware fraud scoring engine** that estimates

$$ P(\text{fraud} \mid x) $$

for a given accessorial claim, along with calibrated confidence and full feature-level explanations. The core model family is **monotonic gradient-boosted decision trees / GAM-style models**, with SHAP-based explanations and counterfactual analysis to determine minimal changes needed to flip a decision.

The engine is designed to be:
- **Regulator-safe:** fully explainable and auditable
- **Governance-ready:** aligned with ALEX gates and SxT ProofPack
- **Adversarial-hardened:** tested against GPS spoofing, backfilled claims, and batch inflation.

---

## 2. Problem Formulation

- **Input:** Feature vector \( x \) from `AT02_FEATURE_SCHEMA.md`
- **Output:** Fraud Assessment Object

```json
{
  "fraud_score": float,           // P(fraud | x), calibrated
  "confidence": float,            // 0–1, based on uncertainty & data quality
  "reason": "str",               // dominant explanation (human readable)
  "dominant_features": ["..."],  // top-K contributing features
  "counterfactual": {"feature": "value", "delta": ...},
  "recommended_action": "approve|hold|deny|review",
  "alex_gate": "pass|fail"
}
```

The fraud score is a **probability-like risk score**, calibrated against historical labels and governance thresholds.

---

## 3. Model Family & Justification

### 3.1. Primary Model: Monotonic Gradient Boosted Trees (LightGBM / XGBoost variant)

- **Type:** Gradient Boosted Decision Trees (GBDT) with **monotonic constraints** on key features.
- **Why:**
  - Handles mixed feature types and complex, non-linear interactions.
  - Monotonicity enforces intuitive, regulator-friendly behavior (e.g., higher `claimed_vs_contract_ratio` should not *reduce* fraud risk).
  - Tree-based SHAP values are well-established and efficient.
  - Supports partial dependence and feature-attribution visualization.

### 3.2. Secondary Model: Generalized Additive Model (GAM) for Governance Layer

- **Type:** Interpretable GAM (e.g., `pygam`, `Explainable Boosting Machines`).
- **Role:**
  - Cross-check the primary model via a simpler, more transparent scoring function.
  - Provides smooth, per-feature curves to present to auditors/regulators.
  - Used in ALEX governance checks for monotonicity and fairness.

### 3.3. Ensemble & Uncertainty

- **Approach:**
  - Train an **ensemble of K GBDT models** with different seeds / bootstrap samples.
  - Compute mean fraud score \( \hat{p} \) and ensemble variance \( \sigma^2 \).
  - Derive **confidence** as a function of variance and data completeness:

    $$
    \text{confidence} = 1 - \alpha \cdot \sigma - \beta \cdot (1 - \text{data\_completeness})
    $$

  - This yields high confidence when models agree and data is complete.

---

## 4. Training Data & Labels

### 4.1. Labels

- **Positive class (fraud = 1):**
  - Accessorials later reversed due to dispute.
  - Accessorials flagged by auditors as invalid.
  - Accessorials failing SxT ProofPack verification.

- **Negative class (fraud = 0):**
  - Accessorials accepted without dispute.
  - Accessorials where IoT + docs strongly support the claim.

- **Ambiguous cases:**
  - Initially excluded from supervised training or treated using **weak labels** with lower weights.

### 4.2. Sampling Strategy

- Class imbalance likely (fraud << non-fraud).
- Techniques:
  - Class weights in loss function.
  - Focal loss variant (emphasize hard positives/negatives).
  - Time-aware splits (avoid leakage by ensuring training data precedes validation window).

---

## 5. Core Pipeline

1. **Ingestion:**
   - Collect MT-01, AT-02, IT-01, CCT-01, IoT streams, document metadata.
2. **Feature Builder:**
   - Compute features per `AT02_FEATURE_SCHEMA.md`.
   - Enforce deterministic, versioned transformations.
3. **Model Scorer (GBDT Ensemble):**
   - Compute \( \hat{p}_k = P_k(\text{fraud} | x) \) for each model \(k\).
   - Aggregate: \( \hat{p} = \frac{1}{K} \sum_k \hat{p}_k \).
   - Compute ensemble variance \( \sigma^2 \) and confidence.
4. **Explainability Layer:**
   - Compute SHAP values per model, aggregate top-K.
   - Map feature contributions to human-readable reasons.
5. **Governance Layer (ALEX):**
   - Apply score thresholds and governance rules.
   - Compare GBDT outputs with GAM outputs for consistency.
6. **Output Construction:**
   - Populate Fraud Assessment Object.
   - Emit decision and explanations to ChainIQ and SxT ProofPack.

---

## 6. Loss Function & Calibration

### 6.1. Loss Function

- **Base loss:** Weighted binary cross-entropy:

$$
\mathcal{L} = - w_1 y \log(p) - w_0 (1-y) \log(1-p)
$$

- **Optional:** Focal loss to emphasize misclassified examples:

$$
\mathcal{L}_{\text{focal}} = - (1-p)^\gamma w_1 y \log(p) - p^\gamma w_0 (1-y) \log(1-p)
$$

with \(\gamma \in [1, 2]\).

### 6.2. Calibration

- Use **Platt scaling** or **isotonic regression** on a held-out calibration set.
- Governance requirement: predicted fraud probabilities must be **well-calibrated** by deciles.

---

## 7. Monotonicity Constraints

Key features with monotonic constraints (examples):

- **Monotonic increasing (↑ feature → ↑ fraud risk):**
  - `claimed_vs_contract_ratio`
  - `dwell_duration_delta_minutes` (claim > observed)
  - `carrier_dispute_rate_90d`
  - `carrier_dispute_loss_rate_90d`
  - `carrier_accessorial_frequency_30d`
  - `iot_message_dropout_rate`
  - `device_reboot_count_in_window`
  - `device_location_jumps_over_threshold_count`
  - `time_sync_discrepancy_seconds`
  - `batch_claim_amount_concentration_ratio`

- **Monotonic decreasing (↑ feature → ↓ fraud risk):**
  - `detention_window_alignment_score`
  - `gps_signal_quality_score`
  - `data_completeness_score`
  - `signature_match_score`

Features not obviously monotonic remain unconstrained but are monitored.

---

## 8. Explainability & Reason Codes

### 8.1. SHAP-based Explanations

- For each prediction, compute SHAP values \( \phi_i \) for features.
- Rank features by |\(\phi_i\)| and select top-K (e.g., K=5).
- Map features to **reason templates**:
  - Example: `claimed_vs_contract_ratio` high → "Claimed amount is X% above contractual norm."
  - Example: `dwell_duration_delta_minutes` high → "Claimed detention exceeds IoT-observed dwell by Y minutes."

### 8.2. Reason Field

- `reason` is a short, human-readable summary based on the top 1–2 features.
- Example:
  - "High claimed-vs-contract ratio and poor IoT alignment with detention window."

### 8.3. Dominant Features

- `dominant_features` is a list of feature names/IDs driving the decision.
- Used by ChainIQ, SxT ProofPack, and auditors.

---

## 9. Counterfactual Explanations

### 9.1. Definition

- Find minimal change \( \Delta x \) such that fraud score falls below a governance threshold (e.g., from 0.85 → <0.6).

### 9.2. Constraints

- Only allow changes to features that are **actionable** or **disputable**, e.g.:
  - Claimed detention duration
  - Accessorial amount
  - Reason code (within allowed mapping, e.g., clerical correction)
- Do **not** propose changes to immutable or factual IoT readings.

### 9.3. Implementation Sketch

- Use a local search over candidate features, guided by SHAP values.
- For each candidate feature:
  - Perturb within realistic bounds and recompute fraud score.
  - Track minimal \( \Delta x \) meeting governance thresholds.
- Store as:

```json
"counterfactual": {
  "feature": "claimed_amount_usd",
  "from": 850.0,
  "to": 400.0,
  "delta": -450.0,
  "note": "Reducing claimed amount to align with contract and IoT dwell would drop fraud risk below 0.6."
}
```

---

## 10. Model Governance Hooks (ALEX)

- **Versioning:**
  - Each trained model has `model_version_id`, training data snapshot ID, feature schema version.
- **Lineage:**
  - Training code, hyperparameters, and evaluation metrics stored.
- **Checks:**
  - Monotonic constraint validation on holdout data.
  - Bias/fairness checks across carrier tiers, modes, facilities.
  - Performance decay monitored over time (via `AT02_DRIFT_MONITORING.md`).

ALEX can enforce policies such as:
- "No deployment if AUC < threshold on latest validation."
- "No deployment if monotonicity violations exceed epsilon."

---

## 11. Adversarial Threat Model (High-Level)

- **GPS falsification / spoofing** → affects dwell and alignment features.
- **Timestamp manipulation** → skews claim windows and entry lags.
- **Batch accessorial inflation** → visible via batch concentration and spike z-scores.
- **Device tampering** (reboots, dropouts) → captured in tamper features.
- **Document forgery** → reflected in `signature_match_score`, `doc_edit_history_length`, `doc_ocr_confidence_score`.

The model architecture explicitly surfaces these variables to:
- Expose anomalies as top features.
- Feed into SxT ProofPack for cryptographic or independent validation.

---

## 12. Implementation Phases

1. **Phase 1 (This PAC):**
   - Finalize schema, architecture, governance thresholds.
   - Implement offline training pipeline and evaluation.
2. **Phase 2:**
   - Integrate with ChainIQ, SxT ProofPack, AT-02 mint/burn workflows.
   - Extend to IT-01, MT-01, CCT-01 dependencies (`AT02_PHASE2_DEPENDENCIES.md`).
3. **Phase 3:**
   - Continuous learning with feedback from disputes and ALEX decisions.
   - Advanced adversarial robustness techniques (e.g., certified bounds for specific features).
