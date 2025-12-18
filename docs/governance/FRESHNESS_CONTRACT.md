# Trust Data Freshness Contract

> **PAC-GOV-FRESHNESS-01** — DAN (GID-07)
> Version: 1.0.0

## Overview

The Trust Data Freshness Contract ensures that audit bundles and Trust Center data are **provably current**. This contract provides machine-verifiable guarantees that trust evidence is not stale.

## What Freshness Means

| Claim | Meaning |
|-------|---------|
| **Fresh** | All source timestamps are within `max_staleness_seconds` of verification time |
| **Stale** | At least one source timestamp exceeds the staleness threshold |
| **Verification** | Offline, deterministic comparison of timestamps |

### Freshness is Truth Signaling

This contract does **not**:
- Run background jobs
- Auto-refresh data
- Make availability promises
- Modify governance behavior

It **only**:
- Records when data was captured
- Fails loudly when data is old
- Reports exactly how stale each source is

## What Freshness Does NOT Mean

| Non-Claim | Why |
|-----------|-----|
| Data is correct | Only that it's recent |
| System is available | Only that export happened |
| Data will stay fresh | Bundles age over time |
| SLA compliance | No uptime guarantees |

## Freshness Manifest Schema

Every audit bundle includes `FRESHNESS_MANIFEST.json`:

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2025-12-17T18:30:00.000000+00:00",
  "max_staleness_seconds": 86400,
  "source_timestamps": {
    "governance_events": {
      "timestamp": "2025-12-17T18:29:45.123456+00:00",
      "description": "Most recent governance event timestamp"
    },
    "governance_fingerprint": {
      "timestamp": "2025-12-17T18:30:00.000000+00:00",
      "description": "Governance fingerprint computation timestamp"
    },
    "audit_bundle": {
      "timestamp": "2025-12-17T18:30:00.000000+00:00",
      "description": "Audit bundle creation timestamp"
    }
  }
}
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Schema version (semver) |
| `generated_at` | ISO 8601 | Bundle generation timestamp |
| `max_staleness_seconds` | integer | Maximum allowed age before failure |
| `source_timestamps` | object | Per-source timestamp records |

### Source Timestamps

| Source | Description |
|--------|-------------|
| `governance_events` | Most recent event in the events log |
| `governance_fingerprint` | When fingerprint was computed |
| `audit_bundle` | Bundle creation time |

## Verification Algorithm

```python
def verify_freshness(manifest, check_time=now()):
    """
    Fail-closed freshness verification.

    FAILS if: now - any(source_timestamp) > max_staleness_seconds
    """
    max_staleness = manifest["max_staleness_seconds"]

    for source, info in manifest["source_timestamps"].items():
        age_seconds = (check_time - parse(info["timestamp"])).total_seconds()

        if age_seconds > max_staleness:
            return FAIL(
                source=source,
                age=age_seconds,
                max=max_staleness,
                exceeded_by=age_seconds - max_staleness
            )

    return PASS
```

## Why Failure is Expected Behavior

Freshness verification **should fail** when:

1. **Bundle is old** — Audit bundles age over time. A 30-day-old bundle *should* fail a 24-hour freshness check.

2. **Export was delayed** — If events haven't been emitted recently, the bundle reflects that reality.

3. **Time drift** — Clock synchronization issues surface as verification failures.

This is correct behavior. Stale trust data should not silently pass.

## Usage

### Export with Custom Staleness

```python
from core.governance.audit_exporter import export_audit_bundle

# Default: 24-hour staleness threshold
result = export_audit_bundle(output_path="./audit_bundle")

# Custom: 1-hour staleness threshold
result = export_audit_bundle(
    output_path="./audit_bundle",
    max_staleness_seconds=3600  # 1 hour
)
```

### Verify Bundle Freshness

```bash
# Full verification (includes freshness)
python scripts/verify_audit_bundle.py ./audit_bundle

# Skip freshness (for historical bundles)
python scripts/verify_audit_bundle.py ./audit_bundle --skip-freshness
```

### Programmatic Verification

```python
from core.governance.freshness import load_freshness_manifest, verify_freshness

manifest = load_freshness_manifest(Path("./audit_bundle"))
result = verify_freshness(manifest)

if not result.is_fresh:
    for stale in result.stale_sources:
        print(f"STALE: {stale['source']} exceeded by {stale['exceeded_by_seconds']}s")
```

## Verification Output

### Fresh Bundle

```
AUDIT BUNDLE VERIFIED

✓ All required files present
✓ All file hashes match
✓ Bundle hash valid
✓ Governance fingerprint present
✓ Artifact manifest present
✓ All sources fresh

Bundle Info:
  Bundle ID:    audit-abc123def456
  Created:      2025-12-17T18:30:00.000000+00:00
  Bundle Hash:  a1b2c3d4e5f6g7h8...
  Schema:       v1.0.0
  Max Staleness: 86400s (24h)
```

### Stale Bundle

```
AUDIT BUNDLE VERIFICATION FAILED

✓ All required files present
✓ All file hashes match
✓ Bundle hash valid
✓ Governance fingerprint present
✓ Artifact manifest present
✗ Freshness verification failed:
    Source 'governance_events' is stale: 90000s old (max: 86400s, exceeded by: 3600s)
```

## Default Staleness Thresholds

| Context | Default | Rationale |
|---------|---------|-----------|
| Audit Bundle | 86400s (24h) | Daily refresh cycle |
| Trust Center | 86400s (24h) | Aligned with bundles |
| CI Export | 3600s (1h) | Build freshness |

## Compliance Mapping

| Framework | Requirement | How Freshness Helps |
|-----------|-------------|---------------------|
| SOC 2 | Evidence currency | Timestamps prove recency |
| ISO 27001 | Audit trail integrity | Staleness detection |
| Enterprise Procurement | Data freshness | Machine-verifiable |

## Security Considerations

1. **Timestamps are assertions** — They can be faked at export time, but verification fails if they don't match check time.

2. **Bundle hash includes manifest** — Tampering with freshness manifest invalidates the bundle hash.

3. **Offline verification** — No trust required in network or external services.

## No Governance Authority

This module has **no governance authority**:
- Cannot approve or deny operations
- Cannot modify events or fingerprints
- Only reads and reports timestamps

Freshness is **truth signaling**, not **enforcement**.

---

*Document Version: 1.0.0*
*Last Updated: 2025-12-17*
*Owner: DAN (GID-07)*
