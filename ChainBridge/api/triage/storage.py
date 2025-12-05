# api/triage/storage.py
"""
ChainBoard Triage Storage
==========================

In-memory storage for alert assignments, notes, actions, and status overrides.
Fine for MVP/demo - no need for persistence yet.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from api.schemas.chainboard import (
    AlertActionRecord,
    AlertActionType,
    AlertNote,
    AlertOwner,
    AlertSeverity,
    AlertSource,
    AlertStatus,
    AlertWorkItem,
    ControlTowerAlert,
)

# ============================================================================
# IN-MEMORY STATE
# ============================================================================

ALERT_ASSIGNMENTS: Dict[str, AlertOwner] = {}
"""Maps alert_id -> AlertOwner"""

ALERT_NOTES: Dict[str, List[AlertNote]] = {}
"""Maps alert_id -> List[AlertNote]"""

ALERT_ACTIONS: Dict[str, List[AlertActionRecord]] = {}
"""Maps alert_id -> List[AlertActionRecord]"""

ALERT_STATUS_OVERRIDES: Dict[str, AlertStatus] = {}
"""Maps alert_id -> AlertStatus (overrides alert.status)"""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_work_item(alert: ControlTowerAlert) -> AlertWorkItem:
    """
    Build AlertWorkItem from base alert + triage context.

    Args:
        alert: Base ControlTowerAlert

    Returns:
        AlertWorkItem with owner, notes, actions populated from storage
    """
    # Apply status override if exists
    effective_status = ALERT_STATUS_OVERRIDES.get(alert.id, alert.status)
    alert_copy = alert.model_copy()
    alert_copy.status = effective_status

    return AlertWorkItem(
        alert=alert_copy,
        owner=ALERT_ASSIGNMENTS.get(alert.id),
        notes=ALERT_NOTES.get(alert.id, []),
        actions=ALERT_ACTIONS.get(alert.id, []),
    )


def get_work_queue(
    alerts: List[ControlTowerAlert],
    owner_id: Optional[str] = None,
    status: Optional[AlertStatus] = None,
    source: Optional[AlertSource] = None,
    severity: Optional[AlertSeverity] = None,
) -> List[AlertWorkItem]:
    """
    Build filtered work queue from alerts.

    Args:
        alerts: Base alerts list
        owner_id: Filter by assigned owner (None = all)
        status: Filter by status (None = all)
        source: Filter by source (None = all)
        severity: Filter by severity (None = all)

    Returns:
        Filtered list of AlertWorkItem
    """
    items = [get_work_item(alert) for alert in alerts]

    # Apply filters
    if owner_id is not None:
        items = [item for item in items if item.owner and item.owner.id == owner_id]

    if status is not None:
        items = [item for item in items if item.alert.status == status]

    if source is not None:
        items = [item for item in items if item.alert.source == source]

    if severity is not None:
        items = [item for item in items if item.alert.severity == severity]

    return items


def assign_alert(alert_id: str, owner: Optional[AlertOwner], actor: AlertOwner) -> None:
    """
    Assign or unassign alert to owner.

    Args:
        alert_id: Alert ID
        owner: New owner (None = unassign)
        actor: Who performed the assignment
    """
    if owner is None:
        # Unassign
        ALERT_ASSIGNMENTS.pop(alert_id, None)
    else:
        ALERT_ASSIGNMENTS[alert_id] = owner

    # Record action
    action = AlertActionRecord(
        id=str(uuid4()),
        alert_id=alert_id,
        type=AlertActionType.ASSIGN,
        actor=actor,
        payload={"owner_id": owner.id if owner else None},
        created_at=datetime.utcnow(),
    )

    if alert_id not in ALERT_ACTIONS:
        ALERT_ACTIONS[alert_id] = []
    ALERT_ACTIONS[alert_id].append(action)


def add_note(alert_id: str, note: AlertNote) -> None:
    """
    Add note to alert.

    Args:
        alert_id: Alert ID
        note: Note to add (already has ID, timestamp from caller)
    """
    if alert_id not in ALERT_NOTES:
        ALERT_NOTES[alert_id] = []
    ALERT_NOTES[alert_id].append(note)

    # Record action
    action = AlertActionRecord(
        id=str(uuid4()),
        alert_id=alert_id,
        type=AlertActionType.COMMENT,
        actor=note.author,
        payload={"message": note.message},
        created_at=datetime.utcnow(),
    )

    if alert_id not in ALERT_ACTIONS:
        ALERT_ACTIONS[alert_id] = []
    ALERT_ACTIONS[alert_id].append(action)


def update_status(alert_id: str, new_status: AlertStatus, actor: AlertOwner) -> None:
    """
    Update alert status (with override).

    Args:
        alert_id: Alert ID
        new_status: New status
        actor: Who performed the update
    """
    ALERT_STATUS_OVERRIDES[alert_id] = new_status

    # Record action
    action_type = (
        AlertActionType.ACKNOWLEDGE
        if new_status == AlertStatus.ACKNOWLEDGED
        else (AlertActionType.RESOLVE if new_status == AlertStatus.RESOLVED else AlertActionType.COMMENT)
    )

    action = AlertActionRecord(
        id=str(uuid4()),
        alert_id=alert_id,
        type=action_type,
        actor=actor,
        payload={"new_status": new_status.value},
        created_at=datetime.utcnow(),
    )

    if alert_id not in ALERT_ACTIONS:
        ALERT_ACTIONS[alert_id] = []
    ALERT_ACTIONS[alert_id].append(action)
