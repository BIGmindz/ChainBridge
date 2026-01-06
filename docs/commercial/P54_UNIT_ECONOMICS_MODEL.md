# Artifact 3: Unit Economics Model

**PAC Reference:** PAC-JEFFREY-P54  
**Classification:** COMMERCIAL / DESIGN-ONLY  
**Status:** DELIVERED  
**Author:** DAN (GID-07)  
**Date:** 2026-01-03

---

## 1. Overview

This model defines cost structures and unit economics for ChainBridge services. All figures are design estimates—no financial settlement under this PAC.

---

## 2. Cost Structure

### 2.1 Fixed Costs (Monthly)

| Category | Item | Cost/Month |
|----------|------|------------|
| Infrastructure | Cloud compute (base) | $2,500 |
| Infrastructure | Database (managed) | $800 |
| Infrastructure | Storage | $200 |
| Infrastructure | CDN/Network | $300 |
| Operations | Monitoring/Logging | $400 |
| Operations | Security tools | $500 |
| **TOTAL FIXED** | | **$4,700** |

### 2.2 Variable Costs

| Unit | Cost Driver | Cost/Unit |
|------|-------------|-----------|
| PDO | Storage + Compute | $0.12 |
| Trust Score | ML inference | $0.08 |
| Test Execution | Compute cycle | $0.003 |
| ProofPack | Storage + Generation | $0.25 |
| API Call | Gateway processing | $0.0001 |

---

## 3. Unit Economics by SKU

### 3.1 ChainVerify Economics

| SKU | Revenue/Unit | Cost/Unit | Margin |
|-----|--------------|-----------|--------|
| SKU-CV-001 (per PDO) | $2.99 | $0.20 | 93.3% |
| SKU-CV-002 (per PDO) | $2.00 | $0.28 | 86.0% |
| SKU-CV-003 (per PDO) | $1.50 | $0.30 | 80.0% |
| SKU-CV-004 (per report) | $5.00 | $0.50 | 90.0% |
| SKU-CV-005 (per pack) | $10.00 | $0.75 | 92.5% |

### 3.2 ITaaS Economics

| SKU | Revenue/Unit | Cost/Unit | Margin |
|-----|--------------|-----------|--------|
| SKU-IT-001 (per test) | $0.50 | $0.05 | 90.0% |
| SKU-IT-002 (per test) | $0.15 | $0.02 | 86.7% |
| SKU-IT-003 (per test) | $0.08 | $0.01 | 87.5% |
| SKU-IT-004 (per check) | $0.10 | $0.01 | 90.0% |
| SKU-IT-005 (per activation) | $50.00 | $0.50 | 99.0% |

---

## 4. Tier Economics (Blended)

### 4.1 Monthly Tier Analysis

| Tier | Revenue | Variable Cost | Fixed Allocation | Gross Margin |
|------|---------|---------------|------------------|--------------|
| T1 Starter | $699 | $150 | $200 | 50.0% |
| T2 Professional | $2,199 | $400 | $400 | 63.6% |
| T3 Enterprise | $7,000+ | $800 | $800 | 77.1%+ |

### 4.2 Customer Lifetime Value (CLV)

| Tier | Avg Tenure | Monthly Revenue | CLV |
|------|------------|-----------------|-----|
| T1 | 12 months | $699 | $8,388 |
| T2 | 24 months | $2,199 | $52,776 |
| T3 | 36 months | $7,000 | $252,000 |

### 4.3 Customer Acquisition Cost (CAC) Targets

| Tier | CLV | Target CAC | LTV:CAC Ratio |
|------|-----|------------|---------------|
| T1 | $8,388 | $2,000 | 4.2:1 |
| T2 | $52,776 | $10,000 | 5.3:1 |
| T3 | $252,000 | $40,000 | 6.3:1 |

---

## 5. Breakeven Analysis

### 5.1 Per-Tier Breakeven

| Tier | Fixed Costs | Contribution/Customer | Customers to Breakeven |
|------|-------------|----------------------|------------------------|
| T1 | $4,700 | $349 | 14 |
| T2 | $4,700 | $1,399 | 4 |
| T3 | $4,700 | $5,400 | 1 |

### 5.2 Platform Breakeven

```
BREAKEVEN SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

Monthly Fixed Costs:  $4,700
Target Gross Margin:  70%

Scenario A (T1 Only):     14 customers  →  $9,786/mo revenue
Scenario B (T2 Only):      4 customers  →  $8,796/mo revenue
Scenario C (Mixed):        8 T1 + 2 T2  →  $9,990/mo revenue
Scenario D (Enterprise):   1 T3         →  $7,000/mo revenue

═══════════════════════════════════════════════════════════════════════════════
```

---

## 6. Scaling Economics

### 6.1 Volume Discounts Impact

| Volume | Unit Cost Reduction | Margin Impact |
|--------|--------------------|--------------| 
| 1-100 customers | Baseline | Baseline |
| 101-500 customers | -15% | +5% margin |
| 501-1000 customers | -25% | +8% margin |
| 1000+ customers | -35% | +12% margin |

### 6.2 Infrastructure Scaling

| Customer Count | Fixed Cost | Fixed/Customer |
|----------------|------------|----------------|
| 10 | $4,700 | $470 |
| 50 | $6,000 | $120 |
| 100 | $8,000 | $80 |
| 500 | $15,000 | $30 |
| 1000 | $25,000 | $25 |

---

## 7. Risk Factors

| Risk | Impact | Mitigation |
|------|--------|------------|
| Low utilization | Margin compression | Usage-based pricing |
| High support load | Hidden costs | Tiered support |
| Overage abuse | Revenue leakage | Rate limiting |
| Churn | CLV reduction | Annual commitments |

---

## 8. Economics Gate

| Check | Status |
|-------|--------|
| All SKUs have unit economics | ✅ PASS |
| Margins above floor (50%) | ✅ PASS |
| LTV:CAC ratios healthy (>3:1) | ✅ PASS |
| Breakeven achievable | ✅ PASS |

**ECONOMICS GATE: ✅ PASS**

---

**ARTIFACT STATUS: DELIVERED ✅**
