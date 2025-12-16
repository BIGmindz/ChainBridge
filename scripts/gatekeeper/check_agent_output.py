#!/usr/bin/env python3
"""
PAC-DAN-GATEKEEPER-02: Identity + Scope Hard Gates (identity layer)

Validates agent output packets before they reach review:
- Enforces canonical identity mapping (name ↔ gid ↔ emoji/color) from the single registry file.
- Rejects forbidden aliases (e.g., any occurrence of "DANA").
- Requires standard proof-bearing sections so missing evidence is caught early.

Usage:
    python scripts/gatekeeper/check_agent_output.py <file>
    make gatekeeper FILE=<file>

Exit codes:
    0 = PASS
    1 = FAIL (validation errors)
    2 = ERROR (file missing/unreadable or registry missing)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_repo_file(p: Path) -> Path:
    """Validate that a file path is within the repository root (CodeQL path traversal fix)."""
    candidate = p
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    resolved = candidate.resolve()
    if resolved != REPO_ROOT and REPO_ROOT not in resolved.parents:
        raise ValueError("Path escapes repository root")
    if not resolved.is_file():
        raise ValueError(f"Not a file: {resolved}")
    return resolved


REQUIRED_FIELDS = [
    "Identity",
    "Authority",
    "Task",
    "Constraints",
    "Evidence Plan",
    "Status",
    "Proof",  # proof/command evidence is mandatory for gating
]


@dataclass
class ValidationResult:
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    agent_name: Optional[str] = None
    agent_gid: Optional[str] = None
    agent_emoji: Optional[str] = None


class Registry:
    """Loads and provides access to the canonical registry."""

    def __init__(self, path: Path):
        self.path = path
        self.agents: Dict[str, Dict[str, str]] = {}
        self.forbidden_aliases: Set[str] = set()
        self.valid_emojis: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"Registry not found at {self.path}")

        with open(self.path, encoding="utf-8") as fh:
            data = json.load(fh)

        agents = data.get("agents", {})
        for name, info in agents.items():
            upper = name.upper()
            self.agents[upper] = {
                "gid": info.get("gid", "").upper(),
                "emoji": info.get("emoji", ""),
                "role": info.get("role", ""),
            }
            if info.get("emoji"):
                self.valid_emojis.add(info["emoji"])

        for alias in data.get("forbidden_aliases", []):
            self.forbidden_aliases.add(alias.upper())

    def get(self, name: str) -> Optional[Dict[str, str]]:
        return self.agents.get(name.upper())


class Gatekeeper:
    """Identity-focused gatekeeper validator."""

    IDENTITY_PATTERNS = [
        re.compile(
            r"\*\*Identity:?\*\*\s*[:\-]?\s*([A-Za-z0-9_-]+)[^\n]*?(GID-\d+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"Identity\s*[:\-]\s*([A-Za-z0-9_-]+)[^\n]*?(GID-\d+)",
            re.IGNORECASE,
        ),
    ]

    def __init__(self, content: str, registry: Registry):
        self.content = content
        self.registry = registry
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.agent_name: Optional[str] = None
        self.agent_gid: Optional[str] = None
        self.agent_emoji: Optional[str] = None

    def validate(self) -> ValidationResult:
        self._check_forbidden_aliases()
        self._extract_identity()
        self._validate_identity_against_registry()
        self._validate_required_fields()
        self._validate_proof_presence()

        return ValidationResult(
            passed=len(self.errors) == 0,
            errors=self.errors,
            warnings=self.warnings,
            agent_name=self.agent_name,
            agent_gid=self.agent_gid,
            agent_emoji=self.agent_emoji,
        )

    def _check_forbidden_aliases(self) -> None:
        for alias in self.registry.forbidden_aliases:
            if re.search(rf"\b{re.escape(alias)}\b", self.content, re.IGNORECASE):
                self.errors.append(f"Forbidden alias detected: {alias}")

    def _extract_identity(self) -> None:
        match = None
        for pattern in self.IDENTITY_PATTERNS:
            match = pattern.search(self.content)
            if match:
                break

        if not match:
            self.errors.append("Identity line not found or malformed")
            return

        name, gid = match.groups()
        self.agent_name = name.upper()
        self.agent_gid = gid.upper()

        # Extract emoji from the START banner line (first emoji present)
        emoji_match = re.search(r"[🟠🟡🟢🟣🔵🟤🔴⚪🔷💰🩷🟩]", self.content)
        if emoji_match:
            self.agent_emoji = emoji_match.group(0)

    def _validate_identity_against_registry(self) -> None:
        if not self.agent_name or not self.agent_gid:
            return

        canonical = self.registry.get(self.agent_name)
        if not canonical:
            self.errors.append(f"Unknown agent: {self.agent_name}")
            return

        expected_gid = canonical.get("gid")
        expected_emoji = canonical.get("emoji")

        if expected_gid and self.agent_gid != expected_gid:
            self.errors.append(f"Identity mismatch: {self.agent_name} should have {expected_gid}, found {self.agent_gid}")

        if self.agent_emoji:
            if expected_emoji and self.agent_emoji != expected_emoji:
                self.errors.append(f"Emoji mismatch: {self.agent_name} should use {expected_emoji}, found {self.agent_emoji}")
        else:
            self.errors.append("Agent color/emoji not detected in packet header")

    def _validate_required_fields(self) -> None:
        for field_name in REQUIRED_FIELDS:
            patterns = [
                re.compile(rf"\*\*{re.escape(field_name)}\*\*\s*:", re.IGNORECASE),
                re.compile(rf"\b{re.escape(field_name)}\s*:", re.IGNORECASE),
            ]
            if not any(p.search(self.content) for p in patterns):
                self.errors.append(f"Missing required field: {field_name}")

    def _validate_proof_presence(self) -> None:
        # Require at least one pytest command and one pytest summary line.
        pytest_cmd = re.search(r"pytest[\w\s\-:.]*", self.content, re.IGNORECASE)
        pytest_summary = re.search(r"(\d+\s+passed|failed|skipped)", self.content, re.IGNORECASE)
        if not pytest_cmd or not pytest_summary:
            self.errors.append("Proof missing: include pytest command and summary output")


def format_result(result: ValidationResult, filepath: Path) -> str:
    lines: List[str] = []
    if result.passed:
        lines.append(f"✅ GATEKEEPER PASS: {filepath}")
        if result.agent_name:
            lines.append(f"   Agent: {result.agent_name} ({result.agent_gid}) {result.agent_emoji or ''}".rstrip())
    else:
        lines.append(f"❌ GATEKEEPER FAIL: {filepath}")
        lines.append("")
        lines.append("Errors:")
        for err in result.errors:
            lines.append(f"  • {err}")

    if result.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warn in result.warnings:
            lines.append(f"  ⚠ {warn}")

    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate agent output packets for identity and proof compliance.",
        epilog="Exit codes: 0=PASS, 1=FAIL, 2=ERROR",
    )
    parser.add_argument("file", type=Path, help="Path to agent output file to validate")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only output on failure")
    args = parser.parse_args(argv)

    registry_path = REPO_ROOT / "ChainBridge" / "docs" / "governance" / "AGENT_REGISTRY.json"

    try:
        registry = Registry(registry_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: Failed to load registry: {exc}", file=sys.stderr)
        return 2

    # Validate file path to prevent path traversal (CodeQL security fix)
    try:
        safe_file = resolve_repo_file(args.file)
    except ValueError as exc:
        print(f"ERROR: Invalid file path: {exc}", file=sys.stderr)
        return 2

    try:
        content = safe_file.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: Could not read file: {exc}", file=sys.stderr)
        return 2

    result = Gatekeeper(content, registry).validate()

    if args.json:
        payload = {
            "passed": result.passed,
            "file": str(args.file),
            "agent_name": result.agent_name,
            "agent_gid": result.agent_gid,
            "agent_emoji": result.agent_emoji,
            "errors": result.errors,
            "warnings": result.warnings,
        }
        print(json.dumps(payload, indent=2))
    elif not args.quiet or not result.passed:
        print(format_result(result, args.file))

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
