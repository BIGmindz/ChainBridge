"""
Database session management for ChainPay Service.

Handles SQLAlchemy session creation and lifecycle.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

# Import analytics models so metadata is aware before create_all
from . import models_analytics  # noqa: F401

# Database URL - use SQLite by default, can be overridden via environment
DATABASE_URL = os.getenv(
    "CHAINPAY_DATABASE_URL",
    os.getenv("DATABASE_URL", "sqlite:///./chainpay.db"),
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize the database by recreating all tables for a clean schema."""
    # Dropping first avoids stale SQLite schemas lingering between test runs
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
