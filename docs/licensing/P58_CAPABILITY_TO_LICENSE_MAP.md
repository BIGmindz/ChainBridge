# P58 — Capability to License Map

**PAC:** PAC-JEFFREY-P58  
**Artifact:** 2 of 6  
**Classification:** ACCESS CONTROL  
**Status:** DELIVERED  
**Date:** 2026-01-03  

---

## 1. Executive Summary

This document maps every ChainBridge capability to the license tier that grants access. Access is capability-based, not feature-based. Each capability has a proof dependency.

---

## 2. Capability Matrix

### 2.1 ChainBoard Capabilities

| Capability | L1 | L2 | L3 | Proof Dependency |
|------------|----|----|----|--------------------|
| Dashboard View | ✅ | ✅ | ✅ | Onboarding |
| PDO List View | ✅ | ✅ | ✅ | Onboarding |
| PDO Detail View | ✅ | ✅ | ✅ | Onboarding |
| PDO Export | ✅ | ✅ | ✅ | Onboarding |
| PDO Create | ❌ | ✅ | ✅ | 10 validated PDOs |
| PDO Dispute | ❌ | ✅ | ✅ | 10 validated PDOs |
| Operator Config | ❌ | ✅ | ✅ | 10 validated PDOs |
| Settlement Controls | ❌ | ❌ | ✅ | Settlement pilot |
| Escrow Dashboard | ❌ | ❌ | ✅ | Settlement pilot |

### 2.2 ChainIQ Capabilities

| Capability | L1 | L2 | L3 | Proof Dependency |
|------------|----|----|----|--------------------|
| Trust Score View | ✅ | ✅ | ✅ | Onboarding |
| Score History | ✅ | ✅ | ✅ | Onboarding |
| Score Generation | ❌ | ✅ | ✅ | 10 validated PDOs |
| Risk Assessment | ❌ | ✅ | ✅ | 10 validated PDOs |
| Settlement Risk | ❌ | ❌ | ✅ | Settlement pilot |
| Audit Trail Full | ❌ | ✅ | ✅ | 10 validated PDOs |

### 2.3 Settlement Capabilities (P57)

| Capability | L1 | L2 | L3 | Proof Dependency |
|------------|----|----|----|--------------------|
| Settlement View | ❌ | ❌ | ✅ | Settlement pilot |
| Escrow Initiate | ❌ | ❌ | ✅ | Settlement pilot |
| Milestone Release | ❌ | ❌ | ✅ | Settlement pilot |
| Reconciliation View | ❌ | ❌ | ✅ | Settlement pilot |
| Dispute Resolution | ❌ | ❌ | ✅ | Settlement pilot |

### 2.4 API Capabilities

| Capability | L1 | L2 | L3 | Proof Dependency |
|------------|----|----|----|--------------------|
| Read API | ✅ | ✅ | ✅ | Onboarding |
| Write API | ❌ | ✅ | ✅ | 10 validated PDOs |
| Settlement API | ❌ | ❌ | ✅ | Settlement pilot |
| Webhook Receive | ✅ | ✅ | ✅ | Onboarding |
| Webhook Custom | ❌ | ✅ | ✅ | 10 validated PDOs |

---

## 3. Proof Dependency Chain

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PROOF → CAPABILITY CHAIN                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ONBOARDING         10 PDOs           50 PDOs         SETTLEMENT       │
│   VALIDATION         VALIDATED         VALIDATED       PILOT            │
│       │                  │                 │               │            │
│       ▼                  ▼                 ▼               ▼            │
│   ┌────────┐        ┌────────┐        ┌────────┐      ┌────────┐       │
│   │   L1   │───────▶│   L2   │───────▶│  L2+   │─────▶│   L3   │       │
│   │ VERIFY │        │CONTROL │        │ READY  │      │ SETTLE │       │
│   └────────┘        └────────┘        └────────┘      └────────┘       │
│       │                  │                 │               │            │
│       ▼                  ▼                 ▼               ▼            │
│   Read-only          Create/Edit       Eligible for    Full Access     │
│   Dashboard          PDOs              Settlement                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Blocked Access Patterns

| Attempted Action | License | Result | Reason |
|------------------|---------|--------|--------|
| Create PDO | L1 | ❌ BLOCKED | Requires L2 |
| Initiate Settlement | L2 | ❌ BLOCKED | Requires L3 |
| Skip to L3 | New | ❌ BLOCKED | No tier skipping |
| Settlement API | L1/L2 | ❌ BLOCKED | L3 only |

---

## 5. Capability Unlock Events

| Event | Unlocks | License Change |
|-------|---------|----------------|
| Onboarding Complete | L1 capabilities | L1 available |
| 10th PDO validated | L2 capabilities | L2 available |
| 50th PDO validated | L3 eligibility | L3 prerequisites met |
| Settlement pilot pass | Settlement | L3 activated |

---

## 6. Signature Block

| Agent | Role | Signature |
|-------|------|-----------|
| PAX (GID-05) | Capability Mapping | ✅ SIGNED |
| SONNY (GID-02) | Access Review | ✅ SIGNED |
| BENSON (GID-00) | Map Approval | ✅ SIGNED |

---

**Artifact Hash:** `sha256:p58-art2-capability-license-map`  
**Status:** DELIVERED
