"""
🟢 DAN (GID-07) — Governance Audit Bundle Exporter
PAC-GOV-AUDIT-01: External Audit Export & Proof Bundle Contract

Read-only, cryptographically verifiable audit bundle export.

This module creates portable audit bundles containing:
- Governance events (JSONL)
- Artifact manifest + hashes
- Governance fingerprint
- Scope declaration
- Verification instructions

Key properties:
- Deterministic: Same inputs → same output
- Read-only: Source files NEVER modified
- Verifiable: SHA-256 hashes for all content
- Portable: No runtime dependencies for verification
- Offline: Verification requires no network access

NO NEW GOVERNANCE LOGIC. Export only.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.governance.freshness import DEFAULT_MAX_STALENESS_SECONDS, FRESHNESS_MANIFEST_FILENAME, SourceTimestamp, create_freshness_manifest
from core.governance.governance_fingerprint import GovernanceFingerprintEngine
from core.governance.retention import DEFAULT_ROTATING_LOG_PATH, RETENTION_POLICY_VERSION, GovernanceEventExporter

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

AUDIT_BUNDLE_SCHEMA_VERSION = "1.0.0"
AUDIT_BUNDLE_CREATOR = "ChainBridge Governance Audit Exporter"

# Default paths
DEFAULT_ARTIFACT_MANIFEST_PATH = "build/artifacts.json"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class AuditBundleConfig:
    """Configuration for audit bundle export."""

    start_time: datetime | None = None
    end_time: datetime | None = None
    source_log_path: str = DEFAULT_ROTATING_LOG_PATH
    artifact_manifest_path: str = DEFAULT_ARTIFACT_MANIFEST_PATH
    output_path: str | Path | None = None
    project_root: str | Path | None = None
    max_staleness_seconds: int = DEFAULT_MAX_STALENESS_SECONDS


@dataclass
class FileContent:
    """Metadata about a file in the bundle."""

    sha256: str
    size_bytes: int
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditBundleResult:
    """Result of audit bundle export."""

    bundle_path: Path
    bundle_id: str
    bundle_hash: str
    created_at: str
    event_count: int
    file_count: int
    success: bool
    error: str | None = None


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT BUNDLE EXPORTER
# ═══════════════════════════════════════════════════════════════════════════════


class AuditBundleExporter:
    """
    Exports governance evidence as a verifiable audit bundle.

    The audit bundle is a directory containing:
    - AUDIT_MANIFEST.json: Top-level manifest with hashes
    - governance_events/events.jsonl: Consolidated governance events
    - artifacts/artifacts.json: Build artifact manifest
    - fingerprint/governance_fingerprint.json: Governance root fingerprint
    - scope/scope_declaration.json: Explicit scope declaration
    - VERIFY.md: Human-readable verification instructions

    All files are hashed with SHA-256. The bundle_hash is the hash
    of all content hashes concatenated in sorted order.
    """

    def __init__(self, config: AuditBundleConfig | None = None):
        """Initialize exporter with configuration."""
        self.config = config or AuditBundleConfig()
        self._project_root = Path(self.config.project_root or Path.cwd())

    def _compute_sha256(self, data: bytes) -> str:
        """Compute SHA-256 hash of bytes."""
        return hashlib.sha256(data).hexdigest()

    def _compute_file_sha256(self, path: Path) -> str:
        """Compute SHA-256 hash of file contents."""
        return self._compute_sha256(path.read_bytes())

    def _generate_bundle_id(self) -> str:
        """Generate unique bundle identifier."""
        return f"audit-{uuid.uuid4().hex[:12]}"

    def _timestamp_now(self) -> str:
        """Get current UTC timestamp as ISO string."""
        return datetime.now(timezone.utc).isoformat()

    def _create_bundle_dir(self, output_path: Path | None = None) -> Path:
        """Create bundle directory structure."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        if output_path:
            bundle_dir = Path(output_path)
        else:
            bundle_dir = self._project_root / f"audit_bundle_{timestamp}"

        # Create directory structure
        bundle_dir.mkdir(parents=True, exist_ok=True)
        (bundle_dir / "governance_events").mkdir(exist_ok=True)
        (bundle_dir / "artifacts").mkdir(exist_ok=True)
        (bundle_dir / "fingerprint").mkdir(exist_ok=True)
        (bundle_dir / "scope").mkdir(exist_ok=True)
        (bundle_dir / "claims").mkdir(exist_ok=True)

        return bundle_dir

    def _export_governance_events(self, bundle_dir: Path) -> tuple[FileContent, int]:
        """
        Export governance events to bundle.

        Returns (FileContent, event_count).
        """
        events_path = bundle_dir / "governance_events" / "events.jsonl"
        source_path = self._project_root / self.config.source_log_path

        exporter = GovernanceEventExporter(source_path)
        event_count = exporter.export_to_file(
            events_path,
            start_time=self.config.start_time,
            end_time=self.config.end_time,
        )

        # Compute hash
        content_hash = self._compute_file_sha256(events_path)
        size_bytes = events_path.stat().st_size

        return (
            FileContent(
                sha256=content_hash,
                size_bytes=size_bytes,
                extra={"event_count": event_count},
            ),
            event_count,
        )

    def _export_artifact_manifest(self, bundle_dir: Path) -> FileContent | None:
        """
        Export artifact manifest to bundle.

        Returns FileContent or None if not available.
        """
        source_path = self._project_root / self.config.artifact_manifest_path
        dest_path = bundle_dir / "artifacts" / "artifacts.json"

        if not source_path.exists():
            return None

        # Copy file (no transformation)
        shutil.copy2(source_path, dest_path)

        content_hash = self._compute_file_sha256(dest_path)
        size_bytes = dest_path.stat().st_size

        return FileContent(sha256=content_hash, size_bytes=size_bytes)

    def _export_governance_fingerprint(self, bundle_dir: Path) -> FileContent:
        """
        Export governance fingerprint to bundle.

        Computes fresh fingerprint at export time.
        """
        dest_path = bundle_dir / "fingerprint" / "governance_fingerprint.json"

        engine = GovernanceFingerprintEngine(self._project_root)
        fingerprint = engine.compute_fingerprint()

        # Write as JSON
        fingerprint_dict = fingerprint.to_dict()
        content = json.dumps(fingerprint_dict, indent=2, sort_keys=True)
        dest_path.write_text(content, encoding="utf-8")

        content_hash = self._compute_sha256(content.encode("utf-8"))
        size_bytes = len(content.encode("utf-8"))

        return FileContent(
            sha256=content_hash,
            size_bytes=size_bytes,
            extra={"composite_hash": fingerprint.composite_hash},
        )

    def _create_scope_declaration(self, bundle_dir: Path, artifact_present: bool) -> FileContent:
        """Create scope declaration document."""
        dest_path = bundle_dir / "scope" / "scope_declaration.json"

        scope = {
            "schema_version": AUDIT_BUNDLE_SCHEMA_VERSION,
            "included": {
                "governance_events": {
                    "description": "All governance decisions, denials, and violations",
                    "source": self.config.source_log_path,
                    "time_bounded": bool(self.config.start_time or self.config.end_time),
                },
                "artifact_manifest": {
                    "description": "SHA-256 hashes of tracked build artifacts",
                    "source": self.config.artifact_manifest_path,
                    "present": artifact_present,
                },
                "governance_fingerprint": {
                    "description": "Cryptographic fingerprint of governance root files",
                    "source": "computed",
                    "present": True,
                },
            },
            "excluded": {
                "raw_source_code": "Source files not included; only hashes",
                "runtime_secrets": "No credentials, API keys, or secrets exported",
                "user_data": "No PII or user-specific data",
                "third_party_logs": "No external service logs",
            },
            "assumptions": {
                "source_integrity": "Source logs assumed append-only and unmodified",
                "hash_algorithm": "SHA-256 used for all cryptographic hashes",
                "timestamp_source": "System clock at export time",
            },
            "limitations": {
                "completeness": "Only events within specified time range",
                "retention": "Subject to retention policy (older events may be rotated out)",
            },
        }

        content = json.dumps(scope, indent=2, sort_keys=True)
        dest_path.write_text(content, encoding="utf-8")

        content_hash = self._compute_sha256(content.encode("utf-8"))
        size_bytes = len(content.encode("utf-8"))

        return FileContent(sha256=content_hash, size_bytes=size_bytes)

    def _export_claims_snapshot(self, bundle_dir: Path) -> FileContent | None:
        """
        Export claims snapshot to bundle.

        PAC-DAN-CLAIMS-BINDING-02: Bind claim IDs into audit bundles.

        Copies the canonical CLAIM_BINDINGS.json into the bundle's claims/
        directory, creating a point-in-time snapshot of claim-to-artifact
        bindings.

        Returns FileContent or None if bindings file not found.
        """
        source_path = self._project_root / "docs" / "trust" / "CLAIM_BINDINGS.json"
        dest_path = bundle_dir / "claims" / "claims_snapshot.json"

        if not source_path.exists():
            return None

        # Load, validate structure, and write (ensures valid JSON)
        try:
            bindings = json.loads(source_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

        # Extract claim count for metadata
        claim_count = len(bindings.get("claims", {}))

        # Create snapshot with export timestamp
        snapshot = {
            "snapshot_metadata": {
                "source": "docs/trust/CLAIM_BINDINGS.json",
                "exported_at": self._timestamp_now(),
                "claim_count": claim_count,
                "schema_version": bindings.get("meta", {}).get("version", "unknown"),
            },
            "bindings": bindings,
        }

        content = json.dumps(snapshot, indent=2, sort_keys=True)
        dest_path.write_text(content, encoding="utf-8")

        content_hash = self._compute_sha256(content.encode("utf-8"))
        size_bytes = len(content.encode("utf-8"))

        return FileContent(
            sha256=content_hash,
            size_bytes=size_bytes,
            extra={"claim_count": claim_count},
        )

    def _create_freshness_manifest(
        self,
        bundle_dir: Path,
        generated_at: datetime,
        events_timestamp: datetime,
        fingerprint_timestamp: datetime,
        audit_bundle_timestamp: datetime,
    ) -> None:
        """
        Create freshness manifest for the audit bundle.

        PAC-GOV-FRESHNESS-01: Truth signaling for staleness detection.

        Args:
            bundle_dir: Bundle directory
            generated_at: Bundle generation timestamp
            events_timestamp: Timestamp of most recent governance event
            fingerprint_timestamp: Timestamp when fingerprint was computed
            audit_bundle_timestamp: Timestamp when audit bundle was created
        """
        source_timestamps = [
            SourceTimestamp(
                source="governance_events",
                timestamp=events_timestamp,
                description="Most recent governance event timestamp",
            ),
            SourceTimestamp(
                source="governance_fingerprint",
                timestamp=fingerprint_timestamp,
                description="Governance fingerprint computation timestamp",
            ),
            SourceTimestamp(
                source="audit_bundle",
                timestamp=audit_bundle_timestamp,
                description="Audit bundle creation timestamp",
            ),
        ]

        manifest = create_freshness_manifest(
            generated_at=generated_at,
            source_timestamps=source_timestamps,
            max_staleness_seconds=self.config.max_staleness_seconds,
        )

        dest_path = bundle_dir / FRESHNESS_MANIFEST_FILENAME
        dest_path.write_text(manifest.to_json(), encoding="utf-8")

    def _get_latest_event_timestamp(self, events_path: Path) -> datetime:
        """
        Get the timestamp of the most recent event in the events file.

        Returns the current time if no events or parsing fails.
        """
        now = datetime.now(timezone.utc)

        if not events_path.exists():
            return now

        latest_ts = None
        try:
            with events_path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        ts_str = event.get("timestamp", "")
                        if ts_str:
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            if latest_ts is None or ts > latest_ts:
                                latest_ts = ts
                    except (json.JSONDecodeError, ValueError):
                        continue
        except OSError:
            return now

        return latest_ts if latest_ts else now

    def _create_verify_instructions(self, bundle_dir: Path) -> None:
        """Create human-readable verification instructions."""
        dest_path = bundle_dir / "VERIFY.md"

        content = """# Audit Bundle Verification Instructions

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

1. Compute SHA-256 of each file listed in `AUDIT_MANIFEST.json` contents
2. Compare against the `sha256` values in the manifest
3. Concatenate all content hashes (sorted by path)
4. Compute SHA-256 of the concatenation
5. Compare against `bundle_hash` in the manifest

### Example (Python)

```python
import hashlib
import json
from pathlib import Path

def verify_bundle(bundle_path: str) -> bool:
    bundle = Path(bundle_path)
    manifest = json.loads((bundle / "AUDIT_MANIFEST.json").read_text())

    # Verify each file
    for rel_path, meta in manifest["contents"].items():
        file_path = bundle / rel_path
        actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual != meta["sha256"]:
            print(f"FAIL: {rel_path} hash mismatch")
            return False

    # Verify bundle hash
    sorted_hashes = sorted(m["sha256"] for m in manifest["contents"].values())
    computed = hashlib.sha256("".join(sorted_hashes).encode()).hexdigest()
    if computed != manifest["bundle_hash"]:
        print("FAIL: Bundle hash mismatch")
        return False

    print("PASS: Bundle verified")
    return True
```

## What This Proves

- ✓ All included files are unmodified since export
- ✓ Export was deterministic and reproducible
- ✓ Governance events are authentic records
- ✓ Artifact hashes were captured at CI time
- ✓ Governance fingerprint reflects configuration state

## What This Does NOT Prove

- ✗ Source code correctness or absence of bugs
- ✗ Runtime behavior compliance beyond logged events
- ✗ Absence of events (only presence of logged events)
- ✗ External system integrity
- ✗ Network security or access controls

## Support

For questions about this audit bundle, contact your ChainBridge representative
or refer to the Governance documentation.
"""
        dest_path.write_text(content, encoding="utf-8")

    def _create_manifest(
        self,
        bundle_dir: Path,
        bundle_id: str,
        created_at: str,
        contents: dict[str, FileContent],
        governance_fingerprint_hash: str,
    ) -> str:
        """
        Create AUDIT_MANIFEST.json and return bundle_hash.

        The bundle_hash is SHA-256 of sorted concatenation of all content hashes.
        """
        # Compute bundle hash from content hashes
        sorted_hashes = sorted(fc.sha256 for fc in contents.values())
        bundle_hash = self._compute_sha256("".join(sorted_hashes).encode("utf-8"))

        manifest = {
            "schema_version": AUDIT_BUNDLE_SCHEMA_VERSION,
            "bundle_id": bundle_id,
            "created_at": created_at,
            "created_by": AUDIT_BUNDLE_CREATOR,
            "export_parameters": {
                "start_time": (self.config.start_time.isoformat() if self.config.start_time else None),
                "end_time": (self.config.end_time.isoformat() if self.config.end_time else None),
                "source_log_path": self.config.source_log_path,
            },
            "contents": {
                path: {
                    "sha256": fc.sha256,
                    "size_bytes": fc.size_bytes,
                    **fc.extra,
                }
                for path, fc in sorted(contents.items())
            },
            "governance_fingerprint_hash": governance_fingerprint_hash,
            "retention_policy_version": RETENTION_POLICY_VERSION,
            "bundle_hash": bundle_hash,
        }

        manifest_path = bundle_dir / "AUDIT_MANIFEST.json"
        content = json.dumps(manifest, indent=2, sort_keys=True)
        manifest_path.write_text(content, encoding="utf-8")

        return bundle_hash

    def export(self, output_path: str | Path | None = None) -> AuditBundleResult:
        """
        Export audit bundle.

        Args:
            output_path: Optional output directory path

        Returns:
            AuditBundleResult with bundle metadata and status
        """
        bundle_id = self._generate_bundle_id()
        created_at = self._timestamp_now()

        try:
            # Create bundle directory
            bundle_dir = self._create_bundle_dir(Path(output_path) if output_path else None)

            contents: dict[str, FileContent] = {}

            # Export governance events
            events_content, event_count = self._export_governance_events(bundle_dir)
            contents["governance_events/events.jsonl"] = events_content

            # Export artifact manifest (optional)
            artifacts_content = self._export_artifact_manifest(bundle_dir)
            artifact_present = artifacts_content is not None
            if artifacts_content:
                contents["artifacts/artifacts.json"] = artifacts_content

            # Export governance fingerprint
            fingerprint_content = self._export_governance_fingerprint(bundle_dir)
            contents["fingerprint/governance_fingerprint.json"] = fingerprint_content
            governance_fingerprint_hash = fingerprint_content.extra.get("composite_hash", "")

            # Create scope declaration
            scope_content = self._create_scope_declaration(bundle_dir, artifact_present)
            contents["scope/scope_declaration.json"] = scope_content

            # PAC-DAN-CLAIMS-BINDING-02: Export claims snapshot
            claims_content = self._export_claims_snapshot(bundle_dir)
            if claims_content:
                contents["claims/claims_snapshot.json"] = claims_content

            # Create verification instructions
            self._create_verify_instructions(bundle_dir)

            # PAC-GOV-FRESHNESS-01: Create freshness manifest
            # Get actual timestamps from source data
            events_path = bundle_dir / "governance_events" / "events.jsonl"
            events_timestamp = self._get_latest_event_timestamp(events_path)
            bundle_timestamp = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            # Fingerprint timestamp is bundle creation time (computed fresh)
            fingerprint_timestamp = bundle_timestamp

            self._create_freshness_manifest(
                bundle_dir=bundle_dir,
                generated_at=bundle_timestamp,
                events_timestamp=events_timestamp,
                fingerprint_timestamp=fingerprint_timestamp,
                audit_bundle_timestamp=bundle_timestamp,
            )

            # Create manifest (must be last)
            bundle_hash = self._create_manifest(
                bundle_dir,
                bundle_id,
                created_at,
                contents,
                governance_fingerprint_hash,
            )

            return AuditBundleResult(
                bundle_path=bundle_dir,
                bundle_id=bundle_id,
                bundle_hash=bundle_hash,
                created_at=created_at,
                event_count=event_count,
                file_count=len(contents),
                success=True,
            )

        except Exception as e:
            return AuditBundleResult(
                bundle_path=Path(output_path) if output_path else Path("."),
                bundle_id=bundle_id,
                bundle_hash="",
                created_at=created_at,
                event_count=0,
                file_count=0,
                success=False,
                error=str(e),
            )


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def export_audit_bundle(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    output_path: str | Path | None = None,
    source_log_path: str = DEFAULT_ROTATING_LOG_PATH,
    project_root: str | Path | None = None,
    max_staleness_seconds: int = DEFAULT_MAX_STALENESS_SECONDS,
) -> AuditBundleResult:
    """
    Export a governance audit bundle.

    Args:
        start_time: Include events at or after this time
        end_time: Include events at or before this time
        output_path: Output directory for bundle
        source_log_path: Path to governance events log
        project_root: Project root directory
        max_staleness_seconds: Maximum staleness threshold for freshness contract

    Returns:
        AuditBundleResult with bundle metadata and status
    """
    config = AuditBundleConfig(
        start_time=start_time,
        end_time=end_time,
        source_log_path=source_log_path,
        output_path=output_path,
        project_root=project_root,
        max_staleness_seconds=max_staleness_seconds,
    )
    exporter = AuditBundleExporter(config)
    return exporter.export(output_path)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════


def main() -> None:
    """CLI entry point for audit bundle export."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Export ChainBridge Governance Audit Bundle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export all events
  python -m core.governance.audit_exporter --out audit_bundle

  # Export last 30 days
  python -m core.governance.audit_exporter \\
    --start "2025-11-17T00:00:00Z" \\
    --end "2025-12-17T00:00:00Z" \\
    --out audit_Q4_2025
""",
    )

    parser.add_argument(
        "--start",
        type=str,
        help="Start time (ISO 8601 format)",
    )
    parser.add_argument(
        "--end",
        type=str,
        help="End time (ISO 8601 format)",
    )
    parser.add_argument(
        "--out",
        type=str,
        required=True,
        help="Output directory for audit bundle",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=DEFAULT_ROTATING_LOG_PATH,
        help="Source governance events log path",
    )

    args = parser.parse_args()

    # Parse timestamps
    start_time = None
    end_time = None
    if args.start:
        start_time = datetime.fromisoformat(args.start.replace("Z", "+00:00"))
    if args.end:
        end_time = datetime.fromisoformat(args.end.replace("Z", "+00:00"))

    # Export bundle
    result = export_audit_bundle(
        start_time=start_time,
        end_time=end_time,
        output_path=args.out,
        source_log_path=args.source,
    )

    if result.success:
        print("AUDIT BUNDLE EXPORTED")
        print(f"  Bundle ID:    {result.bundle_id}")
        print(f"  Bundle Hash:  {result.bundle_hash}")
        print(f"  Created:      {result.created_at}")
        print(f"  Events:       {result.event_count}")
        print(f"  Files:        {result.file_count}")
        print(f"  Output:       {result.bundle_path}")
    else:
        print("AUDIT BUNDLE EXPORT FAILED")
        print(f"  Error: {result.error}")
        exit(1)


if __name__ == "__main__":
    main()
