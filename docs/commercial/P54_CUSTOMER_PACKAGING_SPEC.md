# Artifact 7: Customer Packaging Spec

**PAC Reference:** PAC-JEFFREY-P54  
**Classification:** COMMERCIAL / DESIGN-ONLY  
**Status:** DELIVERED  
**Author:** SONNY (GID-02)  
**Date:** 2026-01-03

---

## 1. Overview

This specification defines how ChainBridge capabilities are packaged and presented to customers. All packaging is design-only—no sales execution under this PAC.

---

## 2. Package Structure

### 2.1 Core Packages

| Package | Target Customer | Entry Price | Primary Value |
|---------|-----------------|-------------|---------------|
| **ChainBridge Starter** | SMB, Developers | $699/mo | API verification basics |
| **ChainBridge Professional** | Mid-Market | $2,199/mo | Full verification + ITaaS |
| **ChainBridge Enterprise** | Enterprise | Custom | Unlimited + customization |

### 2.2 Package Composition

```
PACKAGE CONTENTS
═══════════════════════════════════════════════════════════════════════════════

STARTER ($699/mo)
├── Platform Access
│   ├── API Gateway (10K calls/mo)
│   └── Operator Console (read-only)
├── ChainVerify Basic
│   ├── 100 PDOs/month
│   ├── Trust Scoring
│   └── Basic Reports
└── Support
    └── Email support (48hr SLA)

PROFESSIONAL ($2,199/mo)
├── Platform Access
│   ├── API Gateway (100K calls/mo)
│   └── Operator Console (full)
├── ChainVerify Professional
│   ├── 500 PDOs/month
│   ├── Trust + CCI Scoring
│   ├── PDF/JSON Reports
│   └── ProofPack Export
├── ITaaS Professional
│   ├── 10,000 tests/day
│   └── Config Drift Detection
└── Support
    └── Priority support (24hr SLA)

ENTERPRISE (Custom)
├── Platform Access
│   ├── API Gateway (unlimited)
│   └── Full Admin Console
├── ChainVerify Enterprise
│   ├── Unlimited PDOs
│   ├── Custom Scoring Models
│   └── White-label Reports
├── ITaaS Enterprise
│   ├── Unlimited tests
│   ├── Chaos Engineering
│   └── Kill-Switch Module
├── Add-ons
│   └── Custom integrations
└── Support
    └── Dedicated CSM + 4hr SLA

═══════════════════════════════════════════════════════════════════════════════
```

---

## 3. Feature Matrix

| Feature | Starter | Professional | Enterprise |
|---------|:-------:|:------------:|:----------:|
| Platform Access | ✅ | ✅ | ✅ |
| API Gateway | 10K/mo | 100K/mo | Unlimited |
| Operator Console | Read-only | Full | Admin |
| PDOs | 100/mo | 500/mo | Unlimited |
| Trust Scoring | ✅ | ✅ | ✅ |
| CCI Scoring | ❌ | ✅ | ✅ |
| Reports (Basic) | ✅ | ✅ | ✅ |
| Reports (PDF/JSON) | ❌ | ✅ | ✅ |
| ProofPack Export | ❌ | ✅ | ✅ |
| ITaaS | ❌ | 10K/day | Unlimited |
| Config Drift | ❌ | ✅ | ✅ |
| Chaos Testing | ❌ | ❌ | ✅ |
| Kill-Switch | ❌ | ❌ | ✅ |
| Custom Models | ❌ | ❌ | ✅ |
| White-label | ❌ | ❌ | ✅ |
| SLA | 48hr | 24hr | 4hr |
| Support | Email | Priority | Dedicated |

---

## 4. Add-On Packages

### 4.1 Available Add-Ons

| Add-On | Compatible With | Price |
|--------|-----------------|-------|
| Extra PDOs (100) | Starter, Pro | $99/mo |
| Extra Tests (10K) | Pro | $199/mo |
| ProofPack Export | Starter | $199/mo |
| Priority Support | Starter | $299/mo |
| Custom Integration | Enterprise | Custom |
| Dedicated Environment | Enterprise | Custom |

### 4.2 Add-On Restrictions

| Add-On | Restriction |
|--------|-------------|
| Kill-Switch | Enterprise only |
| Custom Models | Enterprise only |
| White-label | Enterprise only |
| Chaos Testing | Enterprise only |

---

## 5. Customer-Facing Names

### 5.1 Product Names

| Internal | Customer-Facing |
|----------|-----------------|
| SKU-CV-* | ChainVerify |
| SKU-IT-* | ITaaS |
| SKU-CORE-* | ChainBridge Platform |
| SKU-PIL-* | ChainBridge Pilot |

### 5.2 Feature Names

| Internal | Customer-Facing |
|----------|-----------------|
| PDO | API Profile |
| Trust Score | Verification Score |
| CCI Score | Confidence Index |
| Kill-Switch | Emergency Halt |
| ProofPack | Evidence Bundle |

---

## 6. Packaging Copy

### 6.1 Starter Package (Approved)

```
CHAINBRIDGE STARTER

Get started with API verification in minutes.

✓ Verify up to 100 APIs per month
✓ Automated trust scoring
✓ Basic verification reports
✓ Operator dashboard access
✓ Email support

Perfect for development teams and SMBs looking to
understand their API integration landscape.

$699/month
```

### 6.2 Professional Package (Approved)

```
CHAINBRIDGE PROFESSIONAL

Full-featured verification for growing organizations.

✓ Verify up to 500 APIs per month
✓ Trust + Confidence scoring
✓ PDF and JSON report export
✓ Evidence bundle generation
✓ Continuous test execution (10K/day)
✓ Configuration drift detection
✓ Priority support (24hr SLA)

Built for mid-market companies with critical
API dependencies.

$2,199/month
```

### 6.3 Enterprise Package (Approved)

```
CHAINBRIDGE ENTERPRISE

Unlimited verification with enterprise controls.

✓ Unlimited API verification
✓ Custom scoring models
✓ White-label reports
✓ Unlimited continuous testing
✓ Chaos engineering capabilities
✓ Emergency halt controls
✓ Dedicated customer success manager
✓ 4-hour support SLA

For enterprises requiring comprehensive API
governance and verification.

Contact Sales
```

---

## 7. Upgrade Paths

```
CUSTOMER JOURNEY
═══════════════════════════════════════════════════════════════════════════════

                      ┌─────────────────┐
                      │     PILOT       │
                      │    (Free)       │
                      └────────┬────────┘
                               │
                               ▼
                      ┌─────────────────┐
                      │    STARTER      │
                      │   ($699/mo)     │
                      └────────┬────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
           ┌─────────────────┐   ┌─────────────────┐
           │  PROFESSIONAL   │   │   + Add-ons     │
           │  ($2,199/mo)    │   │                 │
           └────────┬────────┘   └─────────────────┘
                    │
                    ▼
           ┌─────────────────┐
           │   ENTERPRISE    │
           │   (Custom)      │
           └─────────────────┘

═══════════════════════════════════════════════════════════════════════════════
```

---

## 8. Packaging Gate

| Check | Status |
|-------|--------|
| All packages defined | ✅ PASS |
| Feature matrix complete | ✅ PASS |
| Customer-facing names approved | ✅ PASS |
| No certification claims in copy | ✅ PASS |
| Upgrade paths clear | ✅ PASS |

**PACKAGING GATE: ✅ PASS**

---

**ARTIFACT STATUS: DELIVERED ✅**
