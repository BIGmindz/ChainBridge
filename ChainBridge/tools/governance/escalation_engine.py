#!/usr/bin/env python3
"""
Governance Escalation & Ratification Engine

Authority: PAC-ALEX-G1-PHASE-2-GOVERNANCE-ESCALATION-AND-RATIFICATION-LOOPS-01
Owner: ALEX (GID-08)
Mode: FAIL_CLOSED

This engine enforces:
- No indefinite PENDING states
- Mandatory correction → resubmission loops
- Timeboxed escalation SLAs
- Authority-bound decisions
- No silent unblocks

Governance cannot stall. Governance cannot deadlock.
"""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

# ============================================================================
# ESCALATION STATE MODEL (CANONICAL)
# ============================================================================

class EscalationState(Enum):
    """
    Governance escalation states.
    No state may persist indefinitely without authority action.
    """
    DETECTED = "DETECTED"          # Failure detected, awaiting classification
    BLOCKED = "BLOCKED"            # Execution blocked, awaiting correction
    CORRECTION_REQUIRED = "CORRECTION_REQUIRED"  # Explicit deficiency identified
    RESUBMITTED = "RESUBMITTED"    # Corrected artifact submitted for review
    RATIFIED = "RATIFIED"          # Authority approved, escalation closed
    UNBLOCKED = "UNBLOCKED"        # Operations resumed after ratification
    REJECTED = "REJECTED"          # Correction insufficient, re-correction required


class GovernanceFailureType(Enum):
    """Types of governance failures that trigger escalation."""
    PAC_VALIDATION_FAILURE = "PAC_VALIDATION_FAILURE"
    WRAP_VALIDATION_FAILURE = "WRAP_VALIDATION_FAILURE"
    AUTHORITY_VIOLATION = "AUTHORITY_VIOLATION"
    SCOPE_VIOLATION = "SCOPE_VIOLATION"
    FORBIDDEN_ACTION = "FORBIDDEN_ACTION"
    TIMEBOX_EXCEEDED = "TIMEBOX_EXCEEDED"
    DEPENDENCY_DEADLOCK = "DEPENDENCY_DEADLOCK"
    MULTI_AGENT_CONFLICT = "MULTI_AGENT_CONFLICT"
    PROOF_MISSING = "PROOF_MISSING"
    STATE_INVARIANT_VIOLATION = "STATE_INVARIANT_VIOLATION"


class Authority(Enum):
    """Governance authorities."""
    BENSON = "BENSON (GID-00)"
    ALEX = "ALEX (GID-08)"
    SAM = "SAM (GID-06)"
    RUBY = "RUBY (GID-12)"
    HUMAN_CEO = "Human CEO"


# ============================================================================
# ESCALATION RULES (LOCKED)
# ============================================================================

ESCALATION_RULES = {
    "correction_required": {
        "must_include": [
            "explicit_deficiency_list",
            "corrected_artifact_path",
            "acknowledgment_block",
            "correction_author_gid"
        ],
        "timebox_hours": 24,
        "timeout_action": "AUTO_REJECT"
    },
    "resubmission": {
        "must_include": [
            "original_failure_id",
            "correction_summary",
            "resubmission_timestamp"
        ],
        "timebox_hours": 24,
        "timeout_action": "ESCALATE_TO_BENSON"
    },
    "ratification": {
        "authority": Authority.BENSON,
        "secondary_authority": Authority.ALEX,
        "timebox_hours": 48,
        "timeout_action": "ESCALATE_TO_HUMAN"
    },
    "override": {
        "allowed": False,
        "exception_authority": Authority.HUMAN_CEO,
        "requires_proof": True
    }
}

# ============================================================================
# STATE TRANSITION MATRIX (LOCKED)
# ============================================================================

STATE_TRANSITIONS = {
    EscalationState.DETECTED: {
        "valid_next": [EscalationState.BLOCKED, EscalationState.CORRECTION_REQUIRED],
        "authority": Authority.ALEX,
        "timebox_hours": 1,
        "auto_transition": EscalationState.BLOCKED
    },
    EscalationState.BLOCKED: {
        "valid_next": [EscalationState.CORRECTION_REQUIRED],
        "authority": Authority.ALEX,
        "timebox_hours": 4,
        "auto_transition": None  # Cannot auto-unblock
    },
    EscalationState.CORRECTION_REQUIRED: {
        "valid_next": [EscalationState.RESUBMITTED],
        "authority": None,  # Agent responsibility
        "timebox_hours": 24,
        "auto_transition": EscalationState.REJECTED
    },
    EscalationState.RESUBMITTED: {
        "valid_next": [EscalationState.RATIFIED, EscalationState.REJECTED],
        "authority": Authority.BENSON,
        "timebox_hours": 24,
        "auto_transition": None  # Requires explicit decision
    },
    EscalationState.RATIFIED: {
        "valid_next": [EscalationState.UNBLOCKED],
        "authority": Authority.BENSON,
        "timebox_hours": 1,
        "auto_transition": EscalationState.UNBLOCKED
    },
    EscalationState.UNBLOCKED: {
        "valid_next": [],  # Terminal state
        "authority": None,
        "timebox_hours": None,
        "auto_transition": None
    },
    EscalationState.REJECTED: {
        "valid_next": [EscalationState.CORRECTION_REQUIRED],
        "authority": Authority.ALEX,
        "timebox_hours": 1,
        "auto_transition": EscalationState.CORRECTION_REQUIRED
    }
}

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DeficiencyItem:
    """A single deficiency requiring correction."""
    code: str  # e.g., "G0_001"
    description: str
    location: Optional[str] = None
    correction_guidance: Optional[str] = None


@dataclass
class CorrectionPayload:
    """Mandatory correction payload structure."""
    escalation_id: str
    deficiency_list: list  # List of DeficiencyItem
    corrected_artifact_path: str
    acknowledgment: dict  # Must include agent_gid, timestamp, signature
    correction_author_gid: str
    original_failure_timestamp: str
    correction_timestamp: str


@dataclass
class EscalationRecord:
    """A governance escalation record."""
    escalation_id: str
    failure_type: GovernanceFailureType
    detected_at: str  # ISO-8601
    current_state: EscalationState
    state_history: list = field(default_factory=list)
    affected_artifact: Optional[str] = None
    affected_agent_gid: Optional[str] = None
    deficiencies: list = field(default_factory=list)
    correction_payload: Optional[CorrectionPayload] = None
    ratification_authority: Optional[Authority] = None
    ratification_timestamp: Optional[str] = None
    resolution_notes: Optional[str] = None
    timebox_deadline: Optional[str] = None
    next_action_required_by: Optional[str] = None


# ============================================================================
# ESCALATION ENGINE
# ============================================================================

class EscalationEngine:
    """
    Governance Escalation & Ratification Engine.

    Invariants:
    - No indefinite PENDING states
    - Every state has a timebox
    - Every transition requires authority or timeout
    - No silent unblocks
    - No bypass paths
    """

    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file or Path("escalation_state.json")
        self.escalations: dict[str, EscalationRecord] = {}
        self._load_state()

    def _load_state(self):
        """Load escalation state from disk."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                data = json.load(f)
                for eid, record in data.get("escalations", {}).items():
                    self.escalations[eid] = self._dict_to_record(record)

    def _save_state(self):
        """Persist escalation state to disk."""
        data = {
            "escalations": {
                eid: self._record_to_dict(record)
                for eid, record in self.escalations.items()
            },
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def _dict_to_record(self, d: dict) -> EscalationRecord:
        """Convert dict to EscalationRecord."""
        return EscalationRecord(
            escalation_id=d["escalation_id"],
            failure_type=GovernanceFailureType(d["failure_type"]),
            detected_at=d["detected_at"],
            current_state=EscalationState(d["current_state"]),
            state_history=d.get("state_history", []),
            affected_artifact=d.get("affected_artifact"),
            affected_agent_gid=d.get("affected_agent_gid"),
            deficiencies=d.get("deficiencies", []),
            correction_payload=d.get("correction_payload"),
            ratification_authority=Authority(d["ratification_authority"]) if d.get("ratification_authority") else None,
            ratification_timestamp=d.get("ratification_timestamp"),
            resolution_notes=d.get("resolution_notes"),
            timebox_deadline=d.get("timebox_deadline"),
            next_action_required_by=d.get("next_action_required_by")
        )

    def _record_to_dict(self, record: EscalationRecord) -> dict:
        """Convert EscalationRecord to dict."""
        return {
            "escalation_id": record.escalation_id,
            "failure_type": record.failure_type.value,
            "detected_at": record.detected_at,
            "current_state": record.current_state.value,
            "state_history": record.state_history,
            "affected_artifact": record.affected_artifact,
            "affected_agent_gid": record.affected_agent_gid,
            "deficiencies": record.deficiencies,
            "correction_payload": record.correction_payload,
            "ratification_authority": record.ratification_authority.value if record.ratification_authority else None,
            "ratification_timestamp": record.ratification_timestamp,
            "resolution_notes": record.resolution_notes,
            "timebox_deadline": record.timebox_deadline,
            "next_action_required_by": record.next_action_required_by
        }

    def _generate_escalation_id(self) -> str:
        """Generate unique escalation ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        count = len(self.escalations) + 1
        return f"ESC-{timestamp}-{count:04d}"

    def _calculate_timebox(self, state: EscalationState) -> str:
        """Calculate timebox deadline for a state."""
        transition = STATE_TRANSITIONS.get(state)
        if not transition or not transition.get("timebox_hours"):
            return None
        hours = transition["timebox_hours"]
        deadline = datetime.utcnow() + timedelta(hours=hours)
        return deadline.isoformat() + "Z"

    def _get_next_action_authority(self, state: EscalationState) -> str:
        """Determine who must act next for a given state."""
        mapping = {
            EscalationState.DETECTED: "ALEX (GID-08)",
            EscalationState.BLOCKED: "ALEX (GID-08)",
            EscalationState.CORRECTION_REQUIRED: "Affected Agent",
            EscalationState.RESUBMITTED: "BENSON (GID-00)",
            EscalationState.RATIFIED: "BENSON (GID-00)",
            EscalationState.UNBLOCKED: None,
            EscalationState.REJECTED: "Affected Agent"
        }
        return mapping.get(state)

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def detect_failure(
        self,
        failure_type: GovernanceFailureType,
        affected_artifact: str,
        affected_agent_gid: str,
        deficiencies: list[dict]
    ) -> EscalationRecord:
        """
        Detect a governance failure and create escalation record.

        This is the entry point for all governance failures.
        """
        escalation_id = self._generate_escalation_id()
        now = datetime.utcnow().isoformat() + "Z"

        record = EscalationRecord(
            escalation_id=escalation_id,
            failure_type=failure_type,
            detected_at=now,
            current_state=EscalationState.DETECTED,
            state_history=[{
                "state": EscalationState.DETECTED.value,
                "timestamp": now,
                "authority": "SYSTEM"
            }],
            affected_artifact=affected_artifact,
            affected_agent_gid=affected_agent_gid,
            deficiencies=deficiencies,
            timebox_deadline=self._calculate_timebox(EscalationState.DETECTED),
            next_action_required_by=self._get_next_action_authority(EscalationState.DETECTED)
        )

        self.escalations[escalation_id] = record
        self._save_state()

        return record

    def transition_to_blocked(
        self,
        escalation_id: str,
        authority_gid: str
    ) -> EscalationRecord:
        """Transition escalation to BLOCKED state."""
        record = self.escalations.get(escalation_id)
        if not record:
            raise ValueError(f"Escalation {escalation_id} not found")

        if record.current_state != EscalationState.DETECTED:
            raise ValueError(
                f"Cannot transition to BLOCKED from {record.current_state.value}"
            )

        now = datetime.utcnow().isoformat() + "Z"
        record.state_history.append({
            "state": EscalationState.BLOCKED.value,
            "timestamp": now,
            "authority": authority_gid
        })
        record.current_state = EscalationState.BLOCKED
        record.timebox_deadline = self._calculate_timebox(EscalationState.BLOCKED)
        record.next_action_required_by = self._get_next_action_authority(EscalationState.BLOCKED)

        self._save_state()
        return record

    def require_correction(
        self,
        escalation_id: str,
        authority_gid: str,
        deficiency_details: list[dict]
    ) -> EscalationRecord:
        """
        Transition to CORRECTION_REQUIRED.

        This explicitly requires the affected agent to submit a correction.
        """
        record = self.escalations.get(escalation_id)
        if not record:
            raise ValueError(f"Escalation {escalation_id} not found")

        valid_from = [EscalationState.DETECTED, EscalationState.BLOCKED, EscalationState.REJECTED]
        if record.current_state not in valid_from:
            raise ValueError(
                f"Cannot transition to CORRECTION_REQUIRED from {record.current_state.value}"
            )

        now = datetime.utcnow().isoformat() + "Z"
        record.state_history.append({
            "state": EscalationState.CORRECTION_REQUIRED.value,
            "timestamp": now,
            "authority": authority_gid,
            "deficiencies": deficiency_details
        })
        record.current_state = EscalationState.CORRECTION_REQUIRED
        record.deficiencies = deficiency_details
        record.timebox_deadline = self._calculate_timebox(EscalationState.CORRECTION_REQUIRED)
        record.next_action_required_by = record.affected_agent_gid or "Affected Agent"

        self._save_state()
        return record

    def submit_correction(
        self,
        escalation_id: str,
        correction_payload: dict
    ) -> EscalationRecord:
        """
        Submit a correction for review.

        Payload must include:
        - deficiency_list (addressed deficiencies)
        - corrected_artifact_path
        - acknowledgment (with agent_gid, timestamp)
        - correction_author_gid
        """
        record = self.escalations.get(escalation_id)
        if not record:
            raise ValueError(f"Escalation {escalation_id} not found")

        if record.current_state != EscalationState.CORRECTION_REQUIRED:
            raise ValueError(
                f"Cannot submit correction from {record.current_state.value}"
            )

        # Validate payload
        required_fields = ["corrected_artifact_path", "acknowledgment", "correction_author_gid"]
        for field in required_fields:
            if field not in correction_payload:
                raise ValueError(f"Correction payload missing required field: {field}")

        now = datetime.utcnow().isoformat() + "Z"
        record.state_history.append({
            "state": EscalationState.RESUBMITTED.value,
            "timestamp": now,
            "authority": correction_payload["correction_author_gid"],
            "correction_summary": correction_payload.get("correction_summary", "")
        })
        record.current_state = EscalationState.RESUBMITTED
        record.correction_payload = correction_payload
        record.timebox_deadline = self._calculate_timebox(EscalationState.RESUBMITTED)
        record.next_action_required_by = "BENSON (GID-00)"

        self._save_state()
        return record

    def ratify(
        self,
        escalation_id: str,
        authority: Authority,
        notes: Optional[str] = None
    ) -> EscalationRecord:
        """
        Ratify a correction and close the escalation.

        Only BENSON (GID-00) or ALEX (GID-08) may ratify.
        """
        record = self.escalations.get(escalation_id)
        if not record:
            raise ValueError(f"Escalation {escalation_id} not found")

        if record.current_state != EscalationState.RESUBMITTED:
            raise ValueError(
                f"Cannot ratify from {record.current_state.value}"
            )

        if authority not in [Authority.BENSON, Authority.ALEX, Authority.HUMAN_CEO]:
            raise ValueError(f"Authority {authority.value} cannot ratify")

        now = datetime.utcnow().isoformat() + "Z"
        record.state_history.append({
            "state": EscalationState.RATIFIED.value,
            "timestamp": now,
            "authority": authority.value,
            "notes": notes
        })
        record.current_state = EscalationState.RATIFIED
        record.ratification_authority = authority
        record.ratification_timestamp = now
        record.resolution_notes = notes
        record.timebox_deadline = self._calculate_timebox(EscalationState.RATIFIED)
        record.next_action_required_by = "BENSON (GID-00)"

        self._save_state()
        return record

    def reject(
        self,
        escalation_id: str,
        authority_gid: str,
        rejection_reason: str,
        additional_deficiencies: list[dict] = None
    ) -> EscalationRecord:
        """
        Reject a correction and require re-correction.

        The escalation loops back to CORRECTION_REQUIRED.
        """
        record = self.escalations.get(escalation_id)
        if not record:
            raise ValueError(f"Escalation {escalation_id} not found")

        if record.current_state != EscalationState.RESUBMITTED:
            raise ValueError(
                f"Cannot reject from {record.current_state.value}"
            )

        now = datetime.utcnow().isoformat() + "Z"
        record.state_history.append({
            "state": EscalationState.REJECTED.value,
            "timestamp": now,
            "authority": authority_gid,
            "reason": rejection_reason,
            "additional_deficiencies": additional_deficiencies
        })
        record.current_state = EscalationState.REJECTED

        if additional_deficiencies:
            record.deficiencies.extend(additional_deficiencies)

        record.timebox_deadline = self._calculate_timebox(EscalationState.REJECTED)
        record.next_action_required_by = record.affected_agent_gid or "Affected Agent"

        self._save_state()
        return record

    def unblock(
        self,
        escalation_id: str,
        authority_gid: str
    ) -> EscalationRecord:
        """
        Unblock after ratification and close the escalation.

        This is the terminal successful state.
        """
        record = self.escalations.get(escalation_id)
        if not record:
            raise ValueError(f"Escalation {escalation_id} not found")

        if record.current_state != EscalationState.RATIFIED:
            raise ValueError(
                f"Cannot unblock from {record.current_state.value}"
            )

        now = datetime.utcnow().isoformat() + "Z"
        record.state_history.append({
            "state": EscalationState.UNBLOCKED.value,
            "timestamp": now,
            "authority": authority_gid
        })
        record.current_state = EscalationState.UNBLOCKED
        record.timebox_deadline = None
        record.next_action_required_by = None

        self._save_state()
        return record

    # ========================================================================
    # QUERIES
    # ========================================================================

    def get_pending_escalations(self) -> list[EscalationRecord]:
        """Get all escalations not in terminal state."""
        terminal = {EscalationState.UNBLOCKED}
        return [
            r for r in self.escalations.values()
            if r.current_state not in terminal
        ]

    def get_overdue_escalations(self) -> list[EscalationRecord]:
        """Get escalations past their timebox deadline."""
        now = datetime.utcnow()
        overdue = []
        for record in self.escalations.values():
            if record.timebox_deadline:
                deadline = datetime.fromisoformat(record.timebox_deadline.rstrip("Z"))
                if now > deadline and record.current_state != EscalationState.UNBLOCKED:
                    overdue.append(record)
        return overdue

    def get_next_action_queue(self) -> dict[str, list[EscalationRecord]]:
        """Get escalations grouped by who must act next."""
        queue = {}
        for record in self.get_pending_escalations():
            actor = record.next_action_required_by or "UNASSIGNED"
            if actor not in queue:
                queue[actor] = []
            queue[actor].append(record)
        return queue

    def validate_no_deadlocks(self) -> dict:
        """
        Validate that no deadlock paths exist.

        Returns validation result with any issues found.
        """
        issues = []

        # Check 1: All pending escalations have a next_action_required_by
        for record in self.get_pending_escalations():
            if not record.next_action_required_by:
                issues.append({
                    "type": "ORPHAN_ESCALATION",
                    "escalation_id": record.escalation_id,
                    "state": record.current_state.value,
                    "message": "No next action authority assigned"
                })

        # Check 2: All states have valid transitions
        for state, config in STATE_TRANSITIONS.items():
            if state == EscalationState.UNBLOCKED:
                continue  # Terminal state OK
            if not config.get("valid_next") and not config.get("auto_transition"):
                issues.append({
                    "type": "DEADLOCK_STATE",
                    "state": state.value,
                    "message": "State has no exit transitions"
                })

        # Check 3: No indefinite timeboxes (except terminal)
        for state, config in STATE_TRANSITIONS.items():
            if state == EscalationState.UNBLOCKED:
                continue
            if config.get("timebox_hours") is None and config.get("auto_transition") is None:
                issues.append({
                    "type": "UNBOUNDED_TIMEBOX",
                    "state": state.value,
                    "message": "State has no timebox and no auto-transition"
                })

        return {
            "valid": len(issues) == 0,
            "deadlock_possible": len(issues) > 0,
            "issues": issues
        }


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """CLI for escalation engine."""
    import argparse

    parser = argparse.ArgumentParser(description="Governance Escalation Engine")
    parser.add_argument("--mode", choices=["validate", "status", "queue"], required=True)
    parser.add_argument("--state-file", type=Path, default=Path("escalation_state.json"))

    args = parser.parse_args()

    engine = EscalationEngine(args.state_file)

    if args.mode == "validate":
        result = engine.validate_no_deadlocks()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["valid"] else 1)

    elif args.mode == "status":
        pending = engine.get_pending_escalations()
        overdue = engine.get_overdue_escalations()
        print(f"Pending escalations: {len(pending)}")
        print(f"Overdue escalations: {len(overdue)}")
        for record in pending:
            print(f"  - {record.escalation_id}: {record.current_state.value} (next: {record.next_action_required_by})")

    elif args.mode == "queue":
        queue = engine.get_next_action_queue()
        print("=== NEXT ACTION QUEUE ===")
        for actor, records in queue.items():
            print(f"\n{actor}:")
            for record in records:
                deadline = record.timebox_deadline or "N/A"
                print(f"  - {record.escalation_id}: {record.current_state.value} (deadline: {deadline})")


if __name__ == "__main__":
    main()
