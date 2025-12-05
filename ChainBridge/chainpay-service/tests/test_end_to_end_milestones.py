"""
End-to-end integration tests for complete freight lifecycle.

Tests the entire flow from shipment creation through payment settlement:

1. Simulate ChainFreight emitting shipment events (PICKUP_CONFIRMED, POD_CONFIRMED, CLAIM_WINDOW_CLOSED)
2. ChainPay receives webhook events and creates MilestoneSettlements
3. Verify audit endpoints reflect correct milestone statuses and balances
4. Validate that settlements follow risk-based schedules (20/70/10 for LOW-risk)
5. Ensure all operations are deterministic and use in-memory SQLite

Lifecycle:
    Shipment Created (implicit)
      ↓
    FreightToken Created (risk_score=0.15 for LOW-risk)
      ↓
    PaymentIntent Created (amount=$1000, risk_tier=LOW)
      ↓
    PaymentSchedule Generated (20/70/10 split)
      ↓
    Event 1: PICKUP_CONFIRMED → MilestoneSettlement($200)
      ↓
    Event 2: POD_CONFIRMED → MilestoneSettlement($700)
      ↓
    Event 3: CLAIM_WINDOW_CLOSED → MilestoneSettlement($100)
      ↓
    Audit Endpoints Verify all 3 settlements
"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    MilestoneSettlement,
    PaymentIntent,
    PaymentSchedule,
    PaymentScheduleItem,
    PaymentStatus,
    RiskTier,
    ScheduleType,
)
from app.schedule_builder import RiskTierSchedule, build_default_schedule
from app.schemas import ShipmentEventWebhookRequest


class TestEndToEndFreightLifecycle:
    """
    Test complete freight lifecycle from shipment creation through settlement.

    This class models the real-world flow:
    1. Mock ChainFreight sends shipment events via webhook
    2. ChainPay processes events and creates milestone settlements
    3. Audit endpoints verify balances
    """

    def test_e2e_low_risk_freight_full_lifecycle(self, client: TestClient, db_session: Session):
        """
        Full lifecycle test: LOW-risk freight (0.15) with 20/70/10 split.

        Timeline:
        - Create PaymentIntent ($1000, LOW-risk)
        - Generate PaymentSchedule (20/70/10)
        - Emit PICKUP_CONFIRMED → $200 settlement
        - Emit POD_CONFIRMED → $700 settlement
        - Emit CLAIM_WINDOW_CLOSED → $100 settlement
        - Verify 3 MilestoneSettlements created
        - Verify audit endpoints show correct totals
        """
        # Step 1: Create PaymentIntent for LOW-risk freight token
        freight_token_id = 1001
        payment_amount = 1000.0

        payment_intent = PaymentIntent(
            freight_token_id=freight_token_id,
            amount=payment_amount,
            currency="USD",
            risk_score=0.15,  # LOW-risk
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(payment_intent)
        db_session.flush()
        payment_id = payment_intent.id

        # Step 2: Build payment schedule with 20/70/10 split
        schedule = PaymentSchedule(
            payment_intent_id=payment_id,
            schedule_type=ScheduleType.MILESTONE,
            risk_tier=RiskTier.LOW,
            created_at=datetime.utcnow(),
        )
        db_session.add(schedule)
        db_session.flush()

        # Add schedule items (20% PICKUP, 70% POD, 10% CLAIM_WINDOW_CLOSED)
        schedule_items_data = build_default_schedule(RiskTierSchedule.LOW)
        for item_data in schedule_items_data:
            schedule_item = PaymentScheduleItem(
                schedule_id=schedule.id,
                event_type=item_data["event_type"],
                percentage=item_data["percentage"],
                sequence=item_data["order"],
                created_at=datetime.utcnow(),
            )
            db_session.add(schedule_item)

        db_session.commit()

        # Step 3: Emit PICKUP_CONFIRMED event → should create $200 settlement
        pickup_event = ShipmentEventWebhookRequest(
            shipment_id=freight_token_id,
            event_type="PICKUP_CONFIRMED",
            occurred_at=datetime.utcnow(),
            event_id=1001,
        )

        response = client.post("/webhooks/shipment-events", json=pickup_event.model_dump(mode="json"))
        assert response.status_code == 200

        # Verify first milestone created
        db_session.refresh(payment_intent)
        milestones = db_session.query(MilestoneSettlement).filter(MilestoneSettlement.payment_intent_id == payment_id).all()
        assert len(milestones) == 1, "Expected 1 milestone after PICKUP_CONFIRMED"
        assert milestones[0].amount == 200.0, "Expected $200 for first milestone (20%)"
        assert milestones[0].status == PaymentStatus.APPROVED, "Expected APPROVED status"

        # Step 4: Emit POD_CONFIRMED event → should create $700 settlement
        pod_event = ShipmentEventWebhookRequest(
            shipment_id=freight_token_id,
            event_type="POD_CONFIRMED",
            occurred_at=datetime.utcnow(),
            event_id=1002,
        )

        response = client.post("/webhooks/shipment-events", json=pod_event.model_dump(mode="json"))
        assert response.status_code == 200

        # Verify second milestone created
        db_session.refresh(payment_intent)
        milestones = db_session.query(MilestoneSettlement).filter(MilestoneSettlement.payment_intent_id == payment_id).all()
        assert len(milestones) == 2, "Expected 2 milestones after POD_CONFIRMED"
        assert milestones[1].amount == 700.0, "Expected $700 for second milestone (70%)"
        assert milestones[1].status == PaymentStatus.APPROVED, "Expected APPROVED status"

        # Step 5: Emit CLAIM_WINDOW_CLOSED event → should create $100 settlement
        claim_event = ShipmentEventWebhookRequest(
            shipment_id=freight_token_id,
            event_type="CLAIM_WINDOW_CLOSED",
            occurred_at=datetime.utcnow(),
            event_id=1003,
        )

        response = client.post("/webhooks/shipment-events", json=claim_event.model_dump(mode="json"))
        assert response.status_code == 200

        # Verify all three milestones created
        db_session.refresh(payment_intent)
        milestones = (
            db_session.query(MilestoneSettlement)
            .filter(MilestoneSettlement.payment_intent_id == payment_id)
            .order_by(MilestoneSettlement.created_at)
            .all()
        )
        assert len(milestones) == 3, "Expected 3 milestones after all events"
        assert milestones[2].amount == 100.0, "Expected $100 for third milestone (10%)"
        assert milestones[2].status == PaymentStatus.APPROVED, "Expected APPROVED status"

        # Verify total settlements = original amount
        total_settled = sum(m.amount for m in milestones)
        assert total_settled == 1000.0, f"Expected $1000 total, got ${total_settled}"

    def test_e2e_medium_risk_freight_lifecycle(self, client: TestClient, db_session: Session):
        """
        Full lifecycle test: MEDIUM-risk freight (0.50) with 10/70/20 split.

        Verifies different risk tier produces different schedule.
        """
        freight_token_id = 2001
        payment_amount = 2000.0

        # Create MEDIUM-risk payment intent
        payment_intent = PaymentIntent(
            freight_token_id=freight_token_id,
            amount=payment_amount,
            currency="USD",
            risk_score=0.50,  # MEDIUM-risk
            risk_tier=RiskTier.MEDIUM,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(payment_intent)
        db_session.flush()
        payment_id = payment_intent.id

        # Build MEDIUM-risk schedule (10/70/20)
        schedule = PaymentSchedule(
            payment_intent_id=payment_id,
            schedule_type=ScheduleType.MILESTONE,
            risk_tier=RiskTier.MEDIUM,
            created_at=datetime.utcnow(),
        )
        db_session.add(schedule)
        db_session.flush()

        schedule_items_data = build_default_schedule(RiskTierSchedule.MEDIUM)
        for item_data in schedule_items_data:
            schedule_item = PaymentScheduleItem(
                schedule_id=schedule.id,
                event_type=item_data["event_type"],
                percentage=item_data["percentage"],
                sequence=item_data["order"],
                created_at=datetime.utcnow(),
            )
            db_session.add(schedule_item)

        db_session.commit()

        # Emit all three events
        events = [
            ("PICKUP_CONFIRMED", 200.0),  # 10% of $2000
            ("POD_CONFIRMED", 1400.0),  # 70% of $2000
            ("CLAIM_WINDOW_CLOSED", 400.0),  # 20% of $2000
        ]

        for event_type, expected_amount in events:
            event = ShipmentEventWebhookRequest(
                shipment_id=freight_token_id,
                event_type=event_type,
                occurred_at=datetime.utcnow(),
                event_id=None,
            )
            response = client.post("/webhooks/shipment-events", json=event.model_dump(mode="json"))
            assert response.status_code == 200

        # Verify all three milestones with correct amounts
        db_session.refresh(payment_intent)
        milestones = (
            db_session.query(MilestoneSettlement)
            .filter(MilestoneSettlement.payment_intent_id == payment_id)
            .order_by(MilestoneSettlement.created_at)
            .all()
        )

        assert len(milestones) == 3, "Expected 3 milestones"
        assert abs(milestones[0].amount - 200.0) < 0.01, "Expected $200 (10%) for PICKUP"
        assert abs(milestones[1].amount - 1400.0) < 0.01, "Expected $1400 (70%) for POD"
        assert abs(milestones[2].amount - 400.0) < 0.01, "Expected $400 (20%) for CLAIM_WINDOW"

        total_settled = sum(m.amount for m in milestones)
        assert abs(total_settled - 2000.0) < 0.01, f"Expected $2000 total, got ${total_settled}"

    def test_e2e_high_risk_freight_lifecycle(self, client: TestClient, db_session: Session):
        """
        Full lifecycle test: HIGH-risk freight (0.85) with 0/80/20 split.

        Verifies HIGH-risk tier skips PICKUP payment entirely.
        """
        freight_token_id = 3001
        payment_amount = 3000.0

        # Create HIGH-risk payment intent
        payment_intent = PaymentIntent(
            freight_token_id=freight_token_id,
            amount=payment_amount,
            currency="USD",
            risk_score=0.85,  # HIGH-risk
            risk_tier=RiskTier.HIGH,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(payment_intent)
        db_session.flush()
        payment_id = payment_intent.id

        # Build HIGH-risk schedule (0/80/20)
        schedule = PaymentSchedule(
            payment_intent_id=payment_id,
            schedule_type=ScheduleType.MILESTONE,
            risk_tier=RiskTier.HIGH,
            created_at=datetime.utcnow(),
        )
        db_session.add(schedule)
        db_session.flush()

        schedule_items_data = build_default_schedule(RiskTierSchedule.HIGH)
        for item_data in schedule_items_data:
            schedule_item = PaymentScheduleItem(
                schedule_id=schedule.id,
                event_type=item_data["event_type"],
                percentage=item_data["percentage"],
                sequence=item_data["order"],
                created_at=datetime.utcnow(),
            )
            db_session.add(schedule_item)

        db_session.commit()

        # Emit PICKUP_CONFIRMED (should create $0 settlement)
        pickup_event = ShipmentEventWebhookRequest(
            shipment_id=freight_token_id,
            event_type="PICKUP_CONFIRMED",
            occurred_at=datetime.utcnow(),
            event_id=None,
        )
        response = client.post("/webhooks/shipment-events", json=pickup_event.dict())
        assert response.status_code == 200

        # Verify first milestone has 0% amount
        db_session.refresh(payment_intent)
        milestones = db_session.query(MilestoneSettlement).filter(MilestoneSettlement.payment_intent_id == payment_id).all()
        assert len(milestones) == 1
        assert milestones[0].amount == 0.0, "Expected $0 for HIGH-risk PICKUP (0%)"

        # Emit POD_CONFIRMED (should create $2400 settlement - 80%)
        pod_event = ShipmentEventWebhookRequest(
            shipment_id=freight_token_id,
            event_type="POD_CONFIRMED",
            occurred_at=datetime.utcnow(),
            event_id=None,
        )
        response = client.post("/webhooks/shipment-events", json=pod_event.dict())
        assert response.status_code == 200

        # Emit CLAIM_WINDOW_CLOSED (should create $600 settlement - 20%)
        claim_event = ShipmentEventWebhookRequest(
            shipment_id=freight_token_id,
            event_type="CLAIM_WINDOW_CLOSED",
            occurred_at=datetime.utcnow(),
            event_id=None,
        )
        response = client.post("/webhooks/shipment-events", json=claim_event.dict())
        assert response.status_code == 200

        # Verify all three milestones with correct split
        db_session.refresh(payment_intent)
        milestones = (
            db_session.query(MilestoneSettlement)
            .filter(MilestoneSettlement.payment_intent_id == payment_id)
            .order_by(MilestoneSettlement.created_at)
            .all()
        )

        assert len(milestones) == 3, "Expected 3 milestones"
        assert milestones[0].amount == 0.0, "Expected $0 (0%) for PICKUP"
        assert milestones[1].amount == 2400.0, "Expected $2400 (80%) for POD"
        assert milestones[2].amount == 600.0, "Expected $600 (20%) for CLAIM_WINDOW"

    def test_e2e_idempotency_duplicate_events_ignored(self, client: TestClient, db_session: Session):
        """
        Verify idempotency: sending same event twice creates only 1 milestone.

        This ensures the unique constraint on (payment_intent_id, event_type)
        prevents duplicate settlements.
        """
        freight_token_id = 4001

        payment_intent = PaymentIntent(
            freight_token_id=freight_token_id,
            amount=1000.0,
            currency="USD",
            risk_score=0.20,
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(payment_intent)
        db_session.flush()
        payment_id = payment_intent.id

        schedule = PaymentSchedule(
            payment_intent_id=payment_id,
            schedule_type=ScheduleType.MILESTONE,
            risk_tier=RiskTier.LOW,
            created_at=datetime.utcnow(),
        )
        db_session.add(schedule)
        db_session.flush()

        schedule_items_data = build_default_schedule(RiskTierSchedule.LOW)
        for item_data in schedule_items_data:
            schedule_item = PaymentScheduleItem(
                schedule_id=schedule.id,
                event_type=item_data["event_type"],
                percentage=item_data["percentage"],
                sequence=item_data["order"],
                created_at=datetime.utcnow(),
            )
            db_session.add(schedule_item)

        db_session.commit()

        # Send PICKUP_CONFIRMED twice
        event1 = ShipmentEventWebhookRequest(
            shipment_id=freight_token_id,
            event_type="PICKUP_CONFIRMED",
            occurred_at=datetime.utcnow(),
            event_id=1,
        )

        # First attempt succeeds
        response1 = client.post("/webhooks/shipment-events", json=event1.model_dump(mode="json"))
        assert response1.status_code == 200

        # Second attempt (duplicate) should also succeed (idempotent)
        response2 = client.post("/webhooks/shipment-events", json=event1.model_dump(mode="json"))
        assert response2.status_code in [
            200,
            409,
        ], "Duplicate event should be idempotent"

        # Verify only 1 milestone created despite 2 requests
        db_session.refresh(payment_intent)
        milestones = (
            db_session.query(MilestoneSettlement)
            .filter(
                MilestoneSettlement.payment_intent_id == payment_id,
                MilestoneSettlement.event_type == "PICKUP_CONFIRMED",
            )
            .all()
        )
        assert len(milestones) == 1, "Expected exactly 1 milestone for PICKUP_CONFIRMED"

    def test_e2e_audit_endpoints_verify_balances(self, client: TestClient, db_session: Session):
        """
        Verify audit endpoints report correct settlement balances.

        Tests:
        - GET /audit/shipments/{shipment_id} returns all milestones
        - GET /audit/payment_intents/{intent_id}/milestones returns correct details
        - Summary calculations match actual settlements
        """
        freight_token_id = 5001
        payment_amount = 5000.0

        payment_intent = PaymentIntent(
            freight_token_id=freight_token_id,
            amount=payment_amount,
            currency="USD",
            risk_score=0.15,
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(payment_intent)
        db_session.flush()
        payment_id = payment_intent.id

        schedule = PaymentSchedule(
            payment_intent_id=payment_id,
            schedule_type=ScheduleType.MILESTONE,
            risk_tier=RiskTier.LOW,
            created_at=datetime.utcnow(),
        )
        db_session.add(schedule)
        db_session.flush()

        schedule_items_data = build_default_schedule(RiskTierSchedule.LOW)
        for item_data in schedule_items_data:
            schedule_item = PaymentScheduleItem(
                schedule_id=schedule.id,
                event_type=item_data["event_type"],
                percentage=item_data["percentage"],
                sequence=item_data["order"],
                created_at=datetime.utcnow(),
            )
            db_session.add(schedule_item)

        db_session.commit()

        # Emit all events
        for i, event_type in enumerate(["PICKUP_CONFIRMED", "POD_CONFIRMED", "CLAIM_WINDOW_CLOSED"]):
            event = ShipmentEventWebhookRequest(
                shipment_id=freight_token_id,
                event_type=event_type,
                occurred_at=datetime.utcnow(),
                event_id=i + 1,
            )
            client.post("/webhooks/shipment-events", json=event.model_dump(mode="json"))

        # Test audit shipments endpoint
        audit_response = client.get(f"/audit/shipments/{freight_token_id}")
        assert audit_response.status_code == 200
        data = audit_response.json()

        assert "milestones" in data, "Audit response should include milestones"
        assert len(data["milestones"]) == 3, "Should have 3 milestones"
        providers = {m["provider"] for m in data["milestones"]}
        assert providers == {"INTERNAL_LEDGER"}

        # Verify summary
        assert "summary" in data
        summary = data["summary"]
        expected_approved = 5000.0
        assert abs(summary.get("total_approved", 0) - expected_approved) < 0.01

        # Test payment intents audit endpoint
        intent_response = client.get(f"/audit/payment_intents/{payment_id}/milestones")
        assert intent_response.status_code == 200
        intent_data = intent_response.json()

        assert "milestones" in intent_data, "Intent audit response should include milestones"
        assert len(intent_data["milestones"]) == 3, "Should have 3 milestones"
        assert "payment_intent" in intent_data, "Should include payment intent details"

    def test_e2e_currency_handling_usd_eur(self, client: TestClient, db_session: Session):
        """
        Verify multi-currency support: USD and EUR settlements.
        """
        freight_token_id = 6001

        # Create EUR payment intent
        payment_intent = PaymentIntent(
            freight_token_id=freight_token_id,
            amount=1000.0,
            currency="EUR",
            risk_score=0.15,
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(payment_intent)
        db_session.flush()
        payment_id = payment_intent.id

        schedule = PaymentSchedule(
            payment_intent_id=payment_id,
            schedule_type=ScheduleType.MILESTONE,
            risk_tier=RiskTier.LOW,
            created_at=datetime.utcnow(),
        )
        db_session.add(schedule)
        db_session.flush()

        schedule_items_data = build_default_schedule(RiskTierSchedule.LOW)
        for item_data in schedule_items_data:
            schedule_item = PaymentScheduleItem(
                schedule_id=schedule.id,
                event_type=item_data["event_type"],
                percentage=item_data["percentage"],
                sequence=item_data["order"],
                created_at=datetime.utcnow(),
            )
            db_session.add(schedule_item)

        db_session.commit()

        # Emit event
        event = ShipmentEventWebhookRequest(
            shipment_id=freight_token_id,
            event_type="PICKUP_CONFIRMED",
            occurred_at=datetime.utcnow(),
            event_id=1,
        )
        response = client.post("/webhooks/shipment-events", json=event.model_dump(mode="json"))
        assert response.status_code == 200

        # Verify milestone has correct currency
        db_session.refresh(payment_intent)
        milestone = db_session.query(MilestoneSettlement).filter(MilestoneSettlement.payment_intent_id == payment_id).first()
        assert milestone is not None
        assert milestone.currency == "EUR", "Milestone should preserve EUR currency"
        assert abs(milestone.amount - 200.0) < 0.01, "Expected €200 (20%) for PICKUP"

    def test_e2e_sequential_multiple_intents(self, client: TestClient, db_session: Session):
        """
        Test multiple independent freight tokens/payment intents in sequence.

        Ensures no cross-contamination between different shipments.
        """
        intents = []

        # Create 3 independent payment intents
        for i, (freight_id, amount, risk_score) in enumerate(
            [
                (7001, 1000.0, 0.15),  # LOW
                (7002, 2000.0, 0.50),  # MEDIUM
                (7003, 3000.0, 0.85),  # HIGH
            ]
        ):
            payment_intent = PaymentIntent(
                freight_token_id=freight_id,
                amount=amount,
                currency="USD",
                risk_score=risk_score,
                risk_tier=(RiskTier.LOW if risk_score < 0.33 else (RiskTier.MEDIUM if risk_score < 0.67 else RiskTier.HIGH)),
                status=PaymentStatus.PENDING,
                created_at=datetime.utcnow(),
            )
            db_session.add(payment_intent)
            db_session.flush()

            schedule = PaymentSchedule(
                payment_intent_id=payment_intent.id,
                schedule_type=ScheduleType.MILESTONE,
                risk_tier=(RiskTier.LOW if risk_score < 0.33 else (RiskTier.MEDIUM if risk_score < 0.67 else RiskTier.HIGH)),
                created_at=datetime.utcnow(),
            )
            db_session.add(schedule)
            db_session.flush()

            tier = RiskTierSchedule.LOW if risk_score < 0.33 else (RiskTierSchedule.MEDIUM if risk_score < 0.67 else RiskTierSchedule.HIGH)
            schedule_items_data = build_default_schedule(tier)
            for item_data in schedule_items_data:
                schedule_item = PaymentScheduleItem(
                    schedule_id=schedule.id,
                    event_type=item_data["event_type"],
                    percentage=item_data["percentage"],
                    sequence=item_data["order"],
                    created_at=datetime.utcnow(),
                )
                db_session.add(schedule_item)

            intents.append((freight_id, payment_intent.id, amount))

        db_session.commit()

        # Emit POD_CONFIRMED for each intent
        for i, (freight_id, payment_id, amount) in enumerate(intents):
            event = ShipmentEventWebhookRequest(
                shipment_id=freight_id,
                event_type="POD_CONFIRMED",
                occurred_at=datetime.utcnow(),
                event_id=i + 1,
            )
            response = client.post("/webhooks/shipment-events", json=event.model_dump(mode="json"))
            assert response.status_code == 200

        # Verify each intent has independent settlements
        for freight_id, payment_id, amount in intents:
            milestones = db_session.query(MilestoneSettlement).filter(MilestoneSettlement.payment_intent_id == payment_id).all()
            assert len(milestones) == 1, f"Expected 1 milestone for intent {payment_id}"

            # Verify amount matches expected percentage based on risk
            if freight_id == 7001:  # LOW: 70%
                assert abs(milestones[0].amount - (1000.0 * 0.70)) < 0.01
            elif freight_id == 7002:  # MEDIUM: 70%
                assert abs(milestones[0].amount - (2000.0 * 0.70)) < 0.01
            else:  # HIGH: 80%
                assert abs(milestones[0].amount - (3000.0 * 0.80)) < 0.01
