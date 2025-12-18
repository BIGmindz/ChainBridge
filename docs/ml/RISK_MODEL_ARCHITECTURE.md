# Glass-Box Risk Model Architecture

> **Author**: 🟣 MAGGIE (GID-10) — Machine Learning & Applied AI Lead
> **PAC**: PAC-MAGGIE-RISK-SIGNALS-01
> **Status**: SPEC (Design Only — No Training)
> **Created**: 2025-12-17

---

## 1. BLUF

This document specifies a **glass-box model architecture** for computing governance risk signals. The architecture uses:

- **Explainable Boosting Machines (EBMs)** as the canonical model family
- **Monotonic constraints** on all risk-relevant features
- **Calibrated probability outputs** with confidence intervals
- **Full feature-level explainability** for every prediction

No black-box models. No deep learning. No opacity.

---

## 2. Commercial ROI

| Benefit | Impact |
|---------|--------|
| **Audit Readiness** | Risk scores are fully explainable to regulators |
| **Underwriting Support** | Quantified agent risk enables better trust decisions |
| **Operational Efficiency** | Prioritize human review based on risk |
| **Reduced False Positives** | Calibrated scores reduce alert fatigue |
| **Zero Black-Box Debt** | No future liability from unexplainable decisions |

**ROI Timeline**:
- Phase 1 (Signals): Immediate operational value
- Phase 2 (Integration): 6-12 months to full deployment
- Phase 3 (Feedback): Continuous calibration improvement

---

## 3. Model Family Selection

### 3.1. Primary: Explainable Boosting Machine (EBM)

**What**: EBMs are Generalized Additive Models with automatic interaction detection. They produce:

$$
g(\mathbb{E}[y]) = \beta_0 + \sum_j f_j(x_j) + \sum_{i,j} f_{ij}(x_i, x_j)
$$

Where:
- $f_j(x_j)$ are univariate shape functions (one per feature)
- $f_{ij}(x_i, x_j)$ are pairwise interaction terms (automatically detected)

**Why EBMs**:
1. **Interpretable by design**: Each feature's contribution is visualizable
2. **Monotonic constraints**: Can enforce ↑ feature → ↑ risk
3. **Calibrated outputs**: Probability estimates, not just rankings
4. **Interaction detection**: Captures important pairwise effects
5. **Battle-tested**: InterpretML library, Microsoft-backed

**Why NOT alternatives**:

| Alternative | Rejection Reason |
|-------------|------------------|
| Deep Neural Networks | Black-box, not explainable |
| Random Forests | Feature importance ≠ contribution direction |
| XGBoost (unconstrained) | Non-monotonic splits obscure reasoning |
| Linear Regression | Cannot capture non-linear patterns |
| Rule Lists | Too brittle for continuous features |

### 3.2. Secondary: Constrained GAM Checkpoint

For governance-critical applications, a secondary **pure GAM** (no interactions) provides a simpler cross-check:

$$
g(\mathbb{E}[y]) = \beta_0 + \sum_j f_j(x_j)
$$

This simpler model serves as a "sanity check" against the EBM.

---

## 4. Input Features

All features derive from the Risk Signal Taxonomy (`RISK_SIGNAL_TAXONOMY.md`):

### 4.1. Agent Risk Model Inputs

| Feature | Source Signal | Type | Monotonicity |
|---------|---------------|------|--------------|
| `denial_rate_24h` | ATS-01 | ratio [0,1] | ↑ → ↑ risk |
| `drcp_trigger_count_24h` | ATS-02 | count | ↑ → ↑ risk |
| `scope_violation_count_7d` | ATS-04 | count | ↑ → ↑ risk |
| `correction_acceptance_rate` | ATS-05 | ratio [0,1] | ↑ → ↓ risk |
| `forbidden_tool_attempts_24h` | TMS-01 | count | ↑ → ↑ risk |
| `tool_entropy_7d` | TMS-02 | float | ↓ → ↑ risk |
| `artifact_failure_rate_7d` | AIS-01 | ratio [0,1] | ↑ → ↑ risk |
| `agent_age_days` | derived | count | ↑ → ↓ risk |
| `total_decisions_7d` | derived | count | ↑ → ↓ risk (more data) |

### 4.2. Feature Preprocessing

```python
class RiskFeaturePreprocessor:
    """
    Deterministic feature preprocessing for risk model.

    Constraints:
    - No imputation with learned values
    - No normalization that depends on training data
    - All transforms must be invertible for explanation
    """

    def __init__(self):
        # Fixed quantile boundaries (from domain knowledge, not data)
        self.denial_rate_bins = [0.0, 0.05, 0.10, 0.20, 0.50, 1.0]
        self.count_log_base = 10  # log10(count + 1) transform

    def transform_denial_rate(self, rate: float | None) -> float | None:
        """Identity transform - EBM handles raw ratios well."""
        if rate is None:
            return None  # Explicit missing
        return rate

    def transform_count(self, count: int | None) -> float | None:
        """Log transform for count features."""
        if count is None:
            return None
        return math.log10(count + 1)

    def transform_entropy(self, entropy: float | None) -> float | None:
        """Negate entropy so higher = riskier (low diversity)."""
        if entropy is None:
            return None
        return -entropy  # Invert: low entropy → high risk
```

### 4.3. Missing Value Handling

**Critical Design Decision**: Missing values are handled **explicitly**, not imputed.

```python
# WRONG: Impute missing with mean
# denial_rate = denial_rate or mean_denial_rate  # ❌

# RIGHT: Explicit missing indicator
feature_vector = {
    "denial_rate_24h": 0.15,
    "denial_rate_24h_missing": False,
    "drcp_trigger_count_24h": None,  # Explicit null
    "drcp_trigger_count_24h_missing": True,
}
```

EBMs natively support missing values with a learned "missing" bin.

---

## 5. Monotonic Constraints

### 5.1. Constraint Specification

```python
MONOTONIC_CONSTRAINTS = {
    # Positive monotonicity: ↑ feature → ↑ risk
    "denial_rate_24h": +1,
    "drcp_trigger_count_24h": +1,
    "scope_violation_count_7d": +1,
    "forbidden_tool_attempts_24h": +1,
    "artifact_failure_rate_7d": +1,
    "neg_tool_entropy_7d": +1,  # Already negated

    # Negative monotonicity: ↑ feature → ↓ risk
    "correction_acceptance_rate": -1,
    "agent_age_days": -1,
    "total_decisions_7d": -1,

    # No constraint (allow non-monotonic)
    # (none currently - all features constrained)
}
```

### 5.2. Why Monotonicity Matters

Without constraints, a model might learn:
- "Agents with 10-15% denial rate are riskier than those with 20%"
- This is **unexplainable** and likely a data artifact

With constraints:
- Higher denial rate **always** means higher risk
- Auditors can verify reasoning intuitively
- Adversaries cannot exploit non-monotonic "pockets"

---

## 6. Model Training Protocol

### 6.1. Training Data Requirements

| Requirement | Specification |
|-------------|---------------|
| **Minimum events** | 10,000 governance events |
| **Minimum agents** | 20 unique agent GIDs |
| **Time span** | ≥ 30 days of operations |
| **Label source** | Human-reviewed incidents only |
| **Label quality** | ≥ 2 reviewers agree |

### 6.2. Label Definition

**Positive class (risky behavior = 1)**:
- Agent involved in confirmed security incident
- Agent required emergency privilege revocation
- Agent triggered ≥ 3 human escalations in 7 days

**Negative class (normal behavior = 0)**:
- Agent completed 30+ days without incident
- Agent passed all governance checks
- No human escalations required

**Excluded (no label)**:
- Agents with < 30 days history
- Ambiguous cases (1-2 minor escalations)

### 6.3. Training Configuration

```python
from interpret.glassbox import ExplainableBoostingClassifier

model = ExplainableBoostingClassifier(
    # Feature constraints
    feature_names=list(FEATURE_NAMES),
    feature_types=["continuous"] * len(FEATURE_NAMES),
    monotone_constraints=list(MONOTONIC_CONSTRAINTS.values()),

    # Model complexity
    max_bins=256,           # Sufficient granularity
    max_interaction_bins=32, # Limit interaction complexity
    interactions=10,         # Allow top-10 pairwise interactions

    # Regularization
    outer_bags=25,          # Ensemble for stability
    inner_bags=25,          # Inner bagging
    learning_rate=0.01,     # Conservative learning

    # Reproducibility
    random_state=42,
    n_jobs=-1,
)
```

### 6.4. Temporal Validation

**Critical**: No future leakage allowed.

```
Timeline:
[------- Training (Day 1-60) -------][-- Validation (Day 61-75) --][-- Test (Day 76-90) --]

Rules:
- Training features computed from Day 1-60 events only
- Validation labels from incidents occurring Day 61-75
- Test labels from incidents occurring Day 76-90
- NO backward-looking labels (no "this agent will cause incident tomorrow")
```

---

## 7. Output Specification

### 7.1. Risk Score Output

```json
{
  "agent_gid": "GID-07",
  "risk_score": 0.23,
  "risk_score_type": "calibrated_probability",
  "confidence_interval": {
    "lower": 0.18,
    "upper": 0.29,
    "level": 0.90
  },
  "risk_tier": "MEDIUM",
  "risk_tier_thresholds": {
    "LOW": [0.0, 0.15],
    "MEDIUM": [0.15, 0.40],
    "HIGH": [0.40, 0.70],
    "CRITICAL": [0.70, 1.0]
  },
  "model_version": "ebm-v1.0.0",
  "computed_at": "2025-12-17T15:30:00Z"
}
```

### 7.2. Explanation Output

```json
{
  "agent_gid": "GID-07",
  "risk_score": 0.23,
  "feature_contributions": [
    {
      "feature": "denial_rate_24h",
      "value": 0.15,
      "contribution": +0.08,
      "interpretation": "15% denial rate adds 8 percentage points to risk score"
    },
    {
      "feature": "scope_violation_count_7d",
      "value": 2,
      "contribution": +0.05,
      "interpretation": "2 scope violations add 5 percentage points to risk score"
    },
    {
      "feature": "correction_acceptance_rate",
      "value": 0.90,
      "contribution": -0.03,
      "interpretation": "90% correction acceptance reduces risk by 3 percentage points"
    }
  ],
  "top_3_factors": [
    "denial_rate_24h (+0.08)",
    "scope_violation_count_7d (+0.05)",
    "drcp_trigger_count_24h (+0.03)"
  ],
  "baseline_risk": 0.10,
  "explanation_method": "EBM_native_contributions"
}
```

### 7.3. Confidence Interval Calculation

Confidence intervals derive from ensemble variance:

```python
def compute_confidence_interval(
    predictions: list[float],  # From ensemble members
    level: float = 0.90
) -> tuple[float, float]:
    """
    Compute confidence interval from ensemble predictions.

    Uses percentile method (non-parametric, no normality assumption).
    """
    alpha = 1 - level
    lower = np.percentile(predictions, 100 * alpha / 2)
    upper = np.percentile(predictions, 100 * (1 - alpha / 2))
    return (lower, upper)
```

---

## 8. Calibration Protocol

### 8.1. Calibration Objective

A calibrated model satisfies:

$$
P(\text{incident} \mid \text{score} = p) \approx p
$$

For example, among all agents with score 0.20, approximately 20% should have incidents.

### 8.2. Calibration Method

**Platt Scaling** (isotonic regression variant):

```python
from sklearn.calibration import CalibratedClassifierCV

calibrated_model = CalibratedClassifierCV(
    estimator=trained_ebm,
    method="isotonic",  # Preserves monotonicity
    cv=5,               # 5-fold cross-validation
)
calibrated_model.fit(X_calibration, y_calibration)
```

### 8.3. Calibration Validation

Report **Expected Calibration Error (ECE)**:

$$
ECE = \sum_{b=1}^{B} \frac{n_b}{N} |acc_b - conf_b|
$$

Where:
- $B$ = number of bins
- $n_b$ = samples in bin $b$
- $acc_b$ = actual positive rate in bin
- $conf_b$ = average predicted probability in bin

**Acceptance criteria**: ECE < 0.05 (5%)

---

## 9. Model Governance

### 9.1. Version Control

```
models/
├── risk_model_v1.0.0/
│   ├── model.pkl           # Serialized EBM
│   ├── calibrator.pkl      # Platt scaling calibrator
│   ├── config.json         # Training configuration
│   ├── features.json       # Feature schema
│   ├── metrics.json        # Validation metrics
│   ├── training_hash.sha256 # Hash of training data
│   └── CHANGELOG.md        # Model changes
```

### 9.2. Model Card

Every model version requires a Model Card:

```markdown
# Risk Model v1.0.0 — Model Card

## Intended Use
- Advisory risk scoring for governance agents
- Human decision support (NOT automated decisions)

## Training Data
- Source: ChainBridge governance events (2025-10-01 to 2025-11-30)
- Events: 47,382 governance events
- Agents: 28 unique GIDs
- Positive labels: 12 confirmed incidents
- Negative labels: 16 agents with clean records

## Performance
- Validation AUC-ROC: 0.83
- Test AUC-ROC: 0.79
- ECE (calibration): 0.034

## Limitations
- Requires minimum 10 events per agent for stable predictions
- Not validated on agents outside ChainBridge ecosystem
- May underestimate risk for novel attack patterns

## Ethical Considerations
- Model cannot DENY any agent action
- All outputs are advisory and require human review
- No demographic or identity features used

## Monitoring
- Weekly calibration checks
- Monthly drift detection
- Quarterly full retraining
```

### 9.3. Drift Monitoring

```python
class DriftMonitor:
    """Monitor for feature and prediction drift."""

    def check_feature_drift(
        self,
        training_distribution: dict[str, np.ndarray],
        current_distribution: dict[str, np.ndarray],
    ) -> dict[str, float]:
        """
        Compute KL divergence for each feature.

        Alert if KL divergence > 0.1 for any feature.
        """
        drift_scores = {}
        for feature in training_distribution:
            kl_div = self._kl_divergence(
                training_distribution[feature],
                current_distribution[feature]
            )
            drift_scores[feature] = kl_div
        return drift_scores

    def check_prediction_drift(
        self,
        historical_scores: np.ndarray,
        recent_scores: np.ndarray,
    ) -> float:
        """
        Compare prediction distributions.

        Alert if distribution shift detected.
        """
        ks_stat, p_value = stats.ks_2samp(historical_scores, recent_scores)
        return ks_stat
```

---

## 10. Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     GOVERNANCE LAYER                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │   ACM    │  │   DRCP   │  │  Diggi   │  │  ALEX    │        │
│  │Evaluator │  │ Protocol │  │Corrections│  │ Gateway  │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │             │             │             │               │
│       └─────────────┴──────┬──────┴─────────────┘               │
│                            │                                    │
│                            ▼                                    │
│                    ┌──────────────┐                             │
│                    │  Event Sink  │                             │
│                    │ (telemetry)  │                             │
│                    └──────┬───────┘                             │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            ▼ (read-only)
┌───────────────────────────┼─────────────────────────────────────┐
│                    RISK SIGNAL LAYER                            │
│                            │                                    │
│                    ┌───────▼───────┐                            │
│                    │ Signal Reader │                            │
│                    │ (event parser)│                            │
│                    └───────┬───────┘                            │
│                            │                                    │
│                    ┌───────▼───────┐                            │
│                    │   Feature     │                            │
│                    │  Extractor    │                            │
│                    └───────┬───────┘                            │
│                            │                                    │
│                    ┌───────▼───────┐                            │
│                    │   EBM Model   │                            │
│                    │  (inference)  │                            │
│                    └───────┬───────┘                            │
│                            │                                    │
│                    ┌───────▼───────┐                            │
│                    │  Risk Score   │                            │
│                    │  + Explain    │                            │
│                    └───────┬───────┘                            │
│                            │                                    │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼ (annotations only)
┌────────────────────────────┼────────────────────────────────────┐
│                     CONSUMER LAYER                              │
│                            │                                    │
│    ┌───────────────────────┼───────────────────────────┐        │
│    │                       │                           │        │
│    ▼                       ▼                           ▼        │
│ ┌──────────┐        ┌──────────────┐           ┌────────────┐   │
│ │ChainBoard│        │ Alert System │           │ Proofpack  │   │
│ │   OCC    │        │ (thresholds) │           │ Enrichment │   │
│ └──────────┘        └──────────────┘           └────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Critical Path Rule**: Risk Signal Layer is **read-only** downstream from Governance Layer. No feedback loop to decisions.

---

## 11. Acceptance Criteria

- [ ] EBM selected as canonical model family
- [ ] All features have monotonicity constraints documented
- [ ] Calibration protocol defined with ECE < 0.05 threshold
- [ ] Confidence intervals derived from ensemble variance
- [ ] Model card template specified
- [ ] Drift monitoring approach defined
- [ ] Integration architecture shows read-only data flow
- [ ] No black-box models in decision path

---

## 12. References

- [InterpretML Documentation](https://interpret.ml/)
- [RISK_SIGNAL_TAXONOMY.md](./RISK_SIGNAL_TAXONOMY.md) — Input signals
- [RISK_GOVERNANCE_CONTRACT.md](./RISK_GOVERNANCE_CONTRACT.md) — Integration rules
- [AT02_MODEL_ARCHITECTURE.md](./AT02_MODEL_ARCHITECTURE.md) — Related fraud model
