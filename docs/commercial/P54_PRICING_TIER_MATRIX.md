# Artifact 2: Pricing Tier Matrix

**PAC Reference:** PAC-JEFFREY-P54  
**Classification:** COMMERCIAL / DESIGN-ONLY  
**Status:** DELIVERED  
**Author:** PAX (GID-05)  
**Date:** 2026-01-03

---

## 1. Overview

This matrix defines pricing tiers for ChainBridge SKUs. Prices are design primitives—no billing is executed under this PAC.

---

## 2. Tier Structure

### 2.1 Platform Tiers

| Tier | Name | Monthly Base | Target Segment |
|------|------|--------------|----------------|
| T0 | Pilot | $0 | Evaluation |
| T1 | Starter | $499 | SMB / Early Adopter |
| T2 | Professional | $1,999 | Mid-Market |
| T3 | Enterprise | Custom | Enterprise / Strategic |

---

## 3. ChainVerify Pricing

### 3.1 Tier Breakdown

| Tier | SKUs Included | PDOs/Month | Price/Month |
|------|---------------|------------|-------------|
| T0-CV | SKU-CV-001 (limited) | 10 | $0 |
| T1-CV | SKU-CV-001 | 100 | $299 |
| T2-CV | SKU-CV-002, SKU-CV-004 | 500 | $999 |
| T3-CV | SKU-CV-003, SKU-CV-004, SKU-CV-005 | Unlimited | $2,999+ |

### 3.2 Overage Pricing

| Tier | Overage Rate |
|------|--------------|
| T1-CV | $5/PDO |
| T2-CV | $3/PDO |
| T3-CV | Included |

---

## 4. ITaaS Pricing

### 4.1 Tier Breakdown

| Tier | SKUs Included | Tests/Day | Price/Month |
|------|---------------|-----------|-------------|
| T0-IT | None | N/A | N/A |
| T1-IT | SKU-IT-001 | 1,000 | $499 |
| T2-IT | SKU-IT-002, SKU-IT-004 | 10,000 | $1,499 |
| T3-IT | SKU-IT-003, SKU-IT-004, SKU-IT-005 | Unlimited | $3,999+ |

### 4.2 Overage Pricing

| Tier | Overage Rate |
|------|--------------|
| T1-IT | $0.05/test |
| T2-IT | $0.02/test |
| T3-IT | Included |

---

## 5. Bundle Pricing

### 5.1 Platform Bundles

| Bundle | Components | Price/Month | Savings |
|--------|------------|-------------|---------|
| ChainBridge Starter | T1-CV + T1-IT | $699 | 12% |
| ChainBridge Professional | T2-CV + T2-IT + Operator Console | $2,199 | 16% |
| ChainBridge Enterprise | T3-CV + T3-IT + All Add-ons | Custom | Negotiated |

---

## 6. Pilot Pricing

| Pilot Type | Duration | Price | Conversion Credit |
|------------|----------|-------|-------------------|
| Standard Pilot | 30 days | $0 | None |
| Extended Pilot | 60 days | $499 | 100% to first invoice |
| Enterprise Pilot | 90 days | Custom | Negotiated |

---

## 7. Annual Commitment Discounts

| Commitment | Discount |
|------------|----------|
| Monthly | 0% |
| Annual (prepaid) | 15% |
| Multi-year (2yr) | 25% |
| Multi-year (3yr) | 30% |

---

## 8. Pricing Matrix Visualization

```
PRICING TIERS BY CAPABILITY
═══════════════════════════════════════════════════════════════════════════════

                    T0 (Pilot)    T1 (Starter)   T2 (Pro)      T3 (Enterprise)
                    ──────────    ────────────   ─────────     ───────────────
ChainVerify         $0            $299           $999          $2,999+
ITaaS               N/A           $499           $1,499        $3,999+
Platform Base       $0            $499           $1,999        Custom
──────────────────────────────────────────────────────────────────────────────
BUNDLE              $0            $699           $2,199        Custom

═══════════════════════════════════════════════════════════════════════════════
```

---

## 9. Pricing Guardrails

| Rule | Description |
|------|-------------|
| PRICE-GUARD-001 | No discount > 30% without CTO approval |
| PRICE-GUARD-002 | No custom pricing without Enterprise tier |
| PRICE-GUARD-003 | Pilot-to-paid conversion requires 100% of T1+ |
| PRICE-GUARD-004 | Annual commitment required for >25% discount |

---

## 10. Pricing Gate

| Check | Status |
|-------|--------|
| All tiers mapped to SKUs | ✅ PASS |
| Overage rates defined | ✅ PASS |
| Discount limits set | ✅ PASS |
| No settlement execution | ✅ PASS |

**PRICING GATE: ✅ PASS**

---

**ARTIFACT STATUS: DELIVERED ✅**
