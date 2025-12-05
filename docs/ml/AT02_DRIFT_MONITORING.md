# AT-02 Drift & Monitoring Plan

## 1. BLUF

This document specifies how to **monitor and manage drift** for the AT-02 Accessorial Fraud Detection Engine. It covers data drift, concept drift, feature aging, seasonality, and carrier behavior shifts to ensure the model remains reliable in production.

---

## 2. Objectives

- Detect when **input distributions** change (data drift).
- Detect when **label relationships** change (concept drift).
- Track **feature aging** and seasonal patterns.
- Trigger **retraining, recalibration, or governance review** when thresholds are crossed.

---

## 3. Data Drift Monitoring

### 3.1. Monitored Variables

- Key continuous features (examples):
  - `claimed_vs_contract_ratio`
  - `dwell_duration_delta_minutes`
  - `carrier_accessorial_frequency_30d`
  - `iot_message_dropout_rate`
  - `detention_window_alignment_score`

- Key categorical / enum features:
  - `accessorial_type`
  - `accessorial_reason_code`
  - `carrier_credit_tier`
  - `lane_type`

### 3.2. Techniques

- **Univariate drift:**
  - KS-test, PSI (Population Stability Index), or similar.
- **Multivariate drift:**
  - Embedding-based checks (optional later) or clustering distance.

### 3.3. Thresholds

- PSI > 0.2 on a key feature → **warning**.
- PSI > 0.3 on a key feature or several features concurrently → **critical**, trigger review.

---

## 4. Concept Drift Monitoring

### 4.1. Performance Metrics

On a rolling, labeled dataset (e.g., resolved disputes):
- AUC-ROC, AUC-PR.
- Calibration (Brier score, reliability plots).
- Confusion metrics at governance thresholds (0.3, 0.6, 0.8).

### 4.2. Drift Detection Methods

- **Prequential evaluation** on streaming labels when available.
- **Statistical tests** on metric time series:
  - CUSUM / Page-Hinkley tests to catch sudden shifts.

### 4.3. Triggers

- AUC drop > X (e.g., 0.05) vs. baseline over last N days.
- Calibration error increase beyond governance threshold.
- Sustained discrepancy between model outputs and ALEX/human decisions.

---

## 5. Feature Aging & Seasonality

- Track the **time since last retrain** and **time since last calibration**.
- Monitor seasonal effects:
  - Accessorial patterns during peak seasons (e.g., holidays) vs. off-peak.
  - Distinguish **genuine seasonal shifts** from permanent drift.

Approach:
- Maintain **seasonal baselines** (e.g., last year same month) for key features and fraud_score distributions.
- Compare current month vs. historical seasonal baseline.

---

## 6. Carrier & Facility Behavior Changes

### 6.1. Carrier-Level Drift

- Monitor per-carrier metrics:
  - Average fraud_score.
  - Average recommended_action distribution.
  - Dispute rate and outcome rates.

Triggers:
- Sudden jump in average fraud_score for a carrier.
- Divergence between model-assigned risk and actual dispute outcomes.

### 6.2. Facility-Level Drift

- Monitor facility dwell norms and accessorial frequencies.
- Alert if a facility becomes an outlier vs. peers.

---

## 7. Alerts & Governance Workflow

- All drift signals publish into a **Model Monitoring Dashboard**.
- ALEX subscribes to alerts:
  - **Warning:** Log and recommend closer manual review.
  - **Critical:**
    - Freeze new deployments.
    - Optionally tighten thresholds (e.g., more `review`/`hold`).
    - Require a **governance review meeting** for AT-02.

---

## 8. Retraining & Recalibration Policy

- **Regular cadence:** e.g., quarterly retrain + monthly calibration refresh.
- **Triggered retrain:**
  - Critical drift alerts.
  - Major contract or process changes.

Policy:
- New model version must:
  - Pass all unit/integration tests.
  - Meet or exceed baseline metrics.
  - Pass monotonicity and fairness checks.
  - Be approved by ALEX with recorded decision.

---

## 9. Logging for Forensics

For every inference, log:
- Input feature snapshot (or hashed representation where required).
- Fraud_score, confidence, recommended_action, alex_gate.
- Model and schema versions.

This enables **post-hoc analysis** when drift or incidents are detected.

---

## 10. Summary

This monitoring plan ensures AT-02 remains:
- Stable under normal operating conditions.
- Sensitive to real behavioral changes.
- Protected against silent degradation.

Drift signals directly feed into ALEX governance and Maggie’s retraining workflows to keep the system aligned with ChainBridge’s risk doctrine.
