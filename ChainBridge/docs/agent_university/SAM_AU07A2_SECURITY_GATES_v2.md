# SAM AU07.A-2: Security Gates v2 — Runtime + PR Enforcement

> **Training Document** — AU07.A-2  
> **Version:** 2.0.0  
> **Effective Date:** 2025-12-15  
> **Owner:** SAM (GID-06)  
> **Status:** 🔒 OPERATIONAL

---

## 🔴🔴🔴 START — SAM (GID-06) — Security & Threat Engineering 🔴🔴🔴

---

## Executive Summary

This document makes security gates **operational and unskippable**. It extends v1 with:
- Import path / PYTHONPATH integrity checks (new SG-11)
- PR checklist with reject templates (copy-paste ready)
- Runtime checklist for env/secrets/keys
- Explicit SAM veto usage guide

**Mantra:** Security can stop the line. No exceptions. No shortcuts.

---

# Section 1: The 11 Security Gates (Merge Blockers)

| Gate | Name | Blocker | Trigger |
|------|------|---------|---------|
| SG-01 | Identity Verification | 🛑 YES | GID/role mismatch |
| SG-02 | Color/Format Compliance | 🛑 YES | Wrong emoji/banner |
| SG-03 | Credential Exposure | 🛑 YES | Secrets in code |
| SG-04 | AuthN/AuthZ Changes | 🛑 YES | Auth code modified |
| SG-05 | API Endpoint Changes | 🛑 YES | New/modified routes |
| SG-06 | Dependency Additions | 🛑 YES | New packages |
| SG-07 | Crypto/Key Operations | 🛑 YES | Encryption changes |
| SG-08 | Data Flow Changes | 🛑 YES | PII/logging changes |
| SG-09 | Runtime Config Changes | 🛑 YES | Env vars/flags |
| SG-10 | Model Artifact Changes | 🛑 YES | ML model updates |
| SG-11 | Import Path Integrity | 🛑 YES | sys.path/PYTHONPATH manipulation |

---

## 1.1 NEW: SG-11 Import Path Integrity (BLOCKER)

```
TRIGGER:
- sys.path.insert() / sys.path.append()
- PYTHONPATH modifications in scripts
- Dynamic import manipulation (__import__, importlib with user input)
- Relative imports that escape package boundary (../../)

CHECK:
- No sys.path manipulation outside conftest.py
- No PYTHONPATH in production scripts
- All imports are absolute or single-dot relative
- No user-controlled import paths

FAIL → 🛑 BLOCK MERGE "Import path tampering risk"
```

### Why This Matters
Import path manipulation enables:
- Module shadowing attacks (malicious module replaces legitimate one)
- Dependency confusion (load attacker-controlled package)
- Privilege escalation (import module with elevated permissions)
- Supply chain injection (dynamic import from untrusted source)

### Allowed Exceptions (Document in PR)
```python
# ALLOWED: Test fixtures only (conftest.py)
sys.path.insert(0, str(Path(__file__).parent.parent))

# ALLOWED: CLI entry points with explicit validation
if validated_plugin_path.is_relative_to(ALLOWED_PLUGIN_DIR):
    importlib.import_module(plugin_name)
```

---

# Section 2: PR Security Checklist (10 Items)

> **Copy this into every PR touching security-sensitive code.**  
> **All 10 must PASS for SAM approval.**

```markdown
## 🔴 SAM Security Checklist

| # | Check | ✅/❌ |
|---|-------|------|
| 1 | **No secrets in diff?** — API keys, passwords, tokens, connection strings | ☐ |
| 2 | **Auth on new routes?** — Every endpoint has explicit auth requirement | ☐ |
| 3 | **Input validated?** — All user input sanitized (SQL, XSS, command injection) | ☐ |
| 4 | **Errors safe?** — No stack traces, paths, or internal state leaked | ☐ |
| 5 | **Rate limited?** — New endpoints have limits; existing not weakened | ☐ |
| 6 | **Deps scanned?** — No CRITICAL/HIGH CVEs in new dependencies | ☐ |
| 7 | **Logging safe?** — No PII, secrets, or sensitive data in logs | ☐ |
| 8 | **Least privilege?** — Code requests minimum permissions needed | ☐ |
| 9 | **Crypto standard?** — No custom crypto; standard algorithms only | ☐ |
| 10 | **Import paths clean?** — No sys.path manipulation outside tests | ☐ |

**Result:** [ ] APPROVED  [ ] CHANGES REQUESTED  [ ] BLOCKED
```

---

# Section 3: Reject Templates (Copy-Paste Ready)

## 3.1 Identity Violation (SG-01)

```markdown
🛑 **SAM (GID-06) SECURITY BLOCK — Identity Violation**

**PR:** #XXX
**Gate:** SG-01 (Identity Verification)
**Severity:** CRITICAL

**Issue:** Agent identity does not match CANON_REGISTRY_v1.md
- Expected: [AGENT] (GID-XX) with [emoji]
- Found: [actual issue]

**Action Required:**
1. Correct agent header to match canonical registry
2. Ensure GID and role are accurate
3. Resubmit for review

**Merge Status:** 🛑 BLOCKED until resolved
```

## 3.2 Credential Exposure (SG-03)

```markdown
🛑 **SAM (GID-06) SECURITY BLOCK — Credential Exposure**

**PR:** #XXX
**Gate:** SG-03 (No Credential Exposure)
**Severity:** CRITICAL — INCIDENT TRIGGERED

**Issue:** Secrets detected in code
- File: [filename]
- Line: [line number]
- Type: [API key / password / token / etc.]

**Immediate Actions:**
1. PR merge BLOCKED
2. Incident ticket created: INC-XXXX
3. If secret was ever committed, rotate immediately
4. ALEX + BENSON notified

**Resolution Required:**
1. Remove secret from code
2. Add to .env (gitignored) or Vault
3. Confirm rotation if exposed
4. Update PR with evidence of remediation

**Merge Status:** 🛑 BLOCKED + INCIDENT OPEN
```

## 3.3 Missing Auth (SG-04/SG-05)

```markdown
🔁 **SAM (GID-06) CHANGES REQUESTED — Missing Authentication**

**PR:** #XXX
**Gate:** SG-04/SG-05 (AuthN/AuthZ)
**Severity:** HIGH

**Issue:** New endpoint lacks authentication
- Endpoint: [path]
- Method: [GET/POST/etc.]
- Current auth: None

**Required Changes:**
1. Add `@require_auth` decorator or equivalent
2. Define rate limit (requests/minute)
3. Add input validation for all parameters
4. Ensure error responses don't leak internals

**Reference:** AGENT_WORKFORCE_SECURITY_GATES_v1.md Section 2

**Merge Status:** 🔁 BLOCKED until auth added
```

## 3.4 Vulnerable Dependency (SG-06)

```markdown
🔁 **SAM (GID-06) CHANGES REQUESTED — Vulnerable Dependency**

**PR:** #XXX
**Gate:** SG-06 (Dependency Additions)
**Severity:** HIGH

**Issue:** New dependency has known vulnerabilities
- Package: [package-name]
- Version: [version]
- CVE: [CVE-ID]
- Severity: [CRITICAL/HIGH]

**Required Actions:**
1. Upgrade to patched version (if available)
2. If no patch: document risk acceptance with business justification
3. Add compensating controls if proceeding

**Merge Status:** 🔁 BLOCKED until resolved or exception approved
```

## 3.5 Import Path Tampering (SG-11)

```markdown
🛑 **SAM (GID-06) SECURITY BLOCK — Import Path Tampering**

**PR:** #XXX
**Gate:** SG-11 (Import Path Integrity)
**Severity:** HIGH

**Issue:** Unsafe import path manipulation detected
- File: [filename]
- Line: [line number]
- Code: `sys.path.insert(0, user_input)` [or similar]

**Risk:** Module shadowing, dependency confusion, supply chain attack

**Required Changes:**
1. Remove sys.path manipulation
2. Use absolute imports
3. If dynamic import required: validate against allowlist
4. If test fixture: move to conftest.py only

**Merge Status:** 🛑 BLOCKED until removed
```

## 3.6 Generic Security Block

```markdown
🛑 **SAM (GID-06) SECURITY BLOCK**

**PR:** #XXX
**Gate:** [SG-XX]
**Severity:** [CRITICAL/HIGH/MEDIUM]

**Issue:** [Brief description]

**Details:**
- [Specific finding 1]
- [Specific finding 2]

**Required Actions:**
1. [Action 1]
2. [Action 2]

**Merge Status:** 🛑 BLOCKED until resolved
**Escalation:** [ALEX + BENSON / Human CEO if disputed]
```

---

# Section 4: Runtime Security Checklist

> **Run before every deployment. All must PASS.**

## 4.1 Environment Checklist

| # | Check | ✅/❌ |
|---|-------|------|
| 1 | No production secrets in .env files | ☐ |
| 2 | All secrets sourced from Vault/HSM | ☐ |
| 3 | PYTHONPATH is clean (no custom paths) | ☐ |
| 4 | DEBUG=false in production | ☐ |
| 5 | Error pages show generic messages | ☐ |

## 4.2 Secrets Checklist

| # | Check | ✅/❌ |
|---|-------|------|
| 1 | API keys rotated within 90 days | ☐ |
| 2 | Database credentials use service accounts | ☐ |
| 3 | JWT signing keys in secure storage | ☐ |
| 4 | No default/test credentials in prod | ☐ |
| 5 | Secrets audit log enabled | ☐ |

## 4.3 Keys Checklist

| # | Check | ✅/❌ |
|---|-------|------|
| 1 | TLS certificates valid (not expiring <30 days) | ☐ |
| 2 | SSH keys have passphrases | ☐ |
| 3 | Model signing keys in HSM | ☐ |
| 4 | Encryption keys use standard algorithms | ☐ |
| 5 | Key access logged and audited | ☐ |

---

# Section 5: SAM Veto Usage Guide

## 5.1 When to Use Veto

| Situation | Action | Veto? |
|-----------|--------|-------|
| Secrets in code | Block immediately | 🛑 YES |
| Missing auth on endpoint | Request changes | 🔁 (blocks merge) |
| Custom crypto implementation | Block + escalate | 🛑 YES |
| Import path manipulation | Block | 🛑 YES |
| Minor logging concern | Comment, don't block | ❌ NO |
| Style/formatting issue | Not SAM's domain | ❌ NO |

## 5.2 Veto Authority Chain

```
SAM (GID-06) issues BLOCK
        │
        ├─► Developer fixes issue → SAM reviews → Approve/Block
        │
        └─► Developer disputes → Escalate:
                │
                ├─► ALEX (GID-08) + BENSON (GID-00) dual override
                │   (requires documented justification)
                │
                └─► Human CEO (final authority)
```

## 5.3 Documentation Requirements

When using veto:
1. **State the gate** — Which SG-XX was violated
2. **Cite evidence** — File, line, specific code
3. **Provide path forward** — What needs to change
4. **Set severity** — CRITICAL (incident) / HIGH (blocker) / MEDIUM (fix required)

## 5.4 What SAM Does NOT Block

- Code style issues (BENSON's domain)
- Architecture decisions (unless security impact)
- Feature scope (Product's domain)
- Performance optimization (unless security regression)
- UI/UX changes (LIRA's domain, unless data exposure)

---

# Section 6: Quick Reference Card

## Decision Matrix

| Finding | Severity | Action |
|---------|----------|--------|
| Secrets in diff | CRITICAL | 🛑 BLOCK + INCIDENT |
| No auth on endpoint | HIGH | 🛑 BLOCK |
| Vulnerable dep (CRITICAL CVE) | HIGH | 🛑 BLOCK |
| sys.path manipulation | HIGH | 🛑 BLOCK |
| Missing rate limit | MEDIUM | 🔁 REQUEST CHANGES |
| Verbose error messages | MEDIUM | 🔁 REQUEST CHANGES |
| Missing input validation | MEDIUM | 🔁 REQUEST CHANGES |

## Gate Triggers by File Pattern

| Pattern | Gates Triggered |
|---------|-----------------|
| `auth/*.py`, `**/jwt*.py` | SG-04 |
| `api/*.py`, `routes/*.py` | SG-05 |
| `requirements*.txt`, `package.json` | SG-06 |
| `**/crypto*.py`, `**/signing*.py` | SG-07 |
| `*.pkl`, `*.h5`, `ml_models/*` | SG-10 |
| Any `sys.path`, `PYTHONPATH` | SG-11 |
| `.env*`, `config*.yaml` | SG-03, SG-09 |

---

# Section 7: Acceptance Criteria Verification

| Criteria | Status |
|----------|--------|
| 10+ gates including import path integrity | ✅ 11 gates defined |
| Reject templates provided | ✅ 6 templates |
| Runtime checklist (env/secrets/keys) | ✅ 3 checklists, 15 items |
| Explicit veto usage guide | ✅ Section 5 |
| WRAP compliant | ✅ START/END blocks present |

---

## Open Issues

| Issue | Priority | Owner |
|-------|----------|-------|
| Automate SG-11 in pre-commit hook | P1 | DAN (GID-04) |
| Integrate checklist into PR template | P2 | DAN (GID-04) |
| Secrets scanning in CI (trufflehog) | P1 | DAN (GID-04) |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-15 | SAM (GID-06) | Initial security gates |
| 2.0.0 | 2025-12-15 | SAM (GID-06) | Added SG-11, reject templates, runtime checklists, veto guide |

---

## 🔴🔴🔴 END — SAM (GID-06) 🔴🔴🔴
