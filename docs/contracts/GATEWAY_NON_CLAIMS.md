# ChainBridge Gateway Non-Claims Contract

**Document:** GATEWAY_NON_CLAIMS.md
**Version:** 1.0
**Status:** LOCKED
**Classification:** CONTRACT (Legal Boundary Document)

**Contract Owner:** BENSON (GID-00)
**PAC Reference:** PAC-BENSON-GATEWAY-CONTRACT-01
**Effective Date:** 2025-12-18
**Alignment:** TRUST_NON_CLAIMS.md (PAC-ALEX-03)

---

## 1. Purpose

This document explicitly states what the ChainBridge Gateway **does NOT claim** to do.

**Every non-claim is a legal boundary.** These statements exist to prevent misinterpretation, over-implication, and future liability.

This document is specific to the Gateway component. For system-wide non-claims, see `TRUST_NON_CLAIMS.md`.

---

## 2. Correctness Non-Claims

### GW-NC-CORR-001: No Decision Correctness Guarantee

**The Gateway does not guarantee that ALLOW decisions are correct.**

| What Gateway Does Not Claim | Reality |
|-----------------------------|---------|
| "Allowed actions are safe" | Not claimed — Gateway enforces governance, not safety |
| "Allowed actions are optimal" | Not claimed — Gateway does not evaluate outcomes |
| "Allowed actions succeed" | Not claimed — downstream execution may still fail |

**Implication:** An ALLOW decision means governance rules passed, not that the action is correct.

---

### GW-NC-CORR-002: No Intent Correctness Guarantee

**The Gateway does not validate that intents reflect true user/agent intention.**

| What Gateway Does Not Claim | Reality |
|-----------------------------|---------|
| "Intent matches user goal" | Not claimed — Gateway validates structure, not semantics |
| "Intent is well-formed for purpose" | Not claimed — Gateway validates schema, not domain logic |
| "Intent will achieve objective" | Not claimed — outcomes are not predicted |

**Implication:** A valid intent schema does not mean the intent achieves what the submitter expects.

---

### GW-NC-CORR-003: No Business Logic Validation

**The Gateway does not validate business correctness.**

| What Gateway Does Not Claim | Reality |
|-----------------------------|---------|
| "Payment amount is correct" | Not claimed — business logic validation is downstream |
| "Resource ID is valid" | Not claimed — Gateway validates presence, not validity |
| "Metadata is meaningful" | Not claimed — Gateway passes metadata without interpretation |

**Implication:** Garbage-in, garbage-out applies within governance boundaries.

---

## 3. Optimality Non-Claims

### GW-NC-OPT-001: No Optimal Decision Guarantee

**The Gateway does not guarantee optimal decisions.**

| What Gateway Does Not Claim | Reality |
|-----------------------------|---------|
| "Best possible decision" | Not claimed — Gateway applies rules, not optimization |
| "Fastest decision" | Not claimed — performance is best-effort |
| "Most cost-effective decision" | Not claimed — cost optimization is not a Gateway function |

**Implication:** The Gateway provides deterministic rule evaluation, not optimization.

---

### GW-NC-OPT-002: No Intelligent Decision-Making

**The Gateway does not make intelligent decisions.**

| What Gateway Does Not Claim | Reality |
|-----------------------------|---------|
| "AI-powered decisions" | Not claimed — Gateway is deterministic, not ML-based |
| "Context-aware decisions" | Not claimed — Gateway evaluates explicit inputs only |
| "Learning from outcomes" | Not claimed — Gateway has no feedback loop |

**Implication:** The Gateway is a rule engine, not an intelligent system.

---

## 4. Interpretation Non-Claims

### GW-NC-INT-001: No Intent Interpretation

**The Gateway does not interpret intent.**

| What Gateway Does Not Claim | Reality |
|-----------------------------|---------|
| "Understanding user intent" | Not claimed — Gateway validates schema, not meaning |
| "Inferring missing data" | Not claimed — missing fields cause validation failure |
| "Disambiguating intents" | Not claimed — ambiguous intents fail validation |

**Implication:** Intents must be explicit and complete. The Gateway does not help.

---

### GW-NC-INT-002: No Semantic Analysis

**The Gateway does not perform semantic analysis.**

| What Gateway Does Not Claim | Reality |
|-----------------------------|---------|
| "Understanding context" | Not claimed — Gateway is stateless per-request |
| "Understanding relationships" | Not claimed — Gateway evaluates intents in isolation |
| "Understanding history" | Not claimed — Gateway has no memory of past decisions |

**Implication:** Each intent is evaluated independently with no contextual inference.

---

## 5. Certification Non-Claims

### GW-NC-CERT-001: No Model Certification

**The Gateway does not certify models.**

| What Gateway Does Not Claim | Reality |
|-----------------------------|---------|
| "Model is safe" | Not claimed — Gateway governs access, not model quality |
| "Model is accurate" | Not claimed — model evaluation is out of scope |
| "Model is fair" | Not claimed — bias detection is not a Gateway function |
| "Model is explainable" | Not claimed — explainability is ALEX rule enforcement, not Gateway |

**Implication:** Gateway ALLOW does not certify the model producing the intent.

---

### GW-NC-CERT-002: No Agent Certification

**The Gateway does not certify agents.**

| What Gateway Does Not Claim | Reality |
|-----------------------------|---------|
| "Agent is trustworthy" | Not claimed — Gateway enforces ACM, not trust |
| "Agent is authorized" | Partially — Gateway checks ACM capability, not identity |
| "Agent is who they claim" | Not claimed — authentication is out of scope |

**Implication:** Gateway enforces capability boundaries, not agent identity or trustworthiness.

---

## 6. Compliance Non-Claims

### GW-NC-COMP-001: No Compliance Guarantee

**The Gateway does not guarantee regulatory compliance.**

| What Gateway Does Not Claim | Reality |
|-----------------------------|---------|
| "SOC 2 compliant" | Not claimed — Gateway is a component, not a certified system |
| "GDPR compliant" | Not claimed — data handling is application responsibility |
| "PCI DSS compliant" | Not claimed — payment security is ChainPay responsibility |

**Implication:** Compliance requires system-level controls beyond the Gateway.

---

### GW-NC-COMP-002: No Audit Sufficiency

**The Gateway does not guarantee audit sufficiency.**

| What Gateway Does Not Claim | Reality |
|-----------------------------|---------|
| "Audit trail is complete" | Not claimed — Gateway produces evidence, not audit guarantees |
| "Audit trail is sufficient for compliance" | Not claimed — sufficiency depends on regulatory context |
| "Audit trail is tamper-proof" | Not claimed — storage security is out of scope |

**Implication:** Gateway-produced evidence is self-attested, not externally verified.

---

## 7. Insurance Non-Claims

### GW-NC-INS-001: No Insurance Replacement

**The Gateway does not replace insurance.**

| What Gateway Does Not Claim | Reality |
|-----------------------------|---------|
| "Financial protection" | Not claimed — Gateway is governance, not insurance |
| "Loss mitigation" | Not claimed — Gateway prevents unauthorized actions, not losses |
| "Liability coverage" | Not claimed — Gateway evidence is not insurance |

**Implication:** Gateway governance does not substitute for appropriate insurance coverage.

---

## 8. Bias Non-Claims

### GW-NC-BIAS-001: No Bias Removal

**The Gateway does not remove bias.**

| What Gateway Does Not Claim | Reality |
|-----------------------------|---------|
| "Unbiased decisions" | Not claimed — Gateway applies rules, which may encode bias |
| "Fair outcomes" | Not claimed — fairness is not evaluated |
| "Bias detection" | Not claimed — bias analysis is not a Gateway function |

**Implication:** If ACM rules or intents contain bias, Gateway decisions reflect that bias.

---

### GW-NC-BIAS-002: No Fairness Guarantee

**The Gateway does not guarantee fairness.**

| What Gateway Does Not Claim | Reality |
|-----------------------------|---------|
| "Equal treatment" | Not claimed — ACM rules may have differential permissions |
| "Non-discrimination" | Not claimed — Gateway enforces rules as written |
| "Equitable outcomes" | Not claimed — outcomes are not evaluated |

**Implication:** Fairness must be designed into ACM rules and business logic, not assumed from Gateway.

---

## 9. Non-Claim Summary

| Category | Non-Claims | Legal Importance |
|----------|------------|------------------|
| Correctness | 3 | **CRITICAL** — prevents over-attribution |
| Optimality | 2 | **HIGH** — sets performance expectations |
| Interpretation | 2 | **HIGH** — prevents semantic assumptions |
| Certification | 2 | **CRITICAL** — prevents false attestation |
| Compliance | 2 | **CRITICAL** — prevents regulatory misinterpretation |
| Insurance | 1 | **HIGH** — prevents financial assumptions |
| Bias | 2 | **HIGH** — prevents fairness assumptions |
| **Total** | **14** | |

---

## 10. Forbidden Implication Patterns

The following implications must **never** be made about the Gateway:

| ❌ Never Say | ✅ Instead Say |
|-------------|----------------|
| "Gateway guarantees correct decisions" | "Gateway enforces governance rules deterministically" |
| "Gateway understands intent" | "Gateway validates intent schema" |
| "Gateway certifies models" | "Gateway applies ALEX rules to model-originated intents" |
| "Gateway ensures compliance" | "Gateway produces audit evidence for compliance programs" |
| "Gateway removes bias" | "Gateway applies rules as configured" |
| "Gateway makes intelligent decisions" | "Gateway evaluates intents against deterministic rules" |
| "Gateway protects against all attacks" | "Gateway enforces authorization boundaries" |
| "Gateway ensures safety" | "Gateway fails closed on authorization failures" |

---

## 11. Relationship to TRUST_NON_CLAIMS.md

This document extends `TRUST_NON_CLAIMS.md` (PAC-ALEX-03) with Gateway-specific non-claims:

| TRUST_NON_CLAIMS Section | Gateway Extension |
|--------------------------|-------------------|
| TNC-CORR (Correctness) | GW-NC-CORR (Gateway-specific correctness) |
| TNC-CERT (Certification) | GW-NC-CERT (Model/agent certification) |
| TNC-COMP (Completeness) | GW-NC-INT (Interpretation limits) |

When in conflict, this document is authoritative for Gateway-specific non-claims.

---

## 12. Change Authority

This contract can only be modified by:

1. **BENSON (GID-00)** with new PAC reference
2. **ALEX (GID-08)** for alignment with TRUST_NON_CLAIMS.md

All changes require:
- PAC with explicit rationale
- Cross-reference to TRUST_NON_CLAIMS.md
- Legal review recommended for non-claim modifications

---

**Document Hash:** `[To be computed on commit]`
**Last Verified:** 2025-12-18
