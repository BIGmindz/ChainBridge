# AT-02 Phase 2 Dependencies — IT-01, MT-01, CCT-01

## 1. BLUF

This document outlines how the AT-02 Accessorial Fraud Engine (Phase 1) evolves into a **Phase 2 multi-token intelligence layer** connected to:
- **IT-01** (Invoice Deviation Model)
- **MT-01** (ETA & Movement Model)
- **CCT-01** (Carrier Creditworthiness Model)

The goal is to turn AT-02 from an isolated fraud detector into a **coherent component of ChainIQ’s tokenized risk fabric**.

---

## 2. IT-01 Invoice Deviation Model

### 2.1. Dependency on AT-02

- IT-01 will consume AT-02 outputs as **features**:
  - `at02_fraud_score`
  - `at02_confidence`
  - `at02_recommended_action`
  - Counts and amounts of high-risk accessorials on an invoice.

- Rationale:
  - Invoices with many AT-02-high-risk accessorials are more likely to be globally mispriced.

### 2.2. Joint Signals

- IT-01 combines:
  - Base linehaul pricing models.
  - Accessorial risk aggregates from AT-02.
  - Historical invoice dispute and adjustment behavior.

- Examples of joint features:
  - `num_high_risk_accessorials`.
  - `sum_high_risk_accessorial_amount_usd`.
  - `max_at02_fraud_score_on_invoice`.

---

## 3. MT-01 ETA & Movement Models

### 3.1. Mutual Dependencies

- MT-01 provides:
  - Ground-truth dwell, ETA deviations, and route anomalies used in AT-02.
- AT-02 provides:
  - Feedback on where claimed detention/layover does **not** match MT-01’s movement realities.

### 3.2. Shared Feature Store

- A shared **movement feature store** allows both:
  - MT-01 (predictive ETA, route reliability).
  - AT-02 (retrospective accessorial validation).

- Benefits:
  - Consistent treatment of IoT and timeline data.
  - Easier debugging and governance.

---

## 4. CCT-01 Carrier Creditworthiness

### 4.1. Using AT-02 as Behavioral Signal

- CCT-01 incorporates AT-02-derived carrier behavior stats:
  - `carrier_avg_at02_fraud_score_90d`.
  - `carrier_high_risk_accessorial_rate_90d`.
  - `dispute_outcome_adjusted_risk`.

- Rationale:
  - Carriers with consistently inflated/invalid accessorial patterns should see **credit limits and terms adjusted**.

### 4.2. Governance

- ALEX must ensure **gradual** and **fair** adjustments:
  - No abrupt credit cliff just from one model.
  - Rolling averages and confidence bands.

---

## 5. Event Flows Across Tokens

1. **Shipment Execution (MT-01):**
   - Movement token records planned vs. actual movements.
   - IoT streams attached.

2. **Accessorial Claim (AT-02):**
   - Accessorial token minted and evaluated.
   - Fraud Assessment produced.

3. **Invoice Generation (IT-01):**
   - Invoice token aggregates linehaul + accessorials.
   - IT-01 uses AT-02 outputs and base rate models.

4. **Carrier Credit Update (CCT-01):**
   - Carrier token updated using IT-01 & AT-02 outcomes.

---

## 6. Phase 2 Roadmap

- **Step 1:**
  - Stabilize AT-02 in production with drift monitoring.

- **Step 2:**
  - Define IT-01 feature schema with explicit dependencies on AT-02 outputs.

- **Step 3:**
  - Extend MT-01 models to expose real-time anomaly and dwell features to AT-02.

- **Step 4:**
  - Implement CCT-01 with AT-02 & IT-01 aggregated behavior metrics.

- **Step 5:**
  - Build cross-token dashboards for ChainBoard to display:
    - Per-carrier integrated risk and financial impact.

---

## 7. Governance & Audit

- Each token-linked model (AT-02, IT-01, MT-01, CCT-01) must:
  - Document its dependencies on others.
  - Expose how upstream model changes affect downstream risk.

- ALEX enforces:
  - No hidden circular reasoning (e.g., AT-02 using CCT-01 which heavily uses AT-02 again).
  - Clear lineage and causal ordering in token graph.
