"""
Database Connection Management

Provides SQLAlchemy session management for ChainIQ service.
Used by Shadow Mode API and other persistence-dependent endpoints.
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def get_database_url() -> str:
    """
    Get database URL from settings or environment.

    Returns:
        PostgreSQL connection URL

    Raises:
        ValueError: If database URL not configured
    """
    db_url = settings.database_url or os.getenv("DATABASE_URL")

    if not db_url:
        raise ValueError("DATABASE_URL not configured. Set via config.yaml or environment variable.")

    return db_url


def create_session_factory() -> sessionmaker:
    """
    Create SQLAlchemy session factory.

    Returns:
        Session factory for creating database sessions
    """
    try:
        db_url = get_database_url()
        engine = create_engine(db_url, pool_pre_ping=True)
        return sessionmaker(autocommit=False, autoflush=False, bind=engine)
    except ValueError:
        # Return None if database not configured (optional feature)
        return None


# Global session factory
SessionLocal = create_session_factory()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session injection.

    Provides a SQLAlchemy session that is automatically closed after use.
    Use with FastAPI's Depends() for automatic session management.

    Yields:
        SQLAlchemy database session

    Example:
        @router.get("/endpoint")
        def my_endpoint(db: Session = Depends(get_db)):
            # Use db session
            return {"status": "ok"}
    """
    if SessionLocal is None:
        raise ValueError("Database not configured")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
