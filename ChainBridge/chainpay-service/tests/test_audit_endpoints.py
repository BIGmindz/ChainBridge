"""
Integration tests for audit endpoints.

Tests:
- GET /audit/shipments/{shipment_id}: Returns all milestone settlements for a shipment
- GET /audit/payment_intents/{payment_id}/milestones: Returns milestones for a payment intent
- 200 status for existing resources
- 404 status for missing resources
- Correct calculation of summary statistics (approved/settled amounts, counts)
"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import MilestoneSettlement, PaymentIntent, PaymentStatus, RiskTier


class TestAuditShipmentsEndpoint:
    """Test GET /audit/shipments/{shipment_id} endpoint."""

    def test_audit_shipments_returns_200_for_existing_shipment(self, client: TestClient, db_session: Session):
        """Audit shipments endpoint should return 200 for existing shipment."""
        # Create payment intent (representing a shipment in ChainPay)
        intent = PaymentIntent(
            freight_token_id=101,
            amount=1000.0,
            currency="USD",
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        response = client.get(f"/audit/shipments/{intent.freight_token_id}")
        assert response.status_code == 200

    def test_audit_shipments_returns_404_for_nonexistent_shipment(self, client: TestClient):
        """Audit shipments endpoint should return 404 for nonexistent shipment."""
        response = client.get("/audit/shipments/99999")
        assert response.status_code == 404

    def test_audit_shipments_response_structure(self, client: TestClient, db_session: Session):
        """Audit shipments response should have expected structure."""
        intent = PaymentIntent(
            freight_token_id=102,
            amount=1000.0,
            currency="USD",
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        response = client.get(f"/audit/shipments/{intent.freight_token_id}")
        data = response.json()

        assert "shipment_id" in data
        assert "milestones" in data
        assert "summary" in data

    def test_audit_shipments_includes_all_milestones(self, client: TestClient, db_session: Session):
        """Audit shipments should include all milestones for shipment."""
        intent = PaymentIntent(
            freight_token_id=103,
            amount=1000.0,
            currency="USD",
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        # Add multiple milestones
        for i, event in enumerate(["PICKUP_CONFIRMED", "POD_CONFIRMED", "CLAIM_WINDOW_CLOSED"]):
            milestone = MilestoneSettlement(
                payment_intent_id=intent.id,
                event_type=event,
                amount=1000.0 * (0.2 if i == 0 else 0.7 if i == 1 else 0.1),
                currency="USD",
                status=PaymentStatus.PENDING,
                created_at=datetime.utcnow(),
            )
            db_session.add(milestone)
        db_session.commit()

        response = client.get(f"/audit/shipments/{intent.freight_token_id}")
        data = response.json()

        assert len(data["milestones"]) == 3

    def test_audit_shipments_summary_calculations(self, client: TestClient, db_session: Session):
        """Audit shipments summary should correctly calculate amounts."""
        intent = PaymentIntent(
            freight_token_id=104,
            amount=1000.0,
            currency="USD",
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        # Add milestones with different statuses
        milestone1 = MilestoneSettlement(
            payment_intent_id=intent.id,
            event_type="PICKUP_CONFIRMED",
            amount=200.0,
            currency="USD",
            status=PaymentStatus.APPROVED,
            created_at=datetime.utcnow(),
        )
        milestone2 = MilestoneSettlement(
            payment_intent_id=intent.id,
            event_type="POD_CONFIRMED",
            amount=700.0,
            currency="USD",
            status=PaymentStatus.SETTLED,
            created_at=datetime.utcnow(),
        )
        milestone3 = MilestoneSettlement(
            payment_intent_id=intent.id,
            event_type="CLAIM_WINDOW_CLOSED",
            amount=100.0,
            currency="USD",
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add_all([milestone1, milestone2, milestone3])
        db_session.commit()

        response = client.get(f"/audit/shipments/{intent.freight_token_id}")
        data = response.json()
        summary = data["summary"]

        assert summary.get("total_approved_amount") == 200.0
        assert summary.get("total_settled_amount") == 700.0


class TestAuditPaymentIntentsEndpoint:
    """Test GET /audit/payment_intents/{payment_id}/milestones endpoint."""

    def test_audit_payment_intents_returns_200_for_existing_intent(self, client: TestClient, db_session: Session):
        """Audit payment intents endpoint should return 200 for existing intent."""
        intent = PaymentIntent(
            freight_token_id=201,
            amount=2000.0,
            currency="USD",
            risk_tier=RiskTier.MEDIUM,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        response = client.get(f"/audit/payment_intents/{intent.id}/milestones")
        assert response.status_code == 200

    def test_audit_payment_intents_returns_404_for_nonexistent_intent(self, client: TestClient):
        """Audit payment intents endpoint should return 404 for nonexistent intent."""
        response = client.get("/audit/payment_intents/99999/milestones")
        assert response.status_code == 404

    def test_audit_payment_intents_response_structure(self, client: TestClient, db_session: Session):
        """Audit payment intents response should have expected structure."""
        intent = PaymentIntent(
            freight_token_id=202,
            amount=2000.0,
            currency="USD",
            risk_tier=RiskTier.MEDIUM,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        response = client.get(f"/audit/payment_intents/{intent.id}/milestones")
        data = response.json()

        assert "payment_intent" in data
        assert "milestones" in data
        assert "summary" in data

    def test_audit_payment_intents_includes_intent_details(self, client: TestClient, db_session: Session):
        """Audit payment intents response should include payment intent details."""
        intent = PaymentIntent(
            freight_token_id=203,
            amount=3000.0,
            currency="EUR",
            risk_tier=RiskTier.HIGH,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        response = client.get(f"/audit/payment_intents/{intent.id}/milestones")
        data = response.json()
        payment_intent = data["payment_intent"]

        assert payment_intent["id"] == intent.id
        assert payment_intent["amount"] == 3000.0
        assert payment_intent["currency"] == "EUR"

    def test_audit_payment_intents_includes_all_milestones(self, client: TestClient, db_session: Session):
        """Audit payment intents should include all milestones."""
        intent = PaymentIntent(
            freight_token_id=204,
            amount=2500.0,
            currency="USD",
            risk_tier=RiskTier.MEDIUM,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        # Add multiple milestones
        for i, event in enumerate(["PICKUP_CONFIRMED", "POD_CONFIRMED", "CLAIM_WINDOW_CLOSED"]):
            milestone = MilestoneSettlement(
                payment_intent_id=intent.id,
                event_type=event,
                amount=2500.0 * (0.1 if i == 0 else 0.8 if i == 1 else 0.1),
                currency="USD",
                status=PaymentStatus.PENDING,
                created_at=datetime.utcnow(),
            )
            db_session.add(milestone)
        db_session.commit()

        response = client.get(f"/audit/payment_intents/{intent.id}/milestones")
        data = response.json()

        assert len(data["milestones"]) == 3

    def test_audit_payment_intents_summary_calculations(self, client: TestClient, db_session: Session):
        """Audit payment intents summary should correctly calculate amounts."""
        intent = PaymentIntent(
            freight_token_id=205,
            amount=5000.0,
            currency="USD",
            risk_tier=RiskTier.HIGH,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        # Add milestones with different statuses
        milestone1 = MilestoneSettlement(
            payment_intent_id=intent.id,
            event_type="PICKUP_CONFIRMED",
            amount=0.0,
            currency="USD",
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        milestone2 = MilestoneSettlement(
            payment_intent_id=intent.id,
            event_type="POD_CONFIRMED",
            amount=4000.0,
            currency="USD",
            status=PaymentStatus.APPROVED,
            created_at=datetime.utcnow(),
        )
        milestone3 = MilestoneSettlement(
            payment_intent_id=intent.id,
            event_type="CLAIM_WINDOW_CLOSED",
            amount=1000.0,
            currency="USD",
            status=PaymentStatus.SETTLED,
            created_at=datetime.utcnow(),
        )
        db_session.add_all([milestone1, milestone2, milestone3])
        db_session.commit()

        response = client.get(f"/audit/payment_intents/{intent.id}/milestones")
        data = response.json()
        summary = data["summary"]

        assert summary.get("total_approved_amount") == 4000.0
        assert summary.get("total_settled_amount") == 1000.0


class TestAuditEndpointsEmptyStates:
    """Test audit endpoints with empty/zero data."""

    def test_audit_shipments_with_no_milestones(self, client: TestClient, db_session: Session):
        """Audit shipments should handle shipment with no milestones."""
        intent = PaymentIntent(
            freight_token_id=301,
            amount=1000.0,
            currency="USD",
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        response = client.get(f"/audit/shipments/{intent.freight_token_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["milestones"]) == 0

    def test_audit_payment_intents_with_no_milestones(self, client: TestClient, db_session: Session):
        """Audit payment intents should handle intent with no milestones."""
        intent = PaymentIntent(
            freight_token_id=302,
            amount=2000.0,
            currency="USD",
            risk_tier=RiskTier.MEDIUM,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        response = client.get(f"/audit/payment_intents/{intent.id}/milestones")
        assert response.status_code == 200
        data = response.json()
        assert len(data["milestones"]) == 0

    def test_audit_shipments_all_pending_status(self, client: TestClient, db_session: Session):
        """Audit shipments should handle all milestones with PENDING status."""
        intent = PaymentIntent(
            freight_token_id=303,
            amount=1500.0,
            currency="USD",
            risk_tier=RiskTier.MEDIUM,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        for event in ["PICKUP_CONFIRMED", "POD_CONFIRMED", "CLAIM_WINDOW_CLOSED"]:
            milestone = MilestoneSettlement(
                payment_intent_id=intent.id,
                event_type=event,
                amount=500.0,
                currency="USD",
                status=PaymentStatus.PENDING,
                created_at=datetime.utcnow(),
            )
            db_session.add(milestone)
        db_session.commit()

        response = client.get(f"/audit/shipments/{intent.freight_token_id}")
        data = response.json()
        summary = data["summary"]

        assert summary.get("total_approved_amount", 0) == 0
        assert summary.get("total_settled_amount", 0) == 0


class TestAuditEndpointsCrossCurrency:
    """Test audit endpoints with mixed currencies."""

    def test_audit_shipments_mixed_currencies(self, client: TestClient, db_session: Session):
        """Audit shipments should handle milestones with different currencies."""
        intent = PaymentIntent(
            freight_token_id=401,
            amount=1000.0,
            currency="USD",
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db_session.add(intent)
        db_session.commit()

        # Add milestones with different currencies
        currencies = ["USD", "EUR", "GBP"]
        for i, currency in enumerate(currencies):
            milestone = MilestoneSettlement(
                payment_intent_id=intent.id,
                event_type=f"EVENT_{i}",
                amount=300.0,
                currency=currency,
                status=PaymentStatus.PENDING,
                created_at=datetime.utcnow(),
            )
            db_session.add(milestone)
        db_session.commit()

        response = client.get(f"/audit/shipments/{intent.freight_token_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["milestones"]) == 3
