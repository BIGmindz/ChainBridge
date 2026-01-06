# External Pilot Boundary Specification

**PAC Reference:** PAC-JEFFREY-P44  
**Classification:** GOVERNANCE / TRUST BOUNDARY  
**Status:** CANONICAL  
**Effective Date:** 2026-01-03  

---

## 1. Purpose

This document defines the **trust boundaries** and **capability constraints** for external pilots of the ChainBridge platform. All external pilot participants operate within these boundaries without exception.

---

## 2. Pilot Classification

| Classification | Description | Permitted |
|----------------|-------------|-----------|
| EXTERNAL_PILOT | Third-party observation and evaluation | YES |
| INTERNAL_OPERATOR | ChainBridge team operation | NO (separate PAC) |
| PRODUCTION | Live settlement with real funds | NO |
| REGULATOR | Regulatory observation mode | NO (requires P45) |

---

## 3. Trust Boundary Definitions

### 3.1 Permitted Operations (ALLOW LIST)

| Operation | Endpoint Pattern | Description |
|-----------|------------------|-------------|
| READ PDO List | `GET /oc/pdo` | View PDO records (SHADOW only) |
| READ PDO Detail | `GET /oc/pdo/{id}` | View individual PDO |
| READ Timeline | `GET /oc/pdo/{id}/timeline` | View PDO audit trail |
| READ Health | `GET /health` | System health check |
| READ Activities | `GET /occ/activities` | View activity stream |
| READ Artifacts | `GET /occ/artifacts` | View governance artifacts |
| READ Ledger Integrity | `GET /occ/dashboard/ledger/integrity` | Verify ledger state |

### 3.2 Forbidden Operations (DENY LIST)

| Operation | Reason | Enforcement |
|-----------|--------|-------------|
| CREATE PDO | No pilot writes | HTTP 403 + Audit |
| UPDATE PDO | Immutability law | HTTP 403 + Audit |
| DELETE PDO | Immutability law | HTTP 403 + Audit |
| ENGAGE Kill-Switch | Operator-only | HTTP 403 + Audit |
| ARM Kill-Switch | Operator-only | HTTP 403 + Audit |
| ACCESS Production PDOs | Classification barrier | HTTP 404 (hidden) |
| MODIFY Configuration | Operator-only | No endpoint exposed |
| ACCESS Internal Metrics | Operator-only | No endpoint exposed |

### 3.3 Capability Matrix

```
┌────────────────────────────────────────────────────────────────┐
│ EXTERNAL PILOT CAPABILITY MATRIX                               │
├────────────────────────────────────────────────────────────────┤
│ ✅ CAN: View SHADOW PDOs                                       │
│ ✅ CAN: View audit timelines                                   │
│ ✅ CAN: Verify ledger integrity                                │
│ ✅ CAN: Observe activity stream                                │
│ ✅ CAN: Check system health                                    │
├────────────────────────────────────────────────────────────────┤
│ ❌ CANNOT: Create or modify PDOs                               │
│ ❌ CANNOT: Access PRODUCTION PDOs                              │
│ ❌ CANNOT: Trigger kill-switch                                 │
│ ❌ CANNOT: View internal metrics                               │
│ ❌ CANNOT: Modify system configuration                         │
│ ❌ CANNOT: Access operator console mutations                   │
└────────────────────────────────────────────────────────────────┘
```

---

## 4. Authentication & Authorization

### 4.1 Pilot Token Requirements

| Field | Requirement |
|-------|-------------|
| Token Type | Bearer JWT |
| Issuer | ChainBridge Auth Service |
| Audience | `chainbridge-pilot` |
| Scope | `pilot:read` |
| Expiry | 24 hours maximum |
| Renewal | Manual (no auto-refresh) |

### 4.2 Pilot Permissions

```json
{
  "permissions": [
    "pdo:read:shadow",
    "timeline:read",
    "activity:read",
    "artifact:read",
    "health:read",
    "ledger:read:integrity"
  ],
  "denied": [
    "pdo:create",
    "pdo:update",
    "pdo:delete",
    "pdo:read:production",
    "kill_switch:*",
    "operator:*",
    "config:*"
  ]
}
```

---

## 5. Data Isolation

### 5.1 PDO Classification Barrier

- Pilots see ONLY `classification: SHADOW` PDOs
- PRODUCTION PDOs return HTTP 404 (not 403) to prevent enumeration
- No cross-classification queries permitted

### 5.2 Environment Isolation

| Environment | Pilot Access |
|-------------|--------------|
| Production | ❌ BLOCKED |
| Staging | ❌ BLOCKED |
| Pilot Sandbox | ✅ PERMITTED |
| Development | ❌ BLOCKED |

---

## 6. Rate Limits

| Limit Type | Value | Window |
|------------|-------|--------|
| Requests per minute | 30 | 60s |
| Requests per hour | 500 | 3600s |
| Concurrent connections | 5 | N/A |
| Burst limit | 10 | 10s |

Exceeding limits returns HTTP 429 with `Retry-After` header.

---

## 7. Audit Requirements

All pilot activity is logged with:

| Field | Description |
|-------|-------------|
| `pilot_id` | Unique pilot identifier |
| `timestamp` | ISO 8601 UTC timestamp |
| `action` | Operation attempted |
| `endpoint` | API endpoint accessed |
| `result` | SUCCESS / DENIED / ERROR |
| `ip_address` | Client IP (hashed) |

---

## 8. Forbidden Claims

External pilots are **prohibited** from making the following claims:

| Forbidden Claim | Reason |
|-----------------|--------|
| "ChainBridge processes real transactions" | No production in pilot |
| "ChainBridge is auditor-certified" | No certification claims |
| "ChainBridge replaces compliance teams" | No autonomy claims |
| "ChainBridge guarantees settlement" | No settlement in pilot |
| "ChainBridge is production-ready" | Pilot-only access |

---

## 9. Escalation Path

| Issue | Escalation |
|-------|------------|
| Authentication failure | Contact pilot coordinator |
| Rate limit exceeded | Wait for window reset |
| Unexpected behavior | File incident report |
| Security concern | Immediate escalation to SAM |
| Data discrepancy | File audit request |

---

## 10. Termination Conditions

A pilot may be terminated immediately if:

1. Forbidden claims are made publicly
2. Rate limits are systematically abused
3. Unauthorized access is attempted
4. Data is shared outside authorized channels
5. Kill-switch is triggered by operator

---

## 11. Governance References

- **INV-PILOT-001**: Pilots are capability-constrained, not trust-based
- **INV-PILOT-002**: Read-only access only
- **INV-PILOT-003**: SHADOW classification only
- **INV-PILOT-004**: No production coupling
- **INV-OC-005**: Operator Console read-only

---

## 12. Signatures

| Role | Agent | Status |
|------|-------|--------|
| Orchestration | BENSON (GID-00) | ✅ APPROVED |
| Security | SAM (GID-06) | ✅ APPROVED |
| Governance | ALEX (GID-08) | ✅ APPROVED |

---

**Document Hash:** `sha256:pilot-boundary-spec-v1.0.0`  
**Immutability Status:** SEALED
