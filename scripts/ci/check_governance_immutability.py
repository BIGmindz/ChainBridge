#!/usr/bin/env python3
"""
🟢 DAN (GID-07) — Governance File Immutability Check
PAC-DAN-01: Governance-Aware CI/CD & Repo Scope Lock

This script protects governance roots of trust from unauthorized modification.
Changes require explicit GOVERNANCE_OVERRIDE=true environment variable.

NO BYPASS. NO WARN-ONLY.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# ============================================================================
# GOVERNANCE ROOTS OF TRUST
# ============================================================================

DEFAULT_PROTECTED_FILES = [
    # Agent configuration
    "config/agents.json",
    # Agent manifests
    "manifests/GID-00_Diggy.yaml",
    "manifests/GID-01_Cody.yaml",
    "manifests/GID-02_Sonny.yaml",
    "manifests/GID-06_Sam.yaml",
    "manifests/GID-07_Dan.yaml",
    "manifests/GID-08_ALEX.yaml",
    # CI/CD governance scope
    "scripts/ci/governance_scope.json",
]

DEFAULT_PROTECTED_DIRECTORIES = [
    # Governance documentation
    "docs/governance/",
]

# Files that can NEVER be deleted (even with override)
IMMUTABLE_CORE = [
    "config/agents.json",
]


class GovernanceImmutabilityChecker:
    """Checks governance files for unauthorized modifications."""

    def __init__(self, repo_root: Path, config_path: Path | None = None):
        self.repo_root = repo_root
        self.config = self._load_config(config_path)
        self.override_enabled = os.environ.get("GOVERNANCE_OVERRIDE", "").lower() == "true"
        self.override_reason = os.environ.get("GOVERNANCE_OVERRIDE_REASON", "")

    def _load_config(self, config_path: Path | None) -> dict[str, Any]:
        """Load configuration or use defaults."""
        if config_path and config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                return config.get("immutability", {})

        return {
            "protected_files": DEFAULT_PROTECTED_FILES,
            "protected_directories": DEFAULT_PROTECTED_DIRECTORIES,
            "immutable_core": IMMUTABLE_CORE,
        }

    def _get_protected_files(self) -> list[str]:
        """Get list of all protected files (including directory contents)."""
        protected = list(self.config.get("protected_files", []))

        # Expand protected directories
        for dir_path in self.config.get("protected_directories", []):
            full_path = self.repo_root / dir_path
            if full_path.exists() and full_path.is_dir():
                for f in full_path.rglob("*"):
                    if f.is_file():
                        rel_path = str(f.relative_to(self.repo_root))
                        protected.append(rel_path)

        return protected

    def _compute_file_hash(self, file_path: Path) -> str | None:
        """Compute SHA-256 hash of a file."""
        if not file_path.exists():
            return None

        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _get_changed_files(self, base_ref: str = "origin/main") -> list[str]:
        """Get list of files changed compared to base reference."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
            )
            if result.returncode != 0:
                # Try without the triple-dot (for local comparison)
                result = subprocess.run(
                    ["git", "diff", "--name-only", base_ref],
                    capture_output=True,
                    text=True,
                    cwd=self.repo_root,
                )
            return [f for f in result.stdout.strip().split("\n") if f]
        except Exception:
            return []

    def _get_deleted_files(self, base_ref: str = "origin/main") -> list[str]:
        """Get list of files deleted compared to base reference."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=D", f"{base_ref}...HEAD"],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
            )
            if result.returncode != 0:
                result = subprocess.run(
                    ["git", "diff", "--name-only", "--diff-filter=D", base_ref],
                    capture_output=True,
                    text=True,
                    cwd=self.repo_root,
                )
            return [f for f in result.stdout.strip().split("\n") if f]
        except Exception:
            return []

    def check_immutability(self, base_ref: str = "origin/main") -> dict[str, Any]:
        """
        Check if any protected governance files have been modified.

        Returns:
            dict with status, violations, and metadata
        """
        protected_files = set(self._get_protected_files())
        changed_files = set(self._get_changed_files(base_ref))
        deleted_files = set(self._get_deleted_files(base_ref))

        # Find violations
        modified_protected = protected_files & changed_files
        deleted_protected = protected_files & deleted_files

        # Check for immutable core deletions (never allowed)
        immutable_core = set(self.config.get("immutable_core", []))

        # Build result
        violations = []

        for f in modified_protected:
            violations.append(
                {
                    "type": "MODIFIED",
                    "file": f,
                    "severity": "ERROR",
                    "override_allowed": True,
                }
            )

        for f in deleted_protected:
            is_core = f in immutable_core
            violations.append(
                {
                    "type": "DELETED",
                    "file": f,
                    "severity": "CRITICAL" if is_core else "ERROR",
                    "override_allowed": not is_core,
                }
            )

        # Compute current hashes for protected files
        current_hashes = {}
        for f in protected_files:
            file_path = self.repo_root / f
            hash_val = self._compute_file_hash(file_path)
            if hash_val:
                current_hashes[f] = hash_val

        # Determine overall status
        has_critical = any(v["severity"] == "CRITICAL" for v in violations)
        has_errors = any(v["severity"] == "ERROR" for v in violations)

        if has_critical:
            status = "CRITICAL_FAIL"  # Never overridable
        elif has_errors:
            if self.override_enabled:
                status = "OVERRIDE_APPROVED"
            else:
                status = "FAIL"
        else:
            status = "PASS"

        return {
            "status": status,
            "violations": violations,
            "override_enabled": self.override_enabled,
            "override_reason": self.override_reason,
            "protected_file_count": len(protected_files),
            "current_hashes": current_hashes,
            "base_ref": base_ref,
        }

    def generate_hash_manifest(self) -> dict[str, str]:
        """Generate a manifest of all protected file hashes."""
        protected_files = self._get_protected_files()
        manifest = {}

        for f in protected_files:
            file_path = self.repo_root / f
            hash_val = self._compute_file_hash(file_path)
            if hash_val:
                manifest[f] = hash_val

        return manifest


def main() -> int:
    """Main entry point for CI execution."""
    import argparse

    parser = argparse.ArgumentParser(description="🟢 DAN (GID-07) — Governance Immutability Check")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root path",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to governance_scope.json config",
    )
    parser.add_argument(
        "--base-ref",
        type=str,
        default="origin/main",
        help="Base git reference to compare against",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Output results as JSON to file",
    )
    parser.add_argument(
        "--generate-manifest",
        action="store_true",
        help="Generate hash manifest of protected files",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("🟢 DAN (GID-07) — GOVERNANCE IMMUTABILITY CHECK")
    print("=" * 70)
    print(f"Repository: {args.repo_root}")
    print(f"Base Ref: {args.base_ref}")
    print(f"Override Enabled: {os.environ.get('GOVERNANCE_OVERRIDE', 'false')}")
    print()

    # Initialize checker
    config_path = args.config
    if not config_path:
        default_config = args.repo_root / "scripts" / "ci" / "governance_scope.json"
        if default_config.exists():
            config_path = default_config

    checker = GovernanceImmutabilityChecker(args.repo_root, config_path)

    # Generate manifest if requested
    if args.generate_manifest:
        print("Generating hash manifest...")
        manifest = checker.generate_hash_manifest()
        print(json.dumps(manifest, indent=2))
        return 0

    # Run check
    result = checker.check_immutability(args.base_ref)

    # Output results
    print(f"Protected Files: {result['protected_file_count']}")
    print()

    if result["violations"]:
        print("🚨 GOVERNANCE FILE MODIFICATIONS DETECTED")
        print("-" * 50)
        for v in result["violations"]:
            severity_icon = "🔴" if v["severity"] == "CRITICAL" else "❌"
            print(f"  {severity_icon} [{v['type']}] {v['file']}")
            if not v["override_allowed"]:
                print("      ⚠️  IMMUTABLE CORE - Override NOT allowed")
        print()

    if result["override_enabled"] and result["violations"]:
        print("⚠️  GOVERNANCE_OVERRIDE=true detected")
        print(f"   Reason: {result['override_reason'] or 'No reason provided'}")
        print()

    # Print hash summary
    print("PROTECTED FILE HASHES:")
    print("-" * 50)
    for f, h in sorted(result["current_hashes"].items())[:10]:
        print(f"  {h[:12]}... {f}")
    if len(result["current_hashes"]) > 10:
        print(f"  ... and {len(result['current_hashes']) - 10} more")
    print()

    # JSON output if requested
    if args.json_output:
        with open(args.json_output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Results written to: {args.json_output}")

    # Summary and exit
    print("=" * 70)
    print(f"STATUS: {result['status']}")
    print("=" * 70)

    if result["status"] == "CRITICAL_FAIL":
        print()
        print("❌ CRITICAL: Immutable core files cannot be deleted or modified.")
        print("   This is a governance boundary that cannot be overridden.")
        print("🟢 DAN (GID-07)")
        return 2

    if result["status"] == "FAIL":
        print()
        print("❌ GOVERNANCE IMMUTABILITY CHECK FAILED")
        print("   Protected files were modified without authorization.")
        print("   To override, set: GOVERNANCE_OVERRIDE=true GOVERNANCE_OVERRIDE_REASON='...'")
        print("   Governance integrity > velocity")
        print("🟢 DAN (GID-07)")
        return 1

    if result["status"] == "OVERRIDE_APPROVED":
        print()
        print("⚠️  GOVERNANCE OVERRIDE APPROVED")
        print("   Changes to protected files logged for audit.")
        print("🟢 DAN (GID-07)")
        return 0

    print()
    print("✅ GOVERNANCE IMMUTABILITY CHECK PASSED")
    print("🟢 DAN (GID-07)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
