# app/services/audit_service.py
"""
Audit Service - Canonical entry points for recording audit events and decisions.

This module provides helpers to record:
- AuditEvent rows ("what happened")
- DecisionLog rows ("why it happened")

See docs/product/CHAINBRIDGE_AUDIT_PROOFPACK_SPEC.md for semantic details.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models_audit import AuditEvent, DecisionLog


def record_audit_event(
    db: Session,
    *,
    event_type: str,
    actor_type: str,
    actor_id: Optional[str] = None,
    source_system: Optional[str] = None,
    shipment_id: Optional[str] = None,
    payment_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    payload_hash: Optional[str] = None,
    payload_meta: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    """
    Create and persist an AuditEvent row.

    This is the canonical entry point for recording "what happened" in ChainPay.
    Events are append-only and should never be modified after creation.

    Args:
        db: SQLAlchemy session
        event_type: Type of event (e.g., "payout_released", "payment_approved")
        actor_type: Who/what triggered the event ("system", "user", "agent")
        actor_id: Identifier of the actor (user_id, service_id, agent GID)
        source_system: Origin system (EDI, IoT, ChainIQ, etc.)
        shipment_id: Related shipment identifier
        payment_id: Related payment identifier
        customer_id: Related customer identifier
        correlation_id: Cross-system correlation ID for tracing
        payload_hash: Hash of the event payload for integrity
        payload_meta: Summarized metadata (not raw payload)

    Returns:
        The created AuditEvent instance with assigned ID.
    """
    event = AuditEvent(
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        source_system=source_system,
        shipment_id=shipment_id,
        payment_id=payment_id,
        customer_id=customer_id,
        correlation_id=correlation_id,
        payload_hash=payload_hash,
        payload_meta=payload_meta or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def record_decision_log(
    db: Session,
    *,
    decision_type: str,
    outcome: str,
    audit_event_id: Optional[int] = None,
    risk_policy_version: Optional[str] = None,
    payment_policy_version: Optional[str] = None,
    model_version: Optional[str] = None,
    input_snapshot: Optional[Dict[str, Any]] = None,
    rules_fired: Optional[Dict[str, Any]] = None,
    explanation: Optional[Dict[str, Any]] = None,
    overridden: bool = False,
    override_actor_id: Optional[str] = None,
    override_reason: Optional[str] = None,
) -> DecisionLog:
    """
    Create and persist a DecisionLog row.

    This is the canonical entry point for recording "why it happened" in ChainPay.
    Decision logs capture the reasoning chain for audit and compliance purposes.

    Args:
        db: SQLAlchemy session
        decision_type: Type of decision (e.g., "payout_decision", "risk_override")
        outcome: Result of the decision ("approve", "hold", "reject")
        audit_event_id: Optional link to the triggering AuditEvent
        risk_policy_version: Version of risk policy used
        payment_policy_version: Version of payment policy used
        model_version: Version of ML model used (if applicable)
        input_snapshot: Key inputs at decision time
        rules_fired: Which rules triggered the decision
        explanation: Human-readable reasoning
        overridden: Whether this decision was manually overridden
        override_actor_id: Who performed the override
        override_reason: Justification for the override (required if overridden)

    Returns:
        The created DecisionLog instance with assigned ID.
    """
    log = DecisionLog(
        decision_type=decision_type,
        outcome=outcome,
        audit_event_id=audit_event_id,
        risk_policy_version=risk_policy_version,
        payment_policy_version=payment_policy_version,
        model_version=model_version,
        input_snapshot=input_snapshot or {},
        rules_fired=rules_fired or {},
        explanation=explanation or {},
        overridden=1 if overridden else 0,
        override_actor_id=override_actor_id,
        override_reason=override_reason,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
