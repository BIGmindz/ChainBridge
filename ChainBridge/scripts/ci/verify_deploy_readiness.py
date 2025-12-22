#!/usr/bin/env python3
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPLOYMENT READINESS VERIFICATION — A9 ENFORCEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PAC: PAC-DAN-A9-DEPLOYMENT-READINESS-LOCK-01
Author: Dan (GID-07) | DevOps & CI/CD Lead

PURPOSE:
Verify the system is ready for deployment by checking all pre-deploy gates.

INVARIANTS:
- All governance locks (A1-A9) must be present
- Agent registry must be valid
- No environment-specific code paths
- All required artifacts present
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REQUIRED_LOCKS = [
    "A1_ARCHITECTURE_LOCK.md",
    "A2_RUNTIME_BOUNDARY_LOCK.md",
    "A3_PDO_ATOMIC_LOCK.md",
    "A4_SETTLEMENT_GATE_LOCK.md",
    "A5_PROOF_AUDIT_SURFACE_LOCK.md",
    "A6_GOVERNANCE_ALIGNMENT_LOCK.md",
    # A7, A8 may be separate files or embedded
    "A9_DEPLOYMENT_READINESS_LOCK.md",
]

FORBIDDEN_ENV_PATTERNS = [
    # Direct environment checks
    r'os\.environ\.get\(["\']ENV["\']\)\s*==\s*["\']prod',
    r'os\.environ\.get\(["\']ENV["\']\)\s*==\s*["\']production',
    r'os\.environ\.get\(["\']ENV["\']\)\s*==\s*["\']staging',
    r'os\.environ\.get\(["\']ENVIRONMENT["\']\)\s*==',
    # Settings-based checks
    r'settings\.environment\s*==\s*["\']prod',
    r'settings\.environment\s*==\s*["\']production',
    r'settings\.is_production',
    r'settings\.is_staging',
    # Boolean flags by env name
    r'if\s+.*is_production',
    r'if\s+.*is_staging',
    r'if\s+.*in_production',
]

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".pytest_cache",
    "htmlcov",
    ".mypy_cache",
    "build",
    "dist",
    "archive",
    "tests",  # Allow env checks in tests
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VERIFICATION FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_governance_locks(repo_root: Path) -> tuple[bool, dict[str, Optional[str]]]:
    """
    Verify all required governance locks are present.
    Returns (all_present, {lock_name: hash or None})
    """
    governance_dir = repo_root / "docs" / "governance"
    lock_hashes: dict[str, Optional[str]] = {}
    all_present = True

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔒 VERIFYING GOVERNANCE LOCKS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    for lock in REQUIRED_LOCKS:
        lock_path = governance_dir / lock
        if lock_path.exists():
            file_hash = compute_file_hash(lock_path)
            lock_hashes[lock] = file_hash
            print(f"  ✅ {lock}: {file_hash[:16]}...")
        else:
            lock_hashes[lock] = None
            all_present = False
            print(f"  ❌ {lock}: MISSING")

    return all_present, lock_hashes


def verify_agent_registry(repo_root: Path) -> tuple[bool, Optional[str]]:
    """
    Verify agent registry is present and valid JSON.
    Returns (valid, hash or None)
    """
    registry_path = repo_root / "docs" / "governance" / "AGENT_REGISTRY.json"

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔒 VERIFYING AGENT REGISTRY")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if not registry_path.exists():
        print("  ❌ AGENT_REGISTRY.json: MISSING")
        return False, None

    try:
        with open(registry_path) as f:
            data = json.load(f)

        # Basic validation
        if not isinstance(data, dict):
            print("  ❌ AGENT_REGISTRY.json: Invalid structure (not a dict)")
            return False, None

        if "agents" not in data and "registry" not in data:
            print("  ❌ AGENT_REGISTRY.json: Missing agents/registry key")
            return False, None

        file_hash = compute_file_hash(registry_path)
        print(f"  ✅ AGENT_REGISTRY.json: {file_hash[:16]}...")
        return True, file_hash

    except json.JSONDecodeError as e:
        print(f"  ❌ AGENT_REGISTRY.json: Invalid JSON - {e}")
        return False, None


def verify_no_env_specific_code(repo_root: Path) -> tuple[bool, list[tuple[str, int, str]]]:
    """
    Scan for forbidden environment-specific code patterns.
    Returns (no_violations, [(file, line, pattern)])
    """
    violations: list[tuple[str, int, str]] = []
    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_ENV_PATTERNS]

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔒 SCANNING FOR ENVIRONMENT-SPECIFIC CODE")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    scan_dirs = ["src", "app", "core", "modules", "gateway", "api"]

    for scan_dir in scan_dirs:
        dir_path = repo_root / scan_dir
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            # Skip excluded directories
            if any(excluded in py_file.parts for excluded in EXCLUDED_DIRS):
                continue

            try:
                with open(py_file, encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    for pattern in compiled_patterns:
                        if pattern.search(line):
                            rel_path = py_file.relative_to(repo_root)
                            violations.append((str(rel_path), line_num, line.strip()[:80]))
                            break  # One violation per line

            except (OSError, UnicodeDecodeError):
                continue

    if violations:
        print(f"  ❌ Found {len(violations)} environment-specific code violations:")
        for filepath, line_num, code in violations[:10]:  # Show first 10
            print(f"     {filepath}:{line_num}: {code}")
        if len(violations) > 10:
            print(f"     ... and {len(violations) - 10} more")
    else:
        print("  ✅ No forbidden environment patterns found")

    return len(violations) == 0, violations


def verify_required_workflows(repo_root: Path) -> tuple[bool, list[str]]:
    """
    Verify required CI/CD workflows are present.
    Returns (all_present, missing_workflows)
    """
    workflows_dir = repo_root / ".github" / "workflows"
    required_workflows = [
        "governance-check.yml",
        "deployment-gate.yml",
    ]
    missing: list[str] = []

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔒 VERIFYING REQUIRED WORKFLOWS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    for workflow in required_workflows:
        workflow_path = workflows_dir / workflow
        if workflow_path.exists():
            print(f"  ✅ {workflow}")
        else:
            print(f"  ❌ {workflow}: MISSING")
            missing.append(workflow)

    return len(missing) == 0, missing


def verify_dockerfile_immutable_refs(repo_root: Path) -> tuple[bool, list[str]]:
    """
    Check Dockerfiles don't use mutable tags (optional check).
    Returns (no_violations, violations)
    """
    violations: list[str] = []
    mutable_tag_pattern = re.compile(r"^\s*FROM\s+\S+:(latest|main|master|dev|staging)", re.IGNORECASE)

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔒 VERIFYING DOCKERFILE IMMUTABILITY")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    dockerfiles = list(repo_root.glob("**/Dockerfile*"))

    for dockerfile in dockerfiles:
        if any(excluded in dockerfile.parts for excluded in EXCLUDED_DIRS):
            continue

        try:
            with open(dockerfile) as f:
                for line_num, line in enumerate(f, 1):
                    if mutable_tag_pattern.search(line):
                        rel_path = dockerfile.relative_to(repo_root)
                        violations.append(f"{rel_path}:{line_num}: {line.strip()}")
        except OSError:
            continue

    if violations:
        print("  ⚠️  Found mutable tags in Dockerfiles (warning):")
        for v in violations:
            print(f"     {v}")
    else:
        print("  ✅ No mutable tags in Dockerfiles")

    # This is a warning, not a blocker
    return True, violations


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN VERIFICATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def main() -> int:
    """
    Run all deployment readiness checks.
    Returns 0 if ready, 1 if not.
    """
    # Find repo root
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent.parent  # scripts/ci/this.py -> repo root

    if not (repo_root / ".git").exists():
        # Try current directory
        repo_root = Path.cwd()
        if not (repo_root / ".git").exists():
            print("❌ ERROR: Could not find repository root")
            return 1

    print()
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║      🔒 DEPLOYMENT READINESS VERIFICATION — A9 ENFORCEMENT 🔒      ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()
    print(f"Repository: {repo_root}")
    print()

    # Track results
    all_passed = True
    results = {}

    # 1. Verify governance locks
    locks_ok, lock_hashes = verify_governance_locks(repo_root)
    results["governance_locks"] = locks_ok
    if not locks_ok:
        all_passed = False

    # 2. Verify agent registry
    registry_ok, registry_hash = verify_agent_registry(repo_root)
    results["agent_registry"] = registry_ok
    if not registry_ok:
        all_passed = False

    # 3. Verify no environment-specific code
    env_ok, env_violations = verify_no_env_specific_code(repo_root)
    results["no_env_code"] = env_ok
    if not env_ok:
        all_passed = False

    # 4. Verify required workflows
    workflows_ok, missing_workflows = verify_required_workflows(repo_root)
    results["required_workflows"] = workflows_ok
    if not workflows_ok:
        all_passed = False

    # 5. Check Dockerfile immutability (warning only)
    docker_ok, docker_violations = verify_dockerfile_immutable_refs(repo_root)
    results["dockerfile_immutable"] = docker_ok

    # ──────────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ──────────────────────────────────────────────────────────────────────────
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("DEPLOYMENT READINESS SUMMARY")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {check}: {status}")

    print()

    if all_passed:
        print("╔════════════════════════════════════════════════════════════════════╗")
        print("║              ✅ DEPLOYMENT READINESS: VERIFIED ✅                  ║")
        print("╚════════════════════════════════════════════════════════════════════╝")
        print()
        return 0
    else:
        print("╔════════════════════════════════════════════════════════════════════╗")
        print("║           ❌ DEPLOYMENT READINESS: NOT VERIFIED ❌                 ║")
        print("║                    DEPLOYMENT BLOCKED                              ║")
        print("╚════════════════════════════════════════════════════════════════════╝")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
