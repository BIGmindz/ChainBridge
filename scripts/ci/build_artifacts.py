#!/usr/bin/env python3
"""
🟢 DAN (GID-07) — Build Artifact Hash Generator
PAC-DAN-04: Build Artifact Immutability & Hash Attestation

Computes SHA-256 hashes for tracked artifacts at CI build time.
Writes deterministic artifact manifest to build/artifacts.json.

Usage:
    python scripts/ci/build_artifacts.py [--output PATH] [--verify]

Exit codes:
    0 - Success (generate) or verification passed
    1 - Verification failed (hash mismatch)
    2 - Script error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

ARTIFACT_VERSION = "1.0.0"

# Files to track for integrity (critical entrypoints and core logic)
TRACKED_FILES: list[str] = [
    # API Gateway
    "api/server.py",
    "api/__init__.py",
    # Gateway layer
    "gateway/__init__.py",
    "gateway/tool_executor.py",
    "gateway/gateway_guard.py",
    "gateway/alex_middleware.py",
    # Core OCC
    "core/occ/__init__.py",
    "core/occ/schemas/decision.py",
    "core/occ/schemas/artifact.py",
    "core/occ/crypto/ed25519_signer.py",
    # Core Governance
    "core/governance/__init__.py",
    "core/governance/drcp.py",
    "core/governance/boot_checks.py",
    "core/governance/diggi_envelope_handler.py",
    # Governance rules
    ".github/ALEX_RULES.json",
]

# Optional files (included if they exist)
OPTIONAL_FILES: list[str] = [
    "core/oc/auth/__init__.py",
    "gateway/pdo_gate.py",
    "gateway/decision_engine.py",
    "gateway/model_router.py",
]

DEFAULT_OUTPUT = "build/artifacts.json"


# ═══════════════════════════════════════════════════════════════════════════════
# HASH FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read in chunks for large files
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_content_hash(content: bytes) -> str:
    """Compute SHA-256 hash of raw content."""
    return hashlib.sha256(content).hexdigest()


def get_git_commit_sha(repo_root: Path) -> str | None:
    """Get current git commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_git_branch(repo_root: Path) -> str | None:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# ARTIFACT MANIFEST GENERATION
# ═══════════════════════════════════════════════════════════════════════════════


def generate_artifact_manifest(repo_root: Path) -> dict[str, Any]:
    """
    Generate artifact manifest with file hashes.

    Returns deterministic JSON-serializable manifest.
    """
    files: dict[str, str] = {}
    missing: list[str] = []

    # Process required tracked files
    for rel_path in TRACKED_FILES:
        filepath = repo_root / rel_path
        if filepath.exists():
            files[rel_path] = compute_file_hash(filepath)
        else:
            missing.append(rel_path)

    # Process optional files
    for rel_path in OPTIONAL_FILES:
        filepath = repo_root / rel_path
        if filepath.exists():
            files[rel_path] = compute_file_hash(filepath)

    # Compute aggregate hash (deterministic order)
    sorted_hashes = [files[k] for k in sorted(files.keys())]
    aggregate_content = ":".join(sorted_hashes).encode("utf-8")
    aggregate_hash = compute_content_hash(aggregate_content)

    # Build manifest
    manifest: dict[str, Any] = {
        "artifact_version": ARTIFACT_VERSION,
        "artifact_type": "python-service",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": get_git_commit_sha(repo_root),
        "git_branch": get_git_branch(repo_root),
        "files": files,
        "aggregate_hash": aggregate_hash,
        "file_count": len(files),
    }

    if missing:
        manifest["missing_files"] = missing

    return manifest


def write_manifest(manifest: dict[str, Any], output_path: Path) -> None:
    """Write manifest to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")  # Trailing newline


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════


def verify_artifacts(repo_root: Path, manifest_path: Path) -> tuple[bool, list[str]]:
    """
    Verify current files against stored manifest.

    Returns (passed, list_of_mismatches).
    """
    if not manifest_path.exists():
        return False, ["artifacts.json not found"]

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    mismatches: list[str] = []
    stored_files = manifest.get("files", {})

    for rel_path, expected_hash in stored_files.items():
        filepath = repo_root / rel_path

        if not filepath.exists():
            mismatches.append(f"MISSING: {rel_path}")
            continue

        actual_hash = compute_file_hash(filepath)
        if actual_hash != expected_hash:
            mismatches.append(f"MISMATCH: {rel_path}\n" f"  Expected: {expected_hash[:16]}...\n" f"  Actual:   {actual_hash[:16]}...")

    return len(mismatches) == 0, mismatches


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════


def print_banner() -> None:
    """Print script banner."""
    print("═══════════════════════════════════════════════════════════════")
    print(f"  ChainBridge Artifact Hash Generator v{ARTIFACT_VERSION}")
    print("  PAC-DAN-04: Build Artifact Immutability")
    print("═══════════════════════════════════════════════════════════════")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ChainBridge Build Artifact Hash Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Output path for artifacts.json (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify existing manifest instead of generating",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: auto-detect)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress banner output",
    )

    args = parser.parse_args()

    # Determine repo root
    if args.root:
        repo_root = args.root.resolve()
    else:
        repo_root = Path.cwd()
        while repo_root != repo_root.parent:
            if (repo_root / ".git").exists():
                break
            repo_root = repo_root.parent

    if not repo_root.exists():
        print(f"❌ Error: Repository root not found: {repo_root}", file=sys.stderr)
        return 2

    output_path = args.output or (repo_root / DEFAULT_OUTPUT)

    if not args.quiet:
        print_banner()

    try:
        if args.verify:
            # Verification mode
            print(f"🔍 Verifying artifacts against: {output_path}")
            print()

            passed, mismatches = verify_artifacts(repo_root, output_path)

            if passed:
                print("✅ ARTIFACT VERIFICATION PASSED")
                print("   All file hashes match manifest.")
                return 0
            else:
                print("❌ ARTIFACT VERIFICATION FAILED")
                print()
                for mismatch in mismatches:
                    print(f"   {mismatch}")
                print()
                print("::error::Artifact integrity check failed")
                return 1

        else:
            # Generation mode
            print("📦 Generating artifact manifest...")
            print(f"   Root: {repo_root}")
            print()

            manifest = generate_artifact_manifest(repo_root)

            print(f"   Files tracked: {manifest['file_count']}")
            print(f"   Git commit: {manifest.get('git_commit', 'N/A')[:8]}...")
            print(f"   Aggregate hash: {manifest['aggregate_hash'][:16]}...")
            print()

            if manifest.get("missing_files"):
                print("   ⚠️  Missing files:")
                for f in manifest["missing_files"]:
                    print(f"      - {f}")
                print()

            write_manifest(manifest, output_path)

            print(f"✅ Manifest written to: {output_path}")
            return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
