"""
Pytest fixtures and configuration for ChainPay Smart Settlements tests.

Provides:
- In-memory SQLite database for test isolation
- FastAPI TestClient for HTTP testing
- Database session fixtures
- Mock payment intent and freight token factories
"""

import importlib.util
import sys
import types
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure the ChainPay service package is the one that resolves as `app`
SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
_ORIGINAL_APP = sys.modules.get("app")
sys.modules.pop("app", None)
# Force-load the local app package so later imports resolve correctly
app_init = SERVICE_ROOT / "app" / "__init__.py"
spec = importlib.util.spec_from_file_location("app", app_init)
module = importlib.util.module_from_spec(spec)
sys.modules["app"] = module
assert spec.loader is not None
spec.loader.exec_module(module)
# Also ensure Base is exposed on app.models for test imports
try:
    import app.models as _app_models  # type: ignore
    from chainpay_service.app.models import Base as _ChainpayBase  # type: ignore

    _app_models.Base = _ChainpayBase  # type: ignore[attr-defined]
except Exception:
    pass
import chainpay_service.app.database as _cp_db  # type: ignore

# Ensure app submodules point to ChainPay implementations for this test session
import chainpay_service.app.models as _cp_models  # type: ignore
import chainpay_service.app.schemas as _cp_schemas  # type: ignore

sys.modules["app.models"] = _cp_models
sys.modules["app.database"] = _cp_db
sys.modules["app.schemas"] = _cp_schemas
sys.modules["app.services"] = importlib.import_module("chainpay_service.app.services")
# expose ShipmentEventWebhookRequest directly for tests that import from app.schemas
try:
    sys.modules["app.schemas"].ShipmentEventWebhookRequest = _cp_schemas.ShipmentEventWebhookRequest  # type: ignore[attr-defined]
except Exception:
    pass
# Ensure app.models points at the ChainPay models module for imports
import chainpay_service.app.models as _cp_models  # type: ignore

sys.modules["app.models"] = _cp_models

# Provide lightweight fallbacks for optional Kafka dependency
fake_aiokafka = sys.modules.get("aiokafka") or types.ModuleType("aiokafka")


class _NoopConsumer:  # pragma: no cover - simple shim
    def __init__(self, *args, **kwargs):
        pass

    async def start(self):
        return None

    async def stop(self):
        return None


class _NoopProducer(_NoopConsumer):
    async def send_and_wait(self, *args, **kwargs):
        return None


fake_aiokafka.AIOKafkaConsumer = _NoopConsumer
fake_aiokafka.AIOKafkaProducer = _NoopProducer
# Alias for older import style
fake_aiokafka.consumer = fake_aiokafka
fake_aiokafka.producer = fake_aiokafka
sys.modules["aiokafka"] = fake_aiokafka

# Provide a stub ml_engine module for deterministic context-ledger tests
if "ml_engine" not in sys.modules:
    fake_ml = types.ModuleType("ml_engine")
    feature_store = types.ModuleType("ml_engine.feature_store.context_ledger_features")
    feature_store.DEFAULT_FEATURE_COLUMNS = [
        "amount_log",
        "risk_score",
        "corridor_risk_factor",
        "recent_events",
        "recent_failed",
    ]
    feature_store.TARGET_COLUMN = "risk_probability"

    class _StubModel:
        def __init__(self):
            self.feature_columns = feature_store.DEFAULT_FEATURE_COLUMNS

        def predict(self, features):
            # Basic heuristic to keep tests deterministic without the real model
            probability = min(1.0, max(0.0, float(features.get("risk_score", 0.0)) / 100.0))
            return {"risk_probability": probability, "top_signals": ["baseline"]}

    models_mod = types.ModuleType("ml_engine.models.context_ledger_risk_model")
    models_mod.ContextLedgerRiskModel = _StubModel

    sys.modules["ml_engine"] = fake_ml
    sys.modules["ml_engine.feature_store"] = types.ModuleType("ml_engine.feature_store")
    sys.modules["ml_engine.feature_store.context_ledger_features"] = feature_store
    sys.modules["ml_engine.models"] = types.ModuleType("ml_engine.models")
    sys.modules["ml_engine.models.context_ledger_risk_model"] = models_mod

# Provide import safety shim expected by app.main
if "core.import_safety" not in sys.modules:
    core_mod = types.ModuleType("core.import_safety")

    def ensure_import_safety(*args, **kwargs):  # pragma: no cover - test shim
        return None

    core_mod.ensure_import_safety = ensure_import_safety  # type: ignore[attr-defined]
    sys.modules["core"] = types.ModuleType("core")
    sys.modules["core.import_safety"] = core_mod


@pytest.fixture(autouse=True)
def stub_governance_engine(monkeypatch):
    """Avoid loading heavy governance rules during tests."""
    try:
        from app.governance.alex_engine import alex_engine
    except Exception:
        # If governance module is unavailable in isolated test contexts, skip patching.
        yield
        return

    def _apply_rules(token_state, risk_state, ml_prediction):
        return {
            "rationale": "test-governance",
            "severity": "LOW",
            "rule_id": "default",
            "decision_path": ["default"],
            "trace_id": "governance-test-trace",
        }

    monkeypatch.setattr(alex_engine, "apply_governance_rules", _apply_rules)
    yield


def pytest_sessionfinish(session, exitstatus):
    """Restore prior app module after ChainPay tests."""
    if _ORIGINAL_APP is not None:
        sys.modules["app"] = _ORIGINAL_APP
    else:
        sys.modules.pop("app", None)


from app.models import Base, PaymentIntent, PaymentSchedule, PaymentScheduleItem, PaymentStatus, RiskTier, ScheduleType  # noqa: E402

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
    """Provide FastAPI TestClient with test database session.

    NOTE: DEV_AUTH_BYPASS=true is set for backward compatibility with tests
    written before auth was added. For auth-specific tests, see test_security_authz.py
    which explicitly manages this setting.
    """
    import os

    os.environ["DEV_AUTH_BYPASS"] = "true"  # Enable bypass for existing tests

    from app.main import app, get_db  # Local import to avoid heavy dependencies for non-HTTP tests

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    os.environ.pop("DEV_AUTH_BYPASS", None)  # Clean up


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
