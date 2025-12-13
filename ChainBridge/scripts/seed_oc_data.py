"""Seed data for the Exception Cockpit (The OC).

This script populates the database with sample exceptions, playbooks, and
decision records for development and testing of the OC frontend.

Usage:
    python -m scripts.seed_oc_data

Or import and call:
    from scripts.seed_oc_data import seed_oc_data
    seed_oc_data(db_session)
"""

import logging
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default tenant for seed data
DEFAULT_TENANT_ID = "default-tenant"


def seed_oc_data(db: Session, tenant_id: str = DEFAULT_TENANT_ID) -> dict:
    """
    Seed exception, playbook, and decision record data for the OC.

    Returns a summary of created records.
    """
    # Import models here to avoid circular imports
    from api.models.decision_record import DecisionRecord as DecisionRecordModel
    from api.models.exception import Exception as ExceptionModel
    from api.models.playbook import Playbook as PlaybookModel

    created = {"playbooks": 0, "exceptions": 0, "decisions": 0}

    # ==========================================================================
    # PLAYBOOKS
    # ==========================================================================
    playbooks = [
        {
            "id": f"PB-{uuid4()}",
            "tenant_id": tenant_id,
            "name": "Critical Risk Response",
            "description": "Standard operating procedure for handling critical risk threshold breaches",
            "category": "RISK_THRESHOLD",
            "trigger_condition": {"severity": ["CRITICAL"], "type": ["RISK_THRESHOLD"]},
            "steps": [
                {"order": 1, "action": "review_risk_factors", "description": "Analyze ChainIQ risk breakdown", "gate": "auto"},
                {
                    "order": 2,
                    "action": "assess_mitigation",
                    "description": "Evaluate rerouting or carrier alternatives",
                    "gate": "human_approval",
                },
                {"order": 3, "action": "notify_stakeholders", "description": "Alert customer and internal teams", "gate": "auto"},
                {
                    "order": 4,
                    "action": "document_resolution",
                    "description": "Record outcome and lessons learned",
                    "gate": "human_approval",
                },
            ],
            "active": True,
            "version": 1,
        },
        {
            "id": f"PB-{uuid4()}",
            "tenant_id": tenant_id,
            "name": "Payment Hold Resolution",
            "description": "Process for resolving payment holds from ChainPay",
            "category": "PAYMENT_HOLD",
            "trigger_condition": {"type": ["PAYMENT_HOLD"]},
            "steps": [
                {"order": 1, "action": "verify_documents", "description": "Check BoL and required documentation", "gate": "auto"},
                {"order": 2, "action": "contact_shipper", "description": "Request missing documentation", "gate": "human_approval"},
                {"order": 3, "action": "release_funds", "description": "Approve milestone release", "gate": "human_approval"},
            ],
            "active": True,
            "version": 1,
        },
        {
            "id": f"PB-{uuid4()}",
            "tenant_id": tenant_id,
            "name": "Document Gap Resolution",
            "description": "Process for resolving missing documentation issues",
            "category": "DOCUMENT_MISSING",
            "trigger_condition": {"type": ["DOCUMENT_MISSING", "COMPLIANCE_FLAG"]},
            "steps": [
                {"order": 1, "action": "identify_documents", "description": "List all missing documents", "gate": "auto"},
                {"order": 2, "action": "request_documents", "description": "Send request to responsible party", "gate": "auto"},
                {"order": 3, "action": "verify_receipt", "description": "Confirm documents received and valid", "gate": "human_approval"},
            ],
            "active": True,
            "version": 1,
        },
    ]

    playbook_ids = {}
    for pb_data in playbooks:
        existing = db.query(PlaybookModel).filter(PlaybookModel.tenant_id == tenant_id, PlaybookModel.name == pb_data["name"]).first()
        if existing:
            playbook_ids[pb_data["category"]] = existing.id
            logger.info(f"Playbook '{pb_data['name']}' already exists, skipping")
            continue

        pb = PlaybookModel(**pb_data)
        db.add(pb)
        playbook_ids[pb_data["category"]] = pb_data["id"]
        created["playbooks"] += 1
        logger.info(f"Created playbook: {pb_data['name']}")

    db.flush()

    # ==========================================================================
    # EXCEPTIONS
    # ==========================================================================
    now = datetime.utcnow()
    exceptions = [
        {
            "id": f"EXC-{uuid4()}",
            "tenant_id": tenant_id,
            "type": "RISK_THRESHOLD",
            "severity": "CRITICAL",
            "status": "OPEN",
            "summary": "Risk score exceeded critical threshold (92/100)",
            "notes": "ChainIQ detected multiple risk factors including Red Sea conflict zone transit and carrier reliability concerns.",
            "shipment_id": "SHP-2025-0042",
            "playbook_id": playbook_ids.get("RISK_THRESHOLD"),
            "owner_user_id": "op-001",
            "source": "CHAINIQ",
            "details": {"risk_score": 92, "factors": ["geopolitical", "carrier_reliability"]},
            "created_at": now - timedelta(hours=2),
            "updated_at": now - timedelta(minutes=30),
        },
        {
            "id": f"EXC-{uuid4()}",
            "tenant_id": tenant_id,
            "type": "PAYMENT_HOLD",
            "severity": "HIGH",
            "status": "IN_PROGRESS",
            "summary": "Settlement milestone 2 blocked - documentation pending",
            "notes": "ChainPay has placed a hold on the 30% in-transit release pending BoL verification.",
            "shipment_id": "SHP-2025-0038",
            "playbook_id": playbook_ids.get("PAYMENT_HOLD"),
            "owner_user_id": "op-002",
            "source": "CHAINPAY",
            "details": {"milestone": 2, "amount_held": 37500, "currency": "USD"},
            "created_at": now - timedelta(hours=6),
            "updated_at": now - timedelta(hours=1),
        },
        {
            "id": f"EXC-{uuid4()}",
            "tenant_id": tenant_id,
            "type": "ETA_BREACH",
            "severity": "HIGH",
            "status": "OPEN",
            "summary": "ETA slippage detected: +48h from original schedule",
            "notes": "Port congestion at Singapore has caused significant delay. Customer notification pending.",
            "shipment_id": "SHP-2025-0055",
            "source": "SYSTEM",
            "details": {"original_eta": "2025-12-10T14:00:00Z", "new_eta": "2025-12-12T14:00:00Z", "delay_hours": 48},
            "created_at": now - timedelta(hours=4),
            "updated_at": now - timedelta(hours=2),
        },
        {
            "id": f"EXC-{uuid4()}",
            "tenant_id": tenant_id,
            "type": "COMPLIANCE_FLAG",
            "severity": "MEDIUM",
            "status": "OPEN",
            "summary": "ESG compliance review required for carrier",
            "notes": "Carrier flagged for environmental compliance review based on recent audit findings.",
            "shipment_id": "SHP-2025-0061",
            "source": "CHAINIQ",
            "details": {"carrier_id": "CARR-001", "audit_date": "2025-11-15", "findings": ["emissions_reporting"]},
            "created_at": now - timedelta(hours=12),
            "updated_at": now - timedelta(hours=8),
        },
        {
            "id": f"EXC-{uuid4()}",
            "tenant_id": tenant_id,
            "type": "DOCUMENT_MISSING",
            "severity": "MEDIUM",
            "status": "OPEN",
            "summary": "Certificate of Origin missing for customs clearance",
            "notes": "Customs hold at destination port. COO required to release shipment.",
            "shipment_id": "SHP-2025-0048",
            "playbook_id": playbook_ids.get("DOCUMENT_MISSING"),
            "source": "INTEGRATION",
            "details": {"document_type": "COO", "customs_hold_id": "HOLD-2025-1234"},
            "created_at": now - timedelta(hours=18),
            "updated_at": now - timedelta(hours=6),
        },
        {
            "id": f"EXC-{uuid4()}",
            "tenant_id": tenant_id,
            "type": "IOT_ALERT",
            "severity": "LOW",
            "status": "RESOLVED",
            "summary": "Temperature deviation detected - within tolerance",
            "notes": "Reefer unit reported 2°C deviation. Monitoring continues, no action required.",
            "shipment_id": "SHP-2025-0033",
            "source": "IOT",
            "resolution_type": "AUTO_RESOLVED",
            "resolution_notes": "Temperature returned to normal range within 30 minutes",
            "resolved_at": now - timedelta(hours=1),
            "resolved_by": "SYSTEM",
            "details": {"sensor_id": "TEMP-001", "deviation_c": 2, "threshold_c": 5},
            "created_at": now - timedelta(hours=24),
            "updated_at": now - timedelta(hours=1),
        },
    ]

    exception_ids = []
    for exc_data in exceptions:
        existing = (
            db.query(ExceptionModel)
            .filter(
                ExceptionModel.tenant_id == tenant_id,
                ExceptionModel.shipment_id == exc_data["shipment_id"],
                ExceptionModel.type == exc_data["type"],
            )
            .first()
        )
        if existing:
            exception_ids.append(existing.id)
            logger.info(f"Exception for {exc_data['shipment_id']} ({exc_data['type']}) already exists, skipping")
            continue

        exc = ExceptionModel(**exc_data)
        db.add(exc)
        exception_ids.append(exc_data["id"])
        created["exceptions"] += 1
        logger.info(f"Created exception: {exc_data['summary'][:50]}...")

    db.flush()

    # ==========================================================================
    # DECISION RECORDS
    # ==========================================================================
    decisions = [
        {
            "id": f"DEC-{uuid4()}",
            "tenant_id": tenant_id,
            "type": "RISK_DECISION",
            "subtype": "SCORE_EVALUATION",
            "actor_type": "SYSTEM",
            "actor_id": "chainiq-risk-engine",
            "actor_name": "ChainIQ Risk Engine",
            "entity_type": "SHIPMENT",
            "entity_id": "SHP-2025-0042",
            "policy_id": "policy-risk-001",
            "outputs": {"risk_score": 92, "decision": "ESCALATE", "factors": ["geopolitical", "carrier"]},
            "explanation": "Risk score elevated to CRITICAL (92/100) - Red Sea transit + carrier risk factors",
            "primary_factors": ["Red Sea conflict zone", "Below-average carrier reliability"],
            "created_at": now - timedelta(hours=2),
        },
        {
            "id": f"DEC-{uuid4()}",
            "tenant_id": tenant_id,
            "type": "SETTLEMENT_DECISION",
            "subtype": "MILESTONE_HOLD",
            "actor_type": "SYSTEM",
            "actor_id": "chainpay-settlement-engine",
            "actor_name": "ChainPay Settlement Engine",
            "entity_type": "SHIPMENT",
            "entity_id": "SHP-2025-0038",
            "policy_id": "policy-settle-001",
            "outputs": {"milestone": 2, "action": "HOLD", "amount": 37500, "reason": "missing_bol"},
            "explanation": "HOLD: Milestone 2 (30% in-transit) pending BoL verification",
            "created_at": now - timedelta(hours=5),
        },
        {
            "id": f"DEC-{uuid4()}",
            "tenant_id": tenant_id,
            "type": "MANUAL_OVERRIDE",
            "subtype": "EXCEPTION_ASSIGNMENT",
            "actor_type": "USER",
            "actor_id": "op-002",
            "actor_name": "Sarah Finance",
            "entity_type": "EXCEPTION",
            "entity_id": exception_ids[1] if len(exception_ids) > 1 else None,  # Payment hold exception
            "outputs": {"action": "ASSIGN", "previous_owner": None, "new_owner": "op-002"},
            "explanation": "Exception assigned for manual review - awaiting shipper response",
            "created_at": now - timedelta(hours=4),
        },
        {
            "id": f"DEC-{uuid4()}",
            "tenant_id": tenant_id,
            "type": "EXCEPTION_RESOLUTION",
            "subtype": "AUTO_RESOLVED",
            "actor_type": "SYSTEM",
            "actor_id": "iot-monitor",
            "actor_name": "IoT Monitoring System",
            "entity_type": "EXCEPTION",
            "entity_id": exception_ids[5] if len(exception_ids) > 5 else None,  # IOT alert
            "outputs": {"resolution": "AUTO_RESOLVED", "reason": "temperature_normalized"},
            "explanation": "IoT alert resolved - temperature within acceptable range, monitoring continues",
            "created_at": now - timedelta(hours=1),
        },
        {
            "id": f"DEC-{uuid4()}",
            "tenant_id": tenant_id,
            "type": "AUTOMATED_ACTION",
            "subtype": "CUSTOMER_NOTIFICATION",
            "actor_type": "SYSTEM",
            "actor_id": "chainbridge-event-bus",
            "actor_name": "ChainBridge Event Bus",
            "entity_type": "SHIPMENT",
            "entity_id": "SHP-2025-0055",
            "outputs": {"action": "NOTIFY", "notification_type": "ETA_BREACH", "recipient": "customer"},
            "explanation": "ETA breach notification sent to customer (reference: CUST-NOTIFY-0055)",
            "created_at": now - timedelta(hours=3),
        },
    ]

    for dec_data in decisions:
        # Skip if entity_id is None (means the referenced exception wasn't created)
        if dec_data.get("entity_id") is None and dec_data.get("entity_type") == "EXCEPTION":
            continue

        existing = (
            db.query(DecisionRecordModel)
            .filter(DecisionRecordModel.tenant_id == tenant_id, DecisionRecordModel.explanation == dec_data["explanation"])
            .first()
        )
        if existing:
            logger.info(f"Decision '{dec_data['explanation'][:50]}...' already exists, skipping")
            continue

        dec = DecisionRecordModel(**dec_data)
        db.add(dec)
        created["decisions"] += 1
        logger.info(f"Created decision: {dec_data['type']} - {dec_data['explanation'][:40]}...")

    db.commit()

    logger.info(f"Seed complete: {created}")
    return created


def main():
    """Run seeding as a script."""
    from api.database import Base, SessionLocal, engine

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        result = seed_oc_data(db)
        print("\n✅ Seeding complete!")
        print(f"   Playbooks: {result['playbooks']}")
        print(f"   Exceptions: {result['exceptions']}")
        print(f"   Decisions: {result['decisions']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
