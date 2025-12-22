# Proof Artifact Persistence

**PAC-DAN-PROOF-PERSISTENCE-01**  
**Author:** DAN (GID-07)  
**Date:** 2025-12-19  
**Status:** ACTIVE

---

## Storage Decision

**CHOSEN: Option A - Append-Only JSONL Log**

### Rationale
| Factor | JSONL (Chosen) | SQLite |
|--------|---------------|--------|
| Simplicity | ✅ No dependencies | ❌ Driver required |
| Inspectability | ✅ Human-readable | ❌ Requires tools |
| Backup/Replication | ✅ Simple file copy | ⚠️ Special handling |
| Crash Recovery | ✅ fsync guarantees | ⚠️ WAL complexity |
| Append-Only Enforcement | ✅ Natural fit | ⚠️ Must disable UPDATE/DELETE |

---

## File Locations

| File | Purpose | Source of Truth |
|------|---------|-----------------|
| `./data/proofs.jsonl` | Append-only proof log | ✅ YES |
| `./data/proofs_manifest.json` | Runtime state cache | ❌ Advisory only |

### Environment Variables

```bash
# Override proof log location
CHAINBRIDGE_PROOF_LOG_PATH=./data/proofs.jsonl

# Override manifest location  
CHAINBRIDGE_PROOF_MANIFEST_PATH=./data/proofs_manifest.json
```

---

## Proof Record Schema

```json
{
  "proof_id": "uuid-v4",
  "content_hash": "sha256-of-payload",
  "chain_hash": "sha256(prev_chain_hash:content_hash)",
  "timestamp": "ISO8601",
  "proof_type": "execution|artifact|decision",
  "payload": { ... },
  "sequence_number": 1
}
```

### Hash Chain

Each proof includes a `chain_hash` linking it to the previous entry:

```
chain_hash[n] = SHA256(chain_hash[n-1] + ":" + content_hash[n])
```

This creates tamper-evident linking. Any modification breaks the chain.

---

## Startup Validation

On every startup, the system:

1. Reads entire `proofs.jsonl` file
2. Recomputes `content_hash` for each entry
3. Verifies `chain_hash` continuity
4. **CRASHES if any mismatch** (fail loud)

### Boot Log Example (Success)

```
============================================================
PROOF STORAGE VALIDATION
  Status: PASS
  Proof Count: 42
  Last Hash: a3f8b2c1d4e5f6a7...
  Log Path: ./data/proofs.jsonl
============================================================
```

### Boot Log Example (Failure)

```
============================================================
CRITICAL: PROOF INTEGRITY VALIDATION FAILED!
  Error: Line 23: Content hash mismatch! Stored=a3f8b2c1... Computed=9d8e7f6a...
  Startup ABORTED - proof artifacts may be corrupted
============================================================
```

---

## Append-Only Guarantees

### ENFORCED
- ✅ New proofs append to end of file
- ✅ `fsync` on every write
- ✅ File lock prevents concurrent corruption
- ✅ No UPDATE operation exists
- ✅ No DELETE operation exists

### INVARIANTS (INV)
| ID | Invariant | Enforcement |
|----|-----------|-------------|
| INV-001 | Proofs are append-only | No update/delete methods |
| INV-002 | Content-addressable hashing | SHA-256 of payload |
| INV-003 | Startup validation | Hash recomputation |
| INV-004 | Corruption = crash | `ProofIntegrityError` |
| INV-005 | Write durability | `fsync` on every append |

---

## Restart Procedure

### Standard Restart
```bash
# Stop server (Ctrl+C or kill)
# Start server
make api-server  # or: uvicorn api.server:app

# Check boot log for:
#   PROOF STORAGE VALIDATION
#   Status: PASS
```

### Recovery from Corruption

If startup fails with `PROOF INTEGRITY VALIDATION FAILED`:

1. **DO NOT DELETE THE LOG FILE** - it is evidence
2. Copy corrupted file: `cp data/proofs.jsonl data/proofs.jsonl.corrupted`
3. Investigate root cause (disk failure? manual edit?)
4. If recoverable: truncate to last valid entry
5. If not: contact DAN/Benson for forensic review

---

## Operational Commands

```bash
# Count proofs
wc -l data/proofs.jsonl

# View last 5 proofs
tail -5 data/proofs.jsonl | jq .

# Verify latest hash manually
tail -1 data/proofs.jsonl | jq -r '.content_hash'

# View manifest
cat data/proofs_manifest.json | jq .

# Backup proofs (preserves append-only semantics)
cp data/proofs.jsonl data/proofs.jsonl.backup.$(date +%Y%m%d)
```

---

## Integration Points

### API Server (`api/server.py`)
- Calls `init_proof_storage()` at startup
- Crashes if validation fails

### Spine Executor (`core/spine/executor.py`)
- Existing `ProofStore` for execution proofs
- Will be migrated to use `ProofStorageV1` (future PAC)

### ProofPacks API (`src/api/proofpacks_api.py`)
- Existing individual JSON files
- Will be migrated to use `ProofStorageV1` (future PAC)

---

## Monitoring

The following should be monitored:

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Proof count | manifest.json | Unexpected decrease |
| File size | `proofs.jsonl` | Sudden change |
| Startup time | Boot log | > 10s for large logs |
| Validation failures | Boot log | Any occurrence |

---

## Remaining Operational Risk

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Disk full prevents writes | LOW | Monitor disk space |
| Manual file edit | LOW | File permissions (future) |
| Clock skew affects ordering | MEDIUM | Use sequence numbers |
| Large log slows startup | MEDIUM | Archive old proofs (future) |

---

## QA Checklist

- [x] Storage mechanism chosen and documented
- [x] Append-only behavior enforced
- [x] Hash validation on startup
- [x] Corruption causes hard failure
- [x] Storage location explicit
- [x] No write path allows overwrite
- [x] fsync ensures durability
- [x] Chain hash provides tamper detection

---

**END OF DOCUMENT**
