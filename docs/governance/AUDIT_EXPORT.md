# ChainBridge Governance Audit Export

**Document Type**: Customer & Auditor Reference
**Version**: 1.0.0
**Last Updated**: December 2025

---

## Executive Summary

ChainBridge provides a **Governance Audit Bundle** — a portable, cryptographically verifiable archive of all governance evidence. This bundle can be:

- Handed to auditors without explanation
- Verified offline without runtime access
- Independently validated using standard tools (SHA-256)
- Retained for compliance and legal purposes

---

## What This Proves

The Governance Audit Bundle provides evidence that:

| Claim | Evidence |
|-------|----------|
| **Decisions are logged** | Every governance decision (allow/deny) is captured in immutable event logs |
| **Denials are recorded** | Rejected operations include reason codes and context |
| **Artifacts are hashed** | Build outputs are fingerprinted with SHA-256 at CI time |
| **Configuration is versioned** | Governance root files are hashed to detect drift |
| **Evidence is tamper-evident** | Bundle hash changes if any file is modified |

---

## What This Does NOT Prove

| Limitation | Explanation |
|------------|-------------|
| **Source code correctness** | Code quality/bugs are out of scope; only decisions are logged |
| **Runtime behavior beyond logged events** | We prove what was logged, not what wasn't |
| **Absence of events** | Missing events cannot be proven from present data |
| **External system security** | Third-party integrations are not covered |
| **Physical security** | Hardware and network security are separate concerns |

---

## How to Request an Audit Bundle

### Option 1: Self-Service Export

```bash
# Export last 30 days
python -m core.governance.audit_exporter \
  --start "2025-11-17T00:00:00Z" \
  --end "2025-12-17T00:00:00Z" \
  --out audit_bundle_Q4_2025

# Export all available events
python -m core.governance.audit_exporter \
  --out audit_bundle_full
```

### Option 2: Request from ChainBridge

Contact your ChainBridge representative to request an audit bundle for a specific time period.

---

## How to Verify Independently

### Quick Verification

```bash
python scripts/verify_audit_bundle.py audit_bundle_Q4_2025
```

**Expected output (success)**:
```
AUDIT BUNDLE VERIFIED
✓ All required files present
✓ All file hashes match
✓ Bundle hash valid
✓ Governance fingerprint present

Bundle Info:
  Bundle ID:    audit-abc123def456
  Created:      2025-12-17T00:00:00+00:00
  Bundle Hash:  a1b2c3d4e5f6...
  Schema:       v1.0.0
```

### Manual Verification (No Dependencies)

If you prefer not to run our script, you can verify manually:

1. **Parse the manifest**:
   ```bash
   cat audit_bundle/AUDIT_MANIFEST.json | python -m json.tool
   ```

2. **Compute file hashes**:
   ```bash
   shasum -a 256 audit_bundle/governance_events/events.jsonl
   ```

3. **Compare against manifest**: The `sha256` values in `contents` must match

4. **Verify bundle hash**:
   - Sort all `sha256` values alphabetically
   - Concatenate them (no separator)
   - Compute SHA-256 of the result
   - Compare against `bundle_hash`

---

## Bundle Contents

Every audit bundle contains:

```
audit_bundle/
├── AUDIT_MANIFEST.json              # Master manifest with all hashes
├── governance_events/
│   └── events.jsonl                 # All governance decisions
├── artifacts/
│   └── artifacts.json               # Build artifact hashes (if available)
├── fingerprint/
│   └── governance_fingerprint.json  # Configuration fingerprint
├── scope/
│   └── scope_declaration.json       # What's included/excluded
└── VERIFY.md                        # Verification instructions
```

### Governance Events (events.jsonl)

Each line is a complete JSON record:

```json
{
  "event_type": "DECISION_DENIED",
  "timestamp": "2025-12-01T12:00:00.000000+00:00",
  "event_id": "gov-abc123",
  "agent_gid": "GID-05",
  "verb": "EXECUTE",
  "target": "tool_name",
  "decision": "DENY",
  "reason_code": "EXECUTE_NOT_PERMITTED"
}
```

**Event Types**:
- `DECISION_ALLOWED` — Operation permitted
- `DECISION_DENIED` — Operation rejected
- `SCOPE_VIOLATION` — File access outside permitted scope
- `ARTIFACT_VERIFIED` — Build artifact hash matched
- `ARTIFACT_VERIFICATION_FAILED` — Build artifact hash mismatch

---

## Guarantees Enforced

| Guarantee | Implementation |
|-----------|----------------|
| **Deterministic export** | Same inputs always produce same output |
| **Read-only operation** | Source logs are never modified |
| **Complete within range** | All events in specified time range included |
| **Cryptographic integrity** | SHA-256 hashes for every artifact |
| **Offline verification** | No network access required |
| **No transformation** | Events are byte-for-byte copies, not summaries |

---

## Assumptions

The audit bundle assumes:

1. **Source integrity**: Governance logs were append-only and unmodified before export
2. **System clock accuracy**: Timestamps reflect actual system time
3. **Hash algorithm security**: SHA-256 is cryptographically secure

---

## Compliance Mapping

| Framework | Relevant Controls |
|-----------|-------------------|
| **SOC 2** | CC6.1 (Logical Access), CC7.2 (Monitoring) |
| **ISO 27001** | A.12.4 (Logging), A.14.2 (Security in Development) |
| **GDPR** | Article 30 (Records of Processing) |
| **PCI DSS** | Requirement 10 (Track and Monitor Access) |

---

## Retention

Audit bundles should be retained according to your organization's policies. Recommended minimums:

| Use Case | Retention Period |
|----------|------------------|
| Financial services | 7 years |
| Healthcare | 6 years |
| General enterprise | 3 years |
| Internal audit | 1 year |

---

## Contact

For questions about audit bundles or governance:

- **Technical**: engineering@chainbridge.io
- **Compliance**: compliance@chainbridge.io
- **Sales**: enterprise@chainbridge.io

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-17 | Initial release (PAC-GOV-AUDIT-01) |
