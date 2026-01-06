# Artifact 6: IT CCI Scoring Model

**PAC Reference:** PAC-JEFFREY-P52  
**Classification:** ITaaS / GOVERNED  
**Status:** DELIVERED  
**Author:** DAN (GID-07)  
**Orchestrator:** BENSON (GID-00)

---

## 1. Overview

The IT CCI (Chaos Coverage Index) Scoring Model defines how verification scores are computed for ITaaS clients. It adapts ChainBridge's internal CCI methodology for external IT infrastructure verification.

---

## 2. Scoring Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    CCI Scoring Model                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FINAL SCORE = (BASE × 0.40) + (CCI × 0.35) + (SAFETY × 0.25)  │
│                                                                 │
│  Where:                                                         │
│    BASE   = Test pass rate (0-100)                             │
│    CCI    = Chaos coverage score (0-100)                       │
│    SAFETY = Safety compliance (0-100)                          │
│                                                                 │
│  Adjustments:                                                   │
│    + Edge case bonus (up to +5)                                │
│    - Violation penalty (up to -50)                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Weights

| Component | Weight | Description |
|-----------|--------|-------------|
| Base Score | 40% | Raw test pass rate |
| CCI Score | 35% | Chaos dimension coverage |
| Safety Score | 25% | Safety compliance |

---

## 4. Base Score Calculation

```python
def compute_base_score(
    total_tests: int,
    passed_tests: int,
    failed_tests: int,
    blocked_tests: int
) -> float:
    """
    Compute base test pass rate.
    
    Blocked tests are counted as failures for scoring.
    """
    if total_tests == 0:
        return 0.0
    
    effective_passed = passed_tests
    effective_total = total_tests
    
    return (effective_passed / effective_total) * 100
```

---

## 5. CCI Score Calculation

### 5.1 Dimension Weights

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| AUTH | 2.0 | Critical security |
| DATA | 1.8 | Injection attacks |
| STATE | 1.5 | Business logic |
| TIMING | 1.3 | Reliability |
| NETWORK | 1.2 | Resilience |
| RESOURCE | 1.0 | Capacity |

### 5.2 Formula

```python
def compute_cci_score(
    dimension_coverage: list[DimensionCoverage]
) -> float:
    """
    Compute Chaos Coverage Index.
    
    CCI = Σ(dimension_weight × dimension_coverage × dimension_pass_rate) / Σ(dimension_weight)
    """
    WEIGHTS = {
        "AUTH": 2.0,
        "DATA": 1.8,
        "STATE": 1.5,
        "TIMING": 1.3,
        "NETWORK": 1.2,
        "RESOURCE": 1.0,
    }
    
    weighted_sum = 0.0
    weight_total = 0.0
    
    for dc in dimension_coverage:
        weight = WEIGHTS.get(dc.dimension.value, 1.0)
        contribution = weight * (dc.coverage_percentage / 100) * (dc.pass_rate / 100)
        weighted_sum += contribution
        weight_total += weight
    
    if weight_total == 0:
        return 0.0
    
    return (weighted_sum / weight_total) * 100
```

---

## 6. Safety Score Calculation

```python
def compute_safety_score(
    total_tests: int,
    violation_count: int,
    blocked_by_safety: int
) -> float:
    """
    Compute safety compliance score.
    
    Perfect safety = 100 (no violations, proper blocking)
    Violations reduce score significantly
    """
    if total_tests == 0:
        return 100.0
    
    # Base: percentage of tests without violations
    violation_rate = violation_count / total_tests
    base_safety = (1 - violation_rate) * 100
    
    # Bonus for proper blocking (prevented violations)
    if blocked_by_safety > 0:
        block_bonus = min(5.0, blocked_by_safety * 0.5)
        base_safety += block_bonus
    
    return min(100.0, base_safety)
```

---

## 7. Adjustments

### 7.1 Edge Case Bonus

```python
def compute_edge_case_bonus(edge_cases_found: int) -> float:
    """
    Bonus for finding and handling edge cases.
    
    Max bonus: +5 points
    """
    MAX_BONUS = 5.0
    BONUS_PER_EDGE = 0.5
    
    return min(MAX_BONUS, edge_cases_found * BONUS_PER_EDGE)
```

### 7.2 Violation Penalty

```python
def compute_violation_penalty(violations: list[SafetyViolation]) -> float:
    """
    Penalty for safety violations.
    
    Max penalty: -50 points
    -10 per violation (capped)
    """
    MAX_PENALTY = 50.0
    PENALTY_PER_VIOLATION = 10.0
    
    unblocked = [v for v in violations if not v.blocked]
    penalty = len(unblocked) * PENALTY_PER_VIOLATION
    
    return min(MAX_PENALTY, penalty)
```

---

## 8. Final Score Formula

```python
def compute_final_score(
    base_score: float,
    cci_score: float,
    safety_score: float,
    edge_cases_found: int,
    violations: list[SafetyViolation]
) -> float:
    """
    Compute final verification score.
    """
    # Weighted components
    weighted = (
        (base_score * 0.40) +
        (cci_score * 0.35) +
        (safety_score * 0.25)
    )
    
    # Adjustments
    bonus = compute_edge_case_bonus(edge_cases_found)
    penalty = compute_violation_penalty(violations)
    
    final = weighted + bonus - penalty
    
    # Clamp to valid range
    return max(0.0, min(100.0, final))
```

---

## 9. Grade Assignment

```python
def assign_grade(score: float) -> ScoreGrade:
    """Map final score to grade."""
    if score >= 95:
        return ScoreGrade.A_PLUS
    elif score >= 90:
        return ScoreGrade.A
    elif score >= 85:
        return ScoreGrade.B_PLUS
    elif score >= 80:
        return ScoreGrade.B
    elif score >= 75:
        return ScoreGrade.C_PLUS
    elif score >= 70:
        return ScoreGrade.C
    elif score >= 60:
        return ScoreGrade.D
    else:
        return ScoreGrade.F
```

---

## 10. Score Interpretation

| Grade | Score | Interpretation | Action |
|-------|-------|----------------|--------|
| A+ | 95-100 | Comprehensive chaos coverage | Maintain |
| A | 90-94 | Excellent coverage | Minor improvements |
| B+ | 85-89 | Good coverage | Review gaps |
| B | 80-84 | Adequate coverage | Address recommendations |
| C+ | 75-79 | Acceptable | Priority improvements |
| C | 70-74 | Minimum threshold | Significant work needed |
| D | 60-69 | Below threshold | Critical improvements |
| F | <60 | Inadequate | Major remediation |

---

## 11. Monotonicity Invariant

For internal ChainBridge use, CCI must be monotonically non-decreasing per commit. For ITaaS clients, this invariant is informational:

```python
def check_cci_monotonicity(
    previous_cci: float,
    current_cci: float
) -> tuple[bool, float]:
    """
    Check if CCI is monotonically non-decreasing.
    
    Returns (is_monotonic, delta)
    """
    delta = current_cci - previous_cci
    is_monotonic = delta >= 0
    
    return (is_monotonic, delta)
```

---

## 12. API Integration

```python
from core.chainverify import CCIScorer, compute_verification_score

scorer = CCIScorer()
score = compute_verification_score(
    api_id="api-123",
    api_title="Payment API",
    test_results=results,
    dimension_coverage=coverage,
)

print(f"Final Score: {score.final_score}")
print(f"Grade: {score.grade.value}")
```

---

## 13. Invariants

| ID | Invariant | Status |
|----|-----------|--------|
| INV-CCI-001 | Weights sum to 1.0 | ENFORCED |
| INV-CCI-002 | Scores clamped 0-100 | ENFORCED |
| INV-CCI-003 | Grade assignment deterministic | ENFORCED |
| INV-CCI-004 | Violations penalize score | ENFORCED |

---

**ARTIFACT STATUS: DELIVERED ✅**
