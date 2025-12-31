#!/usr/bin/env python3
"""
🟢 DAN (GID-07) — Repo Scope Validation Script
PAC-DAN-01: Governance-Aware CI/CD & Repo Scope Lock

This script enforces allowed/forbidden paths in the repository.
Any reintroduction of legacy/forbidden artifacts = CI failure.

NO BYPASS. NO WARN-ONLY.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ============================================================================
# SCOPE CONFIGURATION (Source of Truth: scripts/ci/governance_scope.json)
# ============================================================================

DEFAULT_ALLOWED_PATHS = [
    "api/",
    "apps/",
    "archive/",  # Read-only quarantine zone
    "assets/",
    "cache/",
    "chainboard-service/",
    "chainboard-ui/",
    "chainiq-service/",
    "ChainBridge/",
    "config/",
    "core/",
    "data/",
    "docs/",
    "examples/",
    "gateway/",
    "htmlcov/",
    "k8s/",
    "logs/",
    "manifests/",
    "market_metrics/",
    "ml_models/",
    "modules/",
    "prompts/",
    "proofpacks/",
    "ql-db/",
    "reports/",
    "sample_data/",
    "scripts/",
    "src/",
    "static/",
    "strategies/",
    "tests/",
    "tools/",
    "tracking/",
    "utils/",
    ".github/",
    ".devcontainer/",
    ".vscode/",
    ".chainbridge/",
]

# Files explicitly allowed at root
DEFAULT_ALLOWED_ROOT_FILES = [
    ".dockerignore",
    ".env.dev",
    ".env.dev.example",
    ".env.example",
    ".flake8",
    ".gitignore",
    ".markdownlint.json",
    ".markdownlintignore",
    ".pre-commit-config.yaml",
    ".pylintrc",
    ".python-version",
    "docker-compose.dev.yml",
    "docker-compose.yml",
    "Dockerfile",
    "main.py",
    "Makefile",
    "pyproject.toml",
    "pytest.ini",
    "README.md",
    "requirements.txt",
    "requirements-dev.txt",
    "ruff.toml",
    "settlement_actions.db",
]

# FORBIDDEN PATTERNS - Legacy/drift artifacts that must NOT exist outside /archive/
# Note: Patterns match anywhere in path. Be specific to avoid false positives.
FORBIDDEN_PATTERNS = [
    # Legacy RSI/crypto bot artifacts (specific files)
    "benson_rsi_bot.py",
    "dynamic_crypto_selector.py",
    "multi_signal_bot.py",
    "MultiSignalBot.py",
    "rsi_bot.py",
    "crypto_bot.py",
    # Legacy directory patterns (outside archive) - specific names
    "/rsi/",  # RSI trading bot folder
    "/trading/",  # Trading folder
    "legacy-rsi-bot",  # Legacy RSI bot
    "legacy-benson-bot",  # Legacy Benson bot
    # Legacy config patterns
    "config.yaml.backup",
    # Legacy scripts at root level
    "/run_bot.sh",
    "/run_dashboard.sh",
    "/run_multi_signal_silent.sh",
    "/run_streamlit_dashboard.sh",
    "/start_trading.sh",
    "/setup_credentials.sh",
    "/setup_new_listings.sh",
    "/restart_system.sh",
    "/monitor.sh",
    "/monitor_full.sh",
    "/push_to_github.sh",
]


class RepoScopeValidator:
    """Validates repository scope against allowed/forbidden definitions."""

    def __init__(self, repo_root: Path, config_path: Optional[Path] = None):
        self.repo_root = repo_root
        self.config = self._load_config(config_path)
        self.violations: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []

    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load scope configuration from JSON file or use defaults."""
        if config_path and config_path.exists():
            with open(config_path) as f:
                raw_config = json.load(f)

            # Handle nested config structure (repo_scope section)
            if "repo_scope" in raw_config:
                return raw_config["repo_scope"]
            return raw_config

        # Use defaults
        return {
            "allowed_paths": DEFAULT_ALLOWED_PATHS,
            "allowed_root_files": DEFAULT_ALLOWED_ROOT_FILES,
            "forbidden_patterns": FORBIDDEN_PATTERNS,
            "archive_path": "archive/",
        }

    def _is_in_archive(self, path: str) -> bool:
        """Check if path is within the archive directory."""
        archive_path = self.config.get("archive_path", "archive/")
        return path.startswith(archive_path)

    def _is_excluded(self, path: str) -> bool:
        """Check if path is in the excluded list (legitimate exceptions)."""
        excluded_paths = self.config.get("excluded_paths", [])
        for excluded in excluded_paths:
            if path.startswith(excluded):
                return True
        return False

    def _is_allowed_path(self, path: str) -> bool:
        """Check if a path is in the allowed list."""
        # Check if it's an allowed directory
        for allowed in self.config["allowed_paths"]:
            if path.startswith(allowed):
                return True

        # Check if it's an allowed root file
        if "/" not in path and path in self.config["allowed_root_files"]:
            return True

        return False

    def _is_forbidden(self, path: str) -> bool:
        """Check if a path matches forbidden patterns."""
        # Items in archive are explicitly allowed (quarantine zone)
        if self._is_in_archive(path):
            return False

        # Items in excluded paths are explicitly allowed (legitimate exceptions)
        if self._is_excluded(path):
            return False

        # Normalize path for matching
        normalized_path = "/" + path if not path.startswith("/") else path

        for pattern in self.config["forbidden_patterns"]:
            # Pattern starting with / means it must match from the start of path component
            if pattern.startswith("/"):
                # Check if pattern matches path segment boundary
                if pattern in normalized_path:
                    return True
            else:
                # Simple substring match for file names
                filename = Path(path).name
                if filename == pattern or filename == pattern.rstrip("/"):
                    return True
                # Also check for directory patterns
                if pattern.endswith("/") and pattern.rstrip("/") in path.split("/"):
                    return True
                # Check if pattern appears anywhere in path
                if pattern in path:
                    return True

        return False

    def check_path(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Check a single path for scope violations.
        Returns violation dict if found, None otherwise.
        """
        # Skip hidden directories (except explicitly allowed)
        if path.startswith(".") and not any(path.startswith(a) for a in [".github/", ".devcontainer/", ".vscode/", ".chainbridge/"]):
            # Allow hidden config files at root
            if "/" not in path:
                return None

        # Check forbidden first (higher priority)
        if self._is_forbidden(path):
            return {
                "type": "FORBIDDEN",
                "path": path,
                "reason": "Matches forbidden pattern (legacy/drift artifact)",
                "severity": "ERROR",
            }

        # Check if path is allowed
        if not self._is_allowed_path(path) and "/" in path:
            # Only flag directories, not root files
            top_level = path.split("/")[0] + "/"
            if top_level not in self.config["allowed_paths"]:
                return {
                    "type": "UNRECOGNIZED",
                    "path": path,
                    "reason": f"Top-level directory '{top_level}' not in allowed list",
                    "severity": "WARNING",
                }

        return None

    def scan_repository(self) -> tuple:
        """
        Scan entire repository for scope violations.
        Returns (errors, warnings).
        """
        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        # Walk the repository
        for root, dirs, files in os.walk(self.repo_root):
            # Skip .git directory
            if ".git" in dirs:
                dirs.remove(".git")
            # Skip virtual environments
            if ".venv" in dirs:
                dirs.remove(".venv")
            if ".venv-lean" in dirs:
                dirs.remove(".venv-lean")
            # Skip cache directories
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
            if ".pytest_cache" in dirs:
                dirs.remove(".pytest_cache")
            if ".ruff_cache" in dirs:
                dirs.remove(".ruff_cache")
            # Skip node_modules (npm dependencies are not subject to repo scope)
            if "node_modules" in dirs:
                dirs.remove("node_modules")
            # Skip htmlcov (coverage reports)
            if "htmlcov" in dirs:
                dirs.remove("htmlcov")

            rel_root = os.path.relpath(root, self.repo_root)
            if rel_root == ".":
                rel_root = ""

            # Check directories
            for d in dirs:
                path = f"{rel_root}/{d}/" if rel_root else f"{d}/"
                violation = self.check_path(path)
                if violation:
                    if violation["severity"] == "ERROR":
                        errors.append(violation)
                    else:
                        warnings.append(violation)

            # Check files
            for f in files:
                path = f"{rel_root}/{f}" if rel_root else f
                violation = self.check_path(path)
                if violation:
                    if violation["severity"] == "ERROR":
                        errors.append(violation)
                    else:
                        warnings.append(violation)

        return errors, warnings

    def check_staged_files(self, staged_files: List[str]) -> tuple:
        """
        Check only staged files (for pre-commit/PR checks).
        Returns (errors, warnings).
        """
        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        for path in staged_files:
            violation = self.check_path(path)
            if violation:
                if violation["severity"] == "ERROR":
                    errors.append(violation)
                else:
                    warnings.append(violation)

        return errors, warnings


def main() -> int:
    """Main entry point for CI execution."""
    import argparse

    parser = argparse.ArgumentParser(description="🟢 DAN (GID-07) — Repo Scope Validator")
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
        "--staged-only",
        action="store_true",
        help="Only check staged files (git diff --cached)",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Output results as JSON to file",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Treat errors as warnings (NOT RECOMMENDED - use only for debugging)",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("🟢 DAN (GID-07) — REPO SCOPE VALIDATION")
    print("=" * 70)
    print(f"Repository: {args.repo_root}")
    print(f"Config: {args.config or 'Using defaults'}")
    print()

    # Initialize validator
    config_path = args.config
    if not config_path:
        default_config = args.repo_root / "scripts" / "ci" / "governance_scope.json"
        if default_config.exists():
            config_path = default_config

    validator = RepoScopeValidator(args.repo_root, config_path)

    # Run validation
    if args.staged_only:
        import subprocess

        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            cwd=args.repo_root,
        )
        staged_files = [f for f in result.stdout.strip().split("\n") if f]
        print(f"Checking {len(staged_files)} staged files...")
        errors, warnings = validator.check_staged_files(staged_files)
    else:
        print("Scanning full repository...")
        errors, warnings = validator.scan_repository()

    # Output results
    print()
    if errors:
        print("❌ SCOPE VIOLATIONS DETECTED (FORBIDDEN ARTIFACTS)")
        print("-" * 50)
        for e in errors:
            print(f"  ERROR: {e['path']}")
            print(f"         {e['reason']}")
        print()

    if warnings:
        print("⚠️  SCOPE WARNINGS (Unrecognized paths)")
        print("-" * 50)
        for w in warnings:
            print(f"  WARN: {w['path']}")
            print(f"        {w['reason']}")
        print()

    # Summary
    print("=" * 70)
    print(f"SUMMARY: {len(errors)} errors, {len(warnings)} warnings")
    print("=" * 70)

    # JSON output if requested
    if args.json_output:
        output = {
            "status": "FAIL" if errors else "PASS",
            "errors": errors,
            "warnings": warnings,
            "error_count": len(errors),
            "warning_count": len(warnings),
        }
        with open(args.json_output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Results written to: {args.json_output}")

    # Exit code
    if errors and not args.warn_only:
        print()
        print("❌ REPO SCOPE CHECK FAILED")
        print("   Legacy/forbidden artifacts detected. Remove or archive them.")
        print("   Repo integrity > velocity")
        print("🟢 DAN (GID-07)")
        return 1

    print()
    print("✅ REPO SCOPE CHECK PASSED")
    print("🟢 DAN (GID-07)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
