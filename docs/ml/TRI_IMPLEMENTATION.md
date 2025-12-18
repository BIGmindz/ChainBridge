# TRI Implementation Guide

> **Author**: 🟣 MAGGIE (GID-10) — Machine Learning & Applied AI Lead
> **PAC**: PAC-MAGGIE-RISK-IMPL-01
> **Status**: IMPLEMENTED
> **Version**: 1.0.0
> **Created**: 2025-12-17

---

## 1. Overview

The Trust Risk Index (TRI) Engine is a deterministic, glass-box risk scoring system that computes a 0.0–1.0 risk score from governance event data. The implementation follows the design specifications from PAC-MAGGIE-RISK-TRUST-01.

### Key Properties

| Property | Implementation |
|----------|---------------|
| **Deterministic** | Same inputs → identical output (bit-stable) |
| **Bounded** | Output always in [0.0, 1.0] |
| **Explainable** | Full contribution breakdown for every feature |
| **Read-only** | No side effects, no event writes |
| **Advisory only** | Enforced in code — cannot be set to False |

---

## 2. Module Structure

```
core/risk/
├── __init__.py           # Public API exports
├── types.py              # Data structures and enums
├── feature_extractors.py # 15 feature extraction functions
├── trust_weights.py      # 4 trust weight calculators
└── tri_engine.py         # Main computation engine

tests/risk/
├── __init__.py
├── test_types.py               # Type validation tests
├── test_feature_extractors.py  # Extractor tests
├── test_trust_weights.py       # Weight computation tests
└── test_tri_engine.py          # Integration tests
```

---

## 3. Usage

### 3.1 Basic Usage

```python
from datetime import datetime, timedelta
from core.risk.tri_engine import EventSummary, TRIEngine

# Create event summary (populated from governance stores)
now = datetime.utcnow()
events = EventSummary(
    window_start=now - timedelta(hours=24),
    window_end=now,
    total_decisions=100,
    denied_decisions=5,
    last_event_time=now - timedelta(minutes=30),
    gameday_passing=130,
    gameday_total=133,
)

# Compute TRI
engine = TRIEngine()
result = engine.compute(events, now)

# Access results
print(f"TRI: {result.tri}")           # 0.0-1.0 score
print(f"Tier: {result.tier}")         # MINIMAL/LOW/MODERATE/HIGH/CRITICAL
print(f"Confidence: [{result.confidence.lower}, {result.confidence.upper}]")
```

### 3.2 JSON Output

```python
# Serialize for API/storage
json_output = result.to_dict()
```

Output format:
```json
{
  "tri": 0.1591,
  "confidence": {"lower": 0.0829, "upper": 0.2354},
  "tier": "MINIMAL",
  "domains": {
    "governance_integrity": {
      "score": 0.081,
      "weight": 0.4,
      "weighted_contribution": 0.0324,
      "null_count": 0
    },
    ...
  },
  "trust_weights": {
    "freshness": 1.0,
    "gameday": 1.0226,
    "evidence": 1.2,
    "density": 1.0,
    "composite": 1.0525
  },
  "metadata": {
    "computed_at": "2025-12-17T19:35:09.643290",
    "window": "24h",
    "event_count": 385,
    "feature_count": 15,
    "null_features": [],
    "model_version": "1.0.0"
  },
  "advisory_only": true
}
```

### 3.3 Contribution Table

```python
# Generate human-readable contribution table
table = result.contribution_table()

for row in table:
    print(f"{row.feature_name}: {row.value} × {row.weight} = {row.contribution}")
    print(f"  Evidence: {row.evidence}")
```

Example output:
```
Gi Denial Rate: 0.05 × 0.30 = 0.006
  Evidence: 5/100 in 24h
Gi Scope Violations: 0.18 × 0.25 = 0.018
  Evidence: 2 events in 24h
...
```

---

## 4. Feature Reference

### 4.1 Governance Integrity (GI) — Weight: 40%

| Feature ID | Description | Input Events |
|------------|-------------|--------------|
| `gi_denial_rate` | Decision denial rate | DECISION_DENIED / total |
| `gi_scope_violations` | Scope boundary violations | SCOPE_VIOLATION |
| `gi_forbidden_verbs` | DIGGI forbidden verb attempts | DIGGI_FORBIDDEN_VERB |
| `gi_tool_denials` | Tool execution denials | TOOL_EXECUTION_DENIED |
| `gi_artifact_failures` | Artifact verification failures | ARTIFACT_VERIFICATION_FAILED |

### 4.2 Operational Discipline (OD) — Weight: 35%

| Feature ID | Description | Input Events |
|------------|-------------|--------------|
| `od_drcp_rate` | DRCP trigger rate | DRCP_TRIGGERED |
| `od_diggi_corrections` | DIGGI correction count | DIGGI_CORRECTION_ISSUED |
| `od_replay_denials` | Replay attack denials | From denial registry |
| `od_envelope_violations` | Envelope boundary violations | Envelope events |
| `od_escalation_recoveries` | Escalation recovery rate | DECISION_ESCALATED |

### 4.3 System Drift (SD) — Weight: 25%

| Feature ID | Description | Input Events |
|------------|-------------|--------------|
| `sd_drift_count` | Governance drift events | GOVERNANCE_DRIFT_DETECTED |
| `sd_fingerprint_changes` | Fingerprint changes | Fingerprint events |
| `sd_boot_failures` | Boot integrity failures | GOVERNANCE_BOOT_FAILED |
| `sd_manifest_deltas` | Manifest configuration changes | Manifest events |
| `sd_freshness_violation` | Data staleness | Time since last event |

---

## 5. Trust Weights

Trust weights penalize unreliable data by multiplying the raw score.

| Weight | Range | Description |
|--------|-------|-------------|
| **TW-Freshness** | [1.0, 2.0] | Time since last event (>48h = 2.0) |
| **TW-Gameday** | [1.0, 2.0] | % of gameday scenarios passing |
| **TW-Evidence** | [1.0, 2.0] | Bound execution rate |
| **TW-Density** | [1.0, 2.0] | Events per hour (log scale) |

Composite weight = geometric mean of all four weights.

---

## 6. EventSummary Fields

The `EventSummary` dataclass is the input interface to the TRI engine:

```python
@dataclass
class EventSummary:
    # Required time context
    window_start: datetime
    window_end: datetime

    # Governance Integrity
    total_decisions: int = 0
    denied_decisions: int = 0
    scope_violations: list[dict] = None  # [{"timestamp": datetime}]
    forbidden_verb_attempts: int = 0
    tool_requests: int = 0
    tool_denials: int = 0
    artifact_verifications: int = 0
    artifact_failures: int = 0

    # Operational Discipline
    total_operations: int = 0
    drcp_triggers: int = 0
    diggi_corrections: int = 0
    replay_denials: int = 0
    envelope_violations: int = 0
    escalations: int = 0
    escalation_recoveries: int = 0

    # System Drift
    drift_events: list[dict] = None  # [{"timestamp": datetime}]
    fingerprint_changes: int = 0
    boot_attempts: int = 0
    boot_failures: int = 0
    manifest_deltas: int = 0

    # Meta
    last_event_time: Optional[datetime] = None

    # Trust weight inputs
    gameday_passing: int = 0
    gameday_total: int = 0
    bound_executions: int = 0
    total_executions: int = 0
```

---

## 7. Integration Points

### 7.1 Governance Event Store → EventSummary

The governance layer must aggregate events into an `EventSummary`. Example:

```python
def build_event_summary(
    event_store: EventStore,
    window_hours: int = 24,
) -> EventSummary:
    """Aggregate governance events into TRI input format."""
    now = datetime.utcnow()
    start = now - timedelta(hours=window_hours)

    events = event_store.query(start=start, end=now)

    return EventSummary(
        window_start=start,
        window_end=now,
        total_decisions=len([e for e in events if e.type in DECISION_TYPES]),
        denied_decisions=len([e for e in events if e.type == "DECISION_DENIED"]),
        # ... populate all fields ...
    )
```

### 7.2 TRI → Trust Center API

```python
@app.get("/trust/risk")
async def get_trust_risk() -> dict:
    """Return current TRI for Trust Center display."""
    events = build_event_summary(event_store)
    engine = TRIEngine()
    result = engine.compute(events)
    return result.to_dict()
```

### 7.3 TRI → Audit Bundle

```python
def generate_audit_bundle() -> dict:
    """Generate audit bundle with TRI contribution table."""
    events = build_event_summary(event_store, window_hours=168)  # 7 days
    engine = TRIEngine()
    result = engine.compute(events)

    return {
        "tri": result.to_dict(),
        "contributions": [
            {
                "feature": row.feature_name,
                "value": row.value,
                "weight": row.weight,
                "contribution": row.contribution,
                "evidence": row.evidence,
            }
            for row in result.contribution_table()
        ],
    }
```

---

## 8. Testing

Run the test suite:

```bash
pytest tests/risk/ -v
```

Test coverage:

| Module | Tests | Coverage |
|--------|-------|----------|
| types.py | 22 | Type bounds, serialization |
| feature_extractors.py | 35 | All extractors, bounds, monotonicity |
| trust_weights.py | 26 | Weight computation, composite |
| tri_engine.py | 22 | Integration, determinism, advisory |

Total: **105 tests**

---

## 9. CLI Demo

```bash
python -m core.risk.tri_engine --demo
```

---

## 10. Constraints Enforced

| Constraint | Enforcement |
|------------|-------------|
| No governance imports | Risk modules import only from `core.risk.*` |
| advisory_only always True | Raises ValueError if set to False |
| Bounded output | Post-init validation on all types |
| Deterministic | Pure functions, no random, no time.now() inside |
| No side effects | No writes, no events, no external calls |

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-17 | Initial implementation |

---

## 12. References

- [TRUST_RISK_TAXONOMY.md](./TRUST_RISK_TAXONOMY.md) — Signal definitions
- [TRUST_RISK_FEATURES.md](./TRUST_RISK_FEATURES.md) — Feature formulas
- [TRUST_RISK_MODEL.md](./TRUST_RISK_MODEL.md) — Composite score spec
- [TRUST_RISK_GOVERNANCE_CONTRACT.md](./TRUST_RISK_GOVERNANCE_CONTRACT.md) — Authority limits
- [TRUST_RISK_FAILURE_MODES.md](./TRUST_RISK_FAILURE_MODES.md) — Failure analysis
