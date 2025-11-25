"""Legal routes for Ricardian instruments.

Contracts (v1.1, canonical):
- status ∈ {ACTIVE, FROZEN, TERMINATED}
- supremacy_enabled / material_adverse_override flags are persisted and surfaced
- GET /legal/ricardian/instruments/by-physical/{ref} returns full instrument or 404 (FE treats as null)
- GET /legal/ricardian/supremacy/{id} returns supremacy+metadata projection; keep additive for future versions
- POST /legal/ricardian/instruments/{id}/kill_switch sets status=FROZEN and material_adverse_override=True
Future changes must be additive or versioned, not silent mutations.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.legal import RicardianInstrument
from api.schemas.legal import (
    RicardianInstrumentCreate,
    RicardianInstrumentResponse,
    RicardianInstrumentUpdate,
    RicardianInstrumentStatus,
)
from api.legal.metadata import build_ricardian_metadata

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/legal", tags=["legal"])


def _get_instrument(db: Session, instrument_id: str) -> RicardianInstrument:
    instrument = db.query(RicardianInstrument).filter(RicardianInstrument.id == instrument_id).first()
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return instrument


@router.post("/ricardian/instruments", response_model=RicardianInstrumentResponse, status_code=201)
def create_instrument(payload: RicardianInstrumentCreate, db: Session = Depends(get_db)) -> RicardianInstrumentResponse:
    instrument = RicardianInstrument(
        id=str(uuid.uuid4()),
        instrument_type=payload.instrument_type.value,
        physical_reference=payload.physical_reference,
        pdf_uri=str(payload.pdf_uri),
        pdf_ipfs_uri=payload.pdf_ipfs_uri,
        pdf_hash=payload.pdf_hash,
        ricardian_version=payload.ricardian_version,
        governing_law=payload.governing_law,
        smart_contract_chain=payload.smart_contract_chain,
        smart_contract_address=payload.smart_contract_address,
        ricardian_metadata=payload.ricardian_metadata or None,
        created_by=payload.created_by,
    )
    if instrument.ricardian_metadata is None:
        instrument.ricardian_metadata = build_ricardian_metadata(instrument)
    db.add(instrument)
    db.commit()
    db.refresh(instrument)
    logger.info(
        "legal.ricardian.created",
        extra={"instrument_id": instrument.id, "physical_reference": instrument.physical_reference},
    )
    return instrument


@router.patch("/ricardian/instruments/{instrument_id}", response_model=RicardianInstrumentResponse)
def update_instrument(
    instrument_id: str, payload: RicardianInstrumentUpdate, db: Session = Depends(get_db)
) -> RicardianInstrumentResponse:
    instrument = _get_instrument(db, instrument_id)
    for field in (
        "smart_contract_chain",
        "smart_contract_address",
        "last_signed_tx_hash",
        "freeze_reason",
        "ricardian_metadata",
    ):
        value = getattr(payload, field, None)
        if value is not None:
            setattr(instrument, field, value)
    if payload.status:
        instrument.status = payload.status.value
    db.add(instrument)
    db.commit()
    db.refresh(instrument)
    logger.info(
        "legal.ricardian.updated",
        extra={"instrument_id": instrument.id, "status": instrument.status},
    )
    return instrument


@router.get("/ricardian/instruments/{instrument_id}", response_model=RicardianInstrumentResponse)
def get_instrument(instrument_id: str, db: Session = Depends(get_db)) -> RicardianInstrumentResponse:
    return _get_instrument(db, instrument_id)


@router.get("/ricardian/instruments/by-physical/{physical_reference}", response_model=RicardianInstrumentResponse)
def get_instrument_by_physical(physical_reference: str, db: Session = Depends(get_db)) -> RicardianInstrumentResponse:
    instrument = (
        db.query(RicardianInstrument)
        .filter(RicardianInstrument.physical_reference == physical_reference)
        .order_by(RicardianInstrument.created_at.desc())
        .first()
    )
    if not instrument:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return instrument


@router.post("/ricardian/instruments/{instrument_id}/freeze", response_model=RicardianInstrumentResponse)
def freeze_instrument(instrument_id: str, reason: str = None, db: Session = Depends(get_db)) -> RicardianInstrumentResponse:
    instrument = _get_instrument(db, instrument_id)
    instrument.status = RicardianInstrumentStatus.FROZEN.value
    instrument.freeze_reason = reason
    db.add(instrument)
    db.commit()
    db.refresh(instrument)
    logger.info("legal.ricardian.frozen", extra={"instrument_id": instrument.id, "reason": reason})
    return instrument


@router.post("/ricardian/instruments/{instrument_id}/unfreeze", response_model=RicardianInstrumentResponse)
def unfreeze_instrument(instrument_id: str, db: Session = Depends(get_db)) -> RicardianInstrumentResponse:
    instrument = _get_instrument(db, instrument_id)
    instrument.status = RicardianInstrumentStatus.ACTIVE.value
    instrument.freeze_reason = None
    db.add(instrument)
    db.commit()
    db.refresh(instrument)
    logger.info("legal.ricardian.unfrozen", extra={"instrument_id": instrument.id})
    return instrument


@router.get("/ricardian/supremacy/{instrument_id}")
def get_supremacy_info(instrument_id: str, db: Session = Depends(get_db)) -> dict:
    instrument = _get_instrument(db, instrument_id)
    metadata = instrument.ricardian_metadata or build_ricardian_metadata(instrument)
    return {
        "instrument_id": instrument.id,
        "supremacy_enabled": instrument.supremacy_enabled,
        "material_adverse_override": instrument.material_adverse_override,
        "metadata": metadata,
        "governing_law": instrument.governing_law,
        "pdf_hash": instrument.pdf_hash,
        "contract_address": instrument.smart_contract_address,
    }


@router.post("/ricardian/instruments/{instrument_id}/kill_switch", response_model=RicardianInstrumentResponse)
def invoke_kill_switch(instrument_id: str, event: str, db: Session = Depends(get_db)) -> RicardianInstrumentResponse:
    instrument = _get_instrument(db, instrument_id)
    instrument.material_adverse_override = True
    instrument.status = RicardianInstrumentStatus.FROZEN.value
    instrument.freeze_reason = f"Material Adverse Event: {event}"
    db.add(instrument)
    db.commit()
    db.refresh(instrument)
    logger.info(
        "legal.ricardian.kill_switch",
        extra={"instrument_id": instrument.id, "event": event},
    )
    return instrument
