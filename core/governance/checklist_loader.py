"""
Governance Checklist Loader — Hard dependency for ALEX startup.

This module loads and validates the governance validation checklist.
If the checklist is missing or invalid, the system refuses to boot.

ALEX (GID-08) consumes this checklist for intent validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml

# Default checklist path
_CHECKLIST_PATH = Path(__file__).parent.parent.parent / "docs" / "governance" / "GOVERNANCE_VALIDATION_CHECKLIST_v1.yaml"


class ChecklistNotFoundError(Exception):
    """Raised when the governance checklist file is missing."""

    pass


class ChecklistVersionError(Exception):
    """Raised when the checklist version is incompatible."""

    pass


class ChecklistValidationError(Exception):
    """Raised when the checklist structure is invalid."""

    pass


@dataclass(frozen=True)
class ValidationGate:
    """A single validation gate in the checklist."""

    gate_id: str
    description: str
    failure_reason: Optional[str]
    failure_detail: Optional[str]
    next_hop: Optional[str]
    fatal: bool


@dataclass(frozen=True)
class DenialReasonDef:
    """Definition of a denial reason code."""

    code: str
    description: str
    severity: str


@dataclass
class GovernanceChecklist:
    """Loaded governance checklist with validation rules."""

    version: str
    minimum_compatible_version: str
    status: str
    enforced_by: str
    chain_of_command_required_verbs: Set[str]
    orchestrator_gid: str
    required_checks: List[ValidationGate]
    denial_reasons: Dict[str, DenialReasonDef]
    invariants: List[str]
    forbidden_verbs: Set[str]
    protected_paths: List[str]
    failure_mode: str

    def requires_chain_of_command(self, verb: str) -> bool:
        """Check if a verb requires chain-of-command routing."""
        return verb.upper() in self.chain_of_command_required_verbs

    def is_verb_forbidden(self, verb: str) -> bool:
        """Check if a verb is system-wide forbidden."""
        return verb.upper() in self.forbidden_verbs

    def get_denial_reason(self, code: str) -> Optional[DenialReasonDef]:
        """Get denial reason definition by code."""
        return self.denial_reasons.get(code)


class ChecklistLoader:
    """Loader for the governance validation checklist.

    This is a HARD DEPENDENCY — if loading fails, the system refuses to boot.
    """

    def __init__(self, checklist_path: Path | None = None) -> None:
        """Initialize the loader.

        Args:
            checklist_path: Path to the checklist YAML file.
                          Defaults to docs/governance/GOVERNANCE_VALIDATION_CHECKLIST_v1.yaml
        """
        self._path = checklist_path or _CHECKLIST_PATH
        self._checklist: Optional[GovernanceChecklist] = None

    def load(self) -> GovernanceChecklist:
        """Load and validate the governance checklist.

        Returns:
            The loaded and validated checklist

        Raises:
            ChecklistNotFoundError: If checklist file is missing
            ChecklistVersionError: If version is incompatible
            ChecklistValidationError: If structure is invalid
        """
        # Check file exists
        if not self._path.exists():
            raise ChecklistNotFoundError(
                f"Governance checklist not found at {self._path}. " "System refuses to boot without governance checklist."
            )

        # Load YAML
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ChecklistValidationError(f"Failed to parse checklist YAML: {e}") from e

        # Validate required fields
        required_fields = [
            "version",
            "minimum_compatible_version",
            "status",
            "enforced_by",
            "required_checks",
            "failure_mode",
        ]
        for field_name in required_fields:
            if field_name not in data:
                raise ChecklistValidationError(f"Missing required field: {field_name}")

        # Validate version
        version = data["version"]
        min_version = data["minimum_compatible_version"]
        if not self._version_compatible(version, min_version):
            raise ChecklistVersionError(
                f"Checklist version {version} is below minimum {min_version}. " "System refuses to boot with incompatible checklist."
            )

        # Parse validation gates
        gates = []
        for gate_data in data.get("required_checks", []):
            gate = ValidationGate(
                gate_id=gate_data["gate_id"],
                description=gate_data.get("description", ""),
                failure_reason=gate_data.get("failure_reason"),
                failure_detail=gate_data.get("failure_detail"),
                next_hop=gate_data.get("next_hop"),
                fatal=gate_data.get("fatal", True),
            )
            gates.append(gate)

        # Parse denial reasons
        denial_reasons: Dict[str, DenialReasonDef] = {}
        for reason_data in data.get("denial_reasons", []):
            reason = DenialReasonDef(
                code=reason_data["code"],
                description=reason_data.get("description", ""),
                severity=reason_data.get("severity", "HIGH"),
            )
            denial_reasons[reason.code] = reason

        # Build checklist object
        self._checklist = GovernanceChecklist(
            version=version,
            minimum_compatible_version=min_version,
            status=data.get("status", "UNKNOWN"),
            enforced_by=data.get("enforced_by", "GID-08"),
            chain_of_command_required_verbs=set(data.get("chain_of_command_required_verbs", [])),
            orchestrator_gid=data.get("orchestrator_gid", "GID-00"),
            required_checks=gates,
            denial_reasons=denial_reasons,
            invariants=data.get("invariants", []),
            forbidden_verbs=set(data.get("forbidden_verbs", [])),
            protected_paths=data.get("protected_paths", []),
            failure_mode=data.get("failure_mode", "DENY"),
        )

        return self._checklist

    def get(self) -> GovernanceChecklist:
        """Get the loaded checklist.

        Returns:
            The loaded checklist

        Raises:
            ChecklistNotFoundError: If checklist not loaded yet
        """
        if self._checklist is None:
            return self.load()
        return self._checklist

    def _version_compatible(self, version: str, minimum: str) -> bool:
        """Check if version is >= minimum.

        Simple semver comparison (major.minor.patch).
        """
        try:
            v_parts = [int(x) for x in version.split(".")]
            m_parts = [int(x) for x in minimum.split(".")]

            # Pad to same length
            while len(v_parts) < 3:
                v_parts.append(0)
            while len(m_parts) < 3:
                m_parts.append(0)

            return tuple(v_parts) >= tuple(m_parts)
        except (ValueError, AttributeError):
            # If we can't parse, assume incompatible
            return False


# Module-level singleton
_checklist_loader: Optional[ChecklistLoader] = None


def get_checklist_loader(path: Path | None = None) -> ChecklistLoader:
    """Get or create the checklist loader singleton.

    Args:
        path: Optional custom path (only used on first call)

    Returns:
        The checklist loader instance
    """
    global _checklist_loader
    if _checklist_loader is None:
        _checklist_loader = ChecklistLoader(path)
    return _checklist_loader


def load_governance_checklist(path: Path | None = None) -> GovernanceChecklist:
    """Load the governance checklist (convenience function).

    Args:
        path: Optional custom path

    Returns:
        The loaded checklist

    Raises:
        ChecklistNotFoundError: If file missing
        ChecklistVersionError: If version mismatch
        ChecklistValidationError: If structure invalid
    """
    loader = get_checklist_loader(path)
    return loader.load()
