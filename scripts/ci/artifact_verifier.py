#!/usr/bin/env python3
"""
🟢 DAN (GID-07) — Runtime Artifact Verifier
PAC-DAN-04: Build Artifact Immutability & Hash Attestation

Verifies artifact integrity at application startup.
Raises ArtifactIntegrityError if hashes mismatch.

Usage:
    # Import and call at startup
    from scripts.ci.artifact_verifier import verify_artifact_integrity
    verify_artifact_integrity()  # Raises on failure

    # Or run standalone
    python scripts/ci/artifact_verifier.py [--strict]

Exit codes:
    0 - Verification passed
    1 - Verification failed
    2 - Script error
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

VERIFIER_VERSION = "1.0.0"
DEFAULT_MANIFEST = "build/artifacts.json"

logger = logging.getLogger("artifact_verifier")


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class ArtifactIntegrityError(Exception):
    """
    Raised when artifact verification fails.

    This is a hard failure - the application MUST NOT proceed.
    """

    def __init__(self, message: str, mismatches: list[str] | None = None):
        super().__init__(message)
        self.mismatches = mismatches or []


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class VerificationResult:
    """Result of artifact verification."""

    passed: bool
    manifest_path: str
    files_verified: int = 0
    mismatches: list[str] = field(default_factory=list)
    manifest_commit: str | None = None
    manifest_generated: str | None = None
    aggregate_hash: str | None = None
    verified_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "passed": self.passed,
            "manifest_path": self.manifest_path,
            "files_verified": self.files_verified,
            "mismatches": self.mismatches,
            "manifest_commit": self.manifest_commit,
            "manifest_generated": self.manifest_generated,
            "aggregate_hash": self.aggregate_hash,
            "verified_at": self.verified_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# HASH FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load artifact manifest from JSON file."""
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


def verify_files(
    repo_root: Path,
    manifest: dict[str, Any],
) -> tuple[int, list[str]]:
    """
    Verify files against manifest hashes.

    Returns (files_verified, mismatches).
    """
    stored_files = manifest.get("files", {})
    mismatches: list[str] = []
    verified = 0

    for rel_path, expected_hash in stored_files.items():
        filepath = repo_root / rel_path

        if not filepath.exists():
            mismatches.append(f"MISSING: {rel_path}")
            continue

        actual_hash = compute_file_hash(filepath)
        verified += 1

        if actual_hash != expected_hash:
            mismatches.append(f"MISMATCH: {rel_path} " f"(expected={expected_hash[:12]}..., actual={actual_hash[:12]}...)")

    return verified, mismatches


def verify_artifact_integrity(
    repo_root: Path | None = None,
    manifest_path: Path | str | None = None,
    strict: bool = True,
) -> VerificationResult:
    """
    Verify artifact integrity against manifest.

    Args:
        repo_root: Repository root path (auto-detected if None)
        manifest_path: Path to artifacts.json (default: build/artifacts.json)
        strict: If True, raises ArtifactIntegrityError on failure

    Returns:
        VerificationResult with verification details

    Raises:
        ArtifactIntegrityError: If strict=True and verification fails
    """
    # Determine repo root
    if repo_root is None:
        repo_root = Path.cwd()
        while repo_root != repo_root.parent:
            if (repo_root / ".git").exists():
                break
            repo_root = repo_root.parent

    repo_root = Path(repo_root).resolve()

    # Determine manifest path
    if manifest_path is None:
        manifest_path = repo_root / DEFAULT_MANIFEST
    else:
        manifest_path = Path(manifest_path)
        if not manifest_path.is_absolute():
            manifest_path = repo_root / manifest_path

    # Check manifest exists
    if not manifest_path.exists():
        result = VerificationResult(
            passed=False,
            manifest_path=str(manifest_path),
            mismatches=["Artifact manifest not found"],
        )
        if strict:
            raise ArtifactIntegrityError(
                f"Artifact manifest not found: {manifest_path}",
                result.mismatches,
            )
        return result

    # Load manifest
    manifest = load_manifest(manifest_path)

    # Verify files
    files_verified, mismatches = verify_files(repo_root, manifest)

    # Build result
    result = VerificationResult(
        passed=len(mismatches) == 0,
        manifest_path=str(manifest_path),
        files_verified=files_verified,
        mismatches=mismatches,
        manifest_commit=manifest.get("git_commit"),
        manifest_generated=manifest.get("generated_at"),
        aggregate_hash=manifest.get("aggregate_hash"),
    )

    # Strict mode raises on failure
    if strict and not result.passed:
        raise ArtifactIntegrityError(
            f"Artifact integrity verification failed: {len(mismatches)} mismatch(es)",
            mismatches,
        )

    return result


def get_artifact_info(
    repo_root: Path | None = None,
    manifest_path: Path | str | None = None,
) -> dict[str, Any] | None:
    """
    Get artifact info for health/status endpoints.

    Returns None if manifest doesn't exist.
    Does NOT verify - just returns recorded info.
    """
    if repo_root is None:
        repo_root = Path.cwd()
        while repo_root != repo_root.parent:
            if (repo_root / ".git").exists():
                break
            repo_root = repo_root.parent

    repo_root = Path(repo_root).resolve()

    if manifest_path is None:
        manifest_path = repo_root / DEFAULT_MANIFEST
    else:
        manifest_path = Path(manifest_path)
        if not manifest_path.is_absolute():
            manifest_path = repo_root / manifest_path

    if not manifest_path.exists():
        return None

    manifest = load_manifest(manifest_path)

    return {
        "artifact_version": manifest.get("artifact_version"),
        "git_commit": manifest.get("git_commit"),
        "git_branch": manifest.get("git_branch"),
        "generated_at": manifest.get("generated_at"),
        "aggregate_hash": manifest.get("aggregate_hash"),
        "file_count": manifest.get("file_count"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STARTUP BANNER
# ═══════════════════════════════════════════════════════════════════════════════


def print_artifact_banner(result: VerificationResult) -> None:
    """Print artifact verification banner at startup."""
    print("═══════════════════════════════════════════════════════════════")
    print("  ChainBridge Artifact Integrity Check")
    print("═══════════════════════════════════════════════════════════════")

    if result.passed:
        print("  ✅ VERIFIED")
        print(f"     Commit:    {result.manifest_commit[:8] if result.manifest_commit else 'N/A'}...")
        print(f"     Hash:      {result.aggregate_hash[:16] if result.aggregate_hash else 'N/A'}...")
        print(f"     Files:     {result.files_verified}")
        print(f"     Generated: {result.manifest_generated or 'N/A'}")
    else:
        print("  ❌ VERIFICATION FAILED")
        print(f"     Mismatches: {len(result.mismatches)}")
        for m in result.mismatches[:5]:
            print(f"       - {m}")
        if len(result.mismatches) > 5:
            print(f"       ... and {len(result.mismatches) - 5} more")

    print("═══════════════════════════════════════════════════════════════")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="ChainBridge Runtime Artifact Verifier",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Path to artifacts.json",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error code on failure",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress banner output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )

    args = parser.parse_args()

    try:
        result = verify_artifact_integrity(
            repo_root=args.root,
            manifest_path=args.manifest,
            strict=False,  # Handle exit code ourselves
        )

        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        elif not args.quiet:
            print_artifact_banner(result)

        if args.strict and not result.passed:
            return 1

        return 0 if result.passed else 1

    except ArtifactIntegrityError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
