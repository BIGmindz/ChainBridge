# ChainBridge Trust Non-Claims

**Document:** TRUST_NON_CLAIMS.md
**Version:** 1.0.0
**Owner:** ALEX (GID-08), Governance & Alignment Engine
**PAC:** PAC-ALEX-03 — Trust Claims & Non-Claims Canonicalization
**Last Updated:** 2025-12-17

---

## Purpose

This document explicitly states what ChainBridge **does NOT claim** to do.

**Every non-claim is a legal boundary.** These statements exist to prevent misinterpretation, over-implication, and future liability.

---

## 1. Security Boundary Non-Claims

### TNC-SEC-01: No Infrastructure Security

**ChainBridge does not secure infrastructure.**

| What We Don't Do | Why |
|------------------|-----|
| Cloud provider security | Out of scope — platform responsibility |
| Network segmentation | Out of scope — infrastructure responsibility |
| VM/container hardening | Out of scope — ops responsibility |
| DDoS protection | Out of scope — edge responsibility |

**Implication:** If your cloud provider is breached, ChainBridge controls can be bypassed.

### TNC-SEC-02: No Operating System Security

**ChainBridge does not harden or secure operating systems.**

| What We Don't Do | Why |
|------------------|-----|
| Kernel hardening | Out of scope — OS responsibility |
| Rootkit detection | Out of scope — security tooling |
| Privilege escalation prevention (OS-level) | Out of scope — OS responsibility |
| Patch management | Out of scope — ops responsibility |

**Implication:** If the underlying OS is compromised, ChainBridge controls can be bypassed.

### TNC-SEC-03: No Credential Management

**ChainBridge does not manage, store, or rotate credentials.**

| What We Don't Do | Why |
|------------------|-----|
| Secrets storage | Out of scope — vault responsibility |
| Credential rotation | Out of scope — IAM responsibility |
| API key management | Out of scope — secrets manager |
| Certificate management | Out of scope — PKI responsibility |

**Implication:** Credential theft outside ChainBridge's boundary is not prevented.

### TNC-SEC-04: No Network Security

**ChainBridge does not provide network-level security.**

| What We Don't Do | Why |
|------------------|-----|
| TLS termination | Out of scope — load balancer |
| mTLS enforcement | Out of scope — service mesh |
| Firewall rules | Out of scope — network ops |
| IP allowlisting | Out of scope — edge security |

**Implication:** Network-level attacks are not mitigated by ChainBridge.

---

## 2. Completeness Non-Claims

### TNC-COMP-01: No Coverage Completeness Guarantee

**ChainBridge does not claim complete coverage of all attack vectors.**

| What We Don't Claim | Reality |
|---------------------|---------|
| "All attacks prevented" | False — we mitigate specific threat classes |
| "100% coverage" | False — coverage is documented, not total |
| "No vulnerabilities" | False — all software has potential vulnerabilities |

**Implication:** ChainBridge provides defense-in-depth at the governance layer, not perimeter security.

### TNC-COMP-02: No Zero-Day Protection

**ChainBridge does not protect against unknown vulnerabilities.**

| What We Don't Claim | Reality |
|---------------------|---------|
| "Zero-day immune" | False — unknown attacks may succeed |
| "Novel attack prevention" | False — we defend known threat classes |

**Implication:** Novel attack techniques may bypass existing controls.

---

## 3. Correctness Non-Claims

### TNC-CORR-01: No Correctness Guarantee

**ChainBridge does not guarantee code correctness.**

| What We Don't Claim | Reality |
|---------------------|---------|
| "Bug-free" | False — all software has bugs |
| "Logically correct" | False — business logic is out of scope |
| "Functional correctness" | False — we govern access, not computation |

**Implication:** ChainBridge governance controls do not validate business logic.

### TNC-CORR-02: No Data Correctness

**ChainBridge does not validate data correctness.**

| What We Don't Claim | Reality |
|---------------------|---------|
| "Data validation" | Out of scope — application responsibility |
| "Input sanitization" | Out of scope — application responsibility |
| "Output correctness" | Out of scope — application responsibility |

**Implication:** Garbage-in, garbage-out still applies within governance boundaries.

---

## 4. Certification Non-Claims

### TNC-CERT-01: No External Certification

**ChainBridge governance is not externally certified.**

| What We Don't Claim | Reality |
|---------------------|---------|
| SOC 2 Type II certified | Not claimed — internal controls only |
| ISO 27001 certified | Not claimed — no external audit |
| FedRAMP authorized | Not claimed — no government certification |
| PCI DSS compliant | Not claimed — not payment-specific |

**Implication:** Trust Center evidence is self-attested, not third-party verified.

### TNC-CERT-02: No Compliance Guarantee

**ChainBridge does not guarantee regulatory compliance.**

| What We Don't Claim | Reality |
|---------------------|---------|
| "GDPR compliant" | Not claimed — data handling is application-specific |
| "HIPAA compliant" | Not claimed — healthcare data is out of scope |
| "SOX compliant" | Not claimed — financial controls are application-specific |

**Implication:** Compliance responsibility remains with the deploying organization.

---

## 5. Availability Non-Claims

### TNC-AVAIL-01: No Uptime Guarantee

**ChainBridge does not guarantee availability.**

| What We Don't Claim | Reality |
|---------------------|---------|
| "99.99% uptime" | Not claimed — infrastructure-dependent |
| "Always available" | Not claimed — failures happen |
| "No downtime" | Not claimed — maintenance windows exist |

**Implication:** High availability requires infrastructure-level redundancy outside ChainBridge.

---

## 6. Attack Mitigation Non-Claims

### TNC-ATK-01: No Supply Chain Attack Prevention

**ChainBridge does not prevent supply chain attacks.**

| What We Don't Claim | Reality |
|---------------------|---------|
| "Dependency security" | Out of scope — pip/npm responsibility |
| "Package verification" | Out of scope — package manager |
| "Build pipeline security" | Partially — artifact integrity only |

**Implication:** If a malicious dependency is introduced before build, it may be included in artifacts.

### TNC-ATK-02: No Social Engineering Prevention

**ChainBridge does not prevent social engineering.**

| What We Don't Claim | Reality |
|---------------------|---------|
| "Phishing prevention" | Out of scope — human factor |
| "Insider threat prevention" | Partially — governance only, not intent |
| "Credential phishing" | Out of scope — human factor |

**Implication:** Human operators can be compromised outside ChainBridge's boundary.

### TNC-ATK-03: No Physical Security

**ChainBridge does not provide physical security.**

| What We Don't Claim | Reality |
|---------------------|---------|
| "Physical access control" | Out of scope — facility responsibility |
| "Hardware tampering detection" | Out of scope — hardware security |

**Implication:** Physical access to infrastructure bypasses all software controls.

---

## Non-Claim Summary

| Category | Non-Claims | Legal Importance |
|----------|------------|------------------|
| Security Boundary | 4 | **CRITICAL** — prevents scope misinterpretation |
| Completeness | 2 | **HIGH** — prevents over-promising |
| Correctness | 2 | **HIGH** — prevents liability |
| Certification | 2 | **CRITICAL** — prevents false attestation |
| Availability | 1 | **MEDIUM** — sets expectations |
| Attack Mitigation | 3 | **HIGH** — defines defense boundary |
| **Total** | **14** | |

---

## Forbidden Implication Patterns

The following implications must **never** be made:

| ❌ Never Say | ✅ Instead Say |
|-------------|----------------|
| "ChainBridge prevents fraud" | "ChainBridge enforces governance controls at the agent layer" |
| "ChainBridge is secure" | "ChainBridge implements documented governance controls" |
| "ChainBridge guarantees safety" | "ChainBridge fails closed on authorization failures" |
| "ChainBridge stops all attacks" | "ChainBridge mitigates documented threat classes" |
| "ChainBridge is certified" | "ChainBridge provides self-attested governance evidence" |
| "ChainBridge ensures compliance" | "ChainBridge provides audit trails for compliance programs" |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-17 | ALEX (GID-08) | Initial canonical non-claims |

---

**CANONICAL REFERENCE** — This document is the authoritative source for ChainBridge trust non-claims.
All UI copy, sales materials, and security questionnaires must reference this document to avoid over-claiming.
