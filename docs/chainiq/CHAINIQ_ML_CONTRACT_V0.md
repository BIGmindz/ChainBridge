# ChainIQ ML Strategy & Model Contract – v0.1

This document defines the compact specification for implementing ML models in ChainIQ. It serves as the contract between model developers (Maggie) and system integrators (Cody/Sonny) for risk and anomaly scoring.

## 1. Inputs

All ML models consume **shipment-level feature vectors** in the shape of `ShipmentFeaturesV0`.

**Feature categories included:**

- **Identifiers & corridor context:** Shipment ID, corridor, origin/destination, mode, commodity, financing type, counterparty risk tier
- **Operational/transit features:** Planned vs. actual transit, ETA deviation, route deviations, dwell times, handoffs, delay flags
- **IoT/temperature features:** Temperature violations, excursion severity, monitoring gaps
- **Documentation & collateral features:** Missing/incomplete docs, discrepancy severity, collateral adequacy
- **Historical performance features:** Shipper prior loss flags, corridor default rates, recent exception counts
- **Sentiment features:** Macro/corridor/counterparty sentiment scores, stability metrics, trade friction

Models should treat features as pre-normalized and ready for inference. Feature engineering happens upstream in `FeatureBuilder`.

## 2. Risk Score Model Contract

**Conceptual function signature (pseudo-code):**

```text
risk_predict(
  features: ShipmentFeaturesV0
) -> {
  score: float,                        # 0.0 to 1.0, higher = higher risk
  contributions: FeatureContribution[],  # feature-level attributions
  model_version: str
}
```

**Semantics:**

- **Score:** Monotonic proxy for "risk of bad economic outcome" (loss/default/major exception).
  - `0.0` = negligible risk (baseline corridor performance)
  - `1.0` = extreme risk (near-certain loss or severe issue)

**Calibration expectations:**

- Scores should approximate probabilities where feasible (e.g., a score of 0.30 implies ~30% historical loss rate for similar shipments).
- Calibration will be validated in v0.2 with reliability diagrams.

**Contributions:**

- Each `FeatureContribution` highlights a feature pushing risk up or down.
- Minimum 3 contributions, prioritized by magnitude of impact.
- Explanations must be business-readable (e.g., "Shipment is 6 hours delayed" not "feature_23 = 1.4").

## 3. Anomaly Model Contract

**Conceptual function signature (pseudo-code):**

```text
anomaly_predict(
  features: ShipmentFeaturesV0
) -> {
  score: float,                        # 0.0 to 1.0, higher = more anomalous
  contributions: FeatureContribution[],
  model_version: str
}
```

**Semantics:**

- **Score:** Rarity of this feature vector vs. normal corridor patterns.
  - `0.0` = typical shipment (within historical norms)
  - `1.0` = extreme outlier (unprecedented feature combination)

**Not always equal to risk:**

- Some anomalies are benign (e.g., unusually fast delivery).
- Anomaly detection flags **unusual**, risk scoring flags **dangerous**.
- Both signals may be used together (high anomaly + high risk = urgent investigation).

**Contributions:**

- Identify which features make this shipment unusual.
- Example: "Dwell time is 3σ above corridor average."

## 4. Model Families & Preference

**For risk models impacting money/credit:**

Prefer **interpretable families:**

- **Logistic regression** with engineered features (interactions, splines)
- **GAMs / EBMs-like behavior:** Piecewise monotonic functions, additive structure
- **Tree ensembles with constraints:** Shallow depth, monotonicity constraints on key features

Avoid:

- Deep neural networks as final scorers (acceptable as feature generators upstream)
- Uninterpretable ensemble stacking without SHAP-like explainability

**For anomaly detection:**

More flexibility allowed:

- Distance-based (Isolation Forest, Mahalanobis distance)
- Density-based (KDE, LOF)
- Autoencoder-like (reconstruction error)

However, final anomaly scores must still pass through a **glass-box layer** that produces interpretable contributions.

## 5. Versioning & Deployment

**Model Identity:**

- Every model has:
  - **Model ID:** Short name (e.g., `risk_glassbox`, `anomaly_density`)
  - **Version:** Semantic versioning (e.g., `v1.0.0`, `v1.1.0`)
  - Example full identifier: `risk_glassbox_v1.0.0`

**Endpoints always return `model_version`** in responses, enabling:

- A/B testing (route 10% of traffic to new model)
- Debugging (trace bad predictions to specific model versions)
- Rollback (revert to prior version if new model underperforms)

**Rollout strategy:**

1. **Shadow mode:** New model logs predictions but doesn't influence decisions. Compare metrics vs. active model.
2. **A/B test:** Route small % of traffic to new model, monitor KPIs (loss rate, alert precision, etc.).
3. **Full rollout:** Promote new model to 100% traffic only after documented improvement.
4. **Rollback capability:** Maintain prior model artifacts for instant reversion if issues arise.

## 6. Logging & Monitoring Expectations

**For every inference, log:**

- **Identifiers:** Shipment ID, corridor
- **Model metadata:** Model ID, version, timestamp
- **Prediction:** Score, top 5 feature contributions
- **Context:** Financing type, counterparty risk tier (for stratified analysis)

**Monitoring dashboards should track:**

- **Score distributions over time:** Detect drift (e.g., sudden spike in high-risk scores)
- **Feature drift:** Monitor input feature distributions vs. training set
- **Outcome tracking:** Join predictions with realized outcomes (did predicted high-risk shipments actually incur losses?)
- **Calibration:** Periodic checks that predicted probabilities match empirical frequencies

**Alerting:**

- Trigger alerts if:
  - Score distribution shifts >20% in 7 days
  - Model returns errors/NaNs
  - Inference latency exceeds SLA (e.g., >500ms p99)

---

**This contract is the bridge between ML research and production integration.** Models that conform to this spec can be hot-swapped into `api_iq_ml.py` without changes to downstream consumers (ChainPay, ChainAudit, IQ Lab UI).
