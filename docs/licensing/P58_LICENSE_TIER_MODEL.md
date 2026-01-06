# P58 — License Tier Model

**PAC:** PAC-JEFFREY-P58  
**Artifact:** 1 of 6  
**Classification:** LICENSING ARCHITECTURE  
**Status:** DELIVERED  
**Date:** 2026-01-03  

---

## 1. Executive Summary

This document defines the **three-tier licensing model** for ChainBridge. Each tier is bound to proven capabilities (P55-P57), not arbitrary features. No license grants access without prior proof validation.

---

## 2. License Tier Overview

| Tier | Name | Purpose | Monthly Price | PDO Limit |
|------|------|---------|---------------|-----------|
| **L1** | VERIFY | Read-only proof verification | $499/mo | 50 PDOs |
| **L2** | CONTROL | Full operator governance | $1,499/mo | 250 PDOs |
| **L3** | SETTLE | Settlement + escrow access | $4,999/mo | 1,000 PDOs |

---

## 3. Tier Definitions

### 3.1 L1 — VERIFY

| Attribute | Value |
|-----------|-------|
| **Target** | Teams validating trust scores, read-only |
| **Seats** | Up to 3 operators (read-only) |
| **PDO Access** | View, validate, export |
| **Settlement** | ❌ NOT INCLUDED |
| **ChainBoard** | Dashboard (read-only) |
| **ChainIQ** | Score viewing only |
| **Support** | Email (48hr SLA) |

**Proof Requirement:** Must have completed onboarding validation.

### 3.2 L2 — CONTROL

| Attribute | Value |
|-----------|-------|
| **Target** | Operations teams managing supply chain trust |
| **Seats** | Up to 10 operators (5 read, 5 control) |
| **PDO Access** | Create, validate, export, dispute |
| **Settlement** | ❌ NOT INCLUDED |
| **ChainBoard** | Full operator console |
| **ChainIQ** | Score generation + audit |
| **Support** | Priority (24hr SLA) |

**Proof Requirement:** 10+ validated PDOs in L1 or pilot.

### 3.3 L3 — SETTLE

| Attribute | Value |
|-----------|-------|
| **Target** | Enterprises with escrow/settlement needs |
| **Seats** | Unlimited operators |
| **PDO Access** | Full lifecycle + settlement |
| **Settlement** | ✅ INCLUDED (P57 capability) |
| **ChainBoard** | Full + settlement controls |
| **ChainIQ** | Full + settlement risk scoring |
| **Support** | Dedicated (4hr SLA) |

**Proof Requirement:** 50+ validated PDOs + settlement pilot completion.

---

## 4. Tier Progression Rules

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    LICENSE PROGRESSION PATH                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ONBOARDING ──▶ L1 (VERIFY) ──▶ L2 (CONTROL) ──▶ L3 (SETTLE)         │
│       │              │               │               │                  │
│       ▼              ▼               ▼               ▼                  │
│   Validation     10 PDOs         50 PDOs      Settlement Pilot         │
│   Required       Required        Required        Required               │
│                                                                         │
│   ┌──────────────────────────────────────────────────────────────────┐ │
│   │ NO TIER SKIPPING · PROOF GATES ENFORCED AT EACH TRANSITION       │ │
│   └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Seat Types

| Seat Type | Permissions | Available In |
|-----------|-------------|--------------|
| **READ** | View PDOs, dashboards, reports | L1, L2, L3 |
| **CONTROL** | Create, modify, dispute PDOs | L2, L3 |
| **SETTLE** | Initiate settlements, escrow | L3 only |
| **ADMIN** | User management, config | L2, L3 |

---

## 6. Overage Policy

| Tier | PDO Overage | Action |
|------|-------------|--------|
| L1 | >50 PDOs/mo | Soft block + upgrade prompt |
| L2 | >250 PDOs/mo | Soft block + upgrade prompt |
| L3 | >1,000 PDOs/mo | $4.99/PDO overage fee |

**No hard cutoffs** — grace period of 10% overage before enforcement.

---

## 7. Invariants

| Invariant | Enforcement |
|-----------|-------------|
| **NO-PROOF-NO-LICENSE** | Tier access requires proof gates |
| **NO-SKIP-TIER** | Must progress L1→L2→L3 |
| **SEAT-BOUND-ACTION** | Actions limited by seat type |
| **SETTLEMENT-L3-ONLY** | Settlement locked to L3 |

---

## 8. Signature Block

| Agent | Role | Signature |
|-------|------|-----------|
| PAX (GID-05) | Tier Strategy | ✅ SIGNED |
| DAN (GID-07) | Pricing Review | ✅ SIGNED |
| BENSON (GID-00) | Model Approval | ✅ SIGNED |

---

**Artifact Hash:** `sha256:p58-art1-license-tier-model`  
**Status:** DELIVERED
