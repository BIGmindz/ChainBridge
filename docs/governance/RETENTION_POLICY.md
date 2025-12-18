# Governance Event Retention Policy

**PAC-DAN-05 — DAN (GID-07)**

## Overview

ChainBridge implements deterministic, auditable governance event retention to:
- Prevent unbounded log growth
- Preserve forensic value
- Support regulatory compliance
- Guarantee no silent data loss

## Retention Policy (Explicit)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `MAX_FILE_SIZE_BYTES` | 50 MB | Maximum size before rotation |
| `MAX_FILE_COUNT` | 20 | Maximum rotated files to keep |
| Rotation Naming | `.jsonl`, `.jsonl.1`, `.jsonl.2`, ... | Numbered suffix convention |
| Deletion Order | Oldest first (FIFO) | `.jsonl.20` deleted before `.jsonl.19` |

**Total Maximum Storage**: ~1 GB (50 MB × 20 files + active file)

## Rotation Algorithm

```
On each event write:
1. Check if current file exceeds MAX_FILE_SIZE_BYTES
2. If exceeded:
   a. Close current file handle
   b. Shift existing .jsonl.N files to .jsonl.(N+1)
   c. Rename .jsonl to .jsonl.1
   d. Delete files where N > MAX_FILE_COUNT
   e. Create new empty .jsonl
3. Write event to .jsonl
4. Flush immediately
```

### Critical Guarantees

- **No Event Splitting**: Events are NEVER split across files
- **No Silent Drops**: Write failures are logged, not swallowed
- **Atomic Rotation**: File renames are atomic on POSIX
- **Append-Only**: Source logs are never modified after write

## File Layout

```
logs/
├── governance_events.jsonl      # Current (active) file
├── governance_events.jsonl.1    # Most recent rotated
├── governance_events.jsonl.2    # Second most recent
├── ...
└── governance_events.jsonl.20   # Oldest (next to be deleted)
```

## Event Format (JSONL)

Each line is a complete JSON object:

```json
{"event_type":"DECISION_DENIED","timestamp":"2025-12-17T16:55:17.897350+00:00","event_id":"gov-27bbebf064ef","agent_gid":"GID-05","verb":"EXECUTE","target":"dangerous_tool","decision":"DENY","reason_code":"EXECUTE_NOT_PERMITTED"}
```

## Export / Snapshot

For auditor handoff or incident response, use `GovernanceEventExporter`:

```python
from core.governance import GovernanceEventExporter, create_exporter

exporter = create_exporter("logs/governance_events.jsonl")

# Get summary
summary = exporter.get_export_summary()

# Export with time filter
from datetime import datetime, timezone, timedelta
start = datetime.now(timezone.utc) - timedelta(days=7)
exporter.export_to_file("audit_export.jsonl", start_time=start)
```

### Export Guarantees

- **Read-Only**: Source files are NEVER modified
- **Deterministic Order**: Oldest events first (chronological)
- **Exact Copy**: Exported events match source byte-for-byte
- **Optional Filtering**: Date range filters supported

## Failure Mode Analysis

| Failure | Behavior | Recovery |
|---------|----------|----------|
| Disk full | Log warning, continue execution | Free space, events resume |
| Permission denied | Log warning, continue execution | Fix permissions |
| Rotation failure | Raise exception (critical) | Manual intervention required |
| Corrupt JSON line | Skip on export, log warning | No automatic recovery |

### Design Philosophy

> If retention cannot be guaranteed, fail closed or escalate.

The system prioritizes:
1. **No silent data loss** over graceful degradation
2. **Deterministic behavior** over optimization
3. **Auditability** over convenience

## Usage

### Production Setup

```python
from core.governance import configure_rotating_sink, emitter

# Configure rotating sink
sink = configure_rotating_sink(
    path="logs/governance_events.jsonl",
    max_file_size_bytes=50 * 1024 * 1024,  # 50 MB
    max_file_count=20,
)
emitter.add_sink(sink)
```

### Check Retention Status

```python
from core.governance import RotatingJSONLSink

sink = RotatingJSONLSink("logs/governance_events.jsonl")
info = sink.get_retention_info()
print(f"Files: {info['current_file_count']}")
print(f"Total size: {info['total_size_bytes'] / 1024 / 1024:.2f} MB")
```

## Compliance Notes

- **GDPR**: Retention period should be documented in privacy policy
- **SOC 2**: Audit logs must be retained for audit window
- **Financial Services**: Check regulatory requirements for log retention periods

This policy provides sensible defaults. Adjust `MAX_FILE_SIZE_BYTES` and `MAX_FILE_COUNT` based on:
- Event volume
- Storage constraints
- Compliance requirements
- Incident response needs

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-17 | Initial retention policy (PAC-DAN-05) |
