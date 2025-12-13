"""Lightweight client for ChainDocs document lookups."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models.chaindocs import Document
from api.schemas.chaindocs import ChainDocsDocument

logger = logging.getLogger(__name__)


class ChainDocsUnavailable(Exception):
    """Raised when ChainDocs cannot be reached or returns a server error."""


def get_document(doc_id: str, db: Optional[Session] = None) -> Optional[ChainDocsDocument]:
    """
    Fetch a document by id from ChainDocs.

    For now this queries the local database directly; callers can mock this to simulate
    real HTTP semantics (404 vs 5xx).
    """
    external_session = db is not None
    session = db or SessionLocal()
    try:
        document = session.query(Document).filter(Document.id == doc_id).first()
        if not document:
            return None
        return ChainDocsDocument(
            document_id=document.id,
            type=document.type,
            status=document.status,
            version=document.current_version or 1,
            hash=document.latest_hash or document.hash or "",
            mletr=document.mletr,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        logger.warning("ChainDocs lookup failed for %s: %s", doc_id, exc)
        raise ChainDocsUnavailable(str(exc)) from exc
    finally:
        if not external_session:
            session.close()
