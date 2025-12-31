# Governance CI Failure Visibility

> **PAC-DAN-P44-GOVERNANCE-CI-FAILURE-VISIBILITY-AUTO-REMEDIATION-01**
> **Owner:** Dan (GID-07)
> **Status:** ACTIVE
> **Mode:** FAIL_CLOSED — Zero Silent Failures

---

## Overview

This document defines the CI failure visibility system for ChainBridge governance.
All CI failures must be:

1. **Classified** — Assigned to a failure taxonomy
2. **Visible** — Rendered with high-contrast output
3. **Actionable** — Include remediation hints

**Zero silent failures. If it fails, you see it.**

---

## Failure Classification Taxonomy

### CONFIG — Configuration/Structure Errors

Failures related to artifact structure, missing blocks, invalid fields.

| Code | Description | Severity |
|------|-------------|----------|
| G0_001 | Missing required block | HIGH |
| G0_002 | Block order violation | HIGH |
| G0_005 | Invalid field value | MEDIUM |
| G0_006 | Missing required field | MEDIUM |
| RG_001 | Missing ReviewGate declaration | HIGH |
| RG_002 | Missing terminal Gold Standard Checklist | MEDIUM |
| BSRG_001 | PAC missing BENSON_SELF_REVIEW_GATE | HIGH |
| BSRG_007 | BSRG checklist item not PASS | MEDIUM |

**Remediation:** Check CANONICAL_CORRECTION_PACK_TEMPLATE.md for required structure.

---

### REGRESSION — Performance Regression

Failures indicating performance degradation vs baseline.

| Code | Description | Severity |
|------|-------------|----------|
| GS_094 | Performance regression detected — execution blocked | CRITICAL |
| GS_115 | PAC state regression — illegal state transition | CRITICAL |

**Remediation:** Review GOVERNANCE_AGENT_BASELINES.md. Either optimize or update baseline with justification.

---

### DRIFT — Semantic Drift

Failures indicating deviation from calibration envelope or unauthorized changes.

| Code | Description | Severity |
|------|-------------|----------|
| GS_095 | Semantic drift detected — execution requires escalation | CRITICAL |
| GS_060 | Overhelpfulness detected — artifact drift without authorization | HIGH |
| GS_061 | Artifact-type boundary violation (PAC vs WRAP) | HIGH |
| GS_031 | Agent color does not match canonical registry | MEDIUM |

**Remediation:** Recalibrate agent output or escalate to BENSON (GID-00).

---

### SEQUENTIAL — PAC/WRAP Sequencing

Failures related to artifact sequencing and coupling.

| Code | Description | Severity |
|------|-------------|----------|
| GS_096 | PAC sequence violation — out-of-order PAC number | CRITICAL |
| GS_110 | Previous PAC has no corresponding WRAP | CRITICAL |
| GS_111 | PAC issuance blocked — prior WRAP not accepted | CRITICAL |
| GS_114 | WRAP does not cryptographically bind to PAC | CRITICAL |

**Remediation:** Ensure PAC↔WRAP coupling is complete before proceeding.

---

### RUNTIME — Runtime Validation

Failures occurring during runtime validation.

| Code | Description | Severity |
|------|-------------|----------|
| G0_003 | Invalid GID format | HIGH |
| G0_004 | Registry mismatch | HIGH |
| WRP_001 | WRAP missing WRAP_INGESTION_PREAMBLE | HIGH |
| GS_090 | Non-executing agent attempted PAC emission | CRITICAL |
| GS_091 | Non-executing agent attempted WRAP emission | CRITICAL |

**Remediation:** Verify agent registry binding and artifact structure.

---

## Severity Levels

| Level | Description | CI Behavior |
|-------|-------------|-------------|
| **CRITICAL** | Blocks all progress | Exit code 2, immediate stop |
| **HIGH** | Requires immediate attention | Exit code 1, continue validation |
| **MEDIUM** | Should be fixed soon | Exit code 1, continue validation |
| **LOW** | Informational | Warning only |

---

## CI Output Format

### Standard Failure Output

```
▰✖▰ PAC-EXAMPLE-P01 — requires correction
    │ [G0_001] Missing required block: AGENT_ACTIVATION_ACK
    │ [G0_002] Block order violation
```

### Failure Summary (Mandatory)

```
═══════════════════════════════════════════════════════════════════════════════
CI FAILURE SUMMARY
═══════════════════════════════════════════════════════════════════════════════

By Failure Class:
  [CONFIG]: 2
  [SEQUENTIAL]: 1

By Severity:
  [HIGH]: 2
  [CRITICAL]: 1

Failures & Remediation:
────────────────────────────────────────────────────────────────────────────────

1. [G0_001] CONFIG
   Severity: HIGH
   Remediation: Add the missing required block. Check CANONICAL_CORRECTION_PACK_TEMPLATE.md
   Agent Action: ADD_MISSING_BLOCK
   Reference: docs/governance/CANONICAL_CORRECTION_PACK_TEMPLATE.md

2. [GS_111] SEQUENTIAL
   Severity: CRITICAL
   Remediation: Prior WRAP not accepted. Ensure previous WRAP is recorded in ledger.
   Agent Action: ACCEPT_PRIOR_WRAP

═══════════════════════════════════════════════════════════════════════════════
❌ CI BLOCKED — Critical failures detected
Exit code: 2
═══════════════════════════════════════════════════════════════════════════════
```

---

## Usage

### Python API

```python
from ci_failure_classifier import FailureClassifier, format_failure_summary

classifier = FailureClassifier()

# Classify single error
failure = classifier.classify("GS_094")
print(failure.remediation_hint)
print(failure.agent_action)

# Classify multiple errors
summary = classifier.classify_multiple(["G0_001", "GS_094", "GS_111"])
print(format_failure_summary(summary))
```

### CI Integration

```python
from ci_renderer import CIRenderer, GovState

renderer = CIRenderer(mode="auto")
renderer.start_run("Governance Validation")

# ... validation results ...

# End with failure classification
error_codes = ["G0_001", "GS_094"]
result = renderer.end_run_with_failure_classification(error_codes)

sys.exit(result["exit_code"])
```

### CLI Flags

```bash
# Rich output (default in CI)
python tools/governance/gate_pack.py --ui

# Compact output
python tools/governance/gate_pack.py --ui-compact

# Plain text (for logs)
python tools/governance/gate_pack.py --no-ui
```

---

## FAIL_CLOSED Behavior

Unknown error codes are classified as `UNKNOWN` with severity `MEDIUM`:

```
1. [UNKNOWN_CODE] UNKNOWN
   Severity: MEDIUM
   Remediation: Unknown error code. Check governance documentation or escalate to BENSON.
   Agent Action: ESCALATE_TO_BENSON
```

**No silent passes. Unknown failures are surfaced and escalated.**

---

## Machine-Readable Output

JSON format for agent consumption:

```json
{
  "status": "BLOCKED",
  "exit_code": 2,
  "total_failures": 3,
  "by_class": {
    "CONFIG": 2,
    "SEQUENTIAL": 1
  },
  "by_severity": {
    "HIGH": 2,
    "CRITICAL": 1
  },
  "failures": [
    {
      "error_code": "G0_001",
      "class": "CONFIG",
      "severity": "HIGH",
      "remediation_hint": "Add the missing required block...",
      "agent_action": "ADD_MISSING_BLOCK",
      "documentation_ref": "docs/governance/CANONICAL_CORRECTION_PACK_TEMPLATE.md"
    }
  ]
}
```

---

## Related Documents

- [CANONICAL_CORRECTION_PACK_TEMPLATE.md](CANONICAL_CORRECTION_PACK_TEMPLATE.md)
- [GOVERNANCE_AGENT_BASELINES.md](GOVERNANCE_AGENT_BASELINES.md)
- [PAC-DAN-P30-TERMINAL-GOVERNANCE-UI-CI-INTEGRATION-01](pacs/PAC-DAN-P30-TERMINAL-GOVERNANCE-UI-CI-INTEGRATION-01.md)
- [PAC-DAN-P44-GOVERNANCE-CI-FAILURE-VISIBILITY-AUTO-REMEDIATION-01](pacs/PAC-DAN-P44-GOVERNANCE-CI-FAILURE-VISIBILITY-AUTO-REMEDIATION-01.md)

---

**END — GOVERNANCE_CI_FAILURE_VISIBILITY.md**
