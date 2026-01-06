# Artifact 2: Config Drift Detection Report

**PAC Reference:** PAC-JEFFREY-P52  
**Classification:** ITaaS / GOVERNED  
**Status:** DELIVERED  
**Author:** CODY (GID-01)  
**Orchestrator:** BENSON (GID-00)

---

## 1. Overview

Config Drift Detection is a core ITaaS capability that identifies configuration changes between a locked baseline and current infrastructure state. This enables continuous verification that IT systems remain in their expected configuration.

---

## 2. Drift Categories

| Category | Description | Severity Range |
|----------|-------------|----------------|
| SECURITY | Auth, permissions, encryption changes | HIGH-CRITICAL |
| NETWORK | Ports, firewall, routing changes | MEDIUM-HIGH |
| RESOURCE | Capacity, quota, limit changes | LOW-MEDIUM |
| SCHEMA | Data structure, API contract changes | MEDIUM-HIGH |
| DEPENDENCY | Library, version, package changes | MEDIUM |
| CONFIG | Application configuration changes | LOW-HIGH |

---

## 3. Drift Detection Model

```
┌─────────────────────────────────────────────────────────────────┐
│                     Drift Detection Flow                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐         ┌─────────────┐                       │
│  │   Baseline  │         │   Current   │                       │
│  │   Snapshot  │         │    State    │                       │
│  └──────┬──────┘         └──────┬──────┘                       │
│         │                       │                               │
│         └───────────┬───────────┘                               │
│                     ▼                                           │
│         ┌───────────────────────┐                               │
│         │    Diff Computation   │                               │
│         └───────────┬───────────┘                               │
│                     │                                           │
│         ┌───────────┼───────────┐                               │
│         ▼           ▼           ▼                               │
│    ┌─────────┐ ┌─────────┐ ┌─────────┐                         │
│    │ ADDED   │ │ REMOVED │ │ CHANGED │                         │
│    └────┬────┘ └────┬────┘ └────┬────┘                         │
│         │           │           │                               │
│         └───────────┼───────────┘                               │
│                     ▼                                           │
│         ┌───────────────────────┐                               │
│         │  Severity Assessment  │                               │
│         └───────────┬───────────┘                               │
│                     ▼                                           │
│         ┌───────────────────────┐                               │
│         │    Drift Event        │                               │
│         │    Emission           │                               │
│         └───────────────────────┘                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Severity Scoring

| Level | Score Range | Response | SLA |
|-------|-------------|----------|-----|
| CRITICAL | 90-100 | Immediate alert | < 1 min |
| HIGH | 70-89 | Priority alert | < 5 min |
| MEDIUM | 40-69 | Standard alert | < 15 min |
| LOW | 1-39 | Informational | < 1 hour |
| INFO | 0 | Log only | N/A |

---

## 5. Drift Event Schema

```python
@dataclass
class DriftEvent:
    """Configuration drift event."""
    event_id: str
    tenant_id: str
    category: DriftCategory
    severity: DriftSeverity
    baseline_value: Any
    current_value: Any
    path: str  # JSONPath to changed element
    detected_at: datetime
    description: str
    recommended_action: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "tenant_id": self.tenant_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "path": self.path,
            "detected_at": self.detected_at.isoformat(),
            "description": self.description,
            "recommended_action": self.recommended_action,
        }
```

---

## 6. Detection Triggers

| Trigger | Frequency | Coverage |
|---------|-----------|----------|
| Scheduled scan | Configurable (default: 15 min) | Full baseline |
| API endpoint change | On detection | Affected endpoints |
| Security configuration | Continuous | Auth/perms only |
| Manual audit request | On-demand | Full or targeted |

---

## 7. Baseline Management

### 7.1 Baseline Locking
- Baselines are immutable once locked
- New baselines require explicit operator action
- Baseline history retained for audit

### 7.2 Baseline Contents
- API schema snapshots
- Configuration manifests
- Dependency versions
- Security settings
- Resource quotas

---

## 8. Integration with Trust Scoring

Drift events directly impact CCI and Trust scores:

| Drift Level | CCI Impact | Trust Grade Impact |
|-------------|------------|-------------------|
| CRITICAL | -20 | Grade drop guaranteed |
| HIGH | -10 | Potential grade drop |
| MEDIUM | -5 | Score reduction |
| LOW | -1 | Minor reduction |
| INFO | 0 | No impact |

---

## 9. Reporting Output

### 9.1 Summary Report
```json
{
  "report_id": "drift-2026-01-03-001",
  "tenant_id": "tenant-abc",
  "scan_type": "scheduled",
  "baseline_id": "baseline-v1.2.0",
  "total_elements_checked": 1247,
  "drift_events": 3,
  "by_severity": {
    "critical": 0,
    "high": 1,
    "medium": 1,
    "low": 1
  },
  "overall_drift_score": 15.2,
  "recommendation": "REVIEW_REQUIRED"
}
```

---

## 10. Invariants

| ID | Invariant | Status |
|----|-----------|--------|
| INV-DRIFT-001 | Baselines are immutable | ENFORCED |
| INV-DRIFT-002 | All drift events logged | ENFORCED |
| INV-DRIFT-003 | Critical drift alerts < 1 min | MONITORED |
| INV-DRIFT-004 | No baseline modification by engine | ENFORCED |

---

**ARTIFACT STATUS: DELIVERED ✅**
