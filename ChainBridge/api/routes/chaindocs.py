"""ChainDocs API routes."""

from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.chainiq_service.constants import REQUIRED_DOCUMENT_TYPES
from api.chaindocs_hashing import compute_sha256
from api.database import get_db
from api.events.bus import EventType, event_bus
from api.models.chaindocs import Document, DocumentVersion, Shipment
from api.models.chainpay import PaymentIntent
from api.schemas.chaindocs import (
    ChainDocsDocument,
    ChainDocsDocumentCreate,
    ChainDocsDossierResponse,
)

router = APIRouter(prefix="/chaindocs", tags=["ChainDocs"])


def _serialize_documents(documents: List[Document]) -> List[ChainDocsDocument]:
    return [
        ChainDocsDocument(
            document_id=document.id,
            type=document.type,
            status=document.status,
            version=document.current_version or 1,
            hash=document.latest_hash or document.hash or "",
            mletr=document.mletr,
        )
        for document in documents
    ]


def _determine_missing_documents(documents: List[Document]) -> List[str]:
    present_types = {document.type for document in documents if document.type}
    required_set = set(REQUIRED_DOCUMENT_TYPES)
    return sorted(list(required_set - present_types))


@router.get("/shipments/{shipment_id}/dossier", response_model=ChainDocsDossierResponse)
async def get_shipment_dossier(
    shipment_id: str, db: Session = Depends(get_db)
) -> ChainDocsDossierResponse:
    """
    Return the dossier for a shipment backed by SQLite.

    TODO: wire Shipment + Document creation to BIS adapter instead of direct POST
    TODO: connect to Seeburger BIS adapter for real ingestion
    TODO: drop-in SxT proof linkage
    """
    if not shipment_id:
        raise HTTPException(status_code=400, detail="shipment_id is required")

    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        return ChainDocsDossierResponse(
            shipment_id=shipment_id,
            documents=[],
            missing_documents=sorted(list(set(REQUIRED_DOCUMENT_TYPES))),
        )

    documents = _serialize_documents(shipment.documents)
    missing = _determine_missing_documents(shipment.documents)

    return ChainDocsDossierResponse(
        shipment_id=shipment_id,
        documents=documents,
        missing_documents=missing,
    )


@router.post(
    "/shipments/{shipment_id}/documents",
    response_model=ChainDocsDocument,
    status_code=200,
)
async def add_document(
    shipment_id: str,
    payload: ChainDocsDocumentCreate,
    db: Session = Depends(get_db),
) -> ChainDocsDocument:
    """
    Insert or update a document for a shipment.

    TODO: wire Shipment + Document creation to BIS adapter instead of direct POST
    """
    if not shipment_id:
        raise HTTPException(status_code=400, detail="shipment_id is required")

    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        shipment = Shipment(id=shipment_id)
        db.add(shipment)
        db.flush()

    document = db.query(Document).filter(Document.id == payload.document_id).first()
    if document:
        document.type = payload.type
        document.status = payload.status
        document.current_version = (document.current_version or 0) + 1
        document.hash = payload.hash
        document.latest_hash = payload.hash
        document.mletr = payload.mletr
    else:
        starting_version = payload.version or 1
        document = Document(
            id=payload.document_id,
            shipment_id=shipment_id,
            type=payload.type,
            status=payload.status,
            current_version=starting_version,
            hash=payload.hash,
            latest_hash=payload.hash,
            mletr=payload.mletr,
            sha256_hex=payload.hash,
        )
        db.add(document)
        db.flush()

    version_entry = DocumentVersion(
        document_id=document.id,
        version_number=document.current_version or 1,
        hash=payload.hash,
        status=payload.status,
        created_by_party=payload.created_by_party,
        source="API",
        reason_code=payload.reason_code,
    )
    db.add(version_entry)

    db.commit()
    db.refresh(document)

    return ChainDocsDocument(
        document_id=document.id,
        type=document.type,
        status=document.status,
        version=document.current_version or 1,
        hash=document.latest_hash or document.hash or "",
        mletr=document.mletr,
    )


@router.post("/documents/{document_id}/verify")
async def verify_document(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.storage_ref:
        raise HTTPException(status_code=400, detail="storage_ref_missing")

    path = Path(document.storage_ref)
    if not path.exists():
        raise HTTPException(status_code=400, detail="storage_ref_not_found")

    current_hash = compute_sha256(path.read_bytes())
    stored_hash = document.sha256_hex or document.latest_hash or document.hash or ""
    valid = stored_hash == current_hash
    linked_intents = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.proof_hash == stored_hash)
        .all()
    )
    event_bus.publish(
        EventType.DOCUMENT_VERIFIED,
        {"document_id": document_id, "valid": valid, "stored_hash": stored_hash, "current_hash": current_hash},
        correlation_id=document_id,
        actor="chaindocs",
    )
    return {
        "valid": valid,
        "document_sha256": current_hash,
        "stored_sha256": stored_hash,
        "linked_payment_intents": [{"id": pi.id, "shipment_id": pi.shipment_id} for pi in linked_intents],
    }
