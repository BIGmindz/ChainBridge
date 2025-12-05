from __future__ import annotations

from typing import Any, Generator


def get_db() -> Generator[Any, None, None]:
    """
    Placeholder DB dependency for the ChainIQ service.

    - Test code is expected to override this dependency with a real Session,
      e.g. using FastAPI's `app.dependency_overrides[get_db]`.
    - Production code should replace this implementation with a proper
      database session provider (e.g. SessionLocal from SQLAlchemy).

    If this function is ever called without being overridden, it will raise
    to avoid silently running without a real database.
    """
    raise RuntimeError("app.database.get_db is not configured for runtime use.")
