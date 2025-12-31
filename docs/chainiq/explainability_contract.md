# ChainIQ Explainability Contract v1

**PAC Reference:** PAC-BENSON-EXEC-MAGGIE-CHAINIQ-008  
**Author:** Maggie (GID-10) — ML & Applied AI Lead  
**Status:** CANONICAL  
**Version:** v1.0.0  
**Applies To:** ChainIQ Risk Model v1  
**Governance:** GOLD_STANDARD  
**Model Policy:** GLASS-BOX ONLY  

---

## 1. Explainability Mandate

Every risk score emitted by ChainIQ Risk Model v1 **MUST** include complete, interpretable explanations that satisfy:

1. **Regulatory Requirements** — Auditors can trace any decision to specific inputs
2. **Operator Trust** — Humans can understand and verify model reasoning
3. **Reproducibility** — Explanations are deterministic and replayable

**Forbidden:**
- ❌ Black-box scores without attribution
- ❌ Opaque embeddings or latent vectors
- ❌ Hidden features or undisclosed inputs
- ❌ Aggregated-only scores without factor breakdown

---

## 2. Glass-Box Model Requirement

### 2.1 Definition

A **glass-box model** exposes its full decision logic such that:

```
For any input x:
  - The exact computation path is visible
  - Each feature's contribution is quantifiable
  - The model structure can be inspected and audited
  - No hidden parameters or transformations exist
```

### 2.2 Allowed Model Families

| Model Type | Glass-Box Status | Notes |
|------------|------------------|-------|
| Logistic Regression | ✅ Allowed | Coefficients are weights |
| GAM / EBM | ✅ Allowed | Shape functions visible |
| Shallow Decision Tree | ✅ Allowed | Rules are explicit |
| Rule-based System | ✅ Allowed | Rules are enumerable |
| Deep Neural Network | ❌ Forbidden | Opaque layers |
| Ensemble without SHAP | ❌ Forbidden | No intrinsic interpretability |
| Black-box with post-hoc LIME | ❌ Forbidden | Explanations are approximations |

### 2.3 EBM Explainability

ChainIQ Risk Model v1 uses **Explainable Boosting Machine (EBM)**, which provides:

```python
# EBM additive structure
score = intercept + Σ f_i(x_i) + Σ f_ij(x_i, x_j)

# Where:
# - f_i(x_i) = shape function for feature i (visible, exportable)
# - f_ij(x_i, x_j) = interaction term (limited, explicit)
# - All functions are piecewise constant (step functions)
```

**Shape functions are stored and versioned** — can be plotted, audited, and compared.

---

## 3. Attribution Requirements

### 3.1 Per-Score Attribution

Every risk score includes **exactly K attributions** (default K=5):

```python
@dataclass
class FeatureAttribution:
    feature_name: str           # Human-readable name
    feature_value: Any          # Actual value observed
    contribution: float         # Magnitude of impact
    contribution_pct: float     # % of total attribution
    direction: Direction        # INCREASES_RISK | DECREASES_RISK
    explanation: str            # Plain-English explanation
    shape_function_value: float # Raw shape function output
```

### 3.2 Attribution Computation

```python
def compute_attributions(model: EBM, features: ShipmentFeaturesV1) -> List[FeatureAttribution]:
    """
    Extract per-feature contributions from EBM shape functions.
    """
    contributions = []
    
    # Main effects
    for i, feature_name in enumerate(model.feature_names):
        value = getattr(features, feature_name)
        shape_value = model.eval_shape_function(i, value)
        
        contributions.append(FeatureAttribution(
            feature_name=to_human_readable(feature_name),
            feature_value=value,
            contribution=abs(shape_value),
            direction="INCREASES_RISK" if shape_value > 0 else "DECREASES_RISK",
            shape_function_value=shape_value
        ))
    
    # Interaction effects (if any)
    for (i, j), interaction_func in model.interactions.items():
        value_i = getattr(features, model.feature_names[i])
        value_j = getattr(features, model.feature_names[j])
        interaction_value = interaction_func(value_i, value_j)
        
        if abs(interaction_value) > INTERACTION_THRESHOLD:
            contributions.append(...)
    
    # Sort by magnitude, take top K
    contributions.sort(key=lambda x: x.contribution, reverse=True)
    return contributions[:K]
```

### 3.3 Attribution Normalization

```python
def normalize_attributions(attributions: List[FeatureAttribution]) -> List[FeatureAttribution]:
    """
    Normalize contributions to sum to 1.0 for percentage display.
    """
    total = sum(abs(a.contribution) for a in attributions)
    for a in attributions:
        a.contribution_pct = abs(a.contribution) / total if total > 0 else 0.0
    return attributions
```

---

## 4. Explanation Format

### 4.1 Technical Format (for logging/audit)

```json
{
  "attributions": [
    {
      "feature_name": "eta_deviation_hours",
      "feature_value": 18.5,
      "contribution": 0.234,
      "contribution_pct": 0.312,
      "direction": "INCREASES_RISK",
      "shape_function_value": 0.234,
      "explanation": "ETA deviation is 18.5 hours, significantly increasing risk."
    },
    {
      "feature_name": "counterparty_risk_tier",
      "feature_value": 4,
      "contribution": 0.189,
      "contribution_pct": 0.252,
      "direction": "INCREASES_RISK",
      "shape_function_value": 0.189,
      "explanation": "Counterparty is Tier 4 (high risk)."
    }
  ],
  "total_explained_contribution": 0.751,
  "intercept": 0.142,
  "model_version": "chainiq_risk_glassbox_v1.0.0"
}
```

### 4.2 Operator Format (for UI/console)

```
┌─────────────────────────────────────────────────────────────────┐
│  RISK SCORE: 0.72 (SEVERE)                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TOP RISK FACTORS:                                              │
│                                                                 │
│  1. 🔴 ETA Deviation (+31.2%)                                   │
│     Shipment is 18.5 hours behind schedule.                     │
│                                                                 │
│  2. 🔴 Counterparty Risk (+25.2%)                               │
│     Counterparty is rated Tier 4 (high risk).                   │
│                                                                 │
│  3. 🔴 Temperature Violations (+18.1%)                          │
│     3 temperature excursions detected.                          │
│                                                                 │
│  4. 🔴 Missing Documents (+12.3%)                               │
│     2 required documents are missing.                           │
│                                                                 │
│  5. 🟢 Collateral Coverage (-8.7%)                              │
│     Collateral covers 1.8x financing amount.                    │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  ELI5: This shipment is high risk primarily due to significant  │
│  delays and a high-risk counterparty.                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Human-Readable Name Mapping

```python
FEATURE_DISPLAY_NAMES = {
    "eta_deviation_hours": "ETA Deviation",
    "temperature_violations_count": "Temperature Violations",
    "missing_docs_count": "Missing Documents",
    "counterparty_risk_tier": "Counterparty Risk",
    "collateral_coverage_ratio": "Collateral Coverage",
    "corridor_default_rate": "Corridor Default Rate",
    "shipper_historical_success_rate": "Shipper History",
    "doc_discrepancy_severity": "Document Discrepancies",
    "monitoring_gap_hours": "Monitoring Gaps",
    "trade_friction_index": "Trade Friction",
    # ... all 24 features mapped
}
```

---

## 5. Explanation Templates

### 5.1 Template Library

```python
EXPLANATION_TEMPLATES = {
    "eta_deviation_hours": {
        "positive": "Shipment is {value:.1f} hours behind schedule.",
        "negative": "Shipment is {value:.1f} hours ahead of schedule.",
        "zero": "Shipment is on schedule."
    },
    "temperature_violations_count": {
        "positive": "{value} temperature excursion(s) detected.",
        "zero": "No temperature violations detected."
    },
    "counterparty_risk_tier": {
        "tier_1": "Counterparty is Tier 1 (lowest risk).",
        "tier_2": "Counterparty is Tier 2 (low risk).",
        "tier_3": "Counterparty is Tier 3 (moderate risk).",
        "tier_4": "Counterparty is Tier 4 (high risk).",
        "tier_5": "Counterparty is Tier 5 (highest risk)."
    },
    "collateral_coverage_ratio": {
        "high": "Collateral covers {value:.1f}x financing amount.",
        "low": "Collateral covers only {value:.1f}x financing amount.",
        "zero": "No collateral provided."
    },
    # ... templates for all features
}
```

### 5.2 ELI5 Generation

```python
def generate_eli5(attributions: List[FeatureAttribution], risk_tier: str) -> str:
    """
    Generate a single-sentence summary for operators.
    """
    top_2 = attributions[:2]
    
    drivers = " and ".join([
        FACTOR_PHRASES[a.feature_name] for a in top_2
    ])
    
    return f"This shipment is {risk_tier.lower()} risk primarily due to {drivers}."
```

---

## 6. Shape Function Export

### 6.1 Export Format

Shape functions are exportable for regulatory inspection:

```json
{
  "model_id": "chainiq_risk_glassbox_v1.0.0",
  "shape_functions": {
    "eta_deviation_hours": {
      "type": "piecewise_constant",
      "bins": [-168, -24, 0, 6, 12, 24, 48, 96, 168, 720],
      "values": [-0.15, -0.08, 0.0, 0.05, 0.12, 0.22, 0.35, 0.45, 0.52]
    },
    "counterparty_risk_tier": {
      "type": "categorical",
      "mapping": {
        "1": -0.18,
        "2": -0.08,
        "3": 0.02,
        "4": 0.19,
        "5": 0.32
      }
    }
  },
  "interactions": {
    "eta_deviation_hours:counterparty_risk_tier": {
      "type": "bivariate_piecewise",
      "grid": "..."
    }
  },
  "intercept": 0.142
}
```

### 6.2 Visualization

Shape functions can be visualized for audit:

```
┌─────────────────────────────────────────────────────────────────┐
│  Shape Function: eta_deviation_hours                            │
│                                                                 │
│  0.6 │                                           ∙∙∙∙∙∙∙∙∙∙     │
│      │                                     ∙∙∙∙∙∙                │
│  0.4 │                               ∙∙∙∙∙∙                      │
│      │                          ∙∙∙∙∙                            │
│  0.2 │                    ∙∙∙∙∙∙                                 │
│ f(x) │               ∙∙∙∙∙                                       │
│  0.0 ├──────────∙∙∙∙∙────────────────────────────────────────   │
│      │     ∙∙∙∙∙                                                 │
│ -0.2 │∙∙∙∙∙                                                      │
│      │                                                           │
│      └───────────────────────────────────────────────────────   │
│     -168  -24   0   12  24  48  96  168  720                    │
│                 ETA Deviation (hours)                            │
│                                                                 │
│  Interpretation: Risk increases monotonically with delay.        │
│  Negative values (early arrival) slightly reduce risk.           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Audit Trail Requirements

### 7.1 Logged for Every Inference

```yaml
audit_record:
  pdo_id: string
  timestamp: datetime
  model_id: string
  model_version: string
  model_checksum: string
  
  input_features:
    - name: string
      value: any
      source: string
      acquired_at: datetime
      
  attributions:
    - feature_name: string
      contribution: float
      direction: string
      explanation: string
      
  risk_score: float
  risk_tier: string
  
  shape_function_version: string
  calibration_version: string
```

### 7.2 Replay Capability

Any historical score can be replayed with identical results:

```python
def replay_score(audit_record: AuditRecord) -> RiskPDO:
    """
    Replay a historical score using stored model version and inputs.
    Must produce identical output.
    """
    model = load_model(audit_record.model_id, audit_record.model_version)
    features = reconstruct_features(audit_record.input_features)
    
    pdo = model.score(features)
    
    assert pdo.risk_score == audit_record.risk_score
    assert pdo.attributions == audit_record.attributions
    
    return pdo
```

---

## 8. Prohibited Practices

### 8.1 Forbidden (NEVER)

| Practice | Violation | Consequence |
|----------|-----------|-------------|
| Return score without attributions | Explainability breach | REJECT emission |
| Use opaque embeddings | Glass-box violation | REJECT model |
| Hide features from attribution | Transparency breach | REJECT model |
| Collapse factors into single score | Aggregation violation | REJECT emission |
| Use approximation explanations (LIME, etc.) | Accuracy violation | REJECT model |
| Modify attributions post-hoc | Integrity breach | REJECT emission |

### 8.2 Enforcement

```python
def validate_explainability(pdo: RiskPDO) -> bool:
    """
    Validate PDO meets explainability requirements.
    FAIL-CLOSED on any violation.
    """
    # Must have attributions
    if not pdo.attributions or len(pdo.attributions) < 3:
        raise ExplainabilityViolation("Insufficient attributions")
    
    # Attributions must have explanations
    for attr in pdo.attributions:
        if not attr.explanation:
            raise ExplainabilityViolation("Missing explanation")
        if attr.feature_name not in FEATURE_DISPLAY_NAMES:
            raise ExplainabilityViolation("Unknown feature")
    
    # Contributions must sum reasonably
    total_contrib = sum(abs(a.contribution) for a in pdo.attributions)
    if total_contrib < 0.5 * abs(pdo.risk_score):
        raise ExplainabilityViolation("Attributions don't explain score")
    
    return True
```

---

## 9. Regulatory Compliance

### 9.1 Supported Frameworks

This explainability contract supports compliance with:

| Framework | Requirement | How Addressed |
|-----------|-------------|---------------|
| SR 11-7 (Model Risk) | Model documentation | Shape functions exported |
| GDPR Art. 22 | Right to explanation | Per-score attributions |
| ECOA | Adverse action reasons | Reason codes provided |
| Basel III | Model validation | Audit trail + replay |
| Fair Lending | Discrimination monitoring | Feature visibility |

### 9.2 Examiner Access

Regulators can request:
- Full model artifact (frozen weights + shape functions)
- Any historical score replay
- Aggregated attribution statistics
- Shape function visualizations
- Calibration evidence

---

## 10. Attestation

```yaml
attestation:
  pac_id: PAC-BENSON-EXEC-MAGGIE-CHAINIQ-008
  author: Maggie (GID-10)
  role: ML & Applied AI Lead
  document: explainability_contract.md
  model_policy: GLASS-BOX ONLY
  attribution_minimum: 3
  created_at: 2025-12-26T00:00:00Z
  status: CANONICAL
```

---

**END OF DOCUMENT — explainability_contract.md**
