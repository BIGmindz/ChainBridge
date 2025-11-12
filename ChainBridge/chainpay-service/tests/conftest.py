"""
Pytest fixtures and configuration for ChainPay Smart Settlements tests.

Provides:
- In-memory SQLite database for test isolation
- FastAPI TestClient for HTTP testing
- Database session fixtures
- Mock payment intent and freight token factories
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app, get_db
from app.models import Base, PaymentIntent, PaymentSchedule, RiskTier, PaymentStatus, ScheduleType, PaymentScheduleItem


# In-memory SQLite for tests
SQLALCHEMY_TEST_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def engine():
    """Create a fresh test database engine for each test function."""
    engine = create_engine(
        SQLALCHEMY_TEST_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(engine) -> Session:
    """Provide a fresh database session for each test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client(db_session: Session):
    """Provide FastAPI TestClient with test database session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def payment_intent_low_risk(db_session: Session) -> PaymentIntent:
    """Create a LOW-risk payment intent for testing."""
    intent = PaymentIntent(
        freight_token_id=101,
        amount=1000.0,
        currency="USD",
        description="Test LOW-risk shipment",
        risk_score=0.15,  # LOW tier
        risk_category="low",
        risk_tier=RiskTier.LOW,
        status=PaymentStatus.PENDING,
        created_at=datetime.utcnow(),
    )
    db_session.add(intent)
    db_session.commit()
    db_session.refresh(intent)
    return intent


@pytest.fixture
def payment_intent_medium_risk(db_session: Session) -> PaymentIntent:
    """Create a MEDIUM-risk payment intent for testing."""
    intent = PaymentIntent(
        freight_token_id=102,
        amount=2000.0,
        currency="USD",
        description="Test MEDIUM-risk shipment",
        risk_score=0.50,  # MEDIUM tier
        risk_category="medium",
        risk_tier=RiskTier.MEDIUM,
        status=PaymentStatus.PENDING,
        created_at=datetime.utcnow(),
    )
    db_session.add(intent)
    db_session.commit()
    db_session.refresh(intent)
    return intent


@pytest.fixture
def payment_intent_high_risk(db_session: Session) -> PaymentIntent:
    """Create a HIGH-risk payment intent for testing."""
    intent = PaymentIntent(
        freight_token_id=103,
        amount=3000.0,
        currency="USD",
        description="Test HIGH-risk shipment",
        risk_score=0.85,  # HIGH tier
        risk_category="high",
        risk_tier=RiskTier.HIGH,
        status=PaymentStatus.PENDING,
        created_at=datetime.utcnow(),
    )
    db_session.add(intent)
    db_session.commit()
    db_session.refresh(intent)
    return intent


@pytest.fixture
def payment_schedule_low_risk(db_session: Session, payment_intent_low_risk: PaymentIntent) -> PaymentSchedule:
    """Create a LOW-risk payment schedule (20/70/10) for testing."""
    schedule = PaymentSchedule(
        payment_intent_id=payment_intent_low_risk.id,
        schedule_type=ScheduleType.MILESTONE,
        description="LOW-risk milestone schedule: 20% PICKUP / 70% POD / 10% CLAIM",
        risk_tier=RiskTier.LOW,
        created_at=datetime.utcnow(),
    )
    db_session.add(schedule)
    db_session.flush()

    # Add schedule items
    items = [
        PaymentScheduleItem(
            schedule_id=schedule.id,
            event_type="PICKUP_CONFIRMED",
            percentage=0.20,
            sequence=1,
            created_at=datetime.utcnow(),
        ),
        PaymentScheduleItem(
            schedule_id=schedule.id,
            event_type="POD_CONFIRMED",
            percentage=0.70,
            sequence=2,
            created_at=datetime.utcnow(),
        ),
        PaymentScheduleItem(
            schedule_id=schedule.id,
            event_type="CLAIM_WINDOW_CLOSED",
            percentage=0.10,
            sequence=3,
            created_at=datetime.utcnow(),
        ),
    ]
    db_session.add_all(items)
    db_session.commit()
    db_session.refresh(schedule)
    return schedule


@pytest.fixture
def payment_schedule_high_risk(db_session: Session, payment_intent_high_risk: PaymentIntent) -> PaymentSchedule:
    """Create a HIGH-risk payment schedule (0/80/20) for testing."""
    schedule = PaymentSchedule(
        payment_intent_id=payment_intent_high_risk.id,
        schedule_type=ScheduleType.MILESTONE,
        description="HIGH-risk milestone schedule: 0% PICKUP / 80% POD / 20% CLAIM",
        risk_tier=RiskTier.HIGH,
        created_at=datetime.utcnow(),
    )
    db_session.add(schedule)
    db_session.flush()

    # Add schedule items
    items = [
        PaymentScheduleItem(
            schedule_id=schedule.id,
            event_type="PICKUP_CONFIRMED",
            percentage=0.0,
            sequence=1,
            created_at=datetime.utcnow(),
        ),
        PaymentScheduleItem(
            schedule_id=schedule.id,
            event_type="POD_CONFIRMED",
            percentage=0.80,
            sequence=2,
            created_at=datetime.utcnow(),
        ),
        PaymentScheduleItem(
            schedule_id=schedule.id,
            event_type="CLAIM_WINDOW_CLOSED",
            percentage=0.20,
            sequence=3,
            created_at=datetime.utcnow(),
        ),
    ]
    db_session.add_all(items)
    db_session.commit()
    db_session.refresh(schedule)
    return schedule
