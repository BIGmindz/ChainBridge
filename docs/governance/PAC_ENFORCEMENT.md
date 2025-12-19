# PAC Enforcement Protocol
**ALEX (GID-08) | PAC-ALEX-GOVERNANCE-LOCK-01**

---

## Purpose

This document defines the **mandatory PAC (Plan of Action & Commitment) enforcement rules** for all code changes in ChainBridge. No code change is valid without a PAC reference.

---

## Rule: No Code Change Without PAC ID

### Format

Every commit message MUST include a PAC reference:

```
<type>(<scope>): <description> (PAC-<AGENT>-<DOMAIN>-<SEQ>)
```

### Examples

```
feat(spine): add proof persistence (PAC-BENSON-EXEC-SPINE-01)
fix(chainpay): validate settlement amount (PAC-DIGGI-03)
chore(security): add model signatures (PAC-SAM-SEC-018)
docs(governance): add ALEX middleware (PAC-ALEX-GOVERNANCE-LOCK-01)
```

### PAC ID Structure

| Component | Description | Example |
|-----------|-------------|---------|
| `PAC-` | Mandatory prefix | `PAC-` |
| `<AGENT>` | Agent GID name | `BENSON`, `ALEX`, `SAM` |
| `<DOMAIN>` | Domain code | `EXEC`, `SEC`, `GOVERNANCE` |
| `<SEQ>` | Sequence number | `01`, `018` |

---

## Color-Gateway Header Requirements

Every PAC header MUST include:

| Field | Required | Description |
|-------|----------|-------------|
| EXECUTING AGENT | Yes | Agent name performing work |
| EXECUTING GID | Yes | Agent GID (e.g., GID-08) |
| EXECUTING COLOR | Yes | Color emoji + name (e.g., ⚪ WHITE) |

### Validation Rules

- Missing color = invalid PAC
- Color mismatch = stop-the-line
- TEAL as executing lane = invalid (orchestration only)

**Reference:** [COLOR_GATEWAY_ENFORCEMENT.md](./COLOR_GATEWAY_ENFORCEMENT.md)

---

## Enforcement Points

### 1. Commit Message Validation

| Check | Rule | Action |
|-------|------|--------|
| PAC present | `PAC-` in message | Block if missing |
| PAC format | Matches pattern | Warn if malformed |

### 2. Pull Request Validation

| Check | Rule | Action |
|-------|------|--------|
| PR title | Contains PAC ID | Block merge if missing |
| PR body | References PAC document | Warn if missing |

### 3. File Header Validation

Critical files MUST have PAC reference in docstring:

```python
"""
Module Name - PAC-<AGENT>-<DOMAIN>-<SEQ>

Description of module purpose.
"""
```

---

## Valid PAC Types

| Type | Use Case |
|------|----------|
| `feat` | New functionality |
| `fix` | Bug fixes |
| `chore` | Maintenance, dependencies |
| `docs` | Documentation only |
| `test` | Test additions/changes |
| `ci` | CI/CD changes |
| `refactor` | Code restructuring |
| `security` | Security fixes |

---

## Exception Handling

### Allowed Exceptions

| Exception | Condition | Approval |
|-----------|-----------|----------|
| Emergency hotfix | Production down | Benson verbal approval, PAC within 24h |
| Security patch | CVE response | SAM approval, PAC within 24h |

### Exception Documentation

All exceptions MUST be documented in `.github/PAC_EXCEPTIONS.md` with:

1. Commit SHA
2. Date
3. Approver
4. Reason
5. Retroactive PAC ID

---

## Current PAC Registry

| PAC ID | Agent | Description |
|--------|-------|-------------|
| PAC-BENSON-EXEC-SPINE-01 | BENSON (GID-00) | Minimum Execution Spine |
| PAC-ALEX-GOVERNANCE-LOCK-01 | ALEX (GID-08) | Governance lock |
| PAC-SAM-SEC-018 | SAM (GID-06) | Model signatures |
| PAC-DIGGI-03 | DIGGI | ChainPay settlement |

---

## Violation Response

| Severity | Violation | Response |
|----------|-----------|----------|
| CRITICAL | PR merged without PAC | Revert, escalate to Benson |
| HIGH | Commit without PAC | Block push, require amendment |
| MEDIUM | Malformed PAC | Warn, allow with correction |

---

## Governance Correction Requirements

### Rule: No Cosmetic-Only Corrections

Governance corrections are NOT format fixes.
Governance corrections are active interventions requiring substance verification.

### REQUIRED RE-AUDIT & ACTION Section

Every Governance Correction PAC MUST include:

| Field | Required | Description |
|-------|----------|-------------|
| Original Mandate | Yes | Verbatim original request |
| Expected Deliverable | Yes | What was supposed to be built |
| Actual Deliverable | Yes | What was actually built |
| PASS/FAIL per Requirement | Yes | Explicit per-item verification |
| Corrective Steps | If FAIL | Concrete actions to resolve |

### Correction PAC Template

```
REQUIRED RE-AUDIT & ACTION

1. ORIGINAL MANDATE
   [Verbatim quote from originating PAC]

2. EXPECTED DELIVERABLE
   - [Item 1]
   - [Item 2]

3. ACTUAL DELIVERABLE
   - [Item 1]: [PASS/FAIL]
   - [Item 2]: [PASS/FAIL]

4. CORRECTIVE STEPS (if any FAIL)
   - [Action 1]
   - [Action 2]

5. VERIFICATION
   - Files checked: [list]
   - Tests run: [Y/N]
   - References verified: [Y/N]
```

### Forbidden Correction Behaviors

- ❌ Fixing headers/colors/wording only
- ❌ Declaring "acknowledged" without action
- ❌ Skipping re-verification of original mandate
- ❌ Assuming work correctness
- ❌ Agents self-asserting compliance

### Correction Routing

- All governance violations route to ALEX (GID-08)
- ALEX corrections always mandate work verification
- Acceptance authority remains Benson-only

---

## Checklist for Code Authors

Before submitting code:

- [ ] Commit message includes valid PAC ID
- [ ] PAC ID format is correct: `PAC-<AGENT>-<DOMAIN>-<SEQ>`
- [ ] Critical file headers include PAC reference
- [ ] PR title includes PAC ID
- [ ] Changes are within PAC scope

---

## Checklist for Reviewers

Before approving:

- [ ] All commits have PAC ID
- [ ] PAC scope matches changes
- [ ] No scope creep beyond PAC
- [ ] No unauthorized files modified

---

## FORBIDDEN INTERPRETATIONS

- ❌ This document does NOT grant ALEX authority
- ❌ This document does NOT override Benson decisions
- ❌ This document does NOT self-enforce
- ❌ ALEX is NOT the owner of this content
- ❌ ALEX cannot accept changes to this document

---

**Prepared by:** ALEX (GID-08)  
**Date:** 2025-12-19  
**PAC Reference:** PAC-ALEX-GOVERNANCE-LOCK-01  
**Classification:** Reference document. Navigational aid only. Non-authoritative.

---

## Git Hook Enforcement (PAC-DAN-PAC-ENFORCEMENT-01)

**Added:** 2025-12-19  
**Author:** DAN (GID-07)

### Local Commit Enforcement

A git `commit-msg` hook enforces PAC ID presence at commit time.

### Installation

```bash
./scripts/install-githooks.sh
```

### Enforcement Regex

```
PAC-[A-Z]+-[A-Z0-9-]+
```

### Allowlist (Bypass)

Commits touching **ONLY** these paths bypass enforcement:

| Path | Reason |
|------|--------|
| `docs/` | Documentation-only changes |
| `.github/` | CI/workflow configuration |
| `README.md` | Root readme updates |

### Example: Blocked Commit

```
$ git commit -m "fix: update config"

════════════════════════════════════════════════════════════════════
❌ COMMIT BLOCKED: Missing PAC ID
════════════════════════════════════════════════════════════════════

Your commit message:
  "fix: update config"

REQUIRED FORMAT:
  Commit message must contain a PAC ID matching:
  PAC-[AGENT]-[TASK-ID]

EXAMPLES:
  PAC-CODY-EXEC-SPINE-01: Implement execution spine
  PAC-SONNY-PROOF-VIEWER-01: Add proof artifact viewer
  feat: new feature PAC-DAN-CI-LINT-01

BYPASS:
  Commits touching ONLY docs/, .github/, or README.md are exempt.

See: docs/governance/PAC_ENFORCEMENT.md
════════════════════════════════════════════════════════════════════
```

### Example: Allowed Commit

```
$ git commit -m "PAC-DAN-PAC-ENFORCEMENT-01: Add git hooks"
[branch abc1234] PAC-DAN-PAC-ENFORCEMENT-01: Add git hooks
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Hook not running | Run `./scripts/install-githooks.sh` |
| Wrong regex match | Ensure uppercase: `PAC-AGENT-TASK-01` |
| Need to bypass | Only touch `docs/`, `.github/`, or `README.md` |

