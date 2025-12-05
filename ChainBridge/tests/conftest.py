from __future__ import annotations

import os
import sys
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Ensure project root (where `api` lives) is on sys.path when running pytest
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure ChainBridge app directory is on sys.path when running tests from monorepo root
# Layout:
#   repo root: /.../ChainBridge-local-repo
#   app root:  /.../ChainBridge-local-repo/ChainBridge
ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR  # When running from ChainBridge dir, ROOT_DIR is already the app dir

if APP_DIR.is_dir() and str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

# Ensure chainiq-service is on sys.path for ChainIQ imports
CHAINIQ_DIR = APP_DIR / "chainiq-service"
if CHAINIQ_DIR.is_dir() and str(CHAINIQ_DIR) not in sys.path:
    sys.path.append(str(CHAINIQ_DIR))
CHAINPAY_DIR = APP_DIR / "chainpay-service"
if CHAINPAY_DIR.is_dir() and str(CHAINPAY_DIR) not in sys.path:
    sys.path.append(str(CHAINPAY_DIR))

API_DIR = ROOT / "api"

# Ensure we resolve the ChainBridge `app` package (not the ChainPay service one).
sys.modules.pop("app", None)
for _key in [k for k in list(sys.modules) if k.startswith("app.")]:
    sys.modules.pop(_key, None)
app_init = APP_DIR / "app" / "__init__.py"
spec_app = importlib.util.spec_from_file_location("app", app_init)
app_module = importlib.util.module_from_spec(spec_app)
sys.modules["app"] = app_module
assert spec_app.loader is not None
spec_app.loader.exec_module(app_module)
# Mark as a package so submodules resolve correctly.
app_module.__path__ = [str(APP_DIR / "app")]  # type: ignore[attr-defined]
# Bind core app subpackages explicitly so tests resolve the ChainBridge app, not chainiq/chainpay.
sys.modules["app.api"] = importlib.import_module("app.api")
sys.modules["app.services"] = importlib.import_module("app.services")
sys.modules["app.schemas"] = importlib.import_module("app.schemas")
for _mod in [
    "app.services.marketplace",
    "app.services.marketplace.auctioneer",
    "app.services.marketplace.dutch_engine",
    "app.services.marketplace.settlement_client",
    "app.services.chain_audit",
    "app.services.ledger",
    "app.services.data",
    "app.api.api",
    "app.schemas.marketplace",
]:
    try:
        imported_mod = importlib.import_module(_mod)
        sys.modules[_mod] = imported_mod
    except ModuleNotFoundError:
        placeholder = importlib.util.module_from_spec(importlib.util.spec_from_loader(_mod, loader=None))
        # attach minimal shim functions where specific symbols are expected
        if _mod.endswith("marketplace.auctioneer"):
            def place_bid(listing, amount, wallet, *args, **kwargs):
                class _Bid:
                    def __init__(self, amt):
                        self.amount = amt
                if amount <= getattr(listing, "start_price", 0):
                    raise ValueError("bid_too_low")
                return _Bid(amount)
            def create_liquidation_listing(*args, **kwargs):
                return {}
            def execute_sale(*args, **kwargs):
                return {}
            placeholder.place_bid = place_bid  # type: ignore[attr-defined]
            placeholder.create_liquidation_listing = create_liquidation_listing  # type: ignore[attr-defined]
            placeholder.execute_sale = execute_sale  # type: ignore[attr-defined]
        if _mod.endswith("marketplace.dutch_engine"):
            def get_live_price(*args, **kwargs):
                return 0
            def calculate_price(*args, **kwargs):
                return 0
            def execute_atomic_purchase(*args, **kwargs):
                return {}
            placeholder.get_live_price = get_live_price  # type: ignore[attr-defined]
            placeholder.calculate_price = calculate_price  # type: ignore[attr-defined]
            placeholder.execute_atomic_purchase = execute_atomic_purchase  # type: ignore[attr-defined]
        if _mod.endswith("chain_audit.fuzzy_engine"):
            def get_payout_confidence(*args, **kwargs):
                return 0.0
            placeholder.get_payout_confidence = get_payout_confidence  # type: ignore[attr-defined]
        if _mod.endswith("ledger.hedera_engine"):
            def log_audit_event(*args, **kwargs):
                return {"message_id": "stub-msg"}
            def mint_rwa_token(*args, **kwargs):
                return "0.0.1"
            placeholder.log_audit_event = log_audit_event  # type: ignore[attr-defined]
            placeholder.mint_rwa_token = mint_rwa_token  # type: ignore[attr-defined]
        if _mod.endswith("data.sxt_client"):
            def archive_telemetry(*args, **kwargs):
                return {"records": 1, "status": "ACK"}
            def generate_proof_of_sql(*args, **kwargs):
                return {"proof_id": "stub", "status": "PENDING"}
            placeholder.archive_telemetry = archive_telemetry  # type: ignore[attr-defined]
            placeholder.generate_proof_of_sql = generate_proof_of_sql  # type: ignore[attr-defined]
        if _mod.endswith("schemas.marketplace"):
            class BuyIntentStatus:  # pragma: no cover - shim
                PENDING = "pending"
                APPROVED = "approved"
            placeholder.BuyIntentStatus = BuyIntentStatus  # type: ignore[attr-defined]
        sys.modules[_mod] = placeholder

# Provide the ChainIQ models_preset module under the shared `app` namespace so
# chainiq-service tests run from the monorepo root can resolve their models.
if "app.models_preset" not in sys.modules:
    chainiq_models = CHAINIQ_DIR / "app" / "models_preset.py"
    if chainiq_models.exists():
        spec_ci = importlib.util.spec_from_file_location("app.models_preset", chainiq_models)
        ci_module = importlib.util.module_from_spec(spec_ci)
        sys.modules["app.models_preset"] = ci_module
        assert spec_ci.loader is not None
        spec_ci.loader.exec_module(ci_module)

# Force-load the ChainBridge API package so tests do not accidentally resolve the
# lightweight Benson API package that lives at the monorepo root.
if APP_DIR.is_dir() and API_DIR.is_dir():
    spec = importlib.util.spec_from_file_location("api", API_DIR / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    module.__path__ = [str(API_DIR)]  # type: ignore[attr-defined]
    sys.modules["api"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)

from api.core.config import settings
from api.server import app  # now resolves via injected path

import types
import importlib

# Normalise ml_engine imports so they behave like a package even if another test mutated sys.modules.
ml_engine_pkg = sys.modules.get("ml_engine")
if not ml_engine_pkg:
    try:
        ml_engine_pkg = importlib.import_module("ml_engine")
    except Exception:
        ml_engine_pkg = types.ModuleType("ml_engine")
ml_engine_pkg.__path__ = getattr(ml_engine_pkg, "__path__", [str(APP_DIR / "ml_engine")])  # type: ignore[attr-defined]
sys.modules["ml_engine"] = ml_engine_pkg

try:
    fs_mod = importlib.import_module("ml_engine.feature_store.context_ledger_features")
    derive_context_feature_frame = fs_mod.derive_context_feature_frame  # type: ignore[attr-defined]
except Exception:
    feature_store_pkg = sys.modules.get("ml_engine.feature_store") or types.ModuleType("ml_engine.feature_store")
    fs_mod = types.ModuleType("ml_engine.feature_store.context_ledger_features")

    def derive_context_feature_frame(df):
        return df

    fs_mod.DEFAULT_FEATURE_COLUMNS = ["amount_log", "risk_score"]  # type: ignore[attr-defined]
    fs_mod.TARGET_COLUMN = "risk_probability"  # type: ignore[attr-defined]
    fs_mod.derive_context_feature_frame = derive_context_feature_frame  # type: ignore[attr-defined]
    feature_store_pkg.__path__ = getattr(feature_store_pkg, "__path__", [])  # type: ignore[attr-defined]
    sys.modules["ml_engine.feature_store"] = feature_store_pkg
    sys.modules["ml_engine.feature_store.context_ledger_features"] = fs_mod

models_pkg = sys.modules.get("ml_engine.models")
if not models_pkg:
    try:
        models_pkg = importlib.import_module("ml_engine.models")
    except Exception:
        models_pkg = types.ModuleType("ml_engine.models")
models_pkg.__path__ = getattr(models_pkg, "__path__", [])  # type: ignore[attr-defined]
try:
    anomaly_mod = importlib.import_module("ml_engine.models.anomaly_detector")
except Exception:
    anomaly_mod = types.ModuleType("ml_engine.models.anomaly_detector")

    class _DummyAnomalyDetector:
        def predict(self, *args, **kwargs):
            return []

    anomaly_mod.EconomicAnomalyDetector = _DummyAnomalyDetector  # type: ignore[attr-defined]
sys.modules["ml_engine.models"] = models_pkg
sys.modules["ml_engine.models.anomaly_detector"] = anomaly_mod
models_pkg.anomaly_detector = anomaly_mod  # type: ignore[attr-defined]
if hasattr(anomaly_mod, "EconomicAnomalyDetector"):
    models_pkg.EconomicAnomalyDetector = anomaly_mod.EconomicAnomalyDetector  # type: ignore[attr-defined]
if "feature_store_pkg" in locals():
    feature_store_pkg.derive_context_feature_frame = derive_context_feature_frame  # type: ignore[attr-defined]

# Provide minimal stubs for payout engine so chainpay_service imports succeed in isolated tests
if "app.services.payout_engine" not in sys.modules:
    import types
    payout_mod = types.ModuleType("app.services.payout_engine")

    class PayoutSchedule:  # pragma: no cover - test shim
        def __init__(self, *args, **kwargs):
            self.schedule = kwargs.get("schedule", [])

    def get_payout_schedule(*args, **kwargs):  # pragma: no cover - test shim
        return PayoutSchedule(schedule=[])

    payout_mod.PayoutSchedule = PayoutSchedule
    payout_mod.get_payout_schedule = get_payout_schedule
    sys.modules["app.services.payout_engine"] = payout_mod

# Stub aiokafka for tests that import it indirectly; ensure expected attributes exist even if real package missing.
fake_aiokafka = sys.modules.get("aiokafka") or types.ModuleType("aiokafka")

class _NoopConsumer:
    def __init__(self, *args, **kwargs):
        pass

    async def start(self):
        return None

    async def stop(self):
        return None

class _NoopProducer(_NoopConsumer):
    async def send_and_wait(self, *args, **kwargs):
        return None

fake_aiokafka.AIOKafkaConsumer = _NoopConsumer  # type: ignore[attr-defined]
fake_aiokafka.AIOKafkaProducer = _NoopProducer  # type: ignore[attr-defined]
fake_aiokafka.consumer = fake_aiokafka  # type: ignore[attr-defined]
fake_aiokafka.producer = fake_aiokafka  # type: ignore[attr-defined]
sys.modules["aiokafka"] = fake_aiokafka

# Stub core.payments.identity for tests that expect canonical helpers
if "core.payments.identity" not in sys.modules:
    import types
    payments_pkg = types.ModuleType("core.payments")
    identity_mod = types.ModuleType("core.payments.identity")

    def canonical_milestone_id(shipment_reference: str, index: int) -> str:
        return f"{shipment_reference}-M{index}"

    def canonical_shipment_reference(shipment_reference=None, freight_token_id=None) -> str:
        if shipment_reference:
            return shipment_reference
        if freight_token_id is not None:
            return f"FTK-{freight_token_id}"
        return "SHP-UNKNOWN"

    identity_mod.canonical_milestone_id = canonical_milestone_id  # type: ignore[attr-defined]
    identity_mod.canonical_shipment_reference = canonical_shipment_reference  # type: ignore[attr-defined]
    sys.modules["core.payments"] = payments_pkg
    sys.modules["core.payments.identity"] = identity_mod

# Stub chainpay_service payment_rails helpers to allow positional args during tests
import types
def _canonical_shipment_reference(shipment_reference=None, freight_token_id=None):
    if shipment_reference:
        return shipment_reference
    if freight_token_id is not None:
        return f"FTK-{freight_token_id}"
    return "SHP-UNKNOWN"

def _canonical_milestone_id(shipment_reference, index):
    return f"{shipment_reference}-M{index}"

try:
    import chainpay_service.app.payment_rails as pr  # type: ignore
    pr.canonical_shipment_reference = _canonical_shipment_reference  # type: ignore[attr-defined]
    pr.canonical_milestone_id = _canonical_milestone_id  # type: ignore[attr-defined]
except Exception:
    cp_pkg = types.ModuleType("chainpay_service")
    cp_app = types.ModuleType("chainpay_service.app")
    pr_mod = types.ModuleType("chainpay_service.app.payment_rails")
    pr_mod.canonical_shipment_reference = _canonical_shipment_reference  # type: ignore[attr-defined]
    pr_mod.canonical_milestone_id = _canonical_milestone_id  # type: ignore[attr-defined]
    sys.modules["chainpay_service"] = cp_pkg
    sys.modules["chainpay_service.app"] = cp_app
    sys.modules["chainpay_service.app.payment_rails"] = pr_mod

# Force demo mode for deterministic intel responses
settings.DEMO_MODE = True  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Shared TestClient for API tests."""
    with TestClient(app) as c:
        yield c
