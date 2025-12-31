"""
core/actions.py - Action Handler for Execution Spine
PAC-CODY-EXEC-SPINE-01 / PAC-CODY-EXEC-SPINE-INTEGRATION-02

Real side effect execution:
- Input: DecisionResult (from core/decisions)
- Output: ActionResult
- Writes to append-only action log (file-backed)
- Explicit error handling

ACTION TYPES:
- APPROVED → record_approval (write to log)
- REQUIRES_REVIEW → record_escalation (write to log)
- REJECTED → record_rejection (write to log)
- ERROR → record_error (write to log)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from core.decisions import DecisionOutcome, DecisionResult

logger = logging.getLogger(__name__)

# Action log directory (append-only log)
ACTION_LOG_DIR = Path(os.getenv("ACTION_LOG_DIR", "logs/actions"))


class ActionStatus(str, Enum):
    """Action execution status."""
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True)
class ActionResult:
    """
    Immutable action result.

    Attributes:
        status: success or failure
        action_type: type of action executed
        event_id: ID of the event
        decision_outcome: the decision that triggered this action
        timestamp: ISO8601 timestamp of action execution
        details: additional details about the action
        error: error message if status is failure
    """
    status: ActionStatus
    action_type: str
    event_id: str
    decision_outcome: str
    timestamp: str
    details: Dict[str, Any]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        result = {
            "status": self.status.value,
            "action_type": self.action_type,
            "event_id": self.event_id,
            "decision_outcome": self.decision_outcome,
            "timestamp": self.timestamp,
            "details": self.details,
        }
        if self.error:
            result["error"] = self.error
        return result


def execute_action(decision: DecisionResult, event_payload: Dict[str, Any], event_id: str) -> ActionResult:
    """
    Execute action based on decision outcome.

    Maps canonical decision outcomes to action handlers:
    - APPROVED → record_approval
    - REQUIRES_REVIEW → record_escalation
    - REJECTED → record_rejection
    - ERROR → record_error

    Args:
        decision: The DecisionResult from core/decisions
        event_payload: Original event payload for context
        event_id: ID of the event being processed

    Returns:
        ActionResult with status and details
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    logger.info(
        "execute_action: starting",
        extra={
            "event_id": event_id,
            "decision": decision.outcome.value,
        }
    )

    action_handlers = {
        DecisionOutcome.APPROVED: _handle_approval,
        DecisionOutcome.REQUIRES_REVIEW: _handle_escalation,
        DecisionOutcome.REJECTED: _handle_rejection,
        DecisionOutcome.ERROR: _handle_error,
    }

    handler = action_handlers.get(decision.outcome)
    if handler is None:
        # Should never happen - defensive
        logger.error(
            "execute_action: unknown decision outcome",
            extra={"event_id": event_id, "outcome": decision.outcome}
        )
        return ActionResult(
            status=ActionStatus.FAILURE,
            action_type="unknown",
            event_id=event_id,
            decision_outcome=decision.outcome.value,
            timestamp=timestamp,
            details={},
            error=f"Unknown decision outcome: {decision.outcome}",
        )

    try:
        result = handler(decision, event_payload, timestamp, event_id)
        logger.info(
            "execute_action: completed",
            extra={
                "event_id": event_id,
                "action_type": result.action_type,
                "status": result.status.value,
            }
        )
        return result
    except Exception as e:
        logger.exception(
            "execute_action: failed",
            extra={"event_id": event_id, "error": str(e)}
        )
        return ActionResult(
            status=ActionStatus.FAILURE,
            action_type=f"handle_{decision.outcome.value}",
            event_id=event_id,
            decision_outcome=decision.outcome.value,
            timestamp=timestamp,
            details={"event_payload": event_payload},
            error=str(e),
        )


def _handle_approval(
    decision: DecisionResult,
    event_payload: Dict[str, Any],
    timestamp: str,
    event_id: str,
) -> ActionResult:
    """Handle APPROVED decision - record approval to log."""
    action_record = {
        "action": "approval_recorded",
        "event_id": event_id,
        "decision_outcome": decision.outcome.value,
        "explanation": decision.explanation,
        "rule_id": decision.rule_id,
        "payload_summary": {
            "amount": event_payload.get("amount"),
            "vendor_id": event_payload.get("vendor_id"),
        },
        "timestamp": timestamp,
    }

    _append_to_action_log(action_record)

    return ActionResult(
        status=ActionStatus.SUCCESS,
        action_type="record_approval",
        event_id=event_id,
        decision_outcome=decision.outcome.value,
        timestamp=timestamp,
        details=action_record,
    )


def _handle_escalation(
    decision: DecisionResult,
    event_payload: Dict[str, Any],
    timestamp: str,
    event_id: str,
) -> ActionResult:
    """Handle REQUIRES_REVIEW decision - record escalation to log."""
    action_record = {
        "action": "escalation_recorded",
        "event_id": event_id,
        "decision_outcome": decision.outcome.value,
        "explanation": decision.explanation,
        "rule_id": decision.rule_id,
        "payload_summary": {
            "amount": event_payload.get("amount"),
            "vendor_id": event_payload.get("vendor_id"),
        },
        "escalation_required": True,
        "timestamp": timestamp,
    }

    _append_to_action_log(action_record)

    return ActionResult(
        status=ActionStatus.SUCCESS,
        action_type="record_escalation",
        event_id=event_id,
        decision_outcome=decision.outcome.value,
        timestamp=timestamp,
        details=action_record,
    )


def _handle_rejection(
    decision: DecisionResult,
    event_payload: Dict[str, Any],
    timestamp: str,
    event_id: str,
) -> ActionResult:
    """Handle REJECTED decision - record rejection to log."""
    action_record = {
        "action": "rejection_recorded",
        "event_id": event_id,
        "decision_outcome": decision.outcome.value,
        "explanation": decision.explanation,
        "rule_id": decision.rule_id,
        "payload": event_payload,
        "timestamp": timestamp,
    }

    _append_to_action_log(action_record)

    return ActionResult(
        status=ActionStatus.SUCCESS,
        action_type="record_rejection",
        event_id=event_id,
        decision_outcome=decision.outcome.value,
        timestamp=timestamp,
        details=action_record,
    )


def _handle_error(
    decision: DecisionResult,
    event_payload: Dict[str, Any],
    timestamp: str,
    event_id: str,
) -> ActionResult:
    """Handle ERROR decision - record error to log."""
    action_record = {
        "action": "error_recorded",
        "event_id": event_id,
        "decision_outcome": decision.outcome.value,
        "explanation": decision.explanation,
        "rule_id": decision.rule_id,
        "payload": event_payload,
        "timestamp": timestamp,
    }

    _append_to_action_log(action_record)

    return ActionResult(
        status=ActionStatus.SUCCESS,
        action_type="record_error",
        event_id=event_id,
        decision_outcome=decision.outcome.value,
        timestamp=timestamp,
        details=action_record,
    )


def _append_to_action_log(record: Dict[str, Any]) -> None:
    """
    Append record to action log file (append-only).

    Creates log directory if it doesn't exist.
    Each record is a single JSON line.
    """
    ACTION_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = ACTION_LOG_DIR / "action_log.jsonl"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

    logger.debug(
        "action_log: record appended",
        extra={"log_file": str(log_file), "event_id": record.get("event_id")}
    )
