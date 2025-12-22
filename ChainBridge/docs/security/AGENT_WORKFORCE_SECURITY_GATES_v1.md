# Agent Workforce Security Gates v1.0

> **Governance Document** — AU07.A
> **Version:** 1.0.0
> **Effective Date:** 2025-12-15
> **Owner:** SAM (GID-06)
> **Status:** 🔒 LOCKED — Changes require SAM + ALEX dual approval

---

## 🔴🔴🔴 START — SAM (GID-06) — Security & Threat Engineering 🔴🔴🔴

---

## Executive Summary

This document defines the mandatory security gates that **block merge** for any WRAP or code artifact in ChainBridge. SAM (GID-06) holds **veto authority** over all merges. No exceptions without Human CEO override.

**Mantra:** Security can stop the line. Always.

---

# Section 1: Security Gates for WRAP Acceptance

## 1.1 Mandatory Security Gates (MERGE BLOCKERS)

| Gate # | Gate Name | Blocker? | SAM Review Required |
|--------|-----------|----------|---------------------|
| SG-01 | Identity Verification | 🛑 YES | ✅ |
| SG-02 | Color/Format Compliance | 🛑 YES | ✅ |
| SG-03 | No Credential Exposure | 🛑 YES | ✅ |
| SG-04 | AuthN/AuthZ Changes | 🛑 YES | ✅ |
| SG-05 | API Endpoint Changes | 🛑 YES | ✅ |
| SG-06 | Dependency Additions | 🛑 YES | ✅ |
| SG-07 | Crypto/Key Operations | 🛑 YES | ✅ |
| SG-08 | Data Flow Changes | 🛑 YES | ✅ |
| SG-09 | Runtime Config Changes | 🛑 YES | ✅ |
| SG-10 | Model Artifact Changes | 🛑 YES | ✅ (with MAGGIE) |

---

## 1.2 Gate Definitions

### SG-01: Identity Verification (BLOCKER)
```
CHECK: Agent GID matches CANON_REGISTRY_v1.md
CHECK: Role matches canonical assignment
CHECK: No impersonation patterns detected
FAIL → BLOCK MERGE + Alert BENSON + ALEX
```

### SG-02: Color/Format Compliance (BLOCKER)
```
CHECK: Emoji block matches GID assignment
CHECK: START/END banners present and matching
CHECK: Hex code (if displayed) matches registry
FAIL → BLOCK MERGE + Reject WRAP immediately
```

### SG-03: No Credential Exposure (BLOCKER)
```
CHECK: No API keys in code (regex scan)
CHECK: No secrets in comments or logs
CHECK: No .env files committed
CHECK: No hardcoded passwords/tokens
FAIL → BLOCK MERGE + Quarantine + Incident ticket
```

### SG-04: AuthN/AuthZ Changes (BLOCKER)
```
TRIGGER: Changes to auth/, session, JWT, RBAC, permissions
REQUIRE: SAM review + explicit security sign-off
REQUIRE: Test coverage for auth bypass scenarios
FAIL → BLOCK MERGE until SAM approves
```

### SG-05: API Endpoint Changes (BLOCKER)
```
TRIGGER: New routes, method changes, public exposure
REQUIRE: Rate limiting defined
REQUIRE: Input validation present
REQUIRE: Error handling doesn't leak internals
FAIL → BLOCK MERGE until SAM approves
```

### SG-06: Dependency Additions (BLOCKER)
```
TRIGGER: New packages in requirements.txt, package.json
REQUIRE: No known CVEs (CRITICAL/HIGH)
REQUIRE: License compatibility verified
REQUIRE: Provenance established (not typosquat)
FAIL → BLOCK MERGE + Document exception if required
```

### SG-07: Crypto/Key Operations (BLOCKER)
```
TRIGGER: Encryption, signing, hashing, key generation
REQUIRE: Standard algorithms only (AES-256, SHA-256, RSA-2048+)
REQUIRE: No custom crypto implementations
REQUIRE: Key material never logged
FAIL → BLOCK MERGE + Escalate to Human CEO if disputed
```

### SG-08: Data Flow Changes (BLOCKER)
```
TRIGGER: PII handling, cross-service data transfer, logging changes
REQUIRE: Data classification defined
REQUIRE: Encryption in transit verified
REQUIRE: Retention policy documented
FAIL → BLOCK MERGE until compliance verified
```

### SG-09: Runtime Config Changes (BLOCKER)
```
TRIGGER: Environment variables, feature flags, thresholds
REQUIRE: No secrets in config files
REQUIRE: Default values are secure (fail-closed)
REQUIRE: Staging/prod separation verified
FAIL → BLOCK MERGE until SAM review
```

### SG-10: Model Artifact Changes (BLOCKER)
```
TRIGGER: ML model updates, training pipeline changes
REQUIRE: Model signed per MODEL_SECURITY_POLICY.md
REQUIRE: MAGGIE co-approval
REQUIRE: No unsigned models in production paths
FAIL → BLOCK MERGE + Quarantine artifact
```

---

## 1.3 Gate Decision Flow

```
WRAP Submitted
      │
      ▼
┌─────────────────┐
│ SG-01: Identity │──NO──▶ 🛑 BLOCK "Agent identity violation"
└─────────────────┘
      │ YES
      ▼
┌─────────────────┐
│ SG-02: Format   │──NO──▶ 🛑 BLOCK "Format non-compliance"
└─────────────────┘
      │ YES
      ▼
┌─────────────────┐
│ SG-03: Secrets  │──NO──▶ 🛑 BLOCK + INCIDENT "Credential exposure"
└─────────────────┘
      │ YES
      ▼
┌─────────────────────────┐
│ SG-04 to SG-10: Review  │──NO──▶ 🛑 BLOCK "Security review required"
└─────────────────────────┘
      │ ALL PASS
      ▼
✅ SAM APPROVAL GRANTED
      │
      ▼
Proceed to BENSON merge gate
```

---

# Section 2: Minimum AuthN/AuthZ Standard

## 2.1 Endpoint Classification

| Class | Auth Required | Rate Limit | Example |
|-------|---------------|------------|---------|
| **PUBLIC** | None | 100/min | Health checks, static assets |
| **AUTHENTICATED** | Bearer JWT | 1000/min | User data, preferences |
| **PRIVILEGED** | JWT + Role check | 100/min | Admin actions, config |
| **INTERNAL** | mTLS + Service ID | 10000/min | Inter-service calls |
| **OC/OCC** | JWT + SAM audit | 50/min | Override/Confirmation |

## 2.2 Mandatory AuthN Requirements

```yaml
# Every new endpoint MUST define:
endpoint_auth:
  path: "/api/v1/resource"
  method: "POST"
  auth_required: true              # MANDATORY field
  auth_type: "bearer_jwt"          # bearer_jwt | mtls | api_key | none
  token_validation:
    issuer: "chainbridge-auth"     # Must validate
    audience: "chainbridge-api"    # Must validate
    expiry_check: true             # Must validate
    signature_verify: true         # Must validate
  rate_limit:
    requests_per_minute: 100       # MANDATORY for all endpoints
    burst: 20                      # Max burst allowed
```

## 2.3 Mandatory AuthZ Requirements

```yaml
# Every protected endpoint MUST define:
endpoint_authz:
  path: "/api/v1/admin/settings"
  required_roles: ["admin", "operator"]     # Minimum one role
  required_permissions: ["settings:write"]  # Granular permissions
  resource_ownership: true                  # Check resource belongs to user
  audit_log: true                           # MANDATORY for privileged ops
```

## 2.4 OC/OCC (Override/Confirmation) Security

```yaml
# Special requirements for human-in-the-loop endpoints:
oc_security:
  confirmation_required: true
  confirmation_expiry_seconds: 300    # 5-minute window
  max_confirmation_attempts: 3        # Lock after 3 failures
  audit_trail: "immutable"            # Cannot be deleted
  sam_notification: true              # Alert SAM on every OC action
```

## 2.5 Rejection Criteria

| Violation | Action |
|-----------|--------|
| Missing `auth_required` field | 🛑 BLOCK |
| No rate limit defined | 🛑 BLOCK |
| Public endpoint accessing PII | 🛑 BLOCK + INCIDENT |
| Role check missing on privileged route | 🛑 BLOCK |
| OC endpoint without audit log | 🛑 BLOCK |

---

# Section 3: Key Management & Rotation SOP

## 3.1 Environment Classification

| Environment | Key Type | Rotation Frequency | Storage |
|-------------|----------|-------------------|---------|
| **LOCAL DEV** | Development keys | Never (disposable) | `.env.local` (gitignored) |
| **CI/CD** | Ephemeral keys | Per-run (auto) | GitHub Secrets / Vault |
| **STAGING** | Staging secrets | 30 days | HashiCorp Vault |
| **PRODUCTION** | Production secrets | 90 days max | HSM / Vault (sealed) |

## 3.2 Development Keys (Local)

```bash
# ALLOWED in local development:
- Self-signed certs for localhost
- Dummy API keys (prefix: dev_xxxx)
- Local database credentials
- Mock exchange credentials (sandbox only)

# NEVER in local development:
- Production API keys
- Real exchange credentials
- Customer data access tokens
- Production database strings
```

### Local Key Generation
```bash
# Generate local development keys (safe):
openssl rand -hex 32 > .env.local.key
echo "DEV_API_KEY=dev_$(openssl rand -hex 16)" >> .env.local

# MUST be in .gitignore:
.env.local
.env.local.key
*.pem
*.key
```

## 3.3 Production Secrets (Critical)

### Storage Requirements
```yaml
production_secrets:
  storage: "hashicorp_vault"  # MANDATORY - no exceptions
  encryption: "aes-256-gcm"   # At-rest encryption
  access_audit: true          # All access logged
  rotation_alert: true        # Alert 14 days before expiry
```

### Rotation Procedure
```
1. Generate new key in Vault (do not expose)
2. Deploy new key to staging
3. Test with synthetic traffic
4. Schedule production rotation window
5. Deploy new key to production (blue/green)
6. Verify no errors for 15 minutes
7. Revoke old key
8. Update rotation log
```

### Rotation Log Template
```markdown
| Date | Secret Name | Old Fingerprint | New Fingerprint | Rotated By | Verified By |
|------|-------------|-----------------|-----------------|------------|-------------|
| YYYY-MM-DD | KRAKEN_API_KEY | sha256:abc... | sha256:def... | DAN (GID-04) | SAM (GID-06) |
```

## 3.4 Emergency Key Revocation

```bash
# INCIDENT: Key compromise detected
# Authority: SAM (GID-06) or Human CEO

1. IMMEDIATELY revoke compromised key
2. Generate emergency replacement
3. Deploy to all environments (bypass staging if critical)
4. Notify all affected parties
5. File incident report within 4 hours
6. Post-mortem within 48 hours
```

## 3.5 Prohibited Actions

| Action | Status | Consequence |
|--------|--------|-------------|
| Committing production keys to git | 🛑 FORBIDDEN | Immediate incident + rotation |
| Sharing keys via Slack/email | 🛑 FORBIDDEN | Key revocation + retraining |
| Using production keys locally | 🛑 FORBIDDEN | Access revoked |
| Bypassing Vault for "convenience" | 🛑 FORBIDDEN | Escalation to Human CEO |
| Disabling key rotation alerts | 🛑 FORBIDDEN | SAM veto on all related PRs |

---

# Section 4: Threat-Driven PR Review Checklist

## 4.1 The 10-Item Security Checklist

> **SAM (GID-06) MANDATORY REVIEW**
> Every PR touching security-sensitive code must pass ALL 10 checks.

| # | Check | PASS/FAIL |
|---|-------|-----------|
| **1** | **No Secrets in Diff?** — grep for API keys, passwords, tokens, connection strings | ☐ |
| **2** | **Auth on New Routes?** — Every new endpoint has explicit auth requirement defined | ☐ |
| **3** | **Input Validated?** — All user input sanitized before use (SQL, XSS, command injection) | ☐ |
| **4** | **Errors Safe?** — Error messages don't leak stack traces, paths, or internal state | ☐ |
| **5** | **Rate Limited?** — New endpoints have rate limits; existing limits not weakened | ☐ |
| **6** | **Deps Scanned?** — New dependencies have no CRITICAL/HIGH CVEs | ☐ |
| **7** | **Logging Safe?** — No PII, secrets, or sensitive data in logs | ☐ |
| **8** | **Least Privilege?** — Code requests minimum permissions needed | ☐ |
| **9** | **Crypto Standard?** — No custom crypto; standard algorithms only | ☐ |
| **10** | **Audit Trail?** — Privileged operations logged with who/what/when | ☐ |

---

## 4.2 Quick Decision Matrix

```
All 10 PASS → ✅ SAM APPROVAL
Any 1-3 FAIL → 🔁 REQUEST CHANGES + Block merge
Any FAIL on #1 (Secrets) → 🛑 BLOCK + INCIDENT
Any FAIL on #9 (Crypto) → 🛑 BLOCK + Escalate to Human CEO
```

---

## 4.3 Checklist Automation Hints

```yaml
# Future CI integration (DAN to implement):
security_scan:
  secrets_detection:
    tool: "trufflehog"
    fail_on: ["HIGH", "CRITICAL"]

  dependency_scan:
    tool: "safety"
    fail_on: ["CRITICAL", "HIGH"]

  sast_scan:
    tool: "semgrep"
    rulesets: ["p/security-audit", "p/secrets"]

  output:
    format: "sarif"
    destination: "codeql-results.sarif"
```

---

## 4.4 Review Response Templates

### Approval
```
✅ SAM (GID-06) SECURITY APPROVAL

PR: #XXX
Checklist: 10/10 PASS
Notes: [Any observations]
Date: YYYY-MM-DD
```

### Request Changes
```
🔁 SAM (GID-06) SECURITY REVIEW — CHANGES REQUESTED

PR: #XXX
Failed Checks: #X, #Y
Details:
- [Specific issue]
- [Required fix]

Merge blocked until resolved.
```

### Block (Incident)
```
🛑 SAM (GID-06) SECURITY BLOCK — INCIDENT CREATED

PR: #XXX
Severity: CRITICAL
Issue: [Secrets exposed / Custom crypto / etc.]

Actions taken:
1. PR merge blocked
2. Incident ticket created: INC-XXXX
3. ALEX + BENSON notified
4. [Additional containment if needed]

Do not attempt to merge until incident resolved.
```

---

# Section 5: Security Enforcement Summary

## 5.1 SAM Veto Authority

| Scope | SAM Can Block | Override Authority |
|-------|---------------|-------------------|
| Any PR | ✅ Yes | ALEX + BENSON dual |
| Any WRAP | ✅ Yes | ALEX + BENSON dual |
| Any Merge | ✅ Yes | ALEX + BENSON dual |
| Any Deploy | ✅ Yes | Human CEO only |
| Emergency Stop | ✅ Yes | Human CEO only |

## 5.2 Escalation Path

```
Security Issue Detected
        │
        ▼
SAM (GID-06) — Assess & Block
        │
        ├─► Minor: Request changes, document
        │
        ├─► Major: Block + Alert BENSON + ALEX
        │
        └─► Critical: Block + Incident + Human CEO notification
```

## 5.3 Non-Negotiable Rules

1. **Security can stop the line** — No deadlines override security
2. **No exceptions without audit** — Every bypass documented
3. **Secrets are NEVER committed** — Instant incident on detection
4. **Production keys are sacred** — HSM/Vault only, no exceptions
5. **SAM reviews all auth changes** — No merge without approval

---

# Section 6: Acceptance Criteria Verification

| Criteria | Status |
|----------|--------|
| Gates include identity/color/format enforcement | ✅ Complete (SG-01, SG-02) |
| Gates include security controls | ✅ Complete (SG-03 to SG-10) |
| SOP distinguishes dev keys vs prod secrets | ✅ Complete (Section 3) |
| Checklist is short + brutal + usable | ✅ Complete (Section 4, 10 items) |
| SAM veto authority documented | ✅ Complete (Sections 1.3, 5.1) |
| AuthN/AuthZ standard defined | ✅ Complete (Section 2) |
| OC/OCC security addressed | ✅ Complete (Section 2.4) |

---

## Open Issues

| Issue | Priority | Owner | Notes |
|-------|----------|-------|-------|
| CI automation for secret scanning | P1 | DAN (GID-04) | Integrate trufflehog in pipeline |
| Vault setup for staging | P1 | DAN (GID-04) | Prerequisite for key rotation |
| SAST tooling deployment | P2 | DAN (GID-04) | Semgrep + CodeQL |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-15 | SAM (GID-06) | Initial release — AU07.A training |

---

## 🔴🔴🔴 END — SAM (GID-06) 🔴🔴🔴
