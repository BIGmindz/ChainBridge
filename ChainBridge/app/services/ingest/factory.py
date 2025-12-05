"""Factory for ingestion adapters."""

from __future__ import annotations

from app.services.ingest.base import BaseIngestor
from app.services.ingest.seeburger import SeeburgerIngestor

_REGISTRY: dict[str, type[BaseIngestor]] = {
    "SEEBURGER": SeeburgerIngestor,
    "SEEBURGER_856": SeeburgerIngestor,
}


def get_ingestor(source: str) -> BaseIngestor:
    key = (source or "").strip().upper()
    ingestor_cls = _REGISTRY.get(key)
    if not ingestor_cls:
        raise ValueError(f"No ingestor registered for '{source}'")
    return ingestor_cls()
