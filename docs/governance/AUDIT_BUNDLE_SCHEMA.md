# Audit Bundle Schema Specification

**PAC-GOV-AUDIT-01 — DAN (GID-07)**
**Version**: 1.0.0
**Status**: Normative

---

## Overview

The ChainBridge Governance Audit Bundle is a portable, read-only, cryptographically verifiable archive containing all evidence required for external audit of the governance system.

This document defines the **contract** — the exact structure, contents, and verification requirements for audit bundles.

---

## Bundle Structure

```
audit_bundle_<timestamp>/
├── AUDIT_MANIFEST.json          # Top-level manifest with hashes
├── governance_events/
│   └── events.jsonl             # Consolidated governance events
├── artifacts/
│   └── artifacts.json           # Build artifact manifest + hashes
├── fingerprint/
│   └── governance_fingerprint.json  # Governance root fingerprint
├── scope/
│   └── scope_declaration.json   # What's included/excluded
└── VERIFY.md                    # Human-readable verification instructions
```

---

## File Specifications

### 1. AUDIT_MANIFEST.json

The root manifest. All verification starts here.

```json
{
  "schema_version": "1.0.0",
  "bundle_id": "audit-<uuid>",
  "created_at": "2025-12-17T00:00:00.000000+00:00",
  "created_by": "ChainBridge Governance Audit Exporter",
  "export_parameters": {
    "start_time": "2025-11-01T00:00:00+00:00",
    "end_time": "2025-12-01T00:00:00+00:00",
    "source_log_path": "logs/governance_events.jsonl"
  },
  "contents": {
    "governance_events/events.jsonl": {
      "sha256": "<hash>",
      "size_bytes": 123456,
      "event_count": 1000
    },
    "artifacts/artifacts.json": {
      "sha256": "<hash>",
      "size_bytes": 2048
    },
    "fingerprint/governance_fingerprint.json": {
      "sha256": "<hash>",
      "size_bytes": 512
    },
    "scope/scope_declaration.json": {
      "sha256": "<hash>",
      "size_bytes": 256
    }
  },
  "governance_fingerprint_hash": "<composite_hash>",
  "retention_policy_version": "1.0.0",
  "bundle_hash": "<sha256 of all content hashes concatenated>"
}
```

**Invariants**:
- `bundle_hash` = SHA-256 of sorted concatenation of all content hashes
- All timestamps are ISO 8601 UTC
- All hashes are lowercase hex SHA-256

---

### 2. governance_events/events.jsonl

Consolidated governance events within the export time range.

**Format**: Newline-delimited JSON (JSONL)
**Ordering**: Chronological (oldest first)
**Transformation**: NONE — byte-for-byte copy from source

Each line is a complete `GovernanceEvent`:

```json
{"event_type":"DECISION_DENIED","timestamp":"2025-12-01T12:00:00.000000+00:00","event_id":"gov-abc123","agent_gid":"GID-05","verb":"EXECUTE","target":"tool_name","decision":"DENY","reason_code":"EXECUTE_NOT_PERMITTED"}
```

**Guarantees**:
- No events are modified
- No events are reordered
- No events are summarized or aggregated
- Source files are never mutated

---

### 3. artifacts/artifacts.json

Build artifact manifest from CI pipeline.

```json
{
  "aggregate_hash": "<sha256>",
  "artifact_type": "python-service",
  "artifact_version": "1.0.0",
  "generated_at": "2025-12-17T00:00:00+00:00",
  "git_commit": "<commit_sha>",
  "git_branch": "<branch_name>",
  "files": {
    "api/server.py": "<sha256>",
    "core/governance/acm_evaluator.py": "<sha256>"
  },
  "file_count": 19
}
```

**Source**: `build/artifacts.json` (if exists)
**Fallback**: Omitted if not available (noted in scope declaration)

---

### 4. fingerprint/governance_fingerprint.json

Governance root file fingerprint.

```json
{
  "governance_version": "v1",
  "composite_hash": "<sha256>",
  "computed_at": "2025-12-17T00:00:00+00:00",
  "inputs": {
    "config/agents.json": "<sha256>",
    ".github/ALEX_RULES.json": "<sha256>",
    "manifests/acm_gid00.yaml": "<sha256>"
  },
  "categories": ["acm_manifests", "agent_authority", "governance_rules"],
  "file_count": 12
}
```

**Source**: Computed at export time using `GovernanceFingerprintEngine`

---

### 5. scope/scope_declaration.json

Explicit declaration of what is and is not included.

```json
{
  "schema_version": "1.0.0",
  "included": {
    "governance_events": {
      "description": "All governance decisions, denials, and violations",
      "source": "logs/governance_events.jsonl",
      "time_bounded": true
    },
    "artifact_manifest": {
      "description": "SHA-256 hashes of tracked build artifacts",
      "source": "build/artifacts.json",
      "present": true
    },
    "governance_fingerprint": {
      "description": "Cryptographic fingerprint of governance root files",
      "source": "computed",
      "present": true
    }
  },
  "excluded": {
    "raw_source_code": "Source files not included; only hashes",
    "runtime_secrets": "No credentials, API keys, or secrets exported",
    "user_data": "No PII or user-specific data",
    "third_party_logs": "No external service logs"
  },
  "assumptions": {
    "source_integrity": "Source logs assumed append-only and unmodified",
    "hash_algorithm": "SHA-256 used for all cryptographic hashes",
    "timestamp_source": "System clock at export time"
  },
  "limitations": {
    "completeness": "Only events within specified time range",
    "retention": "Subject to retention policy (older events may be rotated out)"
  }
}
```

---

### 6. VERIFY.md

Human-readable verification instructions (included in bundle).

```markdown
# Audit Bundle Verification Instructions

## Quick Verification

```bash
python scripts/verify_audit_bundle.py <bundle_path>
```

Expected output:
```
AUDIT BUNDLE VERIFIED
✓ All file hashes match
✓ Bundle hash valid
✓ Governance fingerprint present
✓ No missing artifacts
```

## Manual Verification

1. Compute SHA-256 of each file in `contents`
2. Compare against hashes in AUDIT_MANIFEST.json
3. Concatenate all content hashes (sorted by path)
4. Compute SHA-256 of concatenation
5. Compare against `bundle_hash`

## What This Proves

- All included files are unmodified since export
- Export was deterministic and reproducible
- Governance events are authentic records
- Artifact hashes were captured at CI time

## What This Does NOT Prove

- Source code correctness
- Runtime behavior compliance
- Absence of events (only presence)
- External system integrity
```

---

## Verification Algorithm

```python
def verify_audit_bundle(bundle_path: Path) -> bool:
    """
    Verify audit bundle integrity.

    Returns True only if ALL checks pass.
    """
    manifest = load_json(bundle_path / "AUDIT_MANIFEST.json")

    # Step 1: Verify each file hash
    for rel_path, meta in manifest["contents"].items():
        file_path = bundle_path / rel_path
        actual_hash = sha256(file_path.read_bytes()).hexdigest()
        if actual_hash != meta["sha256"]:
            return False  # FAIL: File tampered

    # Step 2: Verify bundle hash
    sorted_hashes = sorted(
        meta["sha256"] for meta in manifest["contents"].values()
    )
    computed_bundle_hash = sha256("".join(sorted_hashes).encode()).hexdigest()
    if computed_bundle_hash != manifest["bundle_hash"]:
        return False  # FAIL: Manifest tampered

    return True  # PASS
```

---

## Export Guarantees

| Guarantee | Enforcement |
|-----------|-------------|
| **Deterministic** | Same inputs → same output (sorted paths, stable hashes) |
| **Read-only** | Source files never modified |
| **Complete** | All events in time range included |
| **Verifiable** | SHA-256 hashes for every artifact |
| **Portable** | No runtime dependencies for verification |
| **Offline** | Verification requires no network access |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-17 | Initial schema (PAC-GOV-AUDIT-01) |
