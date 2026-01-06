# Artifact 4: Margin Floor Guardrails

**PAC Reference:** PAC-JEFFREY-P54  
**Classification:** COMMERCIAL / DESIGN-ONLY  
**Status:** DELIVERED  
**Author:** DAN (GID-07)  
**Date:** 2026-01-03

---

## 1. Overview

This document defines minimum margin thresholds that protect commercial viability. These are governance guardrails—enforcement requires billing PAC.

---

## 2. Margin Floor Definitions

### 2.1 Tier Margin Floors

| Tier | Minimum Gross Margin | Alert Threshold | Hard Floor |
|------|---------------------|-----------------|------------|
| T1 Starter | 50% | 55% | 45% |
| T2 Professional | 60% | 65% | 55% |
| T3 Enterprise | 70% | 75% | 65% |

### 2.2 SKU Margin Floors

| SKU Category | Minimum Margin | Alert | Hard Floor |
|--------------|----------------|-------|------------|
| ChainVerify | 80% | 82% | 75% |
| ITaaS | 85% | 87% | 80% |
| Platform | 70% | 72% | 65% |
| Add-ons | 90% | 92% | 85% |

---

## 3. Guardrail Rules

### 3.1 Pricing Guardrails

| Rule ID | Rule | Consequence |
|---------|------|-------------|
| MF-001 | Price cannot be set below cost + floor margin | BLOCK |
| MF-002 | Discount cannot reduce margin below floor | BLOCK |
| MF-003 | Custom pricing requires margin calculation | REQUIRE |
| MF-004 | Bundle pricing must meet blended floor | REQUIRE |

### 3.2 Discount Guardrails

| Discount Level | Approval Required | Margin Check |
|----------------|-------------------|--------------|
| 0-10% | Self-service | Automatic |
| 11-20% | Sales Manager | Required |
| 21-30% | VP Sales | Required + CTO notification |
| >30% | CTO | Required + Board notification |

---

## 4. Floor Enforcement Matrix

```
MARGIN ENFORCEMENT FLOW
═══════════════════════════════════════════════════════════════════════════════

                  ┌─────────────────┐
                  │  Price Request  │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Calculate Margin│
                  └────────┬────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ > Alert  │ │ < Alert  │ │ < Floor  │
        │ APPROVE  │ │ WARN     │ │ BLOCK    │
        └──────────┘ └──────────┘ └──────────┘

═══════════════════════════════════════════════════════════════════════════════
```

---

## 5. Exception Process

### 5.1 Floor Override Criteria

| Criterion | Required |
|-----------|----------|
| Strategic account designation | ✅ |
| CTO written approval | ✅ |
| Time-limited (max 6 months) | ✅ |
| Recovery plan documented | ✅ |
| Board notification (if >25% below floor) | ✅ |

### 5.2 Override Limits

| Override Type | Maximum Duration | Maximum Discount |
|---------------|------------------|------------------|
| Strategic pilot | 90 days | 50% below floor |
| Competitive response | 60 days | 30% below floor |
| Enterprise negotiation | 12 months | 20% below floor |

---

## 6. Margin Monitoring

### 6.1 Monitoring Triggers

| Metric | Trigger | Action |
|--------|---------|--------|
| Deal margin | <Alert threshold | Notify Sales Manager |
| Deal margin | <Hard floor | Block deal, escalate |
| Monthly blended margin | <Target-5% | Weekly review |
| Quarterly blended margin | <Target-10% | Board escalation |

### 6.2 Reporting Cadence

| Report | Frequency | Audience |
|--------|-----------|----------|
| Deal margin report | Per-deal | Sales |
| Weekly margin summary | Weekly | Sales Leadership |
| Monthly margin analysis | Monthly | Executive Team |
| Quarterly margin review | Quarterly | Board |

---

## 7. Margin Recovery Protocols

### 7.1 Below-Floor Recovery

| Severity | Margin Gap | Recovery Actions |
|----------|------------|------------------|
| Warning | 0-5% below | Price adjustment at renewal |
| Critical | 5-10% below | Immediate price correction plan |
| Emergency | >10% below | Customer offboarding consideration |

### 7.2 Recovery Timeline

| Gap | Maximum Recovery Time |
|-----|-----------------------|
| <5% | Next renewal |
| 5-10% | 90 days |
| >10% | 30 days or escalate |

---

## 8. Guardrail Governance

| Check | Status |
|-------|--------|
| All tiers have floors | ✅ PASS |
| Override process defined | ✅ PASS |
| Escalation paths clear | ✅ PASS |
| No settlement execution | ✅ PASS |

**GUARDRAIL GATE: ✅ PASS**

---

## 9. Floor Summary Table

```
MARGIN FLOORS BY TIER
═══════════════════════════════════════════════════════════════════════════════

Tier        │ Target │ Alert  │ Hard Floor │ Override Max
────────────┼────────┼────────┼────────────┼─────────────
T1 Starter  │  50%   │  55%   │    45%     │    25%
T2 Pro      │  60%   │  65%   │    55%     │    35%
T3 Ent      │  70%   │  75%   │    65%     │    45%

═══════════════════════════════════════════════════════════════════════════════
```

---

**ARTIFACT STATUS: DELIVERED ✅**
