"""
ChainIQ Storage Layer

Persistence for risk scoring decisions, enabling:
- Audit trail of all risk decisions
- Deterministic replay of past scores
- Trend analysis over time
- ML training data collection
- Compliance reporting

Database: SQLite (lightweight, embedded, zero-config)
Schema: risk_decisions table with full request/response snapshots

Design Principles:
- Append-only (no updates/deletes for audit integrity)
- Full request context stored (enables deterministic replay)
- Indexed by shipment_id and timestamp
- JSON fields for flexibility
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Database location (relative to project root)
DB_PATH = Path(__file__).parent.parent / "data" / "chainiq.db"


def init_db() -> None:
    """
    Initialize the ChainIQ database schema.

    Creates:
    - risk_decisions table for storing all scoring results
    - Indexes for fast lookups by shipment_id and timestamp

    Safe to call multiple times (idempotent).
    """
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create risk_decisions table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id TEXT NOT NULL,
            scored_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            risk_score INTEGER NOT NULL,
            severity TEXT NOT NULL,
            recommended_action TEXT NOT NULL,
            reason_codes TEXT NOT NULL,
            request_data TEXT NOT NULL,
            response_data TEXT NOT NULL
        )
    """
    )

    # Create indexes for fast queries
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_shipment_id
        ON risk_decisions(shipment_id)
    """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_scored_at
        ON risk_decisions(scored_at DESC)
    """
    )

    conn.commit()
    conn.close()

    logger.info("ChainIQ database initialized at %s", DB_PATH)


def insert_score(
    shipment_id: str,
    risk_score: int,
    severity: str,
    recommended_action: str,
    reason_codes: List[str],
    request_data: Dict[str, Any],
    response_data: Dict[str, Any],
) -> int:
    """
    Insert a risk scoring decision into the database.

    Args:
        shipment_id: Unique shipment identifier
        risk_score: Risk score (0-100)
        severity: Risk severity level
        recommended_action: Recommended action
        reason_codes: List of reason codes
        request_data: Full request payload (for replay)
        response_data: Full response payload (for audit)

    Returns:
        Database row ID of inserted record

    Example:
        >>> row_id = insert_score(
        ...     shipment_id="SHP-001",
        ...     risk_score=45,
        ...     severity="MEDIUM",
        ...     recommended_action="MANUAL_REVIEW",
        ...     reason_codes=["ELEVATED_VALUE"],
        ...     request_data={...},
        ...     response_data={...}
        ... )
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO risk_decisions (
            shipment_id,
            risk_score,
            severity,
            recommended_action,
            reason_codes,
            request_data,
            response_data
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            shipment_id,
            risk_score,
            severity,
            recommended_action,
            json.dumps(reason_codes),
            json.dumps(request_data),
            json.dumps(response_data),
        ),
    )

    row_id = cursor.lastrowid
    conn.commit()
    conn.close()

    if row_id is None:
        raise RuntimeError("Failed to insert risk decision")

    logger.info(
        "Stored risk decision: shipment_id=%s, score=%d, severity=%s",
        shipment_id,
        risk_score,
        severity,
    )

    return row_id


def get_score(shipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the most recent risk score for a shipment.

    Args:
        shipment_id: Shipment identifier

    Returns:
        Dictionary with score details, or None if not found

    Example:
        >>> score = get_score("SHP-001")
        >>> if score:
        ...     print(score["risk_score"], score["severity"])
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            shipment_id,
            scored_at,
            risk_score,
            severity,
            recommended_action,
            reason_codes,
            request_data,
            response_data
        FROM risk_decisions
        WHERE shipment_id = ?
        ORDER BY scored_at DESC
        LIMIT 1
    """,
        (shipment_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row["id"],
        "shipment_id": row["shipment_id"],
        "scored_at": row["scored_at"],
        "risk_score": row["risk_score"],
        "severity": row["severity"],
        "recommended_action": row["recommended_action"],
        "reason_codes": json.loads(row["reason_codes"]),
        "request_data": json.loads(row["request_data"]),
        "response_data": json.loads(row["response_data"]),
    }


def list_scores(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    List recent risk scores (most recent first).

    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip (for pagination)

    Returns:
        List of score dictionaries

    Example:
        >>> recent = list_scores(limit=10)
        >>> for score in recent:
        ...     print(score["shipment_id"], score["risk_score"])
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            shipment_id,
            scored_at,
            risk_score,
            severity,
            recommended_action,
            reason_codes,
            request_data,
            response_data
        FROM risk_decisions
        ORDER BY scored_at DESC
        LIMIT ? OFFSET ?
    """,
        (limit, offset),
    )

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        results.append(
            {
                "id": row["id"],
                "shipment_id": row["shipment_id"],
                "scored_at": row["scored_at"],
                "risk_score": row["risk_score"],
                "severity": row["severity"],
                "recommended_action": row["recommended_action"],
                "reason_codes": json.loads(row["reason_codes"]),
                "request_data": json.loads(row["request_data"]),
                "response_data": json.loads(row["response_data"]),
            }
        )

    return results


def get_history(entity_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieve full scoring history for an entity (shipment).

    Returns all risk assessments for the entity in reverse chronological order.
    Useful for audit trails, trend analysis, and decision review.

    Args:
        entity_id: Entity identifier (shipment_id)
        limit: Maximum number of records to return (default 100)

    Returns:
        List of historical scoring records with timestamp, payload, and score

    Example:
        >>> history = get_history("SHP-001", limit=10)
        >>> for record in history:
        ...     print(record["timestamp"], record["score"])
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            shipment_id,
            scored_at,
            risk_score,
            severity,
            recommended_action,
            reason_codes,
            request_data,
            response_data
        FROM risk_decisions
        WHERE shipment_id = ?
        ORDER BY scored_at DESC
        LIMIT ?
    """,
        (entity_id, limit),
    )

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        results.append(
            {
                "id": row["id"],
                "entity_id": row["shipment_id"],
                "timestamp": row["scored_at"],
                "score": row["risk_score"],
                "severity": row["severity"],
                "recommended_action": row["recommended_action"],
                "reason_codes": (json.loads(row["reason_codes"]) if row["reason_codes"] else []),
                "payload": json.loads(row["request_data"]),
                "response_data": json.loads(row["response_data"]),
            }
        )

    return results


def replay_request(shipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the original request data for deterministic replay.

    This enables:
    - Verifying scoring algorithm changes
    - Auditing historical decisions
    - Testing new risk models against historical data

    Args:
        shipment_id: Shipment identifier

    Returns:
        Original request payload, or None if not found

    Example:
        >>> request = replay_request("SHP-001")
        >>> if request:
        ...     # Re-score with current algorithm
        ...     new_score = calculate_risk_score(**request)
    """
    score_data = get_score(shipment_id)

    if not score_data:
        return None

    return score_data["request_data"]


def get_latest_risk_for_shipment(shipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the most recent risk snapshot for a shipment.

    This is the primary helper for ProofPack generation, extracting just the
    essential risk data (no full request/response payloads).

    Args:
        shipment_id: Shipment identifier

    Returns:
        Dictionary with risk snapshot fields, or None if not scored yet

        Fields:
        - shipment_id: Shipment identifier
        - risk_score: Risk score (0-100)
        - severity: Risk severity level (LOW/MEDIUM/HIGH/CRITICAL)
        - recommended_action: Recommended action
        - reason_codes: List of reason codes
        - last_scored_at: ISO-8601 timestamp

    Example:
        >>> risk = get_latest_risk_for_shipment("SHP-001")
        >>> if risk:
        ...     print(f"{risk['severity']} risk: {risk['risk_score']}/100")
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            shipment_id,
            scored_at,
            risk_score,
            severity,
            recommended_action,
            reason_codes
        FROM risk_decisions
        WHERE shipment_id = ?
        ORDER BY scored_at DESC
        LIMIT 1
    """,
        (shipment_id,),
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "shipment_id": row["shipment_id"],
        "risk_score": row["risk_score"],
        "severity": row["severity"],
        "recommended_action": row["recommended_action"],
        "reason_codes": json.loads(row["reason_codes"]),
        "last_scored_at": row["scored_at"],
    }


def get_payment_queue_entry_for_shipment(shipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the payment queue entry for a shipment, if it's on hold.

    This queries the ChainPay payment queue to find if this shipment has a
    pending payment that's currently on hold for risk review.

    Args:
        shipment_id: Shipment identifier

    Returns:
        Dictionary with queue entry details, or None if not in queue

        Fields:
        - payment_id: Payment identifier
        - shipment_id: Shipment identifier
        - amount: Payment amount
        - currency: Payment currency
        - recipient: Recipient address/account
        - status: Payment status (typically "HOLD")
        - hold_reason: Reason for hold
        - created_at: ISO-8601 timestamp

    Example:
        >>> entry = get_payment_queue_entry_for_shipment("SHP-001")
        >>> if entry:
        ...     print(f"Payment ${entry['amount']} on hold: {entry['hold_reason']}")

    Note:
        This is a placeholder implementation. In production, this will query
        the ChainPay service's payment_queue table. For now, returns None
        until ChainPay integration is complete.
    """
    # Placeholder: ChainPay integration pending
    # Once payment_queue table is available, query for HOLD status entries
    # matching the shipment_id parameter
    logger.debug(
        "get_payment_queue_entry_for_shipment: ChainPay integration pending for %s",
        shipment_id,
    )
    return None


def load_shipment_context_for_simulation(shipment_id: str) -> Dict[str, Any]:
    """
    Load the latest known shipment context for sandbox simulation.

    Retrieves the original request payload from the most recent risk scoring
    to enable "what-if" simulations without requiring callers to re-specify
    all shipment details.

    Args:
        shipment_id: Shipment identifier

    Returns:
        Dictionary with shipment context fields:
        - shipment_id: Shipment identifier
        - route: Origin-destination route
        - carrier_id: Carrier identifier
        - shipment_value_usd: Shipment value
        - days_in_transit: Days in transit
        - expected_days: Expected transit days
        - documents_complete: Document completion status
        - shipper_payment_score: Shipper payment reliability

    Raises:
        ValueError: If no scoring history found for shipment

    Example:
        >>> context = load_shipment_context_for_simulation("SHP-001")
        >>> context["route"]
        'CN-US'

    Note:
        This is read-only. No data is persisted during simulation.
    """
    score_data = get_score(shipment_id)

    if not score_data:
        raise ValueError(f"No scoring history found for shipment {shipment_id}")

    # Extract request_data from the most recent scoring
    request_data = score_data.get("request_data", {})

    if not request_data:
        raise ValueError(f"No request payload found for shipment {shipment_id}")

    # Ensure we have the required fields for risk scoring
    required_fields = [
        "route",
        "carrier_id",
        "shipment_value_usd",
        "days_in_transit",
        "expected_days",
        "documents_complete",
        "shipper_payment_score",
    ]

    missing_fields = [f for f in required_fields if f not in request_data]
    if missing_fields:
        raise ValueError(f"Incomplete shipment context for {shipment_id}. " f"Missing fields: {', '.join(missing_fields)}")

    logger.debug(
        "Loaded simulation context for %s: route=%s, carrier=%s",
        shipment_id,
        request_data.get("route"),
        request_data.get("carrier_id"),
    )

    return request_data
