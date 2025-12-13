# ChainIQ Lab Charter – v0.1

ChainIQ is the **risk & intelligence layer** of ChainBridge. It transforms events from shipments, IoT sensors, documentation, and market sentiment into actionable **risk and anomaly insights**. ChainIQ operates as a **Lab**: experiments, models, and signals evolve carefully under governance, explainability, and commercial discipline. This charter defines how ML is allowed to behave within the ChainBridge ecosystem.

## 1. Role of ML in ChainBridge

- **ML produces scores and explanations, not raw decisions.**
  ML outputs feed downstream systems but never directly trigger financial actions.

- **Primary consumers of ML signals:**
  - **ChainAudit** → Controls, policies, and compliance rules
  - **ChainPay** → Pricing, credit limits, payment gating
  - **Operator Console (OC) / IQ Lab** → Visibility, debugging, human oversight

- **ML is one input among many.**
  Decisions incorporate rules, legal constraints, market conditions, and human judgment. No model operates in isolation.

## 2. Glass-Box Principle

For any decision affecting **money movement or credit extension**, the final scoring mechanism must be glass-box (interpretable).

**Requirements for each prediction:**

- **Score:** A value in `[0, 1]` with clearly defined semantics (e.g., probability-of-loss proxy).
- **Feature contributions:** Which features drive the score up or down, with explanations.
- **Model identifier and version:** Traceable to training data and methodology.

**Complex models (e.g., deep neural networks) are allowed:**

- As **feature generators** or upstream predictors.
- **Not** as the final unexplained decision mechanism for risk/credit scoring.

Rationale: Financial regulators, auditors, and customers require explanations. Black-box models create unacceptable liability.

## 3. Core Model Types

ChainIQ defines two initial model families:

### Risk Score Model

- **Input:** `ShipmentFeaturesV0` (shipment-level feature vector)
- **Output:** `RiskScoreResponse` (score + explanation + model_version)
- **Semantics:** Risk of loss, default, or severe bad outcome for this shipment/financing arrangement
- **Use case:** ChainPay pricing, ChainAudit gating, credit limit adjustment

### Anomaly Detector

- **Input:** `ShipmentFeaturesV0`
- **Output:** `AnomalyScoreResponse` (score + explanation + model_version)
- **Semantics:** "How unusual" this shipment is compared to historical corridor patterns
- **Use case:** Early warning system, fraud detection, operational exception alerts

### Future Model Types (acknowledgment only, no implementation yet)

- **Portfolio risk aggregation:** Aggregate risk across active shipments/loans
- **Control suggestion models:** Propose new ChainAudit rules based on emerging patterns
- **Early warning models:** Corridor stress, counterparty drift, macro sentiment shifts

## 4. Governance & Safety

Every model deployed in ChainIQ must satisfy:

**Model Identity:**

- Unique ID (short name, e.g., `risk_ebm`, `anomaly_density`)
- Semantic version (e.g., `risk_ebm_v1.0.0`)
- Documented training dataset window and label definition

**Pre-Deployment Requirements:**

- Offline evaluation against clear metrics (AUC, calibration, precision@recall)
- Sanity checks (no obviously insane outputs on holdout data)
- Rollback capability (ability to revert to previous model version)

**Integration Requirements:**

- ChainPay/ChainAudit **never** directly threshold a model score without:
  - Documented rationale for the threshold
  - Human review and sign-off
  - Comprehensive logging of all decisions influenced by the threshold

- All model inferences logged with:
  - Shipment ID, corridor, model ID/version, score, timestamp
  - Top feature contributions

## 5. Data & Labels

**Canonical Features:**

- `ShipmentFeaturesV0` is the v0.1 feature schema (see `CHAINIQ_FEATURES_V0.md`).
- Features span: identifiers, operational/transit metrics, IoT/temperature data, documentation completeness, historical performance, and sentiment.

**Training Labels:**

- Labels must derive from **real business outcomes:**
  - `realized_loss_flag`: Did this shipment result in financial loss?
  - `loss_amount`: Magnitude of loss (USD)
  - `fraud_confirmed`: Was fraud confirmed by investigation?
  - `severe_exception`: Major delay, loss, or regulatory violation

- **Labels must map to business reality.**
  Avoid "vibes-only" labels (e.g., subjective risk ratings without outcome data).

- **Label definitions must be documented** for each model:
  - Time window (e.g., "90 days post-delivery")
  - Criteria (e.g., "loss > $5k" or "fraud confirmed by compliance team")

## 6. Roadmap v0.1 → v1

**v0.1 (current PAC):**

- Charter and strategy documentation
- Python ML interfaces (`BaseRiskModel`, `BaseAnomalyModel`)
- Stub endpoints live via Cody's work in `api_iq_ml.py`

**v0.2 (next phase):**

- Offline baseline models (logistic regression, GAM-like)
- Evaluation notebooks (AUC, calibration plots, feature importance)
- Historical label generation pipeline

**v0.3 (production readiness):**

- First live model deployed behind existing endpoints
- Shadow mode deployment (log predictions but don't act on them)
- Metrics dashboards and monitoring
- Careful rollout with A/B comparison vs. stub logic

---

**This charter is a living document.** As ChainIQ evolves, governance and safety practices will tighten, but the core principles—explainability, commercial sanity, and no unexamined black boxes—remain non-negotiable.
