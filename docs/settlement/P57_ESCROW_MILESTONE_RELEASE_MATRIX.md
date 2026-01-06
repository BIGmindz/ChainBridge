# P57 — Escrow & Milestone Release Matrix

**PAC:** PAC-JEFFREY-P57  
**Artifact:** 2 of 6  
**Classification:** SETTLEMENT OPERATIONS  
**Status:** DELIVERED  
**Date:** 2026-01-03  

---

## 1. Executive Summary

This matrix defines the **escrow percentages, milestone triggers, and release schedules** for all settlement types. Every release is bound to a PDO and requires explicit trigger satisfaction before funds move.

---

## 2. Escrow Configuration by Settlement Type

### 2.1 Standard Settlement (Most Common)

| Phase | Escrow % | Trigger | Release Amount |
|-------|----------|---------|----------------|
| Invoice Paid | 100% held | Payment confirmation | 0% |
| PDO Validated | 100% held | Proof hash confirmed | 0% |
| Milestone 1: Delivery | 70% released | Delivery confirmation | 70% |
| Milestone 2: Acceptance | 30% released | Acceptance period (7 days) | 30% |

### 2.2 Express Settlement (Low-Risk Repeat Customers)

| Phase | Escrow % | Trigger | Release Amount |
|-------|----------|---------|----------------|
| Invoice Paid | 100% held | Payment confirmation | 0% |
| PDO Validated | 0% held | Proof hash confirmed | 100% |

**Eligibility:** Trust score ≥ 85, 10+ successful PDOs, 0 disputes

### 2.3 High-Value Settlement ($10K+)

| Phase | Escrow % | Trigger | Release Amount |
|-------|----------|---------|----------------|
| Invoice Paid | 100% held | Payment confirmation | 0% |
| PDO Validated | 100% held | Proof hash confirmed | 0% |
| Milestone 1: Initial | 80% held | 48hr review period | 20% |
| Milestone 2: Delivery | 50% held | Delivery confirmation | 30% |
| Milestone 3: Acceptance | 20% held | Customer sign-off | 30% |
| Milestone 4: Final | 0% held | 14-day dispute window | 20% |

### 2.4 Disputed Settlement

| Phase | Escrow % | Trigger | Release Amount |
|-------|----------|---------|----------------|
| Dispute Filed | 100% frozen | Dispute event | 0% |
| Investigation | 100% frozen | N/A | 0% |
| Resolution: Buyer Wins | 100% refunded | Resolution decision | -100% (refund) |
| Resolution: Seller Wins | 0% held | Resolution decision | 100% |
| Resolution: Split | Variable | Resolution decision | Per ruling |

---

## 3. Milestone Release Rules

### 3.1 Mandatory Conditions (All Releases)

| Condition | Requirement | Enforcement |
|-----------|-------------|-------------|
| PDO Valid | Hash exists in ledger | Automated |
| No Active Disputes | Dispute count = 0 | Automated |
| Escrow Funded | Funds confirmed | Automated |
| Kill-Switch Clear | Not triggered | Automated |
| Compliance Clear | No flags | Automated |

### 3.2 Milestone-Specific Triggers

| Milestone | Trigger Event | Verification |
|-----------|---------------|--------------|
| **Delivery** | Delivery confirmation event | Carrier API / Customer confirm |
| **Acceptance** | Acceptance window expires | Time-based (7-14 days) |
| **Sign-Off** | Customer explicit approval | UI action + signature |
| **Final Release** | Dispute window expires | Time-based (14-30 days) |

---

## 4. Escrow Hold Durations

| Settlement Type | Total Hold Duration | Early Release Eligibility |
|-----------------|---------------------|---------------------------|
| Standard | 7-21 days | After acceptance milestone |
| Express | 0 days | Immediate on PDO validation |
| High-Value | 21-45 days | After sign-off milestone |
| Disputed | Indefinite | After resolution |

---

## 5. Release Calculation Examples

### Example 1: Standard PDO ($149)

```
PDO Amount: $149.00
Platform Fee (10%): $14.90
Net Settlement: $134.10

Milestone 1 (70%): $93.87 → Released on delivery
Milestone 2 (30%): $40.23 → Released after 7 days
```

### Example 2: High-Value PDO ($15,000)

```
PDO Amount: $15,000.00
Platform Fee (8%): $1,200.00
Net Settlement: $13,800.00

Milestone 1 (20%): $2,760.00 → Released after 48hr review
Milestone 2 (30%): $4,140.00 → Released on delivery
Milestone 3 (30%): $4,140.00 → Released on sign-off
Milestone 4 (20%): $2,760.00 → Released after 14-day window
```

---

## 6. Escrow Account Structure

| Account Type | Purpose | Settlement Eligible |
|--------------|---------|---------------------|
| `ESCROW_HOLDING` | Funds awaiting release | No |
| `ESCROW_PENDING` | Funds in milestone review | No |
| `ESCROW_CLEARED` | Funds approved for release | Yes |
| `ESCROW_DISPUTED` | Funds frozen for dispute | No |
| `ESCROW_REFUND` | Funds marked for return | No (refund only) |

---

## 7. Release Event Schema

```json
{
  "release_id": "REL-2026-00001",
  "settlement_id": "STL-2026-00001",
  "pdo_hash": "sha256:abc123...",
  "milestone": "DELIVERY",
  "escrow_id": "ESC-2026-00089",
  "release_amount_cents": 9387,
  "remaining_escrow_cents": 4023,
  "timestamp": "2026-01-03T14:30:00Z",
  "trigger_event": "DELIVERY_CONFIRMED",
  "verification": {
    "type": "CARRIER_API",
    "reference": "TRACK-12345"
  }
}
```

---

## 8. Escrow Limits & Caps

| Metric | Limit | Enforcement |
|--------|-------|-------------|
| Max Single Escrow | $50,000 | Automated block |
| Max Daily Releases | $500,000 | Rate limiting |
| Max Open Escrows | 1,000 | Queue management |
| Min Settlement Amount | $10.00 | Automated floor |

---

## 9. Exception Handling

| Scenario | Action | Escalation |
|----------|--------|------------|
| Milestone timeout | Auto-escalate to HELD | Operator review |
| Partial delivery | Pro-rata release calculation | Manual approval |
| Customer unresponsive | 30-day auto-acceptance | System default |
| Escrow funding failure | Settlement cancelled | Refund initiated |

---

## 10. Signature Block

| Agent | Role | Signature |
|-------|------|-----------|
| PAX (GID-05) | Escrow Strategy | ✅ SIGNED |
| DAN (GID-07) | Release Integrity | ✅ SIGNED |
| BENSON (GID-00) | Matrix Approval | ✅ SIGNED |

---

**Artifact Hash:** `sha256:p57-art2-escrow-milestone-matrix`  
**Status:** DELIVERED
