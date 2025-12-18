# Sensitive Domain Gateway Contract

Version: 1.0
Status: LOCKED
Classification: CONTRACT (Immutable)

Contract Owner: BENSON (GID-00)
PAC Reference: PAC-BENSON-TRUST-CONSOLIDATION-01
Effective Date: 2025-12-18

---

## 1. Purpose

This document defines the **Sensitive Domain Gateway** rules for ChainBridge. These rules govern how code, documentation, and communications are produced and reviewed in sensitive domains.

**This is a contract, not a guideline.** Violations invalidate outputs.

---

## 2. Sensitive Domain Definition

### 2.1 Domains Requiring Strict Pre-Commit Discipline

**GATE-001: The following domains are classified as SENSITIVE:**

| Domain | Identifier | Scope |
|--------|------------|-------|
| PDO (Proof Decision Objects) | `pdo` | All PDO schemas, stores, and operations |
| ProofPack | `proofpack` | All ProofPack generation, verification, and export |
| Trust Center | `trust` | All trust evidence and artifact systems |
| Cryptographic Operations | `crypto` | All hash, signature, and key operations |
| Verification | `verification` | All integrity and consistency checks |
| Governance | `governance` | All agent rules and enforcement |
| Audit | `audit` | All audit trails and evidence chains |
| Settlement | `settlement` | All financial settlement logic |

### 2.2 Sensitive Domain Detection

**GATE-002: Code touching these paths is in a sensitive domain:**

```
core/occ/schemas/pdo.py
core/occ/store/pdo_store.py
core/occ/api/proofpack*.py
docs/contracts/*.md
docs/proof/*.md
gateway/pdo_*.py
src/security/*.py
```

---

## 3. Forbidden Language Patterns

### 3.1 Marketing Language

**GATE-003: The following language patterns are FORBIDDEN in sensitive domains:**

| Forbidden Term | Reason |
|----------------|--------|
| "secure" | Implies guarantee that cannot be proven |
| "trusted" | Implies external validation not provided |
| "compliant" | Implies regulatory certification not held |
| "insured" | Implies financial protection not provided |
| "guaranteed" | Implies commitment that cannot be enforced |
| "certified" | Implies external certification not obtained |
| "verified by" | Implies third-party validation not performed |
| "approved by" | Implies external approval not granted |
| "industry-leading" | Marketing language with no definition |
| "best-in-class" | Marketing language with no definition |
| "state-of-the-art" | Marketing language with no definition |
| "enterprise-grade" | Marketing language with no definition |

### 3.2 Probabilistic Language

**GATE-004: The following probabilistic patterns are FORBIDDEN:**

| Forbidden Pattern | Reason |
|-------------------|--------|
| "should work" | Implies uncertainty about behavior |
| "typically" | Implies non-deterministic behavior |
| "usually" | Implies exceptions exist |
| "in most cases" | Implies edge cases are unhandled |
| "almost always" | Implies failures are acceptable |
| "rarely fails" | Implies failures are acceptable |
| "nearly impossible" | Implies possibility exists |
| "highly unlikely" | Implies possibility exists |

### 3.3 Future Guarantee Language

**GATE-005: The following future-tense guarantees are FORBIDDEN:**

| Forbidden Pattern | Reason |
|-------------------|--------|
| "will never" | Cannot guarantee future behavior |
| "will always" | Cannot guarantee future behavior |
| "is guaranteed to" | Cannot enforce runtime guarantees |
| "ensures that" | Implies enforcement that may not exist |
| "prevents all" | Implies completeness that cannot be proven |

---

## 4. Evidence-Only Reasoning Rules

### 4.1 Evidence Requirement

**GATE-006: All claims in sensitive domains must be backed by evidence.**

Evidence types:
- Code that enforces the claim (with file path)
- Test that verifies the claim (with test name)
- Cryptographic proof (hash, signature)
- Audit trail entry

### 4.2 No Implied Behavior

**GATE-007: Behavior must be explicit, not implied.**

BAD: "The system handles edge cases appropriately."
GOOD: "The system raises `PDOImmutabilityError` when update is attempted. Test: `test_pdo_update_raises_immutability_error`."

### 4.3 No Derived Conclusions

**GATE-008: Conclusions must follow directly from evidence.**

BAD: "Since we use SHA-256, the system is secure."
GOOD: "Integrity verification uses SHA-256 hash comparison. Hash mismatch raises `PDOTamperDetectedError`."

### 4.4 No Scope Expansion

**GATE-009: Claims cannot extend beyond what the code does.**

BAD: "ProofPacks provide a complete audit trail."
GOOD: "ProofPacks contain the PDO record and referenced artifacts at export time."

---

## 5. Adversarial Reader Assumption

### 5.1 Reader Model

**GATE-010: All sensitive domain documentation assumes an adversarial reader.**

The reader is assumed to:
- Be looking for false claims
- Be looking for ambiguity to exploit
- Have legal discovery powers
- Have technical expertise to verify claims
- Have no trust relationship with ChainBridge

### 5.2 Documentation Standards

**GATE-011: Documentation must survive adversarial review.**

Standards:
- Every claim must be verifiable
- Every limitation must be explicit
- Every non-claim must be stated
- No room for misinterpretation
- No marketing framing

### 5.3 Non-Claims Section

**GATE-012: Sensitive domain specifications must include explicit non-claims.**

Every specification must include a "What This Does NOT Prove/Assert" section that explicitly states:
- What the system does not guarantee
- What the system does not validate
- What is outside scope
- What the system does not protect against

---

## 6. Pre-Commit Discipline

### 6.1 Assumptions Declaration

**GATE-013: Changes to sensitive domains must declare assumptions.**

Required declarations:
- What existing behavior is assumed correct
- What existing tests are assumed passing
- What schema is assumed canonical
- What external dependencies are assumed stable

### 6.2 Non-Goals Declaration

**GATE-014: Changes to sensitive domains must declare non-goals.**

Required non-goals:
- What this change does NOT do
- What scope is explicitly excluded
- What problems are explicitly not addressed

### 6.3 Forbidden Actions Declaration

**GATE-015: Changes to sensitive domains must declare forbidden actions.**

Required declarations:
- What claims are forbidden
- What language is forbidden
- What scope expansions are forbidden

---

## 7. Review Requirements

### 7.1 Sensitive Domain Review

**GATE-016: All changes to sensitive domains require contract review.**

Review checklist:
- [ ] No forbidden language patterns
- [ ] All claims are evidence-backed
- [ ] Non-claims are explicit
- [ ] Assumptions are declared
- [ ] Non-goals are declared
- [ ] Adversarial reader standard met

### 7.2 Documentation Review

**GATE-017: Sensitive domain documentation requires dual review.**

- Technical accuracy review (code matches docs)
- Language compliance review (no forbidden patterns)

### 7.3 Rejection Criteria

**GATE-018: Changes are rejected if any review criterion fails.**

No partial approval. All criteria must pass.

---

## 8. Enforcement Mechanisms

### 8.1 Automated Checks

**GATE-019: Forbidden language patterns are checked automatically.**

Tooling:
- Pre-commit hooks scan for forbidden terms
- CI pipeline fails on forbidden patterns
- Documentation linter validates structure

### 8.2 Manual Gates

**GATE-020: Sensitive domain changes require manual approval.**

Manual gates:
- ALEX governance check
- Contract owner sign-off
- Security review (for crypto domain)

### 8.3 Violation Response

**GATE-021: Violations trigger immediate halt.**

Response to violations:
1. Block merge/deployment
2. Log violation with context
3. Require remediation before proceeding
4. No exceptions granted

---

## 9. Domain-Specific Rules

### 9.1 PDO Domain Rules

**GATE-022: PDO domain has additional constraints:**

- No update semantics discussion (updates are impossible)
- No delete semantics discussion (deletes are impossible)
- Hash algorithm changes require version bump
- Schema changes require migration plan

### 9.2 ProofPack Domain Rules

**GATE-023: ProofPack domain has additional constraints:**

- No discussion of features not in PROOFPACK_SPEC_v1
- No claims about verification scope beyond defined steps
- No aggregation across PDOs
- No derived data in exports

### 9.3 Trust Domain Rules

**GATE-024: Trust domain has additional constraints:**

- No claims about "trust" as a guarantee
- Evidence-only framing
- No compliance assertions
- No insurance claims

### 9.4 Crypto Domain Rules

**GATE-025: Crypto domain has additional constraints:**

- Algorithm changes require ALEX approval
- Key management changes require security review
- No custom cryptography
- Only approved primitives (SHA-256, AES-256, etc.)

---

## 10. Contract Violations

Any of the following constitute a contract violation:

1. Forbidden language pattern in sensitive domain output
2. Claim without evidence
3. Missing non-claims section
4. Assumptions not declared
5. Change merged without required review
6. Automated check bypassed
7. Violation not logged

**Contract violations invalidate the output. The output must be remediated or withdrawn.**

---

## 11. Remediation Process

### 11.1 Violation Detection

**GATE-026: When a violation is detected:**

1. Halt the affected process
2. Log the violation with full context
3. Notify contract owner
4. Quarantine affected output

### 11.2 Remediation Steps

**GATE-027: Remediation requires:**

1. Identify all instances of violation
2. Correct each instance
3. Re-run all automated checks
4. Obtain manual review approval
5. Document remediation in audit trail

### 11.3 Audit Trail

**GATE-028: All violations and remediations are recorded in audit trail.**

Audit record includes:
- Violation type
- Affected artifact
- Detection method
- Remediation action
- Review approval

---

## 12. Document Control

| Field | Value |
|-------|-------|
| Contract Owner | BENSON (GID-00) |
| Created | 2025-12-18 |
| Status | LOCKED |
| PAC | PAC-BENSON-TRUST-CONSOLIDATION-01 |
| Enforcement | Pre-commit hooks, CI pipeline, manual review |
| Review Required | Any modification requires PAC approval |

---

**END OF CONTRACT — SENSITIVE_DOMAIN_GATEWAY.md**
