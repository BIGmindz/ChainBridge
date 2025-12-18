# ChainBridge Product Truth

**Document:** PRODUCT_TRUTH.md
**Version:** 1.0.0
**Owner:** Pax (GID-05), Product & Smart Contract Strategy
**PAC:** PAC-PAX-TRUST-POSITIONING-01
**Created:** 2025-12-17
**Status:** Canonical — Do not modify without PAC approval

---

## Purpose

This document defines what ChainBridge is today. Every statement is either:
- Backed by a passing automated test, OR
- Explicitly marked as a non-claim

This document exists to prevent credibility debt.

---

## 1. Canonical Product Definition

> **ChainBridge is a software framework that enforces agent identity validation, verb-based authorization, and fail-closed execution blocking at the governance layer. It provides deterministic audit bundles and a read-only evidence API. All behaviors are verified by 974 automated tests, including 133 adversarial "gameday" simulations.**

### Breakdown of Claims (Each Backed by Tests)

| Claim | Test Evidence | Test Count |
|-------|---------------|------------|
| Agent identity validation | `tests/governance/gameday/test_gameday_forged_gid.py` | 17 |
| Unknown agent rejection | `tests/governance/test_acm_evaluator.py` | 24 |
| Verb-based authorization | `tests/governance/test_acm_evaluator.py`, `test_chain_of_command.py` | 35 |
| Forbidden verb enforcement | `tests/governance/gameday/test_gameday_diggi_forbidden_verb.py` | 32 |
| Fail-closed execution blocking | `tests/governance/gameday/test_gameday_tool_without_envelope.py` | 23 |
| Artifact integrity verification | `tests/governance/gameday/test_gameday_artifact_mismatch.py` | 14 |
| Deterministic audit export | `tests/governance/test_audit_export.py` | 32 |
| Read-only Trust API | `tests/api/test_trust_api.py` | 54 |
| Denial persistence (replay protection) | `tests/governance/test_denial_registry_persistence.py` | 24 |
| Governance event retention | `tests/governance/test_event_retention.py` | 39 |

**Total Governance Tests:** 545
**Total Adversarial Gameday Tests:** 133
**Total Repository Tests:** 974
**All Tests Pass:** Yes (verified 2025-12-17)

---

## 2. Explicit Non-Definitions

### ChainBridge Is NOT:

| What It Is NOT | Why This Matters |
|----------------|------------------|
| A security platform | Does not provide network, OS, or infrastructure security |
| A compliance certification | No SOC2, ISO 27001, or FedRAMP attestation exists |
| An enterprise product | No production deployment, scale testing, or SLA exists |
| A blockchain | No distributed ledger, no consensus mechanism |
| A smart contract platform | No on-chain execution, no token economics |
| An AI safety solution | Does not prevent model misbehavior or hallucination |
| A secrets manager | Does not store, rotate, or manage credentials |
| A production-ready system | No load testing, no HA deployment, no incident response |

### What ChainBridge Cannot Guarantee:

| Non-Guarantee | Reality |
|---------------|---------|
| "Prevents all attacks" | Only mitigates tested threat classes |
| "Zero vulnerabilities" | All software has potential vulnerabilities |
| "100% coverage" | Coverage is documented, not total |
| "Zero-day protection" | Unknown attacks may succeed |
| "Scale performance" | No load testing has been performed |
| "Uptime SLA" | No production deployment exists |

---

## 3. Valid Buyer Profile (Today)

### Who Can Realistically Evaluate Value:

| Buyer Type | Why Valid |
|------------|-----------|
| **Technical evaluators** doing due diligence | Can inspect tests, read code, verify claims |
| **Security researchers** assessing governance models | Can review threat coverage, gameday scenarios |
| **Internal engineering teams** evaluating architecture | Can integrate, extend, run tests |
| **Investors** conducting technical DD | Can audit test coverage and code quality |

### What Valid Buyers Expect:

- Access to source code
- Ability to run the full test suite
- Documentation that matches implementation
- Explicit non-claims alongside claims

---

## 4. Invalid Buyer Profile (Today)

### Who Should NOT Be Sold To:

| Buyer Type | Why Invalid |
|------------|-------------|
| **Production workload customers** | No production deployment exists |
| **Compliance-driven buyers** (SOC2, ISO, etc.) | No certifications exist |
| **Buyers expecting SLAs** | No uptime or support commitments exist |
| **Buyers expecting managed service** | Self-hosted only, no ops support |
| **Buyers expecting "enterprise-grade"** | Term is meaningless without scale proof |
| **Buyers expecting blockchain benefits** | No blockchain is implemented |

### Red Flags in Buyer Conversations:

- "Is this SOC2 compliant?" → No
- "What's your SLA?" → None exists
- "How many transactions per second?" → Unknown, untested
- "Is this production-ready?" → No
- "Do you have enterprise support?" → No

---

## 5. Claim Expansion Checklist (Test-Gated)

### Future Claims Require Proof:

| Desired Claim | Required Evidence Before Claim |
|---------------|--------------------------------|
| "Production-ready" | Load test results, HA deployment proof, incident playbook |
| "Enterprise-grade" | Scale test at 10K+ req/sec, multi-region deployment, 99.9% uptime over 90 days |
| "SOC2 compliant" | Completed SOC2 Type II audit report |
| "Secure" | Third-party penetration test report, no critical findings |
| "Battle-tested" | 6+ months production traffic, documented incident history |
| "Blockchain-backed" | Implemented consensus mechanism, on-chain state proof |
| "AI-safe" | Published safety benchmark results, red team findings |
| "Certified" | Specific certification document from recognized body |

### Claim Expansion Protocol:

1. New test(s) must exist proving the capability
2. Test must pass in CI for 30+ days
3. Evidence artifact must be generated and hashed
4. [docs/trust/TRUST_CLAIMS.md](../trust/TRUST_CLAIMS.md) must be updated with traceability
5. This document must be updated with new claim row

---

## 6. Phrase Blacklist (Never Use Externally)

The following phrases are **forbidden** in external communications until evidence exists:

- ❌ "Enterprise-grade"
- ❌ "Production-ready"
- ❌ "Battle-tested"
- ❌ "Compliant with X" (any compliance framework)
- ❌ "Certified"
- ❌ "Secure" (as a standalone adjective)
- ❌ "Guaranteed"
- ❌ "Prevents all X"
- ❌ "Zero X" (zero vulnerabilities, zero risk, etc.)
- ❌ "Will" / "Aims to" / "Designed to" (future tense claims)
- ❌ "Next-generation"
- ❌ "Industry-leading"
- ❌ "Best-in-class"
- ❌ "Blockchain-powered" (not implemented)
- ❌ "AI-powered" (no ML in governance path)
- ❌ "Military-grade"
- ❌ "Bank-grade"
- ❌ "Unhackable"

---

## 7. Phrase Whitelist (Always Safe)

The following phrases are **safe** because they map to test evidence:

- ✅ "Agent identity is validated before processing" (17 tests)
- ✅ "Unknown agents are rejected" (24 tests)
- ✅ "Authorization is verb-based" (35 tests)
- ✅ "Execution is fail-closed" (133 adversarial tests)
- ✅ "Denials are persisted across restarts" (24 tests)
- ✅ "Audit bundles are deterministic" (32 tests)
- ✅ "The Trust API is read-only" (54 tests)
- ✅ "X tests exist verifying Y behavior" (factual count)
- ✅ "All tests pass" (if true at time of statement)
- ✅ "Source code is available for inspection"
- ✅ "Test coverage for governance layer is N%" (if measured)
- ✅ "Governance events are retained for audit" (39 tests)
- ✅ "Artifact integrity is hash-verified at boot" (14 tests)

---

## 8. Document Authority

This document is the **canonical source of product truth**.

- All external communications must be consistent with this document
- Sales materials that contradict this document are invalid
- Marketing claims that exceed this document are invalid
- Roadmap items do not belong in this document

### Update Protocol:

1. New capability is implemented
2. Tests are written and pass
3. PAC is filed requesting claim expansion
4. This document is updated via PAC approval
5. [TRUST_CLAIMS.md](../trust/TRUST_CLAIMS.md) is updated in parallel

---

## Signature Block

| Role | Agent | Acknowledgment |
|------|-------|----------------|
| Product Truth Owner | Pax (GID-05) | Authored |
| Governance Enforcer | ALEX (GID-08) | Must approve changes |
| DevOps Validation | DAN (GID-07) | Test evidence verified |

---

*This document contains no future tense claims. Every positive statement maps to passing tests. A lawyer could not reasonably interpret this as a guarantee. A sales rep cannot stretch this without visibly lying.*
