"""
Diggi Corrections — Deterministic Correction Contract (DCC) v1

This module implements bounded, machine-readable correction plans for denied intents.

CONSTRAINTS (NON-NEGOTIABLE):
- Diggi MUST NOT execute any action
- Diggi MUST NOT retry a denied intent
- Diggi MUST NOT generate new intents
- Diggi MUST NOT escalate implicitly
- Diggi MUST NOT modify authority
- Diggi MUST NOT perform reasoning, optimization, or learning

Diggi MAY ONLY:
- Translate a denial into a bounded correction plan
- Use pre-defined mappings
- Fail closed if no mapping exists

No heuristics. No LLM reasoning. No fallbacks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from core.governance.acm_evaluator import DenialReason

# Verbs that are ABSOLUTELY FORBIDDEN in correction plans
FORBIDDEN_CORRECTION_VERBS: Set[str] = {"EXECUTE", "APPROVE", "BLOCK"}

# Default correction map path
DEFAULT_CORRECTION_MAP_PATH = Path(__file__).parent.parent.parent / "docs" / "governance" / "DIGGI_CORRECTION_MAP_v1.yaml"


class CorrectionError(Exception):
    """Base exception for correction-related errors."""

    pass


class CorrectionMapNotFoundError(CorrectionError):
    """Raised when correction map file is missing."""

    pass


class CorrectionMapInvalidError(CorrectionError):
    """Raised when correction map fails schema validation."""

    pass


class NoValidCorrectionError(CorrectionError):
    """Raised when no correction exists for a denial reason."""

    pass


class ForbiddenVerbInCorrectionError(CorrectionError):
    """Raised when a correction contains a forbidden verb."""

    pass


@dataclass(frozen=True)
class CorrectionStep:
    """A single allowed next step in a correction plan.

    Immutable once created.
    """

    verb: str
    target_scope: Optional[str]  # For PROPOSE/READ
    target: Optional[str]  # For ESCALATE
    description: str

    def __post_init__(self) -> None:
        """Validate that verb is not forbidden."""
        if self.verb.upper() in FORBIDDEN_CORRECTION_VERBS:
            raise ForbiddenVerbInCorrectionError(f"Correction step cannot contain forbidden verb: {self.verb}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: Dict[str, Any] = {
            "verb": self.verb,
            "description": self.description,
        }
        if self.target_scope:
            result["target_scope"] = self.target_scope
        if self.target:
            result["target"] = self.target
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorrectionStep":
        """Create CorrectionStep from dictionary."""
        return cls(
            verb=data["verb"],
            target_scope=data.get("target_scope"),
            target=data.get("target"),
            description=data["description"],
        )


@dataclass(frozen=True)
class CorrectionPlan:
    """A bounded correction plan for a denied intent.

    This is the output of Diggi's deterministic correction lookup.
    Immutable once created.
    """

    cause: str  # DenialReason value
    constraints: tuple[str, ...]  # Why the action was denied
    allowed_next_steps: tuple[CorrectionStep, ...]  # Bounded options

    def __post_init__(self) -> None:
        """Validate no forbidden verbs in steps."""
        for step in self.allowed_next_steps:
            if step.verb.upper() in FORBIDDEN_CORRECTION_VERBS:
                raise ForbiddenVerbInCorrectionError(f"CorrectionPlan cannot contain forbidden verb: {step.verb}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "correction_plan": {
                "cause": self.cause,
                "constraints": list(self.constraints),
                "allowed_next_steps": [step.to_dict() for step in self.allowed_next_steps],
            }
        }

    @classmethod
    def from_dict(cls, cause: str, data: Dict[str, Any]) -> "CorrectionPlan":
        """Create CorrectionPlan from dictionary."""
        steps = [CorrectionStep.from_dict(step_data) for step_data in data.get("allowed_next_steps", [])]
        return cls(
            cause=cause,
            constraints=tuple(data.get("constraints", [])),
            allowed_next_steps=tuple(steps),
        )

    def validate(self) -> bool:
        """Validate the correction plan.

        Returns:
            True if valid

        Raises:
            ForbiddenVerbInCorrectionError: If any step contains forbidden verb
        """
        for step in self.allowed_next_steps:
            if step.verb.upper() in FORBIDDEN_CORRECTION_VERBS:
                raise ForbiddenVerbInCorrectionError(f"CorrectionPlan contains forbidden verb: {step.verb}")
        return True


class CorrectionMap:
    """Loader and validator for the correction mapping file.

    Loads at startup. Fails closed on any error.
    """

    def __init__(self, map_path: Optional[Path] = None):
        """Initialize the correction map.

        Args:
            map_path: Path to correction map YAML. Defaults to standard location.

        Raises:
            CorrectionMapNotFoundError: If file doesn't exist
            CorrectionMapInvalidError: If file fails validation
        """
        self._map_path = map_path or DEFAULT_CORRECTION_MAP_PATH
        self._version: str = ""
        self._schema_version: str = ""
        self._corrections: Dict[str, Dict[str, Any]] = {}
        self._loaded = False

    @property
    def version(self) -> str:
        """Return the correction map version."""
        return self._version

    @property
    def schema_version(self) -> str:
        """Return the schema version."""
        return self._schema_version

    @property
    def is_loaded(self) -> bool:
        """Return whether the map is loaded."""
        return self._loaded

    def load(self) -> None:
        """Load and validate the correction map.

        Raises:
            CorrectionMapNotFoundError: If file doesn't exist
            CorrectionMapInvalidError: If file fails validation
        """
        if not self._map_path.exists():
            raise CorrectionMapNotFoundError(f"Correction map not found: {self._map_path}")

        try:
            with open(self._map_path, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise CorrectionMapInvalidError(f"Invalid YAML in correction map: {e}")

        # Validate required fields
        self._validate_schema(data)

        # Store validated data
        self._version = data["version"]
        self._schema_version = data["schema_version"]
        self._corrections = data["corrections"]

        # Validate all corrections contain no forbidden verbs
        self._validate_no_forbidden_verbs()

        self._loaded = True

    def _validate_schema(self, data: Dict[str, Any]) -> None:
        """Validate correction map schema.

        Raises:
            CorrectionMapInvalidError: If schema validation fails
        """
        required_fields = ["version", "schema_version", "governance_lock", "corrections"]
        for field_name in required_fields:
            if field_name not in data:
                raise CorrectionMapInvalidError(f"Missing required field: {field_name}")

        if not data.get("governance_lock"):
            raise CorrectionMapInvalidError("Correction map must have governance_lock: true")

        if not isinstance(data["corrections"], dict):
            raise CorrectionMapInvalidError("corrections must be a dictionary")

    def _validate_no_forbidden_verbs(self) -> None:
        """Validate that no correction contains forbidden verbs.

        Raises:
            ForbiddenVerbInCorrectionError: If any correction contains forbidden verb
        """
        for reason, correction in self._corrections.items():
            steps = correction.get("allowed_next_steps", [])
            for step in steps:
                verb = step.get("verb", "").upper()
                if verb in FORBIDDEN_CORRECTION_VERBS:
                    raise ForbiddenVerbInCorrectionError(f"Correction for {reason} contains forbidden verb: {verb}")

    def get_correction(self, denial_reason: DenialReason) -> CorrectionPlan:
        """Get correction plan for a denial reason.

        Args:
            denial_reason: The reason for denial

        Returns:
            CorrectionPlan with bounded next steps

        Raises:
            NoValidCorrectionError: If no mapping exists for this reason
            CorrectionMapNotFoundError: If map not loaded
        """
        if not self._loaded:
            raise CorrectionMapNotFoundError("Correction map not loaded — call load() first")

        reason_key = denial_reason.value
        if reason_key not in self._corrections:
            raise NoValidCorrectionError(f"No correction mapping for denial reason: {reason_key}")

        correction_data = self._corrections[reason_key]
        return CorrectionPlan.from_dict(reason_key, correction_data)

    def has_correction(self, denial_reason: DenialReason) -> bool:
        """Check if a correction exists for a denial reason.

        Args:
            denial_reason: The reason to check

        Returns:
            True if correction exists, False otherwise
        """
        if not self._loaded:
            return False
        return denial_reason.value in self._corrections

    def get_all_mapped_reasons(self) -> List[str]:
        """Get all denial reasons that have correction mappings.

        Returns:
            List of DenialReason values that are mapped
        """
        if not self._loaded:
            return []
        return list(self._corrections.keys())


# Module-level singleton
_correction_map: Optional[CorrectionMap] = None


def get_correction_map() -> CorrectionMap:
    """Get the singleton correction map instance.

    Returns:
        The global CorrectionMap instance
    """
    global _correction_map
    if _correction_map is None:
        _correction_map = CorrectionMap()
    return _correction_map


def reset_correction_map() -> None:
    """Reset the singleton correction map (for testing)."""
    global _correction_map
    _correction_map = None


def load_correction_map(map_path: Optional[Path] = None) -> CorrectionMap:
    """Load the correction map from file.

    Args:
        map_path: Optional custom path to correction map

    Returns:
        Loaded CorrectionMap instance

    Raises:
        CorrectionMapNotFoundError: If file doesn't exist
        CorrectionMapInvalidError: If file fails validation
    """
    global _correction_map
    _correction_map = CorrectionMap(map_path)
    _correction_map.load()
    return _correction_map


def get_correction_for_denial(denial_reason: DenialReason) -> CorrectionPlan:
    """Get correction plan for a denial reason.

    This is the primary API for obtaining corrections.

    Args:
        denial_reason: The reason for denial

    Returns:
        CorrectionPlan with bounded next steps

    Raises:
        NoValidCorrectionError: If no mapping exists (FAIL CLOSED)
        CorrectionMapNotFoundError: If map not loaded
    """
    correction_map = get_correction_map()
    return correction_map.get_correction(denial_reason)


# ============================================================
# GOVERNANCE CANONICAL CLOSE
# ============================================================
# This module is DETERMINISTIC.
# Identical input → Identical output.
# No heuristics. No LLM. No inference.
# Unknown DenialReason → NoValidCorrectionError (FAIL CLOSED).
# ============================================================
