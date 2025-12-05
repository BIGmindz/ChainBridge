"""ChainFreight ingestion and reconciliation API routes."""

import logging
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.chainfreight import IngestionBatch, IngestionRecord, ShipmentEvent
from api.models.chaindocs import Shipment
from api.schemas.chainfreight import (
    IngestionBatchCreate,
    IngestionBatchResponse,
    IngestionRecordResponse,
    IngestionStatsResponse,
    ReconciliationRequest,
    ReconciliationResponse,
    ShipmentEventCreate,
    ShipmentEventResponse,
)
from api.services.chainfreight_processor import (
    process_ingestion_batch,
    run_reconciliation,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chainfreight", tags=["ChainFreight"])


@router.post("/batches", response_model=IngestionBatchResponse)
async def create_ingestion_batch(
    batch_create: IngestionBatchCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    # TODO: Add authentication dependency when auth system is implemented
):
    """
    Create a new ingestion batch and process in background.

    This endpoint accepts raw EDI or external data and queues it for processing.
    Processing includes validation, normalization, and reconciliation against
    existing shipments.
    """
    # Security: Enforce batch size limits
    MAX_BATCH_SIZE = 1000
    if len(batch_create.records) > MAX_BATCH_SIZE:
        raise HTTPException(status_code=400, detail=f"Batch size {len(batch_create.records)} exceeds maximum {MAX_BATCH_SIZE}")

    try:
        # Create batch record
        batch = IngestionBatch(
            source_system=batch_create.source_system,
            batch_type=batch_create.batch_type,
            total_records=len(batch_create.records),
        )
        db.add(batch)
        db.flush()  # Get the ID

        # Create individual records
        for idx, raw_record in enumerate(batch_create.records):
            record = IngestionRecord(
                batch_id=batch.id,
                external_id=raw_record.get("id") or raw_record.get("reference"),
                record_type=_determine_record_type(raw_record, batch_create.batch_type),
                shipment_reference=_extract_shipment_reference(raw_record),
                raw_payload=raw_record,
                processing_status="PENDING",
            )
            db.add(record)

        db.commit()

        # Queue background processing
        background_tasks.add_task(process_ingestion_batch, batch.id)

        logger.info(
            f"Created ingestion batch {batch.id} with {batch.total_records} records",
            extra={
                "batch_id": batch.id,
                "source_system": batch.source_system,
                "batch_type": batch.batch_type,
                "record_count": batch.total_records,
            },
        )

        return IngestionBatchResponse(
            id=batch.id,
            source_system=batch.source_system,
            batch_type=batch.batch_type,
            total_records=batch.total_records,
            processed_records=batch.processed_records,
            failed_records=batch.failed_records,
            status=batch.status,
            created_at=batch.created_at,
            completed_at=batch.completed_at,
            error_summary=batch.error_summary,
        )

    except Exception as e:
        logger.error(f"Failed to create ingestion batch: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ingestion batch creation failed: {str(e)}")


@router.get("/batches", response_model=List[IngestionBatchResponse])
async def list_ingestion_batches(
    source_system: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List ingestion batches with optional filtering."""
    query = db.query(IngestionBatch)

    if source_system:
        query = query.filter(IngestionBatch.source_system == source_system)
    if status:
        query = query.filter(IngestionBatch.status == status)

    batches = query.order_by(desc(IngestionBatch.created_at)).offset(offset).limit(limit).all()

    return [
        IngestionBatchResponse(
            id=batch.id,
            source_system=batch.source_system,
            batch_type=batch.batch_type,
            total_records=batch.total_records,
            processed_records=batch.processed_records,
            failed_records=batch.failed_records,
            status=batch.status,
            created_at=batch.created_at,
            completed_at=batch.completed_at,
            error_summary=batch.error_summary,
        )
        for batch in batches
    ]


@router.get("/batches/{batch_id}", response_model=IngestionBatchResponse)
async def get_ingestion_batch(batch_id: str, db: Session = Depends(get_db)):
    """Get details of a specific ingestion batch."""
    batch = db.query(IngestionBatch).filter(IngestionBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Ingestion batch not found")

    return IngestionBatchResponse(
        id=batch.id,
        source_system=batch.source_system,
        batch_type=batch.batch_type,
        total_records=batch.total_records,
        processed_records=batch.processed_records,
        failed_records=batch.failed_records,
        status=batch.status,
        created_at=batch.created_at,
        completed_at=batch.completed_at,
        error_summary=batch.error_summary,
    )


@router.get("/batches/{batch_id}/records", response_model=List[IngestionRecordResponse])
async def list_batch_records(
    batch_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List records within a specific batch."""
    # Verify batch exists
    batch = db.query(IngestionBatch).filter(IngestionBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Ingestion batch not found")

    query = db.query(IngestionRecord).filter(IngestionRecord.batch_id == batch_id)

    if status:
        query = query.filter(IngestionRecord.processing_status == status)

    records = query.offset(offset).limit(limit).all()

    return [
        IngestionRecordResponse(
            id=record.id,
            batch_id=record.batch_id,
            external_id=record.external_id,
            record_type=record.record_type,
            shipment_reference=record.shipment_reference,
            processing_status=record.processing_status,
            error_message=record.error_message,
            reconciliation_status=record.reconciliation_status,
            matched_shipment_id=record.matched_shipment_id,
            created_at=record.created_at,
            processed_at=record.processed_at,
        )
        for record in records
    ]


@router.post("/events", response_model=ShipmentEventResponse)
async def create_shipment_event(event_create: ShipmentEventCreate, db: Session = Depends(get_db)):
    """Create a new shipment lifecycle event."""
    # Verify shipment exists
    shipment = db.query(Shipment).filter(Shipment.id == event_create.shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    event = ShipmentEvent(
        shipment_id=event_create.shipment_id,
        event_type=event_create.event_type,
        event_code=event_create.event_code,
        event_timestamp=event_create.event_timestamp,
        location_code=event_create.location_code,
        location_name=event_create.location_name,
        carrier_code=event_create.carrier_code,
        equipment_id=event_create.equipment_id,
        source_system=event_create.source_system,
        confidence_score=event_create.confidence_score,
        payload_metadata=event_create.metadata,
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    logger.info(
        f"Created shipment event {event.id} for shipment {event.shipment_id}",
        extra={
            "event_id": event.id,
            "shipment_id": event.shipment_id,
            "event_type": event.event_type,
            "source_system": event.source_system,
        },
    )

    return ShipmentEventResponse(
        id=event.id,
        shipment_id=event.shipment_id,
        event_type=event.event_type,
        event_code=event.event_code,
        event_timestamp=event.event_timestamp,
        location_code=event.location_code,
        location_name=event.location_name,
        carrier_code=event.carrier_code,
        equipment_id=event.equipment_id,
        source_system=event.source_system,
        source_record_id=event.source_record_id,
        confidence_score=event.confidence_score,
        metadata=event.payload_metadata,
        created_at=event.created_at,
    )


@router.get("/shipments/{shipment_id}/events", response_model=List[ShipmentEventResponse])
async def list_shipment_events(
    shipment_id: str,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List events for a specific shipment."""
    events = (
        db.query(ShipmentEvent)
        .filter(ShipmentEvent.shipment_id == shipment_id)
        .order_by(ShipmentEvent.event_timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        ShipmentEventResponse(
            id=event.id,
            shipment_id=event.shipment_id,
            event_type=event.event_type,
            event_code=event.event_code,
            event_timestamp=event.event_timestamp,
            location_code=event.location_code,
            location_name=event.location_name,
            carrier_code=event.carrier_code,
            equipment_id=event.equipment_id,
            source_system=event.source_system,
            source_record_id=event.source_record_id,
            confidence_score=event.confidence_score,
            metadata=event.payload_metadata,
            created_at=event.created_at,
        )
        for event in events
    ]


@router.post("/reconcile", response_model=ReconciliationResponse)
async def run_reconciliation_endpoint(
    reconciliation_request: ReconciliationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Run reconciliation to match ingested data with existing shipments.

    This can be run for specific batches, shipment references, or across
    all unmatched records.
    """
    try:
        result = run_reconciliation(
            db=db,
            batch_id=reconciliation_request.batch_id,
            shipment_references=reconciliation_request.shipment_references,
            force_reprocess=reconciliation_request.force_reprocess,
        )

        logger.info(
            f"Reconciliation completed: {result.matched_records} matched, {result.unmatched_records} unmatched",
            extra={
                "processed_records": result.processed_records,
                "matched_records": result.matched_records,
                "unmatched_records": result.unmatched_records,
                "error_count": len(result.errors),
            },
        )

        return result

    except Exception as e:
        logger.error(f"Reconciliation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Reconciliation failed: {str(e)}")


@router.get("/stats", response_model=IngestionStatsResponse)
async def get_ingestion_stats(db: Session = Depends(get_db)):
    """Get statistics and overview of ingestion operations."""
    # Aggregate stats
    total_batches = db.query(func.count(IngestionBatch.id)).scalar()
    total_records = db.query(func.sum(IngestionBatch.total_records)).scalar() or 0
    processed_records = db.query(func.sum(IngestionBatch.processed_records)).scalar() or 0
    failed_records = db.query(func.sum(IngestionBatch.failed_records)).scalar() or 0
    pending_records = total_records - processed_records - failed_records

    # Recent batches
    recent_batches_query = db.query(IngestionBatch).order_by(desc(IngestionBatch.created_at)).limit(10).all()

    recent_batches = [
        IngestionBatchResponse(
            id=batch.id,
            source_system=batch.source_system,
            batch_type=batch.batch_type,
            total_records=batch.total_records,
            processed_records=batch.processed_records,
            failed_records=batch.failed_records,
            status=batch.status,
            created_at=batch.created_at,
            completed_at=batch.completed_at,
        )
        for batch in recent_batches_query
    ]

    # Source system breakdown
    source_breakdown_query = (
        db.query(IngestionBatch.source_system, func.count(IngestionBatch.id)).group_by(IngestionBatch.source_system).all()
    )
    source_breakdown = {source: count for source, count in source_breakdown_query}

    # Type breakdown
    type_breakdown_query = db.query(IngestionBatch.batch_type, func.count(IngestionBatch.id)).group_by(IngestionBatch.batch_type).all()
    type_breakdown = {batch_type: count for batch_type, count in type_breakdown_query}

    return IngestionStatsResponse(
        total_batches=total_batches,
        total_records=total_records,
        processed_records=processed_records,
        failed_records=failed_records,
        pending_records=pending_records,
        recent_batches=recent_batches,
        source_breakdown=source_breakdown,
        type_breakdown=type_breakdown,
    )


def _determine_record_type(raw_record: dict, batch_type: str) -> str:
    """Determine the record type from raw data and batch context."""
    # Simple heuristic - can be enhanced with more sophisticated logic
    if batch_type in ["EDI_214", "TELEMATICS"]:
        return "SHIPMENT_UPDATE"
    elif batch_type == "EDI_856":
        return "ADVANCE_SHIP_NOTICE"
    elif batch_type == "EDI_210":
        return "INVOICE_UPDATE"
    else:
        return "UNKNOWN"


def _extract_shipment_reference(raw_record: dict) -> Optional[str]:
    """Extract shipment reference from raw record."""
    # Common fields where shipment references might be found
    possible_fields = ["bol", "pro_number", "reference", "shipment_id", "tracking_number"]

    for field in possible_fields:
        if field in raw_record and raw_record[field]:
            return str(raw_record[field])

    return None
