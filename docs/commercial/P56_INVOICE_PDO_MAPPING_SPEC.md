# Artifact 2: Invoice ↔ PDO Mapping Spec

**PAC Reference:** PAC-JEFFREY-P56  
**Classification:** COMMERCIAL / BILLING  
**Status:** DELIVERED  
**Author:** PAX (GID-05)  
**Date:** 2026-01-03

---

## 1. Overview

This specification defines the mapping between invoices and PDOs, ensuring every charge is traceable to verified proof.

---

## 2. Mapping Architecture

```
INVOICE ↔ PDO RELATIONSHIP
═══════════════════════════════════════════════════════════════════

┌─────────────┐     1:N     ┌─────────────┐     1:1     ┌─────────────┐
│   INVOICE   │────────────▶│  LINE ITEM  │────────────▶│     PDO     │
└─────────────┘             └─────────────┘             └─────────────┘
       │                           │                           │
       │                           │                           │
       ▼                           ▼                           ▼
┌─────────────┐             ┌─────────────┐             ┌─────────────┐
│  CUSTOMER   │             │   PROOF     │             │   SCORE     │
└─────────────┘             │   HASH      │             │   REPORT    │
                            └─────────────┘             └─────────────┘

═══════════════════════════════════════════════════════════════════
```

---

## 3. Invoice Schema

```json
{
  "invoice_id": "INV-2026-001-0001",
  "customer_id": "ENT-001",
  "issue_date": "2026-01-03",
  "due_date": "2026-02-02",
  "currency": "USD",
  "line_items": [
    {
      "line_id": "LI-001",
      "pdo_id": "pdo-ent001-001",
      "proof_hash": "sha256:pf001...a3b",
      "description": "ChainVerify PDO Verification",
      "quantity": 1,
      "unit_price": 149.00,
      "amount": 149.00
    }
  ],
  "subtotal": 149.00,
  "tax": 0.00,
  "total": 149.00,
  "legal_disclaimer_id": "CHAINVERIFY-LEGAL-001"
}
```

---

## 4. PDO → Invoice Mapping Rules

### 4.1 Core Rules

| Rule ID | Rule | Enforcement |
|---------|------|-------------|
| MAP-001 | 1 PDO = 1 Line Item | STRICT |
| MAP-002 | 1 Proof Hash per Line Item | STRICT |
| MAP-003 | No Line Item without PDO | STRICT |
| MAP-004 | No PDO charged twice | STRICT |
| MAP-005 | Proof must predate invoice | STRICT |

### 4.2 Validation Checks

| Check | Query | Expected |
|-------|-------|----------|
| Orphan invoices | Invoice without PDO | 0 |
| Orphan charges | Line item without proof | 0 |
| Duplicate charges | Same PDO on multiple invoices | 0 |
| Timestamp order | Proof.timestamp < Invoice.timestamp | Always |

---

## 5. Invoice Generation Flow

```
PDO VERIFICATION → INVOICE GENERATION
═══════════════════════════════════════════════════════════════════

[1] PDO Created
     │
     ▼
[2] Verification Executed
     │
     ▼
[3] Proof Hash Generated
     │
     ▼
[4] Score Report Created
     │
     ▼
[5] BILLING TRIGGER ──────────────────────────────────────────────
     │
     ▼
[6] Invoice Line Item Created
     │  - pdo_id = PDO.id
     │  - proof_hash = Proof.hash
     │  - amount = Pricing.lookup(PDO.tier)
     │
     ▼
[7] Invoice Aggregated (per customer, per billing cycle)
     │
     ▼
[8] Invoice Issued
     │
     ▼
[9] Payment Collected

═══════════════════════════════════════════════════════════════════
```

---

## 6. Sample Invoice

```
┌─────────────────────────────────────────────────────────────────┐
│                         INVOICE                                 │
├─────────────────────────────────────────────────────────────────┤
│  Invoice #:     INV-2026-001-0001                               │
│  Date:          2026-01-03                                      │
│  Customer:      ENT-001 (FinTech Corp)                          │
│  Due Date:      2026-02-02                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DESCRIPTION                    QTY    UNIT PRICE    AMOUNT     │
│  ─────────────────────────────────────────────────────────────  │
│  ChainVerify PDO Verification                                   │
│    PDO: pdo-ent001-001           1      $149.00      $149.00    │
│    Proof: sha256:pf001...a3b                                    │
│                                                                 │
│  ChainVerify PDO Verification                                   │
│    PDO: pdo-ent001-002           1      $149.00      $149.00    │
│    Proof: sha256:pf001...c4d                                    │
│                                                                 │
│  ... (16 more line items)                                       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                              SUBTOTAL:            $2,682.00     │
│                              TAX:                 $    0.00     │
│                              ─────────────────────────────────  │
│                              TOTAL:               $2,682.00     │
├─────────────────────────────────────────────────────────────────┤
│  LEGAL DISCLAIMER (CHAINVERIFY-LEGAL-001):                      │
│  This invoice is for verification services only. ChainVerify    │
│  does not certify, guarantee, or warrant API security or        │
│  compliance. See full terms at chainbridge.io/legal.            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Audit Trail

| Event | Stored | Immutable |
|-------|--------|-----------|
| PDO created | ✅ | ✅ |
| Verification executed | ✅ | ✅ |
| Proof hash generated | ✅ | ✅ |
| Invoice line created | ✅ | ✅ |
| Invoice issued | ✅ | ✅ |
| Payment received | ✅ | ✅ |

---

## 8. Mapping Gate

| Check | Status |
|-------|--------|
| 1:1 PDO to Line Item | ✅ PASS |
| Proof required per line | ✅ PASS |
| No orphan charges | ✅ PASS |
| Audit trail complete | ✅ PASS |

**MAPPING GATE: ✅ PASS**

---

**ARTIFACT STATUS: DELIVERED ✅**
