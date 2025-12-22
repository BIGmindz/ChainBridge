# A4 — Settlement Gate Lock

> **Governance Document** — PAC-BENSON-A4-SETTLEMENT-GATE-LOCK-01
> **Version:** A4
> **Effective Date:** 2025-12-22
> **Authority:** Benson (GID-00)
> **Status:** LOCKED / CANONICAL
> **Change Authority:** Benson (GID-00) — Requires new PAC
> **Prerequisites:** A1_ARCHITECTURE_LOCK, A2_RUNTIME_BOUNDARY_LOCK, A3_PDO_ATOMIC_LOCK

---

## 0. PURPOSE

Lock settlement as a **gated, provable, irreversible transition** from:

```
PDO → Execution → Cash/Token Movement → Audit Proof
```

No money moves without passing the Settlement Gate.
No settlement occurs without a valid PDO.
No settlement is reversible after proof emission.

---

## 1. CONTEXT

| Lock | Scope | Status |
|------|-------|--------|
| A1 | Three-plane architecture | ✅ ENFORCED |
| A2 | Runtime boundary | ✅ ENFORCED |
| A3 | PDO atomic unit | ✅ ENFORCED |
| A4 | Settlement gate | 🔒 THIS DOCUMENT |

Settlement is the **economic finality layer** — where decisions become irreversible financial reality.

---

## 2. SETTLEMENT INVARIANTS (LOCKED)

```yaml
A4_SETTLEMENT_GATE_LOCK {
  settlement_is_optional: false
  settlement_requires_valid_pdo: true
  settlement_requires_signature: true
  settlement_requires_cro_clearance: true
  settlement_without_pdo: forbidden
  direct_payment_paths: forbidden
  settlement_is_irreversible: true
  settlement_emits_proof: mandatory
  proof_links_to_pdo: mandatory
  rollback_allowed: false
}
```

### Invariant Breakdown

| Invariant | Rule | Violation Response |
|-----------|------|-------------------|
| SETTLEMENT_NOT_OPTIONAL | Every execution must pass Settlement Gate | HALT |
| REQUIRES_VALID_PDO | PDO must be complete and signed | BLOCK |
| REQUIRES_SIGNATURE | Settlement authorization must be signed | BLOCK |
| REQUIRES_CRO_CLEARANCE | Ruby (GID-12) must clear or not block | BLOCK |
| NO_SETTLEMENT_WITHOUT_PDO | PDO is mandatory precondition | HALT |
| NO_DIRECT_PAYMENT | All payment rails pass through gate | BLOCK |
| IRREVERSIBLE | Once settled, no rollback | PERMANENT |
| EMITS_PROOF | Settlement produces SettlementProof | REQUIRED |
| PROOF_LINKS_PDO | Proof references originating PDO | REQUIRED |

---

## 3. SETTLEMENT FLOW (LOCKED)

```
PDO (signed, validated)
  ↓
CRO DECISION CHECK
  ↓
SETTLEMENT GATE
  ↓
SETTLEMENT PROOF CREATED
  ↓
PAYMENT RAIL EXECUTION
  ↓
AUDIT ARTIFACT
```

### Gate Preconditions

```yaml
SETTLEMENT_PRECONDITIONS {
  pdo_exists: REQUIRED
  pdo_signed: REQUIRED
  pdo_validated: REQUIRED
  cro_decision: ALLOW | NOT_BLOCKED
  settlement_eligibility: true
  all_checks_pass: REQUIRED
}
```

If any precondition fails → **SETTLEMENT BLOCKED**

---

## 4. SETTLEMENT PROOF (CANONICAL SCHEMA)

```yaml
SettlementProof {
  proof_id: UUID                      # Unique settlement identifier
  pdo_id: UUID                        # Link to originating PDO
  pdo_hash: SHA256                    # Hash of PDO at settlement time
  settlement_type: ENUM               # FIAT | TOKEN | HYBRID
  amount: DECIMAL                     # Settlement amount
  currency: STRING                    # Currency code
  destination: STRING                 # Payment destination
  rail: ENUM                          # ChainPay | Chainlink | External
  settled_at: ISO-8601                # Settlement timestamp
  signature: REQUIRED                 # Cryptographic proof
  signer_gid: REQUIRED                # Who authorized
  irreversible: true                  # Always true
}
```

### Required Fields

| Field | Required | Immutable | Description |
|-------|----------|-----------|-------------|
| proof_id | ✅ | ✅ | Unique identifier |
| pdo_id | ✅ | ✅ | Reference to PDO |
| pdo_hash | ✅ | ✅ | PDO integrity proof |
| settlement_type | ✅ | ✅ | Type classification |
| amount | ✅ | ✅ | Settlement amount |
| currency | ✅ | ✅ | Currency code |
| destination | ✅ | ✅ | Payment target |
| rail | ✅ | ✅ | Payment rail used |
| settled_at | ✅ | ✅ | Timestamp |
| signature | ✅ | ✅ | Cryptographic signature |
| signer_gid | ✅ | ✅ | Signer identity |
| irreversible | ✅ | ✅ | Always true |

---

## 5. FORBIDDEN PATTERNS (EXPLICIT)

```yaml
FORBIDDEN {
  "direct_api_to_payment"
  "settlement_without_pdo"
  "unsigned_settlement"
  "reversible_settlement"
  "settlement_before_cro_check"
  "payment_rail_bypass"
  "proof_omission"
  "mutable_settlement_proof"
  "backdated_settlement"
}
```

| Pattern | Why Forbidden |
|---------|---------------|
| direct_api_to_payment | Bypasses governance entirely |
| settlement_without_pdo | No decision authority |
| unsigned_settlement | No proof of authorization |
| reversible_settlement | Undermines finality |
| settlement_before_cro_check | Risk bypass |
| payment_rail_bypass | Untracked money movement |
| proof_omission | No audit trail |
| mutable_settlement_proof | Breaks integrity |
| backdated_settlement | Fraudulent timestamp |

**No warnings. No exceptions.**

---

## 6. AGENT AUTHORITY BINDING

| Agent | GID | Settlement Scope |
|-------|-----|------------------|
| **Benson** | GID-00 | Settlement schema, gate orchestration |
| **Ruby** | GID-12 | CRO clearance decision |
| **Sam** | GID-06 | Threat validation before settlement |
| **Dan** | GID-07 | CI enforcement of settlement gates |
| **Cody** | GID-01 | Settlement service implementation |

```yaml
AGENT_SETTLEMENT_BINDING {
  BENSON: {
    scope: ["schema", "orchestration", "gate_design"]
    can_authorize_settlement: true
  }
  RUBY: {
    scope: ["cro_clearance"]
    can_block_settlement: true
    can_authorize_settlement: false
  }
  SAM: {
    scope: ["threat_validation"]
    can_block_settlement: true
    can_authorize_settlement: false
  }
  DAN: {
    scope: ["ci_enforcement"]
    can_gate_deployment: true
  }
  CODY: {
    scope: ["implementation"]
    can_authorize_settlement: false
  }
}
```

---

## 7. CI / GOVERNANCE ENFORCEMENT

Required gates (FAIL-CLOSED):

| Gate | Check | Failure Response |
|------|-------|------------------|
| PDO reference | Settlement references valid PDO | BLOCK |
| CRO decision | CRO clearance present | BLOCK |
| Signature check | Settlement is signed | BLOCK |
| Proof emission | SettlementProof created | BLOCK |
| Proof integrity | Proof links to PDO hash | BLOCK |
| Irreversibility | No rollback mechanisms | BLOCK |

```yaml
CI_GATES {
  settlement_pdo_reference: REQUIRED
  settlement_cro_check: REQUIRED
  settlement_signature: REQUIRED
  settlement_proof_emission: REQUIRED
  settlement_proof_integrity: REQUIRED
  settlement_irreversibility: REQUIRED
  mode: FAIL_CLOSED
}
```

---

## 8. PAYMENT RAILS

All supported payment rails MUST pass through Settlement Gate:

| Rail | Type | Settlement Required |
|------|------|---------------------|
| **ChainPay** | Fiat | ✅ MANDATORY |
| **Chainlink** | Token/Cross-chain | ✅ MANDATORY |
| **External** | Third-party | ✅ MANDATORY |

```yaml
PAYMENT_RAIL_BINDING {
  ChainPay: {
    type: "FIAT"
    settlement_gate: REQUIRED
    direct_access: FORBIDDEN
  }
  Chainlink: {
    type: "TOKEN"
    settlement_gate: REQUIRED
    direct_access: FORBIDDEN
  }
  External: {
    type: "THIRD_PARTY"
    settlement_gate: REQUIRED
    direct_access: FORBIDDEN
  }
}
```

**No rail may be accessed directly. All go through Settlement Gate.**

---

## 9. CANONICAL PROMPTS (REUSE VERBATIM)

### 🔒 Settlement Readiness Check

```
Before settlement:
1. Does a valid, signed PDO exist?
2. Has CRO (Ruby) cleared or not blocked?
3. Is settlement_eligibility = true in PDO?
4. Is the payment rail available?

If any check fails → BLOCK SETTLEMENT
```

### 🔒 Settlement Execution Prompt

```
Executing settlement:
- proof_id: [generated UUID]
- pdo_id: [from PDO]
- pdo_hash: [computed hash]
- settlement_type: [FIAT/TOKEN/HYBRID]
- amount: [value]
- currency: [code]
- destination: [target]
- rail: [ChainPay/Chainlink/External]
- settled_at: [ISO-8601]
- signature: [pending]
- signer_gid: [pending]
- irreversible: true

Settlement incomplete until signed and proof emitted.
```

### 🔒 Post-Settlement Audit Prompt

```
Settlement complete:
- proof_id: [UUID]
- linked to pdo_id: [UUID]
- amount: [value] [currency]
- rail: [rail used]
- settled_at: [timestamp]
- irreversible: CONFIRMED

This settlement cannot be rolled back.
Audit artifact created.
```

---

## 10. LOCK DECLARATION

```yaml
A4_SETTLEMENT_GATE_LOCK {
  version: "A4"
  status: "LOCKED"
  enforced: true
  mutable: false
  scope: "ALL_PAYMENT_RAILS"
  rollback_allowed: false
  next_step: "A5_PROOF_AUDIT_SURFACE_LOCK"
}
```

---

## RELATIONSHIP TO A1/A2/A3

| Lock | Scope | Relationship |
|------|-------|--------------|
| A1 | Architecture (three planes) | Settlement is Proof Plane output |
| A2 | Runtime boundary | Runtime executes settlement, doesn't decide |
| A3 | PDO atomic unit | PDO is required input to Settlement Gate |
| A4 | Settlement gate | Converts PDO → Economic finality |

A4 is the **economic boundary** — where decisions become money movement.

---

🟦🟩 **BENSON (GID-00)** — Chief Architect & Orchestrator
