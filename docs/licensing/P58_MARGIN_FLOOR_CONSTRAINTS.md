# P58 — Margin Floor Constraints

**PAC:** PAC-JEFFREY-P58  
**Artifact:** 3 of 6  
**Classification:** FINANCIAL GOVERNANCE  
**Status:** DELIVERED  
**Date:** 2026-01-03  

---

## 1. Executive Summary

This document defines **margin floor constraints** for all license tiers. No tier may be priced below the margin floor. CFO-defensible unit economics required.

---

## 2. Margin Floor Requirements

| Metric | Minimum | Target | Enforcement |
|--------|---------|--------|-------------|
| Gross Margin | 75% | 85% | Hard floor |
| Contribution Margin | 60% | 70% | Soft floor |
| Net Margin | 40% | 50% | Target |

---

## 3. Tier Unit Economics

### 3.1 L1 — VERIFY ($499/mo)

| Component | Amount | % of Revenue |
|-----------|--------|--------------|
| Revenue | $499 | 100% |
| Infrastructure | -$25 | 5% |
| Support (shared) | -$20 | 4% |
| Platform overhead | -$30 | 6% |
| **Gross Margin** | **$424** | **85%** ✅ |

### 3.2 L2 — CONTROL ($1,499/mo)

| Component | Amount | % of Revenue |
|-----------|--------|--------------|
| Revenue | $1,499 | 100% |
| Infrastructure | -$75 | 5% |
| Support (priority) | -$100 | 7% |
| Platform overhead | -$75 | 5% |
| **Gross Margin** | **$1,249** | **83%** ✅ |

### 3.3 L3 — SETTLE ($4,999/mo)

| Component | Amount | % of Revenue |
|-----------|--------|--------------|
| Revenue | $4,999 | 100% |
| Infrastructure | -$200 | 4% |
| Support (dedicated) | -$400 | 8% |
| Settlement ops | -$250 | 5% |
| Platform overhead | -$150 | 3% |
| **Gross Margin** | **$3,999** | **80%** ✅ |

---

## 4. Margin Validation Summary

| Tier | Price | Gross Margin | Floor (75%) | Status |
|------|-------|--------------|-------------|--------|
| L1 | $499 | 85% | 75% | ✅ PASS |
| L2 | $1,499 | 83% | 75% | ✅ PASS |
| L3 | $4,999 | 80% | 75% | ✅ PASS |

**All tiers pass margin floor validation.**

---

## 5. Discount Guardrails

| Discount Type | Max Allowed | Approval Required |
|---------------|-------------|-------------------|
| Annual prepay | 20% | Auto-approved |
| Multi-year | 25% | Sales lead |
| Volume (5+ seats) | 15% | Auto-approved |
| Strategic | 30% | JEFFREY approval |

**Hard limit:** No discount may push margin below 60%.

---

## 6. Prohibited Pricing Actions

| Action | Reason | Enforcement |
|--------|--------|-------------|
| Free tier | Margin = 0% | Blocked |
| Usage-based | Unpredictable margin | Blocked |
| Cost-plus | Exposes internals | Blocked |
| Competitor matching | Race to bottom | Blocked |

---

## 7. Margin Monitoring

| Metric | Frequency | Alert Threshold |
|--------|-----------|-----------------|
| Tier gross margin | Weekly | <78% |
| Blended margin | Monthly | <80% |
| Discount utilization | Monthly | >40% of deals |
| Support cost ratio | Monthly | >10% of revenue |

---

## 8. Signature Block

| Agent | Role | Signature |
|-------|------|-----------|
| DAN (GID-07) | Unit Economics | ✅ SIGNED |
| PAX (GID-05) | Pricing Strategy | ✅ SIGNED |
| BENSON (GID-00) | Margin Approval | ✅ SIGNED |

---

**Artifact Hash:** `sha256:p58-art3-margin-floor-constraints`  
**Status:** DELIVERED
