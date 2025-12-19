"""
Invariant Violation Telemetry — Structured Logging for Invariant Breaches

PAC-CODY-INVARIANT-ENFORCEMENT-01: Automated Invariant Enforcement

This module provides deterministic, structured, machine-parsable logging for:
- PDO immutability violations
- ProofPack verification failures
- Hash/integrity breaches

Telemetry is:
- Structured (JSON format)
- Non-PII (no personal data)
- Machine-parsable
- Deterministic

Author: CODY (GID-01) - Backend
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID


# =============================================================================
# TELEMETRY CONFIGURATION
# =============================================================================


class InvariantDomain(str, Enum):
    """Invariant domain classification."""

    PDO = "pdo"
    PROOFPACK = "proofpack"
    VERIFICATION = "verification"
    GOVERNANCE = "governance"


class ViolationType(str, Enum):
    """Types of invariant violations."""

    # PDO violations
    PDO_IMMUTABILITY = "pdo_immutability"
    PDO_UPDATE_ATTEMPTED = "pdo_update_attempted"
    PDO_DELETE_ATTEMPTED = "pdo_delete_attempted"
    PDO_HASH_MODIFICATION = "pdo_hash_modification"
    PDO_TAMPER_DETECTED = "pdo_tamper_detected"

    # ProofPack violations
    PROOFPACK_INVALID_PDO_HASH = "proofpack_invalid_pdo_hash"
    PROOFPACK_INVALID_ARTIFACT_HASH = "proofpack_invalid_artifact_hash"
    PROOFPACK_INVALID_MANIFEST_HASH = "proofpack_invalid_manifest_hash"
    PROOFPACK_INVALID_LINEAGE = "proofpack_invalid_lineage"
    PROOFPACK_INVALID_REFERENCES = "proofpack_invalid_references"
    PROOFPACK_INCOMPLETE = "proofpack_incomplete"
    PROOFPACK_GENERATION_FAILED = "proofpack_generation_failed"


# =============================================================================
# TELEMETRY EVENT
# =============================================================================


class InvariantViolationEvent:
    """Structured telemetry event for invariant violations."""

    def __init__(
        self,
        domain: InvariantDomain,
        violation_type: ViolationType,
        invariant_id: str,
        message: str,
        pdo_id: Optional[UUID] = None,
        expected_value: Optional[str] = None,
        actual_value: Optional[str] = None,
        source_file: Optional[str] = None,
        source_line: Optional[int] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ):
        """
        Create an invariant violation event.

        Args:
            domain: The invariant domain (pdo, proofpack, etc.)
            violation_type: Type of violation detected
            invariant_id: The invariant ID from CANONICAL_INVARIANTS.md
            message: Human-readable description
            pdo_id: Optional PDO ID involved
            expected_value: Expected hash/value (if applicable)
            actual_value: Actual hash/value found (if applicable)
            source_file: Source file where violation detected
            source_line: Line number where violation detected
            additional_context: Any additional non-PII context
        """
        self.timestamp = datetime.now(timezone.utc)
        self.domain = domain
        self.violation_type = violation_type
        self.invariant_id = invariant_id
        self.message = message
        self.pdo_id = pdo_id
        self.expected_value = expected_value
        self.actual_value = actual_value
        self.source_file = source_file
        self.source_line = source_line
        self.additional_context = additional_context or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        event = {
            "event_type": "invariant_violation",
            "timestamp": self.timestamp.isoformat(),
            "domain": self.domain.value,
            "violation_type": self.violation_type.value,
            "invariant_id": self.invariant_id,
            "message": self.message,
        }

        if self.pdo_id:
            event["pdo_id"] = str(self.pdo_id)
        if self.expected_value:
            event["expected"] = self.expected_value
        if self.actual_value:
            event["actual"] = self.actual_value
        if self.source_file:
            event["source_file"] = self.source_file
        if self.source_line:
            event["source_line"] = self.source_line
        if self.additional_context:
            event["context"] = self.additional_context

        return event

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


# =============================================================================
# TELEMETRY LOGGER
# =============================================================================


class InvariantTelemetryLogger:
    """
    Structured logger for invariant violations.

    Logs to a dedicated logger with JSON-formatted messages
    for machine parsing and aggregation.
    """

    def __init__(self, logger_name: str = "chainbridge.invariant_telemetry"):
        """Initialize the telemetry logger."""
        self._logger = logging.getLogger(logger_name)

    def emit(self, event: InvariantViolationEvent) -> None:
        """
        Emit an invariant violation event.

        Args:
            event: The violation event to log
        """
        # Log as structured JSON on a single line
        self._logger.error(
            f"INVARIANT_VIOLATION: {event.to_json()}"
        )

    # =========================================================================
    # PDO VIOLATION HELPERS
    # =========================================================================

    def log_pdo_update_attempt(
        self,
        pdo_id: UUID,
        source_file: str = "pdo_store.py",
    ) -> None:
        """Log a PDO update attempt violation."""
        event = InvariantViolationEvent(
            domain=InvariantDomain.PDO,
            violation_type=ViolationType.PDO_UPDATE_ATTEMPTED,
            invariant_id="INV-PDO-004",
            message=f"Attempted update on immutable PDO {pdo_id}",
            pdo_id=pdo_id,
            source_file=source_file,
        )
        self.emit(event)

    def log_pdo_delete_attempt(
        self,
        pdo_id: UUID,
        source_file: str = "pdo_store.py",
    ) -> None:
        """Log a PDO delete attempt violation."""
        event = InvariantViolationEvent(
            domain=InvariantDomain.PDO,
            violation_type=ViolationType.PDO_DELETE_ATTEMPTED,
            invariant_id="INV-PDO-004",
            message=f"Attempted delete on immutable PDO {pdo_id}",
            pdo_id=pdo_id,
            source_file=source_file,
        )
        self.emit(event)

    def log_pdo_hash_modification_attempt(
        self,
        pdo_id: UUID,
        source_file: str = "pdo_store.py",
    ) -> None:
        """Log a PDO hash modification attempt violation."""
        event = InvariantViolationEvent(
            domain=InvariantDomain.PDO,
            violation_type=ViolationType.PDO_HASH_MODIFICATION,
            invariant_id="INV-PDO-001",
            message=f"Attempted hash modification on PDO {pdo_id}",
            pdo_id=pdo_id,
            source_file=source_file,
        )
        self.emit(event)

    def log_pdo_tamper_detected(
        self,
        pdo_id: UUID,
        expected_hash: str,
        actual_hash: str,
        source_file: str = "pdo_store.py",
    ) -> None:
        """Log a PDO tamper detection event."""
        event = InvariantViolationEvent(
            domain=InvariantDomain.PDO,
            violation_type=ViolationType.PDO_TAMPER_DETECTED,
            invariant_id="INV-PDO-006",
            message=f"Tamper detected on PDO {pdo_id}: hash mismatch",
            pdo_id=pdo_id,
            expected_value=expected_hash,
            actual_value=actual_hash,
            source_file=source_file,
        )
        self.emit(event)

    # =========================================================================
    # PROOFPACK VIOLATION HELPERS
    # =========================================================================

    def log_proofpack_verification_failure(
        self,
        pdo_id: Optional[UUID],
        outcome: str,
        expected_hash: Optional[str] = None,
        actual_hash: Optional[str] = None,
        source_file: str = "verifier.py",
    ) -> None:
        """Log a ProofPack verification failure."""
        # Map outcome to violation type
        violation_map = {
            "INVALID_PDO_HASH": ViolationType.PROOFPACK_INVALID_PDO_HASH,
            "INVALID_ARTIFACT_HASH": ViolationType.PROOFPACK_INVALID_ARTIFACT_HASH,
            "INVALID_MANIFEST_HASH": ViolationType.PROOFPACK_INVALID_MANIFEST_HASH,
            "INVALID_LINEAGE": ViolationType.PROOFPACK_INVALID_LINEAGE,
            "INVALID_REFERENCES": ViolationType.PROOFPACK_INVALID_REFERENCES,
            "INCOMPLETE": ViolationType.PROOFPACK_INCOMPLETE,
        }
        violation_type = violation_map.get(
            outcome, ViolationType.PROOFPACK_INCOMPLETE
        )

        event = InvariantViolationEvent(
            domain=InvariantDomain.PROOFPACK,
            violation_type=violation_type,
            invariant_id="INV-PP-003",
            message=f"ProofPack verification failed: {outcome}",
            pdo_id=pdo_id,
            expected_value=expected_hash,
            actual_value=actual_hash,
            source_file=source_file,
        )
        self.emit(event)

    def log_proofpack_generation_failure(
        self,
        pdo_id: UUID,
        reason: str,
        source_file: str = "generator.py",
    ) -> None:
        """Log a ProofPack generation failure."""
        event = InvariantViolationEvent(
            domain=InvariantDomain.PROOFPACK,
            violation_type=ViolationType.PROOFPACK_GENERATION_FAILED,
            invariant_id="INV-PP-001",
            message=f"ProofPack generation failed for PDO {pdo_id}: {reason}",
            pdo_id=pdo_id,
            source_file=source_file,
            additional_context={"reason": reason},
        )
        self.emit(event)


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_telemetry_logger: Optional[InvariantTelemetryLogger] = None


def get_invariant_telemetry() -> InvariantTelemetryLogger:
    """Get the singleton telemetry logger instance."""
    global _telemetry_logger
    if _telemetry_logger is None:
        _telemetry_logger = InvariantTelemetryLogger()
    return _telemetry_logger


def reset_invariant_telemetry() -> None:
    """Reset the telemetry logger (for testing)."""
    global _telemetry_logger
    _telemetry_logger = None
