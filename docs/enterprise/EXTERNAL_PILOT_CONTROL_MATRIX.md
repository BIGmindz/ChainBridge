# External Pilot Control Matrix

**PAC Reference:** PAC-JEFFREY-P46  
**Classification:** ENTERPRISE PILOT  
**Governance Mode:** HARD / FAIL-CLOSED  
**Version:** 1.0.0  
**Date:** 2026-01-02

---

## 1. Overview

This matrix defines the complete control surface for external pilot access to ChainBridge. It specifies what external parties CAN and CANNOT do, the gates they must pass, and the monitoring applied to their access.

### Core Principle

> **External trust is earned through restriction, not access.**

---

## 2. Pilot Participant Categories

### 2.1 Category Definitions

| Category | Code | Description | Trust Level |
|----------|------|-------------|-------------|
| Enterprise Partner | `EXT-ENT` | Banks, financial institutions | MEDIUM |
| Regulator Observer | `EXT-REG` | Regulatory bodies | HIGH (read-only) |
| External Auditor | `EXT-AUD` | SOC2/ISO auditors | HIGH (read-only) |
| Technology Partner | `EXT-TECH` | Integration partners | LOW |
| Investor Observer | `EXT-INV` | Due diligence access | MINIMAL |

### 2.2 Category Capabilities

| Capability | EXT-ENT | EXT-REG | EXT-AUD | EXT-TECH | EXT-INV |
|------------|---------|---------|---------|----------|---------|
| View PDOs (Shadow) | ✅ | ✅ | ✅ | ✅ | ❌ |
| View Timelines | ✅ | ✅ | ✅ | ✅ | ❌ |
| View ProofPacks | ✅ | ✅ | ✅ | ❌ | ❌ |
| Verify Hashes | ✅ | ✅ | ✅ | ❌ | ❌ |
| Download Exports | ✅ | ✅ | ✅ | ❌ | ❌ |
| View Kill-Switch State | ✅ | ✅ | ✅ | ❌ | ❌ |
| Create Test PDOs | ✅ | ❌ | ❌ | ✅ | ❌ |
| View System Health | ✅ | ✅ | ✅ | ✅ | ✅ |
| View Demo Dashboard | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 3. Control Gates

### 3.1 Pre-Access Gates

| Gate | Name | Description | Required For |
|------|------|-------------|--------------|
| G-01 | Organization Approval | Legal/business approval | ALL |
| G-02 | NDA Execution | Signed non-disclosure | ALL |
| G-03 | Technical Contact | Named technical POC | ALL |
| G-04 | Security Review | Security questionnaire | EXT-ENT, EXT-TECH |
| G-05 | Regulatory Clearance | Regulator authorization | EXT-REG |
| G-06 | Audit Scope Definition | Defined audit boundaries | EXT-AUD |

### 3.2 Access Gates

| Gate | Name | Description | Enforcement |
|------|------|-------------|-------------|
| G-10 | Identity Verification | MFA + named account | Automatic |
| G-11 | Session Establishment | Time-bounded session | Automatic |
| G-12 | Scope Binding | Role-based access | Automatic |
| G-13 | Rate Limit Application | Per-category limits | Automatic |
| G-14 | Audit Trail Activation | All actions logged | Automatic |

### 3.3 Runtime Gates

| Gate | Name | Trigger | Action |
|------|------|---------|--------|
| G-20 | Rate Limit Breach | Exceeded limits | Throttle + alert |
| G-21 | Unauthorized Access | Denied endpoint | Block + alert |
| G-22 | Anomaly Detection | Unusual pattern | Review + possible terminate |
| G-23 | Session Expiry | Time exceeded | Terminate |
| G-24 | Kill-Switch Engagement | System halt | Block new sessions |

---

## 4. Permission Lattice by Category

### 4.1 Enterprise Partner (EXT-ENT)

```
ENTERPRISE PARTNER PERMISSIONS
├── READ
│   ├── pdo:shadow:read ✅
│   ├── pdo:shadow:list ✅
│   ├── timeline:read ✅
│   ├── proofpack:read ✅
│   ├── proofpack:verify ✅
│   ├── proofpack:download ✅
│   ├── audit:read ✅
│   ├── health:read ✅
│   └── kill_switch:view_state ✅
├── WRITE (LIMITED)
│   ├── pdo:shadow:create ✅ (test only)
│   └── pdo:shadow:update ❌
├── CONTROL
│   ├── kill_switch:* ❌
│   ├── operator:* ❌
│   └── config:* ❌
└── ADMIN
    └── * ❌
```

### 4.2 Regulator Observer (EXT-REG)

```
REGULATOR OBSERVER PERMISSIONS
├── READ
│   ├── pdo:shadow:read ✅
│   ├── pdo:shadow:list ✅
│   ├── timeline:read ✅
│   ├── proofpack:read ✅
│   ├── proofpack:verify ✅
│   ├── proofpack:download ✅
│   ├── audit:read ✅ (full)
│   ├── health:read ✅
│   ├── kill_switch:view_state ✅
│   ├── agent:view_state ✅
│   └── governance:read ✅
├── WRITE
│   └── * ❌ (NONE)
├── CONTROL
│   └── * ❌ (NONE)
└── ADMIN
    └── * ❌ (NONE)
```

### 4.3 Technology Partner (EXT-TECH)

```
TECHNOLOGY PARTNER PERMISSIONS
├── READ
│   ├── pdo:shadow:read ✅
│   ├── pdo:shadow:list ✅
│   ├── timeline:read ✅
│   ├── health:read ✅
│   └── api:docs:read ✅
├── WRITE (LIMITED)
│   └── pdo:shadow:create ✅ (test only)
├── CONTROL
│   └── * ❌ (NONE)
└── ADMIN
    └── * ❌ (NONE)
```

---

## 5. Rate Limits by Category

| Category | Req/Min | Req/Hour | Concurrent | Burst | Exports/Day |
|----------|---------|----------|------------|-------|-------------|
| EXT-ENT | 30 | 500 | 3 | 10 | 100 |
| EXT-REG | 20 | 300 | 1 | 5 | 50 |
| EXT-AUD | 20 | 300 | 1 | 5 | 50 |
| EXT-TECH | 60 | 1000 | 5 | 20 | 200 |
| EXT-INV | 10 | 100 | 1 | 3 | 10 |

---

## 6. Session Constraints

| Category | Max Duration | Idle Timeout | Refresh | Concurrent |
|----------|--------------|--------------|---------|------------|
| EXT-ENT | 8 hours | 30 min | No | 3 |
| EXT-REG | 8 hours | 30 min | No | 1 |
| EXT-AUD | 4 hours | 30 min | No | 1 |
| EXT-TECH | 12 hours | 60 min | Yes | 5 |
| EXT-INV | 2 hours | 15 min | No | 1 |

---

## 7. Data Boundaries

### 7.1 Visible Data

| Data Type | EXT-ENT | EXT-REG | EXT-AUD | EXT-TECH | EXT-INV |
|-----------|---------|---------|---------|----------|---------|
| Shadow PDOs | ✅ | ✅ | ✅ | ✅ | ❌ |
| Decision Timelines | ✅ | ✅ | ✅ | ✅ | ❌ |
| ProofPacks | ✅ | ✅ | ✅ | ❌ | ❌ |
| Audit Logs | Limited | Full | Full | ❌ | ❌ |
| System Health | ✅ | ✅ | ✅ | ✅ | ✅ |
| Agent States | ❌ | ✅ | ✅ | ❌ | ❌ |
| Governance Rules | ❌ | ✅ | ✅ | ❌ | ❌ |

### 7.2 Hidden Data (ALL Categories)

- ❌ Production PDOs
- ❌ Real financial data
- ❌ Customer PII
- ❌ Internal operator data
- ❌ System credentials
- ❌ Kill-switch control interfaces
- ❌ Agent control interfaces
- ❌ Configuration internals

---

## 8. Monitoring & Alerting

### 8.1 Real-Time Monitoring

| Metric | Threshold | Alert Level |
|--------|-----------|-------------|
| Request rate | >80% of limit | WARNING |
| Failed auth | 3+ in 5 min | HIGH |
| Denied operations | Any | MEDIUM |
| Session anomaly | Pattern deviation | HIGH |
| Bulk export | >50% quota | WARNING |

### 8.2 Alert Escalation

| Level | Response Time | Notification |
|-------|---------------|--------------|
| CRITICAL | Immediate | CTO + Security |
| HIGH | < 15 min | Security Team |
| MEDIUM | < 1 hour | Operations |
| WARNING | < 4 hours | Logged |

---

## 9. Kill-Switch Impact on External Pilots

### 9.1 When Kill-Switch is ENGAGED

| Function | Impact |
|----------|--------|
| Existing sessions | CONTINUE (read-only) |
| New sessions | BLOCKED |
| Write operations | SUSPENDED |
| Read operations | AVAILABLE |
| Exports | AVAILABLE |

### 9.2 Communication Protocol

```
KILL-SWITCH ENGAGEMENT NOTIFICATION

When kill-switch is engaged during active pilot sessions:

1. Banner displayed: "System in safety mode. Read access continues."
2. Write operations return: HTTP 503 with reason
3. New login attempts return: HTTP 503 with ETA
4. Session timer paused (doesn't count against limit)
5. Export functionality remains active
```

---

## 10. Onboarding Workflow

### 10.1 Standard Onboarding (EXT-ENT, EXT-TECH)

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL PILOT ONBOARDING                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  WEEK 1: ADMINISTRATIVE                                          │
│  ├─ NDA execution                                                │
│  ├─ Security questionnaire                                       │
│  ├─ Technical contact nomination                                 │
│  └─ Scope definition                                             │
│                                                                  │
│  WEEK 2: TECHNICAL SETUP                                         │
│  ├─ Account provisioning                                         │
│  ├─ MFA enrollment                                               │
│  ├─ API key generation (if applicable)                           │
│  └─ Test environment access                                      │
│                                                                  │
│  WEEK 3: GUIDED PILOT                                            │
│  ├─ Orientation session                                          │
│  ├─ Supervised exploration                                       │
│  ├─ Q&A with technical team                                      │
│  └─ Feedback collection                                          │
│                                                                  │
│  WEEK 4+: INDEPENDENT PILOT                                      │
│  ├─ Full pilot access (within bounds)                            │
│  ├─ Regular check-ins                                            │
│  ├─ Issue escalation path                                        │
│  └─ Pilot completion review                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Regulator Onboarding (EXT-REG)

```
REGULATOR ONBOARDING (EXPEDITED)

DAY 1: Legal & Compliance
├─ Authorization verification
├─ Scope agreement
└─ Contact establishment

DAY 2: Technical Setup
├─ Account creation
├─ MFA enrollment
└─ Access verification

DAY 3+: Active Observation
├─ Full read access
├─ Dedicated support contact
└─ On-demand briefings
```

---

## 11. Exit Protocol

### 11.1 Standard Exit

```
PILOT EXIT CHECKLIST

□ Final feedback session completed
□ All exports downloaded
□ Session terminated
□ API keys revoked (if applicable)
□ Audit log archived
□ NDA obligations confirmed
□ Exit survey completed
```

### 11.2 Emergency Exit

```
EMERGENCY EXIT (Security Incident)

1. Immediate session termination
2. All credentials revoked
3. Audit log preserved
4. Security team notified
5. Legal team notified
6. Incident documented
```

---

## 12. Governance Invariants

### INV-EXT-001: No Production Access
External pilots have zero access to production data.

### INV-EXT-002: No Control Authority
External pilots have zero control over system operations.

### INV-EXT-003: Complete Audit Trail
All external pilot actions are logged and retained.

### INV-EXT-004: Kill-Switch Supremacy
Kill-switch can block all new external sessions.

### INV-EXT-005: Session Bounded
All external sessions have hard time limits.

### INV-EXT-006: Fail-Closed Default
Unknown permissions default to DENIED.

---

## 13. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-02 | BENSON/DAN | Initial external pilot control matrix |

---

**Document Authority:** PAC-JEFFREY-P46  
**Classification:** ENTERPRISE PILOT  
**Governance:** HARD / FAIL-CLOSED
