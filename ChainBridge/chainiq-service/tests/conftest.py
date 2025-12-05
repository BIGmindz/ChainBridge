from __future__ import annotations

import os
import sys
import importlib.util
from pathlib import Path
import types
import importlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


# Insert chainiq-service root into sys.path for correct app imports
SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

# Ensure the project root is also importable so modules like `core.*` resolve
PROJECT_ROOT = SERVICE_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Provide lightweight fallbacks for optional deps used by background publishers
if "aiokafka" not in sys.modules:
    fake_aiokafka = types.ModuleType("aiokafka")

    class _NoopProducer:  # pragma: no cover - simple shim
        def __init__(self, *args, **kwargs):
            pass

        async def start(self):
            return None

        async def stop(self):
            return None

        async def send_and_wait(self, *args, **kwargs):
            return None

    fake_aiokafka.AIOKafkaProducer = _NoopProducer
    sys.modules["aiokafka"] = fake_aiokafka

# Stub import safety hook expected by app.main
if "core.import_safety" not in sys.modules:
    core_pkg = types.ModuleType("core")
    safety_mod = types.ModuleType("core.import_safety")

    def ensure_import_safety(*args, **kwargs):  # pragma: no cover - shim
        return None

    safety_mod.ensure_import_safety = ensure_import_safety  # type: ignore[attr-defined]
    sys.modules["core"] = core_pkg
    sys.modules["core.import_safety"] = safety_mod

# Ensure this test suite resolves the local ChainIQ `app` package, not the monorepo root app.
_ORIGINAL_APP = sys.modules.get("app")
sys.modules.pop("app", None)
for _k in [k for k in list(sys.modules) if k.startswith("app.")]:
    sys.modules.pop(_k, None)
app_init = SERVICE_ROOT / "app" / "__init__.py"
spec_app = importlib.util.spec_from_file_location("app", app_init)
app_module = importlib.util.module_from_spec(spec_app)
sys.modules["app"] = app_module
assert spec_app.loader is not None
spec_app.loader.exec_module(app_module)
app_module.__path__ = [str(SERVICE_ROOT / "app")]  # type: ignore[attr-defined]
# Eager-load models_preset so later imports don't fail during test collection
try:
    sys.modules["app.models_preset"] = importlib.import_module("app.models_preset")
except Exception:
    pass


# =============================================================================
# DATABASE FIXTURES
# =============================================================================


TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture
def db_session() -> Session:
    """Provide a clean database session for each test.

    Uses in-memory SQLite so tests are fast and isolated.
    Tables are created fresh for each test function.
    """
    from app.models_preset import Base

    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables and remove DB file after test
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("./test.db"):
            os.remove("./test.db")


# -----------------------------------------------------------------------------
# DB Dependency Override for FastAPI
# -----------------------------------------------------------------------------
from app.main import app
from app.database import get_db


@pytest.fixture(autouse=True)
def override_get_db(db_session: Session):
    """Override FastAPI's get_db dependency to use the test db_session."""

    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.pop(get_db, None)
