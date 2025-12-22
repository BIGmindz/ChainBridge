"""Centralized PDO Gate Enforcement.

Single point of enforcement for "No PDO → No execution".
All gateway and OCC write paths MUST call require_pdo() before proceeding.

Fail-closed design: if PDO is missing, invalid, or rejected, execution halts.

Constitutional Enforcement: PAC-CODY-CONSTITUTION-ENFORCEMENT-02
- Wires constitution_engine.assert_lock() for LOCK-PDO-GATE-001
- Emits EXECUTION_BLOCKED telemetry on violation
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from gateway.pdo_schema import GatewayPDO


logger = logging.getLogger("gateway.pdo_gate")


class PDOGateError(Exception):
    """Raised when execution is blocked due to missing or invalid PDO."""

    def __init__(self, message: str, pdo: Optional["GatewayPDO"] = None) -> None:
        super().__init__(message)
        self.pdo = pdo


def _emit_execution_blocked(reason: str, pdo: Optional["GatewayPDO"] = None) -> None:
    """Emit EXECUTION_BLOCKED telemetry event."""
    import json
    from datetime import datetime

    event = {
        "event": "EXECUTION_BLOCKED",
        "lock_id": "LOCK-PDO-GATE-001",
        "reason": reason,
        "pdo_id": str(pdo.pdo_id) if pdo and hasattr(pdo, "pdo_id") else None,
        "timestamp": datetime.utcnow().isoformat(),
    }
    logger.warning("EXECUTION_BLOCKED: %s", json.dumps(event, separators=(",", ":")))


class PDOGate:
    """
    Centralized PDO gate enforcer.

    Usage:
        gate = PDOGate()
        gate.require_pdo(pdo)  # Raises PDOGateError if not approved
    """

    def require_pdo(self, pdo: Optional["GatewayPDO"]) -> "GatewayPDO":
        """
        Enforce that a valid, approved PDO exists before execution.

        Args:
            pdo: The Policy Decision Object to validate.

        Returns:
            The validated PDO (for chaining).

        Raises:
            PDOGateError: If PDO is None, invalid, or rejected.
        """
        # Import here to avoid circular dependency
        from gateway.intent_schema import IntentState
        from gateway.pdo_schema import GatewayPDO, PDOOutcome

        # Gate 1: PDO must exist
        if pdo is None:
            _emit_execution_blocked("No PDO provided", None)
            raise PDOGateError("Execution blocked: No PDO provided")

        # Gate 2: PDO must be the correct type
        if not isinstance(pdo, GatewayPDO):
            _emit_execution_blocked(f"Invalid PDO type ({type(pdo).__name__})", None)
            raise PDOGateError(f"Execution blocked: Invalid PDO type ({type(pdo).__name__})")

        # Gate 3: PDO state must be DECIDED (terminal state)
        if pdo.state != IntentState.DECIDED:
            _emit_execution_blocked(f"PDO not in terminal state (state={pdo.state.value})", pdo)
            raise PDOGateError(
                f"Execution blocked: PDO not in terminal state (state={pdo.state.value})",
                pdo=pdo,
            )

        # Gate 4: PDO outcome must be APPROVED
        if pdo.outcome != PDOOutcome.APPROVED:
            reasons = ", ".join(pdo.reasons) if pdo.reasons else "No reasons provided"
            _emit_execution_blocked(f"PDO rejected ({reasons})", pdo)
            raise PDOGateError(
                f"Execution blocked: PDO rejected ({reasons})",
                pdo=pdo,
            )

        return pdo

        return pdo

    def is_approved(self, pdo: Optional["GatewayPDO"]) -> bool:
        """
        Check if PDO would pass the gate without raising.

        Args:
            pdo: The Policy Decision Object to check.

        Returns:
            True if PDO is valid and approved, False otherwise.
        """
        try:
            self.require_pdo(pdo)
            return True
        except PDOGateError:
            return False


# Module-level singleton for convenience
_default_gate = PDOGate()


def require_pdo(pdo: Optional["GatewayPDO"]) -> "GatewayPDO":
    """
    Module-level convenience function for PDO enforcement.

    This is the canonical entry point for all PDO gate checks.
    """
    return _default_gate.require_pdo(pdo)


def is_pdo_approved(pdo: Optional["GatewayPDO"]) -> bool:
    """
    Module-level convenience function to check PDO approval status.
    """
    return _default_gate.is_approved(pdo)
