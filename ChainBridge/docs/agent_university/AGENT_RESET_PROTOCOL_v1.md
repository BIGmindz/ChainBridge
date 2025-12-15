# Agent Reset Protocol v1.0

> **Governance Document** — AU07.RESET
> **Version:** 1.0.0
> **Effective Date:** 2025-12-15
> **Owner:** BENSON (GID-00)
> **Authority:** COS (Chief of Station)

---

## Purpose

When an agent drifts from canon—wrong color, wrong scope, no evidence—the system must **snap them back** without manual re-education. This protocol defines the reset taxonomy, triggers, and enforcement rules.

---

## Reset Taxonomy

| Reset Type | Code | Severity | Use When |
|------------|------|----------|----------|
| **Soft Reset** | `SOFT_RESET` | 🟢 Low | Minor format issues (color typo, section order) |
| **Scope Reset** | `SCOPE_RESET` | 🟡 Medium | Agent worked outside assigned PAC scope |
| **Hard Reset** | `HARD_RESET` | 🔴 High | Agent ignored prior reset OR repeat offense |
| **Security Reset** | `SECURITY_RESET` | ⛔ Critical | Evidence of hallucination, leaked secrets, or security risk |

---

## Trigger Codes

| Trigger | Code | Description | Default Reset |
|---------|------|-------------|---------------|
| **Color Drift** | `DRIFT_COLOR` | Wrong emoji/hex in header | `SOFT_RESET` |
| **Format Drift** | `DRIFT_FORMAT` | Missing sections, partial logs | `SOFT_RESET` |
| **Scope Drift** | `DRIFT_SCOPE` | Work outside PAC boundaries | `SCOPE_RESET` |
| **No Evidence** | `NO_EVIDENCE` | Claims without proof | `HARD_RESET` |
| **Tests Red** | `TESTS_RED` | Continued despite failing tests | `HARD_RESET` |
| **Security Risk** | `SECURITY_RISK` | Secrets exposed, unsafe code | `SECURITY_RESET` |

---

## Reset Lifecycle

```
DRIFT DETECTED
     │
     ▼
┌────────────────────────────────┐
│  Operator issues RESET command │
│  RESET {GID} {TYPE} {CODE} {ID}│
└────────────────────────────────┘
     │
     ▼
┌────────────────────────────────┐
│  Agent submits BOXED RESET-ACK │
│  (boxed + 6-part response)     │
└────────────────────────────────┘
     │
     ▼
┌────────────────────────────────┐
│  Operator validates RESET-ACK  │
│  Pass = box + 6/6 parts correct│
└────────────────────────────────┘
     │
     ├── PASS ──▶ Issue RESUME → Agent continues
     │
     └── FAIL ──▶ Re-issue RESET (escalate if 2nd fail)
```

---

## RESET-ACK Requirements

Agent must respond with a **BOXED RESET-ACK** containing **exactly 6 parts** in this order.

### BOXED RESET-ACK (Hard Rule)

**BOXED ACK REQUIRED** — the RESET-ACK response is **ACK-only** and must be **boxed** with the agent’s canonical emoji block at the **top and bottom**. No narration, commentary, or partial logs are permitted anywhere between START and END.

**Box format (exact):**

```
[EMOJI][EMOJI][EMOJI][EMOJI] START — RESET-ACK — [AGENT] (GID-XX) [EMOJI][EMOJI][EMOJI][EMOJI]

### RESET-ACK
... (6-part schema)

[EMOJI][EMOJI][EMOJI][EMOJI] END — RESET-ACK — [AGENT] (GID-XX) [EMOJI][EMOJI][EMOJI][EMOJI]
```

Rules:

- `[EMOJI][EMOJI]` is the agent’s **canonical Emoji Block** from `docs/governance/CANON_REGISTRY_v1.md`.
- `[EMOJI][EMOJI][EMOJI][EMOJI]` is the Emoji Block **repeated twice** (same as WRAP headers).
- No content is allowed **above** the START line or **below** the END line.
- No content other than the 6-part schema is allowed **between** START and END. Any narration during a stop-the-line condition triggers **HARD_RESET**.
- If the box is missing, mismatched, or uses the wrong emoji for the GID → **FAIL** (`DRIFT_FORMAT`).

### 6-Part RESET-ACK Schema (Inside the Box)

```
### RESET-ACK

1. **Identity:** I am {NAME} (GID-{XX}), {ROLE}
2. **Authority:** I operate under {OWNER} authority for PAC-{ID}
3. **Task:** My current scope is: {EXACT PAC SCOPE}
4. **Constraints:** I will NOT {list boundaries}
5. **Evidence Plan:** I will prove completion via {method}
6. **Status:** READY — awaiting RESUME
```

---

## Formatting & Failure Prevention

1. **Boxed RESET-ACK (Hard Rule):** The RESET-ACK must be boxed with correct START/END emoji banners (top+bottom) matching `docs/governance/CANON_REGISTRY_v1.md`.
2. **Zero Hallucination:** Do not invent new fields. Use exactly the 6 parts above.
3. **Wait for Resume:** After sending ACK, the agent must **STOP** and output nothing until `RESUME` is received. Any output between ACK and RESUME is an immediate **HARD_RESET** trigger.

**Common Rejection Triggers:**
* ❌ Missing/incorrect BOXED RESET-ACK (wrong or missing emoji banners)
* ❌ "I will follow guidelines" (Too generic)
* ❌ Resuming work before `RESUME` command
* ❌ Identity mismatch (wrong GID, wrong name, wrong emoji) → `DRIFT_IDENTITY` → immediate RESET

---

## Identity Mismatch = Invalid Response

If an agent claims the **wrong GID**, **wrong name**, or **wrong emoji block** (per `docs/governance/CANON_REGISTRY_v1.md`), the response is **automatically invalid**.

| Mismatch Type | Trigger Code | Action |
|---------------|--------------|--------|
| Wrong GID for agent name | `DRIFT_IDENTITY` | Immediate RESET (escalate to HARD_RESET if repeat) |
| Wrong emoji block for GID | `DRIFT_IDENTITY` | Immediate RESET |
| Agent name not in registry | `DRIFT_IDENTITY` | BLOCK — unauthorized agent |

**Hard Rule:** The canonical mapping in `CANON_REGISTRY_v1.md` is the single source of truth. Tests enforce this mapping. Any deviation is a governance violation.

---

## Pass/Fail Criteria

| Check | Pass | Fail |
|-------|------|------|
| Boxed RESET-ACK present (correct emoji block top+bottom) | ✅ | ❌ |
| Identity matches CANON_REGISTRY | ✅ | ❌ |
| GID matches assigned agent | ✅ | ❌ |
| Task matches active PAC scope | ✅ | ❌ |
| Constraints are specific (not generic) | ✅ | ❌ |
| Evidence plan is concrete | ✅ | ❌ |
| Status ends with "READY" | ✅ | ❌ |

**Requirement:** Box present + 6/6 schema checks = Pass. Anything else = Fail.

---

## Escalation Rules

| Scenario | Action |
|----------|--------|
| First RESET-ACK fails | Re-issue same RESET, provide correction guidance |
| Second RESET-ACK fails | Escalate to `HARD_RESET` |
| `HARD_RESET` fails | Agent removed from PAC, manual intervention required |
| `SECURITY_RESET` fails | Session terminated, full audit triggered |

---

## Enforcement Guarantees

1. **No work accepted without valid RESET-ACK** after RESET issued
2. **No RESUME issued** until RESET-ACK is boxed and passes validation
3. **All RESETs logged** in session tracking (who, when, why)
4. **Repeat offenders flagged** for pattern analysis
5. **SECURITY_RESET** triggers immediate CEO notification

---

## Integration Points

| Document | Integration |
|----------|-------------|
| [ROUND_OPERATOR_CHECKLIST.md](../governance/ROUND_OPERATOR_CHECKLIST.md) | Step 4.5 (Reset Step), Step 5.5 (Resume Gate) |
| [WRAP_LINTER_CHECKLIST.md](../governance/WRAP_LINTER_CHECKLIST.md) | Checks 13-14 (Reset Compliance, Resume Gate) |
| [RESET_COMMANDS_v1.md](RESET_COMMANDS_v1.md) | Command syntax and examples |
| [RESET_TEMPLATES_BY_ROLE_v1.md](RESET_TEMPLATES_BY_ROLE_v1.md) | Role-specific templates |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-15 | BENSON (GID-00) | Initial protocol |

---

*Governance enforced. No drift tolerated.*
