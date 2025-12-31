# PDO Risk Explainability Law v1.0

**Document ID:** `DOC-CHAINIQ-RISK-EXPLAIN-001`  
**PAC Reference:** `PAC-BENSON-EXEC-GOVERNANCE-MULTI-AGENT-PDO-STRESS-023`  
**Agent:** GID-10 (Maggie) — ML & Applied AI Lead  
**Status:** ACTIVE  
**Effective Date:** 2025-12-26

---

## 1. Purpose

This document establishes the **PDO Risk Explainability Law**, which mandates that
every risk-tagged PDO artifact MUST be accompanied by a human-readable explanation
of the risk factors that influenced the decision outcome.

The goal is to ensure:
- **Transparency**: All stakeholders can understand WHY a decision was made
- **Auditability**: Risk explanations are cryptographically bound to PDO artifacts
- **Accountability**: Risk factors are traceable to specific signals and thresholds

---

## 2. Scope

This law applies to:
- All PDO artifacts with `outcome_status` of `CORRECTIVE` or `REJECTED`
- All PDO artifacts where `risk_score >= 0.5` (configurable threshold)
- Any PDO explicitly flagged for explanation by governance rules

---

## 3. Definitions

| Term | Definition |
|------|------------|
| **Risk Factor** | A quantifiable signal contributing to a risk assessment |
| **Risk Explanation** | Human-readable text describing why a risk score was assigned |
| **Explainability Hash** | SHA-256 hash binding explanation to PDO artifact |
| **Contributing Signal** | Individual input (metric, indicator, model output) affecting risk |
| **Confidence Interval** | Statistical bounds on risk prediction accuracy |

---

## 4. Invariants

### INV-RISK-001: Explanation Required for High-Risk PDOs
Every PDO with `risk_score >= RISK_THRESHOLD` MUST have an attached explanation.
```
∀ pdo ∈ PDO_SET:
  pdo.risk_score >= RISK_THRESHOLD → pdo.explanation ≠ NULL
```

### INV-RISK-002: Explanation Immutability
Once attached, an explanation CANNOT be modified or detached.
```
∀ pdo ∈ PDO_SET:
  attached(pdo, explanation) → immutable(explanation)
```

### INV-RISK-003: Cryptographic Binding
Explanation MUST be hash-bound to the PDO it explains.
```
∀ explanation ∈ EXPLANATION_SET:
  explanation.pdo_hash == SHA256(pdo.content)
```

### INV-RISK-004: Factor Traceability
Each risk factor in an explanation MUST reference a verifiable signal source.
```
∀ factor ∈ explanation.factors:
  exists(signal_source[factor.signal_id])
```

### INV-RISK-005: Confidence Disclosure
Explanations MUST include confidence bounds for the risk assessment.
```
∀ explanation ∈ EXPLANATION_SET:
  explanation.confidence_lower ≠ NULL ∧
  explanation.confidence_upper ≠ NULL
```

### INV-RISK-006: Temporal Validity
Explanations MUST include the timestamp window during which signals were sampled.
```
∀ explanation ∈ EXPLANATION_SET:
  explanation.signal_window_start < explanation.signal_window_end
```

---

## 5. Risk Explanation Structure

### 5.1 Core Fields

```python
@dataclass(frozen=True)
class RiskExplanation:
    explanation_id: str          # Unique identifier
    pdo_id: str                  # Reference to PDO
    pdo_hash: str                # Cryptographic binding to PDO
    
    risk_score: float            # Computed risk score [0.0, 1.0]
    risk_level: str              # LOW | MEDIUM | HIGH | CRITICAL
    
    summary: str                 # Human-readable summary (1-2 sentences)
    detailed_reasoning: str      # Full explanation text
    
    factors: List[RiskFactor]    # Contributing risk factors
    mitigations: List[str]       # Suggested mitigations (optional)
    
    confidence_lower: float      # Lower bound of confidence interval
    confidence_upper: float      # Upper bound of confidence interval
    
    signal_window_start: str     # ISO timestamp - signal collection start
    signal_window_end: str       # ISO timestamp - signal collection end
    
    model_version: str           # Risk model version used
    created_at: str              # ISO timestamp
    explanation_hash: str        # Hash of this explanation
```

### 5.2 Risk Factor Structure

```python
@dataclass(frozen=True)
class RiskFactor:
    factor_id: str               # Unique factor identifier
    signal_id: str               # Source signal identifier
    signal_name: str             # Human-readable signal name
    
    value: float                 # Signal value at evaluation time
    threshold: float             # Threshold that triggered concern
    weight: float                # Factor weight in risk calculation
    
    direction: str               # ABOVE | BELOW | OUTSIDE_RANGE
    contribution: float          # Contribution to final risk score
    
    explanation: str             # Human-readable factor explanation
```

---

## 6. Risk Levels

| Level | Score Range | Description |
|-------|-------------|-------------|
| **LOW** | 0.0 - 0.3 | Minimal risk, proceed with standard monitoring |
| **MEDIUM** | 0.3 - 0.5 | Elevated risk, enhanced monitoring recommended |
| **HIGH** | 0.5 - 0.7 | Significant risk, corrective action likely needed |
| **CRITICAL** | 0.7 - 1.0 | Severe risk, immediate intervention required |

---

## 7. Operations

### 7.1 Allowed Operations

| Operation | Description | Preconditions |
|-----------|-------------|---------------|
| `explain(pdo)` | Generate explanation for PDO | PDO must exist |
| `attach(pdo, explanation)` | Bind explanation to PDO | Explanation must be valid |
| `query(pdo_id)` | Retrieve explanation for PDO | PDO must have explanation |
| `validate(explanation)` | Verify explanation integrity | Explanation must exist |
| `export(format)` | Export explanations | Format must be supported |

### 7.2 Forbidden Operations

| Operation | Reason |
|-----------|--------|
| `modify_explanation()` | Violates INV-RISK-002 |
| `detach_explanation()` | Violates INV-RISK-002 |
| `backdate_explanation()` | Violates temporal integrity |
| `override_binding()` | Violates INV-RISK-003 |

---

## 8. Explanation Generation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RISK EXPLANATION PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────┐    ┌──────────────┐    ┌────────────────┐    ┌────────────┐  │
│   │   PDO   │───▶│ Risk Scoring │───▶│ Factor Analysis│───▶│ Explanation│  │
│   │ Artifact│    │    Engine    │    │    Module      │    │  Generator │  │
│   └─────────┘    └──────────────┘    └────────────────┘    └────────────┘  │
│        │                │                    │                    │         │
│        │                ▼                    ▼                    ▼         │
│        │         ┌──────────────┐    ┌────────────────┐   ┌────────────┐   │
│        │         │  risk_score  │    │   factors[]    │   │  summary   │   │
│        │         │  risk_level  │    │  contributions │   │  reasoning │   │
│        │         └──────────────┘    └────────────────┘   └────────────┘   │
│        │                                                         │         │
│        └─────────────────────────────────────────────────────────┘         │
│                                      │                                      │
│                                      ▼                                      │
│                         ┌──────────────────────────┐                       │
│                         │    RiskExplanation       │                       │
│                         │  (cryptographically      │                       │
│                         │   bound to PDO)          │                       │
│                         └──────────────────────────┘                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Signal Sources

The Risk Explainer may consume signals from:

| Source Category | Examples |
|-----------------|----------|
| **Market Signals** | Volatility index, liquidity depth, price momentum |
| **Sentiment Signals** | Social sentiment score, news sentiment, whale alerts |
| **Technical Signals** | RSI, MACD divergence, support/resistance proximity |
| **On-Chain Signals** | Active addresses, transaction volume, gas fees |
| **Model Outputs** | ML predictions, anomaly scores, pattern matches |

---

## 10. Compliance Export

Risk explanations MUST be exportable for compliance review:

### 10.1 Supported Formats

- **JSON**: Full structured export
- **CSV**: Tabular summary for spreadsheet analysis
- **PDF**: Human-readable compliance report

### 10.2 Required Export Fields

```json
{
  "export_id": "EXP-RISK-2025-12-26-001",
  "export_timestamp": "2025-12-26T12:00:00Z",
  "pdo_count": 150,
  "high_risk_count": 12,
  "explanations": [...],
  "hash_chain_root": "abc123...",
  "exported_by": "GID-10"
}
```

---

## 11. Integration Points

### 11.1 With PDO Audit Trail (INV-AUDIT-*)
Risk explanations are recorded in the audit trail alongside PDO artifacts.

### 11.2 With ChainIQ Risk Engine
The explainer consumes risk scores from the ChainIQ risk calculation pipeline.

### 11.3 With Governance Loop
Explanations inform BER decisions and corrective actions.

---

## 12. Configuration

```python
RISK_EXPLAINER_CONFIG = {
    "risk_threshold": 0.5,           # Score requiring explanation
    "max_factors_displayed": 10,     # Top N factors to show
    "confidence_method": "bootstrap", # CI calculation method
    "explanation_max_length": 2000,  # Max chars for detailed reasoning
    "signal_window_default_hours": 24,
    "model_version": "risk-explain-v1.0.0"
}
```

---

## 13. Enforcement

Violations of this law result in:
- **CORRECTIVE** outcome for any unexplained high-risk PDO
- **Audit flag** for missing confidence bounds
- **BER escalation** for repeated violations

---

## 14. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-26 | GID-10 (Maggie) | Initial release |

---

## 15. Approval

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ APPROVAL BLOCK                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ Law ID:        CHAINIQ-RISK-EXPLAIN-LAW-001                                │
│ Version:       1.0                                                          │
│ Status:        ACTIVE                                                       │
│ Author:        GID-10 (Maggie)                                             │
│ Reviewed By:   GID-00 (Benson Execution)                                   │
│ PAC Binding:   PAC-BENSON-EXEC-GOVERNANCE-MULTI-AGENT-PDO-STRESS-023       │
│ Effective:     2025-12-26                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

**END OF DOCUMENT**
