# Color Linter Rules Specification

```
ARTIFACT TYPE:    Linter Rule Specification
AUTHORITY LEVEL:  None
BINDING EFFECT:   None
ACCEPTANCE:       Not implied
FUNCTION:         Declarative rules reference (no implementation)
```

---

## FORBIDDEN INTERPRETATIONS

- ❌ This document does NOT grant authority
- ❌ This document does NOT contain implementation
- ❌ This document does NOT modify pac_linter.py
- ❌ ALEX is NOT the owner of this content
- ❌ ALEX cannot accept changes to this document

---

## Rule Declarations

### RULE-COLOR-001: PAC Header Color Present

- Check: PAC contains EXECUTING COLOR field
- Failure: Missing color declaration
- Action: Reject PAC

### RULE-COLOR-002: PAC Header Agent Present

- Check: PAC contains EXECUTING AGENT field
- Failure: Missing agent declaration
- Action: Reject PAC

### RULE-COLOR-003: PAC Header GID Present

- Check: PAC contains EXECUTING GID field
- Failure: Missing GID declaration
- Action: Reject PAC

### RULE-COLOR-004: Color ↔ Agent Match

- Check: Declared color matches agent's registered color
- Reference: AGENT_REGISTRY.json
- Failure: Color does not match agent
- Action: Reject PAC

### RULE-COLOR-005: GID ↔ Agent Match

- Check: Declared GID matches agent's registered GID
- Reference: AGENT_REGISTRY.json
- Failure: GID does not match agent
- Action: Reject PAC

### RULE-COLOR-006: TEAL Execution Forbidden

- Check: TEAL is not declared as EXECUTING lane
- Failure: TEAL appears as executing color
- Action: Reject PAC
- Reason: TEAL is orchestration-only

### RULE-COLOR-007: Single Color Declaration

- Check: Only one color appears in EXECUTING declaration
- Failure: Multiple colors declared
- Action: Reject PAC

### RULE-COLOR-008: Color Emoji Consistency

- Check: Color emoji matches color name
- Reference: AGENT_REGISTRY.json emoji field
- Failure: Emoji ↔ color name mismatch
- Action: Warn

---

## Validation Sequence

1. RULE-COLOR-001 (color present)
2. RULE-COLOR-002 (agent present)
3. RULE-COLOR-003 (GID present)
4. RULE-COLOR-007 (single color)
5. RULE-COLOR-006 (TEAL forbidden)
6. RULE-COLOR-004 (color match)
7. RULE-COLOR-005 (GID match)
8. RULE-COLOR-008 (emoji consistency)

---

## Error Messages

| Rule | Message |
|------|---------|
| RULE-COLOR-001 | `Missing EXECUTING COLOR in PAC header` |
| RULE-COLOR-002 | `Missing EXECUTING AGENT in PAC header` |
| RULE-COLOR-003 | `Missing EXECUTING GID in PAC header` |
| RULE-COLOR-004 | `Color mismatch: {agent} is {expected}, not {declared}` |
| RULE-COLOR-005 | `GID mismatch: {agent} is {expected}, not {declared}` |
| RULE-COLOR-006 | `TEAL cannot be executing lane (orchestration only)` |
| RULE-COLOR-007 | `Multiple colors declared in EXECUTING field` |
| RULE-COLOR-008 | `Emoji {emoji} does not match color {color}` |

---

## Implementation Notes

- Implementation deferred to DAN (GID-07) or designated agent
- This document contains declarative rules only
- No code modifications in this specification

---

**Prepared by:** ALEX (GID-08)
**Date:** 2025-12-19
**PAC Reference:** PAC-BENSON-COLOR-GATEWAY-IMPLEMENTATION-01
**Classification:** Declarative specification. Non-authoritative.
