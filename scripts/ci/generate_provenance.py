#!/usr/bin/env python3
"""
🟢 DAN (GID-07) — Build Provenance Generator
PAC-DAN-01: Governance-Aware CI/CD & Repo Scope Lock

This script generates provenance metadata for every CI build.
Table stakes for regulated environments.
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class ProvenanceGenerator:
    """Generates build provenance metadata."""

    def __init__(self, repo_root: Path, config_path: Optional[Path] = None):
        self.repo_root = repo_root
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load configuration."""
        if config_path and config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {}

    def _get_commit_sha(self) -> str:
        """Get current commit SHA."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def _get_commit_short(self) -> str:
        """Get short commit SHA."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def _get_branch(self) -> str:
        """Get current branch name."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def _compute_governance_hash(self) -> str:
        """Compute combined hash of governance files."""
        governance_files = [
            "config/agents.json",
            "scripts/ci/governance_scope.json",
        ]

        # Add manifest files
        manifests_dir = self.repo_root / "manifests"
        if manifests_dir.exists():
            for f in sorted(manifests_dir.glob("GID-*.yaml")):
                governance_files.append(str(f.relative_to(self.repo_root)))

        combined = hashlib.sha256()
        for f in sorted(governance_files):
            file_path = self.repo_root / f
            if file_path.exists():
                with open(file_path, "rb") as fh:
                    combined.update(fh.read())

        return combined.hexdigest()

    def _get_acm_version(self) -> str:
        """Get ACM version from config."""
        provenance = self.config.get("provenance", {})
        return provenance.get("acm_version", "1.0.0")

    def _get_checklist_version(self) -> str:
        """Get checklist version from config."""
        provenance = self.config.get("provenance", {})
        return provenance.get("checklist_version", "1.0.0")

    def generate(self) -> dict[str, Any]:
        """Generate provenance metadata."""
        now = datetime.now(timezone.utc)

        return {
            "schema_version": "1.0.0",
            "generator": "DAN (GID-07)",
            "timestamp": now.isoformat(),
            "timestamp_unix": int(now.timestamp()),
            "git": {
                "commit_sha": self._get_commit_sha(),
                "commit_short": self._get_commit_short(),
                "branch": self._get_branch(),
            },
            "governance": {
                "hash": self._compute_governance_hash(),
                "acm_version": self._get_acm_version(),
                "checklist_version": self._get_checklist_version(),
            },
            "ci": {
                "workflow": os.environ.get("GITHUB_WORKFLOW", "local"),
                "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
                "run_number": os.environ.get("GITHUB_RUN_NUMBER", "0"),
                "actor": os.environ.get("GITHUB_ACTOR", os.environ.get("USER", "unknown")),
                "event": os.environ.get("GITHUB_EVENT_NAME", "local"),
                "repository": os.environ.get("GITHUB_REPOSITORY", "local"),
            },
            "environment": {
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "platform": sys.platform,
            },
        }

    def format_header(self, provenance: dict[str, Any]) -> str:
        """Format provenance as build log header."""
        lines = [
            "=" * 70,
            "🟢 DAN (GID-07) — BUILD PROVENANCE",
            "=" * 70,
            f"Timestamp:        {provenance['timestamp']}",
            f"Commit:           {provenance['git']['commit_sha']}",
            f"Branch:           {provenance['git']['branch']}",
            f"Governance Hash:  {provenance['governance']['hash'][:16]}...",
            f"ACM Version:      {provenance['governance']['acm_version']}",
            f"Checklist Ver:    {provenance['governance']['checklist_version']}",
            f"CI Workflow:      {provenance['ci']['workflow']}",
            f"CI Run ID:        {provenance['ci']['run_id']}",
            "=" * 70,
        ]
        return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="🟢 DAN (GID-07) — Build Provenance Generator")
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
        "--output",
        type=Path,
        default=None,
        help="Output JSON file path",
    )
    parser.add_argument(
        "--format",
        choices=["json", "header", "both"],
        default="both",
        help="Output format",
    )

    args = parser.parse_args()

    # Load config
    config_path = args.config
    if not config_path:
        default_config = args.repo_root / "scripts" / "ci" / "governance_scope.json"
        if default_config.exists():
            config_path = default_config

    generator = ProvenanceGenerator(args.repo_root, config_path)
    provenance = generator.generate()

    # Output
    if args.format in ("header", "both"):
        print(generator.format_header(provenance))
        print()

    if args.format in ("json", "both"):
        print(json.dumps(provenance, indent=2))

    if args.output:
        with open(args.output, "w") as f:
            json.dump(provenance, f, indent=2)
        print(f"\nProvenance written to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
