# CCI-Driven Merge Gate Specification

**PAC Reference:** PAC-JEFFREY-P48  
**Classification:** GOVERNANCE INTEGRATION  
**Doctrine Reference:** DOC-002 (Chaos Coverage Index)  
**Version:** 1.0.0  
**Date:** 2026-01-02

---

## 1. Overview

This specification defines the merge gate that enforces CCI (Chaos Coverage Index) monotonicity per Doctrine DOC-002 from PAC-JEFFREY-P47.

### Core Invariant

```
NO CCI GROWTH → NO MERGE
```

---

## 2. Gate Definition

### 2.1 Gate Identifier

```
GATE-CCI-001: Chaos Coverage Index Merge Gate
```

### 2.2 Trigger Conditions

The gate activates on:
- Pull Request creation
- Pull Request update (new commits)
- Manual gate check request

### 2.3 Gate Logic

```python
def check_cci_merge_gate(pr_branch: str, target_branch: str) -> GateResult:
    """
    CCI Merge Gate per Doctrine DOC-002.
    
    Returns PASS only if:
    1. CCI is maintained or increased
    2. No chaos dimension loses coverage
    3. All canonical dimensions have at least one test
    """
    
    baseline_cci = get_baseline_cci(target_branch)
    current_cci = compute_cci(pr_branch)
    
    # Check 1: CCI monotonicity
    if current_cci.value < baseline_cci.value:
        return GateResult(
            passed=False,
            reason=f"CCI DECREASE: {baseline_cci.value:.2f} → {current_cci.value:.2f}",
            action="BLOCK_MERGE"
        )
    
    # Check 2: No dimension regression
    for dimension in CANONICAL_DIMENSIONS:
        baseline_count = baseline_cci.dimension_counts.get(dimension, 0)
        current_count = current_cci.dimension_counts.get(dimension, 0)
        
        if current_count < baseline_count:
            return GateResult(
                passed=False,
                reason=f"Dimension {dimension} regression: {baseline_count} → {current_count}",
                action="BLOCK_MERGE"
            )
    
    # Check 3: All dimensions covered
    uncovered = [d for d in CANONICAL_DIMENSIONS if current_cci.dimension_counts.get(d, 0) == 0]
    if uncovered:
        return GateResult(
            passed=False,
            reason=f"Uncovered dimensions: {uncovered}",
            action="BLOCK_MERGE"
        )
    
    return GateResult(
        passed=True,
        reason=f"CCI maintained: {baseline_cci.value:.2f} → {current_cci.value:.2f}",
        action="ALLOW_MERGE"
    )
```

---

## 3. Canonical Chaos Dimensions

Per Doctrine DOC-002, the six canonical dimensions are:

| Dimension | Code | Description | Minimum Coverage |
|-----------|------|-------------|------------------|
| Authentication | AUTH | Identity, session, permission failures | ≥ 1 test |
| State | STATE | Inconsistent, stale, corrupted state | ≥ 1 test |
| Concurrency | CONC | Race conditions, deadlocks, ordering | ≥ 1 test |
| Time | TIME | Clock skew, timeout, scheduling | ≥ 1 test |
| Data | DATA | Malformed, missing, overflow, injection | ≥ 1 test |
| Governance | GOV | Rule violations, policy conflicts | ≥ 1 test |

---

## 4. CCI Calculation

### 4.1 Formula

```
CCI = Σ (chaos_tests_per_dimension) / total_dimensions

Where:
- chaos_tests_per_dimension = count of tests tagged with each dimension
- total_dimensions = 6 (canonical)
```

### 4.2 Example

```
Dimension Counts:
  AUTH: 15 tests
  STATE: 12 tests
  CONC: 8 tests
  TIME: 6 tests
  DATA: 20 tests
  GOV: 11 tests
  
Total chaos tests: 72
CCI = 72 / 6 = 12.0
```

---

## 5. Test Tagging Convention

### 5.1 Marker Syntax

Tests must be tagged with chaos dimension markers:

```python
import pytest

@pytest.mark.chaos_auth
def test_invalid_token_rejected():
    """AUTH dimension: Invalid token should be rejected."""
    pass

@pytest.mark.chaos_state
def test_stale_cache_detected():
    """STATE dimension: Stale cache should trigger refresh."""
    pass

@pytest.mark.chaos_conc
def test_concurrent_updates_serialized():
    """CONC dimension: Concurrent updates should serialize."""
    pass

@pytest.mark.chaos_time
def test_timeout_triggers_fallback():
    """TIME dimension: Timeout should trigger fallback."""
    pass

@pytest.mark.chaos_data
def test_malformed_input_rejected():
    """DATA dimension: Malformed input should be rejected."""
    pass

@pytest.mark.chaos_gov
def test_policy_violation_blocked():
    """GOV dimension: Policy violation should be blocked."""
    pass
```

### 5.2 Multiple Dimensions

A test may cover multiple dimensions:

```python
@pytest.mark.chaos_auth
@pytest.mark.chaos_state
def test_expired_session_with_stale_token():
    """Covers AUTH (session) and STATE (staleness)."""
    pass
```

---

## 6. CI Integration

### 6.1 GitHub Actions Workflow

```yaml
name: CCI Merge Gate

on:
  pull_request:
    branches: [main, develop]

jobs:
  cci-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for baseline comparison
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Compute baseline CCI
        run: |
          git checkout ${{ github.base_ref }}
          python -c "from core.occ.governance import get_cci_report; print(get_cci_report())" > baseline_cci.json
          git checkout ${{ github.head_ref }}
      
      - name: Compute current CCI
        run: |
          python -c "from core.occ.governance import get_cci_report; print(get_cci_report())" > current_cci.json
      
      - name: Run CCI Gate
        run: |
          python scripts/ci/check_cci_gate.py baseline_cci.json current_cci.json
```

### 6.2 Gate Check Script

```python
#!/usr/bin/env python
"""
CCI Gate Check Script

Usage: python check_cci_gate.py <baseline_json> <current_json>
"""

import json
import sys

def main():
    if len(sys.argv) != 3:
        print("Usage: check_cci_gate.py <baseline_json> <current_json>")
        sys.exit(1)
    
    with open(sys.argv[1]) as f:
        baseline = json.load(f)
    
    with open(sys.argv[2]) as f:
        current = json.load(f)
    
    baseline_cci = baseline.get("cci_value", 0)
    current_cci = current.get("cci_value", 0)
    
    print(f"Baseline CCI: {baseline_cci:.2f}")
    print(f"Current CCI:  {current_cci:.2f}")
    
    if current_cci < baseline_cci:
        print(f"❌ GATE FAILED: CCI decreased from {baseline_cci:.2f} to {current_cci:.2f}")
        print("   Doctrine DOC-002 violation: CCI must be monotonic")
        sys.exit(1)
    
    # Check dimension coverage
    baseline_dims = baseline.get("dimensions", {})
    current_dims = current.get("dimensions", {})
    
    for dim, data in baseline_dims.items():
        baseline_count = data.get("count", 0)
        current_count = current_dims.get(dim, {}).get("count", 0)
        
        if current_count < baseline_count:
            print(f"❌ GATE FAILED: Dimension {dim} regressed from {baseline_count} to {current_count}")
            sys.exit(1)
    
    # Check all dimensions covered
    uncovered = [d for d, data in current_dims.items() if data.get("count", 0) == 0]
    if uncovered:
        print(f"❌ GATE FAILED: Uncovered dimensions: {uncovered}")
        sys.exit(1)
    
    print(f"✅ GATE PASSED: CCI maintained/increased ({baseline_cci:.2f} → {current_cci:.2f})")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

---

## 7. Override Procedure

Per Doctrine DOC-002, local overrides are **NOT PERMITTED**.

To bypass the CCI gate requires:
1. LAW-TIER corrective PAC
2. JEFFREY authorization
3. ALEX acknowledgment
4. Full audit trail documenting justification

---

## 8. Reporting

### 8.1 Gate Report Format

```json
{
  "gate_id": "GATE-CCI-001",
  "timestamp": "2026-01-02T12:00:00Z",
  "pr_number": 42,
  "result": "PASS",
  "baseline_cci": 12.0,
  "current_cci": 12.5,
  "delta": 0.5,
  "dimension_report": {
    "AUTH": {"baseline": 15, "current": 16, "delta": 1},
    "STATE": {"baseline": 12, "current": 12, "delta": 0},
    "CONC": {"baseline": 8, "current": 9, "delta": 1},
    "TIME": {"baseline": 6, "current": 6, "delta": 0},
    "DATA": {"baseline": 20, "current": 21, "delta": 1},
    "GOV": {"baseline": 11, "current": 11, "delta": 0}
  },
  "uncovered_dimensions": [],
  "action_taken": "ALLOW_MERGE"
}
```

### 8.2 OCC Dashboard Integration

The CCI gate status is surfaced in the OCC dashboard:
- Current CCI value
- Dimension breakdown chart
- Gate history (last 30 days)
- Trend analysis

---

## 9. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-02 | DAN (GID-07) | Initial specification |

---

**Document Authority:** PAC-JEFFREY-P48  
**Doctrine Reference:** DOC-002 (Chaos Coverage Index)  
**Enforcement:** MECHANICAL via CI
