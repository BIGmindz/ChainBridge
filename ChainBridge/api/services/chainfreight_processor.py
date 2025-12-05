"""ChainFreight background processing and reconciliation service."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.chainfreight import IngestionBatch, IngestionRecord, ShipmentEvent
from api.models.chaindocs import Shipment
from api.schemas.chainfreight import ReconciliationResponse

logger = logging.getLogger(__name__)


class ChainFreightProcessor:
    """Handles processing and normalization of ingested data."""

    def __init__(self, db: Session):
        self.db = db

    def process_edi_214(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Process EDI 214 (Transportation Carrier Shipment Status) record."""
        try:
            normalized = {
                "shipment_reference": raw_record.get("pro_number") or raw_record.get("bol"),
                "carrier_code": raw_record.get("scac"),
                "status_code": raw_record.get("status_code"),
                "status_description": raw_record.get("status_description"),
                "location": {
                    "city": raw_record.get("city"),
                    "state": raw_record.get("state"),
                    "country": raw_record.get("country"),
                    "postal_code": raw_record.get("postal_code"),
                },
                "timestamp": self._parse_edi_timestamp(raw_record.get("date"), raw_record.get("time")),
                "equipment_id": raw_record.get("equipment_id"),
            }

            # Extract events from EDI segments
            events = self._extract_events_from_edi_214(raw_record)
            if events:
                normalized["events"] = events

            return normalized

        except Exception as e:
            logger.error(f"Failed to process EDI 214 record: {str(e)}")
            raise

    def process_edi_210(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Process EDI 210 (Motor Carrier Freight Details and Invoice) record."""
        try:
            normalized = {
                "shipment_reference": raw_record.get("pro_number") or raw_record.get("bol"),
                "invoice_number": raw_record.get("invoice_number"),
                "total_charges": raw_record.get("total_charges"),
                "currency": raw_record.get("currency", "USD"),
                "line_items": raw_record.get("line_items", []),
                "billing_period": raw_record.get("billing_period"),
                "due_date": raw_record.get("due_date"),
            }
            return normalized

        except Exception as e:
            logger.error(f"Failed to process EDI 210 record: {str(e)}")
            raise

    def process_telematics(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Process telematics/IoT data record."""
        try:
            normalized = {
                "equipment_id": raw_record.get("vehicle_id") or raw_record.get("trailer_id"),
                "location": {
                    "latitude": raw_record.get("lat"),
                    "longitude": raw_record.get("lng"),
                    "altitude": raw_record.get("altitude"),
                },
                "timestamp": raw_record.get("timestamp"),
                "speed": raw_record.get("speed"),
                "heading": raw_record.get("heading"),
                "odometer": raw_record.get("odometer"),
                "fuel_level": raw_record.get("fuel_level"),
                "engine_hours": raw_record.get("engine_hours"),
                "driver_id": raw_record.get("driver_id"),
                "status": raw_record.get("status"),
            }
            return normalized

        except Exception as e:
            logger.error(f"Failed to process telematics record: {str(e)}")
            raise

    def _parse_edi_timestamp(self, date_str: Optional[str], time_str: Optional[str]) -> Optional[str]:
        """Parse EDI date/time format to ISO timestamp."""
        if not date_str:
            return None

        try:
            # Common EDI date formats: YYMMDD, YYYYMMDD
            if len(date_str) == 6:
                # YYMMDD format
                year = int("20" + date_str[:2])
                month = int(date_str[2:4])
                day = int(date_str[4:6])
            elif len(date_str) == 8:
                # YYYYMMDD format
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
            else:
                return None

            # Parse time if provided (HHMM or HHMMSS format)
            hour = minute = second = 0
            if time_str:
                if len(time_str) == 4:
                    hour = int(time_str[:2])
                    minute = int(time_str[2:4])
                elif len(time_str) == 6:
                    hour = int(time_str[:2])
                    minute = int(time_str[2:4])
                    second = int(time_str[4:6])

            dt = datetime(year, month, day, hour, minute, second)
            return dt.isoformat()

        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse EDI timestamp {date_str}/{time_str}: {str(e)}")
            return None

    def _extract_events_from_edi_214(self, raw_record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract shipment events from EDI 214 record."""
        events = []

        # EDI 214 can contain multiple status segments
        status_segments = raw_record.get("status_segments", [])
        for segment in status_segments:
            event = {
                "event_code": segment.get("status_code"),
                "event_type": self._map_edi_status_to_event_type(segment.get("status_code")),
                "timestamp": self._parse_edi_timestamp(segment.get("date"), segment.get("time")),
                "location_code": segment.get("location_code"),
                "description": segment.get("status_description"),
            }
            events.append(event)

        return events

    def _map_edi_status_to_event_type(self, status_code: Optional[str]) -> str:
        """Map EDI status codes to canonical event types."""
        if not status_code:
            return "UNKNOWN"

        # Common EDI 214 status code mappings
        mapping = {
            "AF": "ARRIVED_FACILITY",
            "AG": "DEPARTED_FACILITY",
            "D1": "DELIVERY",
            "I1": "IN_TRANSIT",
            "NS": "PICKUP",
            "OA": "PICKUP",
            "OD": "DELIVERY",
            "X1": "EXCEPTION",
            "X6": "DELAY",
        }

        return mapping.get(status_code, "UNKNOWN")


async def process_ingestion_batch(batch_id: str):
    """Background task to process an ingestion batch."""
    db = next(get_db())
    processor = ChainFreightProcessor(db)

    try:
        batch = db.query(IngestionBatch).filter(IngestionBatch.id == batch_id).first()
        if not batch:
            logger.error(f"Ingestion batch {batch_id} not found")
            return

        logger.info(f"Processing ingestion batch {batch_id} with {batch.total_records} records")

        records = (
            db.query(IngestionRecord)
            .filter(and_(IngestionRecord.batch_id == batch_id, IngestionRecord.processing_status == "PENDING"))
            .all()
        )

        processed_count = 0
        failed_count = 0

        for record in records:
            try:
                # Process based on batch type
                raw_payload_dict = record.raw_payload
                if batch.batch_type == "EDI_214":
                    normalized_data = processor.process_edi_214(raw_payload_dict)
                elif batch.batch_type == "EDI_210":
                    normalized_data = processor.process_edi_210(raw_payload_dict)
                elif batch.batch_type == "TELEMATICS":
                    normalized_data = processor.process_telematics(raw_payload_dict)
                else:
                    raise ValueError(f"Unsupported batch type: {batch.batch_type}")

                # Update record with normalized data
                record.normalized_data = normalized_data
                record.processing_status = "PROCESSED"
                record.processed_at = datetime.utcnow()

                # Create shipment events if applicable
                await _create_events_from_normalized_data(db, record, normalized_data)

                processed_count += 1

            except Exception as e:
                logger.error(f"Failed to process record {record.id}: {str(e)}")
                record.processing_status = "FAILED"
                record.error_message = str(e)
                record.processed_at = datetime.utcnow()
                failed_count += 1

        # Update batch status
        batch.processed_records = processed_count
        batch.failed_records = failed_count
        batch.status = "COMPLETED" if failed_count == 0 else "COMPLETED_WITH_ERRORS"
        batch.completed_at = datetime.utcnow()

        if failed_count > 0:
            batch.error_summary = f"{failed_count} records failed processing"

        db.commit()

        logger.info(f"Completed processing batch {batch_id}: {processed_count} processed, {failed_count} failed")

        # Run reconciliation for processed records
        await _run_batch_reconciliation(db, batch_id)

    except Exception as e:
        logger.error(f"Failed to process batch {batch_id}: {str(e)}")
        if batch:
            batch.status = "FAILED"
            batch.error_summary = str(e)
            batch.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


async def _create_events_from_normalized_data(db: Session, record: IngestionRecord, normalized_data: Dict[str, Any]):
    """Create ShipmentEvent records from normalized data."""
    events = normalized_data.get("events", [])
    shipment_id = record.matched_shipment_id

    if not shipment_id or not events:
        return

    for event_data in events:
        if not event_data.get("timestamp") or not event_data.get("event_type"):
            continue

        event = ShipmentEvent(
            shipment_id=shipment_id,
            event_type=event_data["event_type"],
            event_code=event_data.get("event_code"),
            event_timestamp=datetime.fromisoformat(event_data["timestamp"].replace("Z", "+00:00")),
            location_code=event_data.get("location_code"),
            location_name=event_data.get("description"),
            source_system=record.batch.source_system,
            source_record_id=record.id,
            confidence_score=0.8,  # Default confidence for processed data
            metadata={"original_status_code": event_data.get("event_code")},
        )
        db.add(event)


def _create_events_from_normalized_data_sync(db: Session, record: IngestionRecord, normalized_data: Dict[str, Any]):
    """Synchronous version of _create_events_from_normalized_data."""
    events = normalized_data.get("events", [])
    shipment_id = record.matched_shipment_id

    if not shipment_id or not events:
        return

    for event_data in events:
        if not event_data.get("timestamp") or not event_data.get("event_type"):
            continue

        try:
            timestamp_str = event_data["timestamp"]
            if isinstance(timestamp_str, str):
                event_timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                event_timestamp = timestamp_str

            event = ShipmentEvent(
                shipment_id=shipment_id,
                event_type=event_data["event_type"],
                event_code=event_data.get("event_code"),
                event_timestamp=event_timestamp,
                location_code=event_data.get("location_code"),
                location_name=event_data.get("description"),
                source_system="INGESTION",  # Use a generic source
                source_record_id=record.id,
                confidence_score=0.8,
                metadata={"original_status_code": event_data.get("event_code")},
            )
            db.add(event)
        except Exception as e:
            logger.warning(f"Failed to create event from normalized data: {e}")
            continue


async def _run_batch_reconciliation(db: Session, batch_id: str):
    """Run reconciliation for all records in a batch."""
    try:
        result = run_reconciliation(db=db, batch_id=batch_id)
        logger.info(f"Batch {batch_id} reconciliation: {result.matched_records} matched, {result.unmatched_records} unmatched")
    except Exception as e:
        logger.error(f"Failed to run reconciliation for batch {batch_id}: {str(e)}")


def run_reconciliation(
    db: Session,
    batch_id: Optional[str] = None,
    shipment_references: Optional[List[str]] = None,
    force_reprocess: bool = False,
) -> ReconciliationResponse:
    """
    Run reconciliation to match ingested records with existing shipments.

    Args:
        db: Database session
        batch_id: Process only records from this batch
        shipment_references: Process only records with these references
        force_reprocess: Re-process already matched records

    Returns:
        ReconciliationResponse with processing results
    """
    try:
        # Build query for records to reconcile
        query = db.query(IngestionRecord).filter(IngestionRecord.processing_status == "PROCESSED")

        if not force_reprocess:
            query = query.filter(IngestionRecord.reconciliation_status.is_(None))

        if batch_id:
            query = query.filter(IngestionRecord.batch_id == batch_id)

        if shipment_references:
            query = query.filter(IngestionRecord.shipment_reference.in_(shipment_references))

        records = query.all()

        processed_records = len(records)
        matched_records = 0
        unmatched_records = 0
        errors = []
        batch_summary: Dict[str, int] = {}

        for record in records:
            try:
                # Try to match by shipment reference
                matched_shipment = None

                if record.shipment_reference:
                    # Look for shipments with matching BOL, PRO number, or other references
                    matched_shipment = db.query(Shipment).filter(Shipment.bol == record.shipment_reference).first()

                    if not matched_shipment:
                        # Try other reference fields
                        matched_shipment = db.query(Shipment).filter(Shipment.pro_number == record.shipment_reference).first()

                if matched_shipment:
                    record.reconciliation_status = "MATCHED"
                    record.matched_shipment_id = matched_shipment.id
                    matched_records += 1

                    # Create events for the matched shipment if applicable
                    if record.normalized_data and "events" in record.normalized_data:
                        _create_events_from_normalized_data_sync(db, record, record.normalized_data)

                else:
                    record.reconciliation_status = "UNMATCHED"
                    unmatched_records += 1

                # Track batch summary
                if record.batch_id:
                    batch_summary[record.batch_id] = batch_summary.get(record.batch_id, 0) + 1

            except Exception as e:
                error_msg = f"Failed to reconcile record {record.id}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        db.commit()

        return ReconciliationResponse(
            processed_records=processed_records,
            matched_records=matched_records,
            unmatched_records=unmatched_records,
            errors=errors,
            batch_summary=batch_summary if batch_summary else None,
        )

    except Exception as e:
        db.rollback()
        error_msg = f"Reconciliation failed: {str(e)}"
        logger.error(error_msg)
        raise
