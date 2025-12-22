#!/usr/bin/env python3
"""
🟢 DAN (GID-07) — Audit Bundle Verification Script
PAC-GOV-AUDIT-01: External Audit Export & Proof Bundle Contract
PAC-GOV-FRESHNESS-01: Trust Data Freshness Contract

Standalone verification script for ChainBridge Governance Audit Bundles.

Features:
- No external dependencies (stdlib only)
- No network calls
- Offline verification
- PASS/FAIL only output
- Freshness verification (staleness detection)

Usage:
    python scripts/verify_audit_bundle.py <bundle_path>
    python scripts/verify_audit_bundle.py <bundle_path> --skip-freshness

Expected output (success):
    AUDIT BUNDLE VERIFIED
    ✓ All file hashes match
    ✓ Bundle hash valid
    ✓ Governance fingerprint present
    ✓ All sources fresh
    ✓ No missing artifacts

Expected output (failure):
    AUDIT BUNDLE VERIFICATION FAILED
    ✗ File hash mismatch: governance_events/events.jsonl
    ✗ Source 'governance_events' is stale: 90000s old (max: 86400s)
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

MANIFEST_FILENAME = "AUDIT_MANIFEST.json"
FRESHNESS_MANIFEST_FILENAME = "FRESHNESS_MANIFEST.json"
REQUIRED_FILES = [
    "governance_events/events.jsonl",
    "fingerprint/governance_fingerprint.json",
    "scope/scope_declaration.json",
]
OPTIONAL_FILES = [
    "artifacts/artifacts.json",
]


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hash of bytes."""
    return hashlib.sha256(data).hexdigest()


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hash of file contents."""
    return compute_sha256(path.read_bytes())


def load_manifest(bundle_path: Path) -> dict[str, Any] | None:
    """Load and parse AUDIT_MANIFEST.json."""
    manifest_path = bundle_path / MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def verify_file_hashes(bundle_path: Path, manifest: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Verify SHA-256 hashes of all files in the manifest.

    Returns (success, errors).
    """
    errors: list[str] = []
    contents = manifest.get("contents", {})

    for rel_path, meta in contents.items():
        file_path = bundle_path / rel_path
        expected_hash = meta.get("sha256", "")

        if not file_path.exists():
            errors.append(f"Missing file: {rel_path}")
            continue

        actual_hash = compute_file_sha256(file_path)
        if actual_hash != expected_hash:
            errors.append(f"Hash mismatch: {rel_path}")
            errors.append(f"  Expected: {expected_hash}")
            errors.append(f"  Actual:   {actual_hash}")

    return len(errors) == 0, errors


def verify_bundle_hash(manifest: dict[str, Any]) -> tuple[bool, str]:
    """
    Verify the bundle hash.

    The bundle hash is SHA-256 of sorted concatenation of all content hashes.

    Returns (success, error_message).
    """
    contents = manifest.get("contents", {})
    expected_bundle_hash = manifest.get("bundle_hash", "")

    if not expected_bundle_hash:
        return False, "Missing bundle_hash in manifest"

    # Compute bundle hash from content hashes
    sorted_hashes = sorted(meta.get("sha256", "") for meta in contents.values())
    computed_hash = compute_sha256("".join(sorted_hashes).encode("utf-8"))

    if computed_hash != expected_bundle_hash:
        return False, f"Bundle hash mismatch (expected: {expected_bundle_hash}, got: {computed_hash})"

    return True, ""


def verify_required_files(bundle_path: Path, manifest: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Verify that all required files are present.

    Returns (success, missing_files).
    """
    contents = manifest.get("contents", {})
    missing: list[str] = []

    for required_file in REQUIRED_FILES:
        if required_file not in contents:
            missing.append(required_file)

    return len(missing) == 0, missing


def verify_governance_fingerprint(
    bundle_path: Path,
) -> tuple[bool, str]:
    """
    Verify that governance fingerprint is present and valid JSON.

    Returns (success, error_message).
    """
    fingerprint_path = bundle_path / "fingerprint" / "governance_fingerprint.json"

    if not fingerprint_path.exists():
        return False, "Governance fingerprint file missing"

    try:
        fingerprint = json.loads(fingerprint_path.read_text(encoding="utf-8"))
        if "composite_hash" not in fingerprint:
            return False, "Governance fingerprint missing composite_hash"
        return True, ""
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in governance fingerprint: {e}"


def load_freshness_manifest(bundle_path: Path) -> dict[str, Any] | None:
    """Load and parse FRESHNESS_MANIFEST.json."""
    manifest_path = bundle_path / FRESHNESS_MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def parse_iso_timestamp(ts_str: str) -> datetime:
    """Parse ISO 8601 timestamp string to datetime."""
    # Handle Z suffix
    ts_str = ts_str.replace("Z", "+00:00")
    return datetime.fromisoformat(ts_str)


def verify_freshness(
    bundle_path: Path,
    check_time: datetime | None = None,
) -> tuple[bool, list[str]]:
    """
    Verify that all sources are within freshness threshold.

    PAC-GOV-FRESHNESS-01: Fail-closed freshness verification.

    Verification FAILS if:
        now - any(source_timestamp) > max_staleness_seconds

    Returns (success, messages).
    """
    from datetime import timezone

    messages: list[str] = []

    # Load freshness manifest
    freshness = load_freshness_manifest(bundle_path)
    if freshness is None:
        return False, ["✗ Missing FRESHNESS_MANIFEST.json"]

    # Get check time (default to now)
    if check_time is None:
        check_time = datetime.now(timezone.utc)

    # Ensure check_time is timezone-aware
    if check_time.tzinfo is None:
        check_time = check_time.replace(tzinfo=timezone.utc)

    max_staleness = freshness.get("max_staleness_seconds", 86400)
    source_timestamps = freshness.get("source_timestamps", {})

    stale_sources: list[str] = []

    for source, info in source_timestamps.items():
        ts_str = info.get("timestamp", "")
        if not ts_str:
            stale_sources.append(f"Source '{source}' missing timestamp")
            continue

        try:
            ts = parse_iso_timestamp(ts_str)
            # Ensure timestamp is timezone-aware
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            age_seconds = int((check_time - ts).total_seconds())

            if age_seconds > max_staleness:
                exceeded_by = age_seconds - max_staleness
                stale_sources.append(
                    f"Source '{source}' is stale: {age_seconds}s old " f"(max: {max_staleness}s, exceeded by: {exceeded_by}s)"
                )
        except ValueError as e:
            stale_sources.append(f"Source '{source}' has invalid timestamp: {e}")

    if stale_sources:
        messages.append("✗ Freshness verification failed:")
        for msg in stale_sources:
            messages.append(f"    {msg}")
        return False, messages

    messages.append("✓ All sources fresh")
    return True, messages


def verify_audit_bundle(
    bundle_path: str | Path,
    skip_freshness: bool = False,
    check_time: datetime | None = None,
) -> tuple[bool, list[str]]:
    """
    Verify an audit bundle.

    Args:
        bundle_path: Path to the audit bundle directory
        skip_freshness: If True, skip freshness verification
        check_time: Time to check freshness against (defaults to now)

    Returns:
        (success, messages) where messages contains either
        success confirmations or error details.
    """
    bundle = Path(bundle_path)
    messages: list[str] = []
    all_passed = True

    # Check bundle exists
    if not bundle.exists():
        return False, [f"Bundle path does not exist: {bundle}"]

    if not bundle.is_dir():
        return False, [f"Bundle path is not a directory: {bundle}"]

    # Load manifest
    manifest = load_manifest(bundle)
    if manifest is None:
        return False, [f"Cannot load {MANIFEST_FILENAME}"]

    # Verify required files present
    files_ok, missing = verify_required_files(bundle, manifest)
    if files_ok:
        messages.append("✓ All required files present")
    else:
        all_passed = False
        messages.append("✗ Missing required files:")
        for f in missing:
            messages.append(f"    - {f}")

    # Verify file hashes
    hashes_ok, hash_errors = verify_file_hashes(bundle, manifest)
    if hashes_ok:
        messages.append("✓ All file hashes match")
    else:
        all_passed = False
        messages.append("✗ File hash verification failed:")
        for err in hash_errors:
            messages.append(f"    {err}")

    # Verify bundle hash
    bundle_hash_ok, bundle_hash_error = verify_bundle_hash(manifest)
    if bundle_hash_ok:
        messages.append("✓ Bundle hash valid")
    else:
        all_passed = False
        messages.append(f"✗ {bundle_hash_error}")

    # Verify governance fingerprint
    fingerprint_ok, fingerprint_error = verify_governance_fingerprint(bundle)
    if fingerprint_ok:
        messages.append("✓ Governance fingerprint present")
    else:
        all_passed = False
        messages.append(f"✗ {fingerprint_error}")

    # Check optional artifacts
    artifacts_path = bundle / "artifacts" / "artifacts.json"
    if artifacts_path.exists():
        messages.append("✓ Artifact manifest present")
    else:
        messages.append("○ Artifact manifest not present (optional)")

    # PAC-GOV-FRESHNESS-01: Verify freshness (fail-closed)
    if not skip_freshness:
        freshness_ok, freshness_msgs = verify_freshness(bundle, check_time)
        if freshness_ok:
            messages.extend(freshness_msgs)
        else:
            all_passed = False
            messages.extend(freshness_msgs)
    else:
        messages.append("○ Freshness verification skipped")

    return all_passed, messages


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify a ChainBridge Governance Audit Bundle.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify bundle (includes freshness check)
  python scripts/verify_audit_bundle.py ./audit_bundle

  # Verify bundle without freshness check
  python scripts/verify_audit_bundle.py ./audit_bundle --skip-freshness
""",
    )

    parser.add_argument(
        "bundle_path",
        type=str,
        help="Path to the audit bundle directory",
    )
    parser.add_argument(
        "--skip-freshness",
        action="store_true",
        help="Skip freshness verification (for testing or historical bundles)",
    )

    args = parser.parse_args()

    success, messages = verify_audit_bundle(
        args.bundle_path,
        skip_freshness=args.skip_freshness,
    )

    if success:
        print("AUDIT BUNDLE VERIFIED")
    else:
        print("AUDIT BUNDLE VERIFICATION FAILED")

    print()
    for msg in messages:
        print(msg)

    # Print bundle info on success
    if success:
        manifest = load_manifest(Path(args.bundle_path))
        if manifest:
            print()
            print("Bundle Info:")
            print(f"  Bundle ID:    {manifest.get('bundle_id', 'N/A')}")
            print(f"  Created:      {manifest.get('created_at', 'N/A')}")
            print(f"  Bundle Hash:  {manifest.get('bundle_hash', 'N/A')[:16]}...")
            print(f"  Schema:       v{manifest.get('schema_version', 'N/A')}")

            # Print freshness info if available
            freshness = load_freshness_manifest(Path(args.bundle_path))
            if freshness:
                max_staleness = freshness.get("max_staleness_seconds", 0)
                print(f"  Max Staleness: {max_staleness}s ({max_staleness // 3600}h)")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
