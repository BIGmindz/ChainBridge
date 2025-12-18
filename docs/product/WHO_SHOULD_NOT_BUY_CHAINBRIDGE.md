# Who Should Not Buy ChainBridge

**Document:** WHO_SHOULD_NOT_BUY_CHAINBRIDGE.md
**Version:** 2.0.0
**Owner:** Pax (GID-05), Product & Commercial Strategy
**PAC:** PAC-PAX-BUYER-DISQUALIFICATION-01
**Updated:** 2025-12-17
**Status:** Canonical — Customer-Facing, Sales-Enforced

---

## Purpose

This document states who should not buy ChainBridge.

Read it before requesting a demo. If any section describes you, do not proceed.

---

## TRI Reality Check

ChainBridge computes a Trust Risk Index (TRI) — a score in [0.0, 1.0] derived from governance events.

**What TRI is:**
- A deterministic scalar computed from observable events
- Bounded, explainable, and auditable
- Advisory only — TRI has zero authority over governance decisions

**What TRI is not:**
- A fraud detector
- A security score
- A compliance metric
- A guarantee of anything

**Test Evidence:** 105 tests in `tests/risk/` validate TRI computation bounds, determinism, and feature extraction.

If you expect TRI to "prevent" anything, stop here. TRI measures. It does not act.

---

## 1. If You Expect Security, Do Not Buy

**ChainBridge does not provide network, infrastructure, OS, identity provider, credential, or endpoint security.**

If you are seeking a security product, do not buy ChainBridge.

### What ChainBridge Does NOT Do:

| Category | Capabilities NOT Provided |
|----------|---------------------------|
| Network security | Firewall rules, DDoS protection, mTLS, TLS termination, IP allowlisting |
| Infrastructure security | Cloud provider security, VM hardening, container security |
| Endpoint security | Antivirus, EDR, rootkit detection, patch management |
| Credential management | Secrets storage, credential rotation, API key management, certificate management |
| Threat detection | SIEM, SOAR, SOC tooling, intrusion detection |
| Compliance certification | SOC 2, ISO 27001, FedRAMP, PCI DSS, HIPAA |

**Mapped Non-Claims:** TNC-SEC-01, TNC-SEC-02, TNC-SEC-03, TNC-SEC-04, TNC-CERT-01

### If You Need Any of These, Stop Here

ChainBridge governs agent actions. It does not secure your infrastructure, network, or operating system. If your cloud provider, OS, or network is compromised, ChainBridge controls can be bypassed.

---

## 2. If You Want Guarantees, Do Not Buy

**ChainBridge enforces governance rules and records outcomes. It does not guarantee that any system is correct, safe, secure, or free from failure.**

### What ChainBridge Does NOT Guarantee:

| Expectation | Reality |
|-------------|---------|
| Uptime guarantee | None. Availability depends on your infrastructure. |
| Correctness guarantee | None. Business logic validation is out of scope. |
| Fraud prevention guarantee | None. ChainBridge blocks unauthorized agent actions. It does not prevent fraud. |
| Security guarantee | None. ChainBridge is not a security product. |
| SLA-backed outcomes | None. No SLA exists. |
| "Safe" or "secure" systems | Not claimed. These terms have no meaning without context. |
| TRI score accuracy | None. TRI reflects observed events, not ground truth. |

**Mapped Non-Claims:** TNC-COMP-01, TNC-CORR-01, TNC-AVAIL-01, TNC-CERT-02

### If You Need Guarantees, Stop Here

ChainBridge provides documented controls and evidence. It does not promise outcomes. All software has bugs. All systems have failure modes. ChainBridge is not exempt.

---

## 3. If You Want Automation Without Accountability, Do Not Buy

**ChainBridge intentionally fails closed, emits evidence, and surfaces denials. This increases friction.**

If you want invisible automation, this product is not suitable.

### What ChainBridge Does NOT Support:

| Expectation | Reality |
|-------------|---------|
| Autonomous decisions without audit | Not supported. Every decision is logged. |
| "AI that just acts" | Not supported. Every action requires authorization. |
| Black-box scoring | Not supported. TRI features are enumerated and weighted explicitly. |
| Hidden enforcement | Not supported. Denials are surfaced, not silent. |
| Silent failure | Not supported. Failures emit events and block execution. |

**Test Evidence:** 133 adversarial "gameday" tests verify that failures are loud, not silent.

### TRI Trust Weights — Observable Penalties

TRI applies four trust weights that penalize unreliable data:

| Weight | Penalizes | Range |
|--------|-----------|-------|
| Freshness | Stale data (no events in 48h) | [1.0, 2.0] |
| Gameday | Unverified scenarios (failing tests) | [1.0, 2.0] |
| Evidence | Unbound executions (missing audit) | [1.0, 2.0] |
| Density | Sparse observations (<1 event/hour) | [1.0, 2.0] |

**Test Evidence:** 26 tests in `test_trust_weights.py` validate weight bounds and monotonicity.

If you want scores without transparency, TRI is unsuitable.

### If You Want Friction-Free Automation, Stop Here

ChainBridge creates friction by design. It blocks first, asks questions later. If you want systems that "just work" without visibility, this is the wrong product.

---

## 4. If You Need Turnkey Integration, Do Not Buy

**ChainBridge is a governance layer. It requires explicit integration, manifests, and agent registration.**

If you expect a turnkey solution, do not proceed.

### What ChainBridge Does NOT Provide:

| Expectation | Reality |
|-------------|---------|
| Plug-and-play installs | Not supported. Configuration is required. |
| Zero configuration | Not supported. Agents must be registered. |
| Drop-in compliance | Not supported. Compliance is your responsibility. |
| Out-of-the-box workflows | Not supported. Workflows require custom manifests. |
| Managed service | Not available. Self-hosted only. |
| Enterprise support | Not available. |

**Mapped Non-Claims:** TNC-CERT-02 (compliance responsibility remains with deploying organization)

### If You Need Turnkey, Stop Here

ChainBridge requires:
- Writing agent manifests (YAML)
- Registering agents in the ACM
- Integrating governance checks into your execution paths
- Operating your own infrastructure

If you do not have engineering capacity for this, do not buy.

---

## 5. If You Want Marketing Claims, Do Not Buy

**ChainBridge does not use the following phrases because they are not test-backed:**

| Phrase | Status |
|--------|--------|
| "Enterprise-grade" | ❌ Not claimed |
| "Production-ready" | ❌ Not claimed |
| "Battle-tested" | ❌ Not claimed |
| "Certified" | ❌ Not claimed |
| "Industry-leading" | ❌ Not claimed |
| "Secure by default" | ❌ Not claimed |
| "AI-powered" | ❌ Not claimed |
| "Blockchain-powered" | ❌ Not claimed |
| "Prevents fraud" | ❌ Not claimed |
| "Guarantees safety" | ❌ Not claimed |
| "Intelligent risk scoring" | ❌ Not claimed — TRI is deterministic, not intelligent |
| "Predictive" | ❌ Not claimed — TRI reflects observed events only |

**Reference:** [PRODUCT_TRUTH.md](PRODUCT_TRUTH.md) — Canonical product positioning

### If You Need These Phrases, Stop Here

If your procurement process requires vendor claims of "enterprise-grade," "production-ready," or "certified," ChainBridge cannot satisfy those requirements. These phrases have no meaning without evidence, and ChainBridge does not manufacture evidence.

---

## 6. If You Need Scale Proof, Do Not Buy

**ChainBridge has no production deployment, no load testing results, and no scale benchmarks.**

| Question | Answer |
|----------|--------|
| "How many transactions per second?" | Unknown. Untested. |
| "What's the latency at scale?" | Unknown. Untested. |
| "How does it perform under load?" | Unknown. Untested. |
| "Is it horizontally scalable?" | Unknown. Untested. |
| "How fast is TRI computation?" | Unknown at scale. Unit tests pass in milliseconds. |

### If You Need Scale Proof, Stop Here

ChainBridge has 1,079 passing tests. None of them are load tests. If your use case requires proven scale, this product cannot provide that evidence.

---

## 7. If You Need Compliance Shortcuts, Do Not Buy

**ChainBridge does not make you compliant with anything.**

| Expectation | Reality |
|-------------|---------|
| "SOC 2 compliance" | ChainBridge has no SOC 2 certification. Using it does not make you SOC 2 compliant. |
| "ISO 27001 compliance" | ChainBridge has no ISO 27001 certification. Using it does not make you ISO 27001 compliant. |
| "GDPR compliance" | ChainBridge does not handle data. GDPR compliance is your responsibility. |
| "HIPAA compliance" | ChainBridge has no healthcare-specific controls. HIPAA compliance is your responsibility. |

**Mapped Non-Claims:** TNC-CERT-01, TNC-CERT-02

### If You Need Compliance Checkbox, Stop Here

ChainBridge provides audit trails. It does not provide compliance. Your auditor will not accept "we use ChainBridge" as evidence of compliance.

---

## 8. If You Expect TRI to Replace Human Judgment, Do Not Buy

**TRI is advisory only. It has zero authority over governance decisions.**

| Expectation | Reality |
|-------------|---------|
| "TRI blocks risky actions" | ❌ False. TRI computes a score. Governance blocks actions. |
| "TRI learns from behavior" | ❌ False. TRI applies fixed weights to observed features. |
| "TRI predicts risk" | ❌ False. TRI reflects historical events, not future outcomes. |
| "Low TRI means safe" | ❌ False. TRI measures governance health, not safety. |
| "High TRI means dangerous" | ❌ False. TRI penalizes data quality issues, not threats. |

### TRI Feature Domains (15 Features, 3 Domains)

| Domain | Features | What It Measures |
|--------|----------|------------------|
| Governance Integrity | 5 | Denial rates, scope violations, forbidden verbs, tool denials, artifact failures |
| Operational Discipline | 5 | DRCP usage, DIGGI corrections, replay denials, envelope violations, escalation recoveries |
| System Drift | 5 | Drift count, fingerprint changes, boot failures, manifest deltas, freshness violations |

**Test Evidence:** 35 tests in `test_feature_extractors.py` validate feature extraction logic.

### If You Expect Automation, Stop Here

TRI produces a number. A human (or governance rule you write) decides what to do with it. TRI does not act. TRI does not prevent. TRI measures.

---

## What ChainBridge Actually Does

For context, here is what ChainBridge does do (test-backed):

### Governance Layer (974 Tests)

| Capability | Test Evidence | Test Count |
|------------|---------------|------------|
| Validates agent identity before processing | `test_gameday_forged_gid.py` | 17 |
| Rejects unknown agents | `test_acm_evaluator.py` | 24 |
| Enforces verb-based authorization | `test_acm_evaluator.py`, `test_chain_of_command.py` | 35 |
| Blocks forbidden verbs | `test_gameday_diggi_forbidden_verb.py` | 32 |
| Fails closed on authorization failure | `test_gameday_tool_without_envelope.py` | 23 |
| Verifies artifact integrity at boot | `test_gameday_artifact_mismatch.py` | 14 |
| Exports deterministic audit bundles | `test_audit_export.py` | 32 |
| Provides read-only Trust API | `test_trust_api.py` | 54 |
| Persists denials across restarts | `test_denial_registry_persistence.py` | 24 |

### TRI Computation (105 Tests)

| Capability | Test Evidence | Test Count |
|------------|---------------|------------|
| Computes deterministic TRI score | `test_tri_engine.py` | 22 |
| Bounds TRI output to [0.0, 1.0] | `test_tri_engine.py` | 22 |
| Extracts 15 governance features | `test_feature_extractors.py` | 35 |
| Computes trust weights in [1.0, 2.0] | `test_trust_weights.py` | 26 |
| Validates TRI types and schemas | `test_types.py` | 22 |

**Total Tests:** 1,079
**Adversarial Gameday Tests:** 133
**TRI-Specific Tests:** 105
**All Tests Pass:** Yes

---

## Summary: Do Not Buy If

| ❌ If You... | Reason |
|-------------|--------|
| Expect security | ChainBridge is not a security product |
| Want guarantees | ChainBridge makes no guarantees |
| Want invisible automation | ChainBridge surfaces failures loudly |
| Need turnkey integration | ChainBridge requires custom integration |
| Require marketing claims | ChainBridge does not make unverified claims |
| Need scale proof | No load testing exists |
| Need compliance shortcuts | ChainBridge does not certify anything |
| Expect TRI to act | TRI measures. It does not prevent. |

---

## If You Made It Here

If you read this document and still want to proceed, you understand:

1. ChainBridge governs agent actions. It does not secure infrastructure.
2. ChainBridge provides audit evidence. It does not guarantee outcomes.
3. ChainBridge fails closed. It creates friction.
4. ChainBridge requires integration. It is not plug-and-play.
5. ChainBridge has tests. It does not have certifications.
6. TRI is a score, not a shield. It measures governance health, not safety.

Request a technical evaluation only if you accept these constraints.

---

## Non-Claim Traceability

| Section | Mapped Non-Claims |
|---------|-------------------|
| TRI Reality | Test evidence (105 TRI tests) |
| §1 Security | TNC-SEC-01, TNC-SEC-02, TNC-SEC-03, TNC-SEC-04, TNC-CERT-01 |
| §2 Guarantees | TNC-COMP-01, TNC-CORR-01, TNC-AVAIL-01, TNC-CERT-02 |
| §3 Automation | Test evidence (gameday tests, trust weight tests) |
| §4 Turnkey | TNC-CERT-02 |
| §5 Marketing Claims | PRODUCT_TRUTH.md phrase blacklist |
| §6 Scale | No test evidence for scale |
| §7 Compliance | TNC-CERT-01, TNC-CERT-02 |
| §8 TRI Expectations | TRI engine tests (advisory-only validation) |

---

## Document Authority

This document is customer-facing and sales-enforced.

- Sales may not make claims that contradict this document
- Prospects must be directed to this document before demos
- Legal prefers this document to marketing copy

---

*This document contains no future tense. No aspirational language. No hedging. Every statement aligns with existing tests or explicit non-claims.*
