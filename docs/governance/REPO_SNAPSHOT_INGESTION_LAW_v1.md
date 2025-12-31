# REPO_SNAPSHOT_INGESTION_LAW_v1.md

## Repository Snapshot Ingestion Law

```
PAC Reference:  PAC-BENSON-EXEC-GOVERNANCE-REPO-SNAPSHOT-INGESTION-018
Effective Date: 2025-12-26
Version:        1.0.0
Classification: HARD LAW — Non-Negotiable
```

---

## 1. Purpose

This document establishes **Repository Snapshot Ingestion** as a mandatory,
deterministic bootstrap prerequisite for all execution sessions.

The snapshot eliminates context drift between:
- ChatGPT drafting surfaces
- VS Code execution environments
- Any other execution context

---

## 2. Definitions

### 2.1. Repository Snapshot

A **Repository Snapshot** is a point-in-time capture of the codebase that includes:

| Component      | Format     | Required | Description                          |
|----------------|------------|----------|--------------------------------------|
| Source Archive | ZIP        | ✅ YES   | Complete source tree                 |
| Manifest File  | JSON       | ✅ YES   | File list with paths and hashes      |
| Snapshot Hash  | SHA-256    | ✅ YES   | Hash of the archive                  |
| Timestamp      | ISO-8601   | ✅ YES   | Creation time                        |
| Source         | String     | ✅ YES   | Origin identifier (e.g., "vscode")   |

### 2.2. Snapshot Lock

A **Snapshot Lock** is an immutable binding between:
- The session bootstrap token
- The snapshot SHA-256 hash
- The snapshot timestamp

Once locked, the snapshot cannot be changed without terminating the session.

---

## 3. Ingestion Requirements — HARD LAW

### 3.1. Mandatory Pre-Bootstrap

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     SNAPSHOT INGESTION SEQUENCE                         │
└─────────────────────────────────────────────────────────────────────────┘

SNAP-01 │ Snapshot Received    │ Receive ZIP + MANIFEST + SHA256
SNAP-02 │ Hash Verification    │ Verify SHA256 matches archive
SNAP-03 │ Manifest Validation  │ Validate all files listed
SNAP-04 │ Snapshot Locked      │ Bind hash to session
        ↓
BOOT-01 │ Identity Lock        │ (Standard bootstrap continues)
BOOT-02 │ Mode Lock            │
BOOT-03 │ Lane Lock            │
BOOT-04 │ Tool Strip           │
BOOT-05 │ Echo Handshake       │
        ↓
        │ SESSION SEALED       │ Ready for PAC execution
```

### 3.2. Invariants — MANDATORY

```python
INV-SNAP-001: No PAC execution without snapshot ingestion
INV-SNAP-002: Snapshot hash must match archive before lock
INV-SNAP-003: Snapshot is immutable per session
INV-SNAP-004: Re-ingestion mid-session is forbidden
INV-SNAP-005: Hash mismatch invalidates session immediately
INV-SNAP-006: Missing snapshot blocks bootstrap (FAIL-CLOSED)
```

---

## 4. Snapshot Structure

### 4.1. Archive Format

```
chainbridge-snapshot-{timestamp}.zip
├── src/
├── core/
├── tests/
├── docs/
├── config/
└── SNAPSHOT_MANIFEST.json
```

### 4.2. Manifest Schema

```json
{
  "$schema": "https://chainbridge.io/schemas/snapshot_manifest_v1.json",
  "version": "1.0.0",
  "snapshot_id": "snap_20251226120000_abc123",
  "created_at": "2025-12-26T12:00:00Z",
  "source": "vscode",
  "archive_hash": "sha256:abcd1234...",
  "file_count": 1234,
  "files": [
    {
      "path": "core/governance/enforcement.py",
      "hash": "sha256:...",
      "size": 12345
    }
  ]
}
```

### 4.3. Hash Calculation

```python
# Archive hash calculation
import hashlib

def calculate_snapshot_hash(archive_path: str) -> str:
    """Calculate SHA-256 hash of snapshot archive."""
    sha256 = hashlib.sha256()
    with open(archive_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"
```

---

## 5. Drift Detection

### 5.1. What Constitutes Drift

| Drift Type         | Detection Method        | Result      |
|--------------------|-------------------------|-------------|
| File modified      | Hash mismatch           | HARD FAIL   |
| File added         | Not in manifest         | HARD FAIL   |
| File deleted       | Missing from filesystem | HARD FAIL   |
| Archive corrupted  | Hash mismatch           | HARD FAIL   |
| Timestamp drift    | Clock skew detection    | WARNING     |

### 5.2. Drift Response

```
DRIFT DETECTED → SESSION TERMINATED → NEW SNAPSHOT REQUIRED
```

No recovery. No partial re-ingestion. Complete restart required.

---

## 6. Session Binding

### 6.1. Snapshot Lock State

```python
@dataclass(frozen=True)
class SnapshotLock:
    """Immutable snapshot lock binding."""
    
    snapshot_id: str
    archive_hash: str
    timestamp: str
    source: str
    locked_at: str
    session_token: Optional[str] = None
```

### 6.2. Bootstrap Integration

```python
# Snapshot must be locked BEFORE BOOT-01
if not snapshot_state.is_locked:
    raise SnapshotRequiredError(
        "HARD FAIL: Snapshot ingestion required before bootstrap"
    )

# SNAP-01 through SNAP-04 must complete before BOOT-01
bootstrap_result = enforcer.bootstrap(
    gid=gid,
    mode=mode,
    lane=lane,
    snapshot=snapshot_lock,  # Required
)
```

---

## 7. Terminal Emissions — Canonical

### 7.1. Snapshot Received

```
════════════════════════════════════════════════════════════════════
🧾 SNAPSHOT RECEIVED
   SNAPSHOT_ID: snap_20251226120000_abc123
   SOURCE: vscode
   FILE_COUNT: 1234
   ARCHIVE_HASH: sha256:abcd1234...
════════════════════════════════════════════════════════════════════
```

### 7.2. Snapshot Locked

```
════════════════════════════════════════════════════════════════════
🔐 SNAPSHOT LOCKED
   SNAPSHOT_ID: snap_20251226120000_abc123
   HASH: sha256:abcd1234...
   BOUND_TO_SESSION: boot_20251226120001_GID-01_xyz789
════════════════════════════════════════════════════════════════════
```

### 7.3. Snapshot Drift Detected

```
════════════════════════════════════════════════════════════════════
⛔ SNAPSHOT DRIFT DETECTED
   EXPECTED_HASH: sha256:abcd1234...
   ACTUAL_HASH: sha256:xyz9876...
   RESULT: SESSION TERMINATED
   ACTION: NEW_SNAPSHOT_REQUIRED
════════════════════════════════════════════════════════════════════
```

### 7.4. Snapshot Verified

```
════════════════════════════════════════════════════════════════════
🟩 SNAPSHOT VERIFIED
   SNAPSHOT_ID: snap_20251226120000_abc123
   HASH: sha256:abcd1234... ✅ MATCH
   STATUS: READY_FOR_BOOTSTRAP
════════════════════════════════════════════════════════════════════
```

---

## 8. Failure Modes

### 8.1. Missing Snapshot

```
Attempt PAC execution without snapshot:
  → HARD FAIL
  → Bootstrap blocked at SNAP-01
  → Message: "Snapshot ingestion required"
```

### 8.2. Hash Mismatch

```
Archive hash doesn't match declared hash:
  → HARD FAIL
  → Session terminated
  → Message: "Snapshot drift detected"
```

### 8.3. Re-Ingestion Attempt

```
Attempt to ingest new snapshot in sealed session:
  → HARD FAIL
  → Session terminated
  → Message: "Re-ingestion forbidden"
```

### 8.4. Manifest Corruption

```
Manifest file missing or malformed:
  → HARD FAIL
  → Ingestion blocked
  → Message: "Invalid snapshot manifest"
```

---

## 9. Anti-Patterns — FORBIDDEN

### 9.1. ❌ Snapshot Bypass

```python
# FORBIDDEN — No execution without snapshot
bootstrap(gid="GID-01", mode="EXECUTION", lane="GOVERNANCE")
# HARD FAIL — snapshot=None
```

### 9.2. ❌ Hash Trust

```python
# FORBIDDEN — Never trust without verification
snapshot = SnapshotLock(hash="declared_hash")
# Must verify: snapshot.verify(archive) before lock
```

### 9.3. ❌ Mid-Session Re-Ingestion

```python
# FORBIDDEN — Session is immutable
sealed_session.ingest_snapshot(new_snapshot)
# HARD FAIL — Re-ingestion forbidden
```

### 9.4. ❌ Partial Ingestion

```python
# FORBIDDEN — All or nothing
snapshot.lock_without_verification()
# HARD FAIL — Hash verification required
```

---

## 10. Code Enforcement Location

```
core/governance/snapshot_state.py      — Immutable snapshot lock model
core/governance/snapshot_enforcer.py   — Verification and binding
core/governance/bootstrap_enforcer.py  — Pre-bootstrap snapshot check
core/governance/terminal_gates.py      — Terminal emission support
```

---

## 11. Changelog

| Version | Date       | PAC Reference | Description                        |
|---------|------------|---------------|------------------------------------|
| 1.0.0   | 2025-12-26 | PAC-018       | Initial snapshot ingestion law     |

---

## 12. Attestation

```
This document is HARD LAW.
No PAC execution without snapshot.
No exceptions.
FAIL-CLOSED only.
Code-enforced.
```

---

**END REPO_SNAPSHOT_INGESTION_LAW_v1.md**
