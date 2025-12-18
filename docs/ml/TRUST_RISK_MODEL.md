# Trust Risk Model Specification

> **Author**: 🟣 MAGGIE (GID-10) — Machine Learning & Applied AI Lead
> **PAC**: PAC-MAGGIE-RISK-TRUST-01
> **Status**: SPEC (Design Only — No Training, No Code)
> **Created**: 2025-12-17

---

## 1. BLUF

This document specifies the **Trust Risk Index (TRI)** — a composite, glass-box risk score that:

- Ranges from 0.0 to 1.0
- Is monotonic (more bad signals → higher score)
- Is decomposable (every contribution traceable)
- Has explicit confidence bands
- Is trust-weighted (stale evidence → inflated risk)

**This score is advisory only. It has zero authority.**

---

## 2. Model Philosophy

### 2.1 Glass-Box Requirement

The Trust Risk Index is computed using **Generalized Additive Model (GAM)** principles:

$$
TRI = \sigma\left( \beta_0 + \sum_{j} w_j \cdot f_j(x_j) \right) \times TW
$$

Where:
- $\sigma$ = sigmoid function to bound output in [0, 1]
- $\beta_0$ = baseline risk intercept
- $w_j$ = weight for feature $j$ (fixed, not learned)
- $f_j(x_j)$ = monotonic transform of feature $j$
- $TW$ = composite trust weight multiplier

**Why GAM**:
- Each feature's contribution is **independently readable**
- Monotonicity is **guaranteed by construction**
- No interaction terms hide reasoning
- Auditors can inspect each component

### 2.2 No Black Boxes

| Component | Status |
|-----------|--------|
| Neural networks | ❌ Forbidden |
| Deep learning | ❌ Forbidden |
| Random forests | ❌ Forbidden |
| Unsupervised clustering | ❌ Forbidden |
| LLM inference | ❌ Forbidden |
| Learned weights | ❌ Forbidden (in this PAC) |
| Hand-tuned weights | ✅ Allowed |
| Monotonic transforms | ✅ Required |

---

## 3. Composite Score Architecture

### 3.1 Three-Layer Aggregation

```
Layer 1: Feature Computation
    └── 15 base features from governance events

Layer 2: Domain Subscores
    ├── GI_score (Governance Integrity)
    ├── OD_score (Operational Discipline)
    └── SD_score (System Drift)

Layer 3: Trust Risk Index
    └── TRI = weighted_aggregate(GI, OD, SD) × trust_weight
```

### 3.2 Domain Subscore Formulas

#### Governance Integrity Score (GI_score)

$$
GI_{score} = w_1 \cdot gi\_denial\_rate_{7d} + w_2 \cdot clip(gi\_scope\_violations_{7d}, 0, 10)/10 + w_3 \cdot gi\_forbidden\_verb\_rate_{7d} + w_4 \cdot gi\_unknown\_agent\_rate_{7d} + w_5 \cdot gi\_tool\_denial\_rate_{7d}
$$

**Weights** (sum to 1.0):
| Feature | Weight | Rationale |
|---------|--------|-----------|
| `gi_denial_rate_7d` | 0.30 | Core access control metric |
| `gi_scope_violations_7d` | 0.25 | Any violation is serious |
| `gi_forbidden_verb_rate_7d` | 0.20 | Privilege boundary probing |
| `gi_unknown_agent_rate_7d` | 0.15 | Identity security |
| `gi_tool_denial_rate_7d` | 0.10 | Execution boundary |

**Null Handling**:
```
IF feature is null:
    Use weight redistribution to remaining features
    (preserve relative proportions)
```

---

#### Operational Discipline Score (OD_score)

$$
OD_{score} = w_1 \cdot od\_drcp\_rate_{7d} + w_2 \cdot od\_human\_escalation\_rate_{7d} + w_3 \cdot od\_artifact\_failure\_rate_{7d} + w_4 \cdot od\_retry\_after\_deny\_rate_{7d}
$$

**Weights** (sum to 1.0):
| Feature | Weight | Rationale |
|---------|--------|-----------|
| `od_drcp_rate_7d` | 0.25 | Correction protocol load |
| `od_human_escalation_rate_7d` | 0.25 | Automation confidence |
| `od_artifact_failure_rate_7d` | 0.30 | Integrity verification |
| `od_retry_after_deny_rate_7d` | 0.20 | Protocol compliance |

**Note**: `od_diggi_corrections` excluded from score (context signal only).

---

#### System Drift Score (SD_score)

$$
SD_{score} = w_1 \cdot clip(sd\_drift\_count_{7d}, 0, 5)/5 + w_2 \cdot sd\_boot\_failure\_rate_{7d} + w_3 \cdot clip(sd\_fingerprint\_changes_{7d}, 0, 5)/5 + w_4 \cdot sd\_freshness\_violation + w_5 \cdot sd\_gameday\_coverage\_gap
$$

**Weights** (sum to 1.0):
| Feature | Weight | Rationale |
|---------|--------|-----------|
| `sd_drift_count_7d` | 0.25 | Configuration tampering |
| `sd_boot_failure_rate_7d` | 0.20 | Deployment health |
| `sd_fingerprint_changes_7d` | 0.15 | Configuration stability |
| `sd_freshness_violation` | 0.25 | Evidence currency |
| `sd_gameday_coverage_gap` | 0.15 | Testing completeness |

---

### 3.3 Trust Risk Index Formula

$$
TRI_{base} = \alpha_{GI} \cdot GI_{score} + \alpha_{OD} \cdot OD_{score} + \alpha_{SD} \cdot SD_{score}
$$

**Domain Weights** (sum to 1.0):
| Domain | Weight | Rationale |
|--------|--------|-----------|
| GI (Governance Integrity) | 0.40 | Core access control |
| OD (Operational Discipline) | 0.35 | Operational health |
| SD (System Drift) | 0.25 | Configuration stability |

$$
TRI_{weighted} = \min(1.0, TRI_{base} \times TW_{composite})
$$

Where $TW_{composite}$ is the composite trust weight.

---

### 3.4 Trust Weight Composite

$$
TW_{composite} = \sqrt[4]{tw\_freshness \times tw\_gameday \times tw\_evidence \times tw\_density}
$$

**Geometric mean** ensures:
- No single weight dominates
- All weights contribute proportionally
- Multiplier range: [1.0, 2.0]

**Example**:
```
tw_freshness = 1.2 (bundle 2 days old)
tw_gameday = 1.0 (full coverage)
tw_evidence = 1.1 (10% artifact failures)
tw_density = 1.0 (sufficient events)

TW_composite = (1.2 × 1.0 × 1.1 × 1.0)^0.25 = 1.08
```

---

## 4. Output Specification

### 4.1 Trust Risk Index Output

```json
{
  "trust_risk_index": {
    "value": 0.23,
    "tier": "LOW",
    "computed_at": "2025-12-17T15:30:00Z",
    "observation_window": "7d",
    "model_version": "tri-v1.0.0"
  },
  "confidence": {
    "level": 0.85,
    "band_lower": 0.18,
    "band_upper": 0.28,
    "note": "Based on 1,247 events in window"
  },
  "domain_scores": {
    "governance_integrity": 0.15,
    "operational_discipline": 0.28,
    "system_drift": 0.12
  },
  "trust_weight": {
    "composite": 1.08,
    "freshness": 1.2,
    "gameday": 1.0,
    "evidence": 1.1,
    "density": 1.0
  }
}
```

### 4.2 Risk Tiers

| Tier | Range | Interpretation |
|------|-------|----------------|
| **MINIMAL** | [0.00, 0.10) | Very low operational risk signals |
| **LOW** | [0.10, 0.25) | Normal operational friction |
| **MODERATE** | [0.25, 0.50) | Elevated signals, review recommended |
| **HIGH** | [0.50, 0.75) | Significant signals, investigation needed |
| **CRITICAL** | [0.75, 1.00] | Severe signals, immediate attention |

**CRITICAL**: No tier is labeled "safe" or "unsafe". All tiers are relative risk indicators.

### 4.3 Feature Contribution Breakdown

```json
{
  "feature_contributions": [
    {
      "feature": "gi_denial_rate_7d",
      "value": 0.12,
      "weight": 0.30,
      "contribution": 0.036,
      "domain": "governance_integrity",
      "interpretation": "12% denial rate contributes 3.6 points to GI score"
    },
    {
      "feature": "od_artifact_failure_rate_7d",
      "value": 0.05,
      "weight": 0.30,
      "contribution": 0.015,
      "domain": "operational_discipline",
      "interpretation": "5% artifact failure rate contributes 1.5 points to OD score"
    }
  ],
  "top_contributors": [
    "gi_denial_rate_7d (0.036)",
    "od_human_escalation_rate_7d (0.025)",
    "sd_freshness_violation (0.020)"
  ]
}
```

---

## 5. Confidence Calculation

### 5.1 Confidence Level

$$
confidence = \min(1.0, \frac{event\_count}{min\_events}) \times data\_completeness
$$

Where:
- `event_count` = total governance events in window
- `min_events` = 500 (threshold for full confidence)
- `data_completeness` = fraction of features with non-null values

### 5.2 Confidence Band

$$
band\_width = (1 - confidence) \times max\_band\_width
$$

Where `max_band_width = 0.15` (±7.5% at minimum confidence)

```
band_lower = max(0.0, TRI - band_width / 2)
band_upper = min(1.0, TRI + band_width / 2)
```

---

## 6. Monotonicity Guarantees

### 6.1 Feature-Level Monotonicity

Every feature transform $f_j(x_j)$ is monotonically non-decreasing in risk direction:

| Feature | Transform | Monotonicity |
|---------|-----------|--------------|
| `gi_denial_rate` | Identity | ↑ x → ↑ f(x) |
| `gi_scope_violations` | clip(x, 0, 10)/10 | ↑ x → ↑ f(x) |
| `gi_forbidden_verb_rate` | Identity | ↑ x → ↑ f(x) |
| `gi_unknown_agent_rate` | Identity | ↑ x → ↑ f(x) |
| `gi_tool_denial_rate` | Identity | ↑ x → ↑ f(x) |
| `od_drcp_rate` | Identity | ↑ x → ↑ f(x) |
| `od_human_escalation_rate` | Identity | ↑ x → ↑ f(x) |
| `od_artifact_failure_rate` | Identity | ↑ x → ↑ f(x) |
| `od_retry_after_deny_rate` | Identity | ↑ x → ↑ f(x) |
| `sd_drift_count` | clip(x, 0, 5)/5 | ↑ x → ↑ f(x) |
| `sd_boot_failure_rate` | Identity | ↑ x → ↑ f(x) |
| `sd_fingerprint_changes` | clip(x, 0, 5)/5 | ↑ x → ↑ f(x) |
| `sd_freshness_violation` | Identity (bool) | 1 > 0 |
| `sd_gameday_coverage_gap` | Identity | ↑ x → ↑ f(x) |

### 6.2 Aggregate Monotonicity

Since:
- All weights are positive
- All transforms are monotonically non-decreasing
- Aggregation uses weighted sum

The composite TRI is **guaranteed monotonic**: Worse inputs → Higher TRI. Never the reverse.

---

## 7. Time Decay Model

### 7.1 Exponential Decay Formula

For features with decay:

$$
effective\_count = \sum_{i} e^{-\lambda \cdot age_i}
$$

Where:
- $\lambda = \ln(2) / half\_life\_hours$
- $age_i$ = hours since event $i$

### 7.2 Decay Parameters

| Feature Type | Half-Life | Rationale |
|--------------|-----------|-----------|
| Scope violations | 168h (7d) | Serious, persists |
| Drift detection | 72h (3d) | Important but may be resolved |
| Other events | None | Use windowed counts |

---

## 8. Visualization Spec

### 8.1 Gauge Display

```
        Trust Risk Index
    ┌─────────────────────┐
    │         0.23        │
    │        ──────       │
    │   ████████░░░░░░░   │
    │   LOW               │
    └─────────────────────┘

    0.0  0.25  0.50  0.75  1.0
     │     │     │     │    │
    MIN   LOW   MOD  HIGH  CRIT
```

### 8.2 Domain Breakdown

```
    Domain Scores (7-day window)

    Governance Integrity  ████████░░░░░░░░  0.15
    Operational Discipline ███████████░░░░░  0.28
    System Drift          ████░░░░░░░░░░░░  0.12

    Trust Weight Applied: 1.08×
```

### 8.3 Trend Chart

```
    TRI Trend (30 days)
    1.0 ─┐
        │
    0.5 ─┤                    ╭──╮
        │    ╭──╮    ╭──╮   ╭╯  ╰──
    0.25─┤───╯  ╰────╯  ╰───╯
        │
    0.0 ─┴────────────────────────────
        -30d  -20d  -10d  Today
```

---

## 9. Edge Cases & Bounds

### 9.1 No Data Scenario

```
IF total_events_in_window == 0:
    TRI = null
    tier = "UNKNOWN"
    message = "Insufficient data for risk assessment"
```

### 9.2 All Features Null

```
IF all domain scores are null:
    TRI = null
    tier = "UNKNOWN"
    message = "No computable risk signals"
```

### 9.3 Maximum Risk

```
IF computed_TRI > 1.0 (after trust weight):
    TRI = 1.0
    tier = "CRITICAL"
    message = "Maximum risk threshold reached"
```

### 9.4 Perfect Score

```
IF all features == 0 AND trust_weight == 1.0:
    TRI = 0.0
    tier = "MINIMAL"
    message = "All governance signals nominal"
```

---

## 10. Model Versioning

### 10.1 Version Format

```
tri-v{major}.{minor}.{patch}

Example: tri-v1.0.0
```

### 10.2 Change Impact

| Change Type | Version Impact | Example |
|-------------|----------------|---------|
| Weight adjustment | Minor | 0.30 → 0.35 |
| New feature | Minor | Add new signal |
| Formula change | Major | Change aggregation |
| Bug fix | Patch | Fix null handling |

### 10.3 Version Record

Every TRI output includes model version for reproducibility.

---

## 11. What This Model Does NOT Do

| Claim | Status |
|-------|--------|
| Predict future incidents | ❌ No |
| Guarantee safety | ❌ No |
| Replace human judgment | ❌ No |
| Authorize actions | ❌ No |
| Block transactions | ❌ No |
| Trigger automation | ❌ No |

**This is a risk signal, not a control.**

---

## 12. Acceptance Criteria

- [x] Composite score in [0.0, 1.0] range
- [x] All weights documented and sum to 1.0
- [x] Monotonicity guaranteed by construction
- [x] Feature contributions decomposable
- [x] Confidence bands specified
- [x] Trust weights penalize stale evidence
- [x] Risk tiers defined without "safe" label
- [x] Edge cases handled
- [x] Versioning scheme specified

---

## 13. References

- [TRUST_RISK_TAXONOMY.md](./TRUST_RISK_TAXONOMY.md) — Signal definitions
- [TRUST_RISK_FEATURES.md](./TRUST_RISK_FEATURES.md) — Feature formulas
- [TRUST_RISK_GOVERNANCE_CONTRACT.md](./TRUST_RISK_GOVERNANCE_CONTRACT.md) — Integration rules
