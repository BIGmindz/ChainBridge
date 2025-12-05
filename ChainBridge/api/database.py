"""Database utilities for the ChainBridge API."""

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from api.core.config import settings

DATABASE_URL = settings.DATABASE_URL
url = make_url(DATABASE_URL)
connect_args = {}

if url.get_backend_name() == "sqlite":
    db_path = Path(url.database) if url.database else Path("chainbridge.db")
    if not db_path.is_absolute():
        db_path = Path(__file__).resolve().parent.parent / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{db_path}"
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """Initialize database tables."""
    # Import models so that SQLAlchemy registers the metadata before create_all.
    for module_path in [
        "api.models.chaindocs",
        "api.models.chainpay",
        "api.models.chainiq",
        "api.models.legal",
        "api.models.finance",
        "api.models.shadow_pilot",
        "app.models.ingest",
        "app.models.marketplace",
    ]:
        try:
            __import__(module_path)
        except Exception as exc:  # pragma: no cover - optional modules may be absent in test envs
            print(f"Warning: failed to import {module_path}: {exc}")

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
