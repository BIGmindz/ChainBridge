# Artifact 1: SKU Catalog & Capability Map

**PAC Reference:** PAC-JEFFREY-P54  
**Classification:** COMMERCIAL / DESIGN-ONLY  
**Status:** DELIVERED  
**Author:** PAX (GID-05)  
**Date:** 2026-01-03

---

## 1. Overview

This catalog maps verified ChainBridge capabilities to sellable Stock Keeping Units (SKUs). All SKUs are design primitives—no billing or settlement is executed under this PAC.

---

## 2. SKU Inventory

### 2.1 Core Platform SKUs

| SKU ID | Name | Description | Capability Source |
|--------|------|-------------|-------------------|
| SKU-CORE-001 | ChainBridge Platform Access | Base platform access, authentication, tenant isolation | P46-P49 |
| SKU-CORE-002 | API Gateway | RESTful API access with rate limiting | P46 |
| SKU-CORE-003 | Operator Console | Web-based operator dashboard | P47, P53 |

### 2.2 ChainVerify SKUs

| SKU ID | Name | Description | Capability Source |
|--------|------|-------------|-------------------|
| SKU-CV-001 | ChainVerify Basic | API verification scoring (up to 100 PDOs/month) | P49 |
| SKU-CV-002 | ChainVerify Professional | Advanced scoring + CCI (up to 500 PDOs/month) | P49, P52 |
| SKU-CV-003 | ChainVerify Enterprise | Unlimited PDOs + custom scoring models | P49, P52 |
| SKU-CV-004 | Trust Report Export | PDF/JSON trust report generation | P49 |
| SKU-CV-005 | ProofPack Generation | Cryptographic evidence bundles | P49 |

### 2.3 ITaaS SKUs

| SKU ID | Name | Description | Capability Source |
|--------|------|-------------|-------------------|
| SKU-IT-001 | ITaaS Starter | Continuous verification (up to 1000 tests/day) | P52 |
| SKU-IT-002 | ITaaS Professional | Full verification engine (up to 10,000 tests/day) | P52 |
| SKU-IT-003 | ITaaS Enterprise | Unlimited + chaos engineering | P52 |
| SKU-IT-004 | Config Drift Detection | Real-time drift monitoring | P52 |
| SKU-IT-005 | Kill-Switch Module | Emergency halt capability | P52 |

### 2.4 Pilot SKUs

| SKU ID | Name | Description | Capability Source |
|--------|------|-------------|-------------------|
| SKU-PIL-001 | Pilot Program Entry | Shadow PDO access, controlled scope | P53 |
| SKU-PIL-002 | Pilot Extension | Extended pilot duration (+30 days) | P53 |
| SKU-PIL-003 | Pilot-to-Production Upgrade | Conversion pathway | P53 |

---

## 3. Capability-to-SKU Matrix

```
CAPABILITY                          SKU MAPPING
═══════════════════════════════════════════════════════════════════════════════
API Authentication                  → SKU-CORE-001, SKU-CORE-002
Tenant Isolation                    → SKU-CORE-001
PDO Read/Write                      → SKU-CV-001, SKU-CV-002, SKU-CV-003
Trust Scoring                       → SKU-CV-001, SKU-CV-002, SKU-CV-003
CCI Scoring                         → SKU-CV-002, SKU-CV-003
Trust Report Generation             → SKU-CV-004
ProofPack Export                    → SKU-CV-005
Continuous Verification             → SKU-IT-001, SKU-IT-002, SKU-IT-003
Chaos Testing                       → SKU-IT-003
Config Drift Detection              → SKU-IT-004
Kill-Switch                         → SKU-IT-005
Shadow PDO Access                   → SKU-PIL-001
Pilot Conversion                    → SKU-PIL-003
═══════════════════════════════════════════════════════════════════════════════
```

---

## 4. SKU Dependencies

| SKU | Requires |
|-----|----------|
| SKU-CV-002 | SKU-CORE-001 |
| SKU-CV-003 | SKU-CORE-001 |
| SKU-IT-001 | SKU-CORE-001, SKU-CV-001 |
| SKU-IT-002 | SKU-CORE-001, SKU-CV-002 |
| SKU-IT-003 | SKU-CORE-001, SKU-CV-003 |
| SKU-IT-005 | SKU-IT-002 or SKU-IT-003 |
| SKU-PIL-003 | SKU-PIL-001 |

---

## 5. SKU Exclusions (Non-Sellable)

| Capability | Reason |
|------------|--------|
| Production settlement | Not verified (future PAC) |
| Financial reporting | Requires billing PAC |
| Multi-region deployment | Infrastructure not ready |
| Custom SLA | Requires legal review |

---

## 6. Verification Traceability

| SKU | Verification Evidence |
|-----|----------------------|
| SKU-CV-* | P49 artifacts, 5385 tests |
| SKU-IT-* | P52 artifacts, ITaaS specs |
| SKU-PIL-* | P53 artifacts, pilot reports |
| SKU-CORE-* | P46-P48 foundation |

---

## 7. Commercial Gate

| Check | Status |
|-------|--------|
| All SKUs trace to verified capability | ✅ PASS |
| No unverified capability sold | ✅ PASS |
| No settlement SKUs | ✅ PASS |
| Dependencies documented | ✅ PASS |

**COMMERCIAL GATE: ✅ PASS**

---

**ARTIFACT STATUS: DELIVERED ✅**
