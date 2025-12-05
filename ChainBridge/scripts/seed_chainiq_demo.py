"""Seed deterministic ChainIQ demo data for Fleet Cockpit."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from sqlalchemy.orm import Session

from api.database import SessionLocal, init_db
from api.models.canonical import RiskLevel, TransportMode
from api.models.chaindocs import Shipment
from api.models.chainiq import DocumentHealthSnapshot, SnapshotExportEvent

TOTAL_DOCS = 4
OPTIONAL_DOCS = 1


@dataclass(frozen=True)
class DemoShipment:
    shipment_id: str
    corridor: str
    mode: str
    incoterm: str
    risk_score: int
    risk_level: str
    blocking_gap_count: int
    days_delayed: int
    export_history: List[str]

    @property
    def present_count(self) -> int:
        missing_required = min(self.blocking_gap_count, TOTAL_DOCS)
        return max(TOTAL_DOCS - missing_required, 0)

    @property
    def completeness_pct(self) -> int:
        return int(round((self.present_count / TOTAL_DOCS) * 100)) if TOTAL_DOCS else 100


CORRIDOR_PROFILES: List[dict] = [
    {
        "prefix": "SHIP-OCE",
        "corridor": "CN-US",
        "mode": TransportMode.OCEAN.value,
        "incoterm": "FOB",
    },
    {
        "prefix": "SHIP-AIR",
        "corridor": "DE-US",
        "mode": TransportMode.AIR.value,
        "incoterm": "CIF",
    },
    {
        "prefix": "SHIP-ROAD",
        "corridor": "MX-US",
        "mode": TransportMode.TRUCK_LTL.value,
        "incoterm": "DAP",
    },
    {
        "prefix": "SHIP-OCE2",
        "corridor": "IN-US",
        "mode": TransportMode.OCEAN.value,
        "incoterm": "FOB",
    },
    {
        "prefix": "SHIP-AIR2",
        "corridor": "BR-US",
        "mode": TransportMode.AIR.value,
        "incoterm": "FCA",
    },
    {
        "prefix": "SHIP-ROAD2",
        "corridor": "US-CA",
        "mode": TransportMode.INTERMODAL.value,
        "incoterm": "EXW",
    },
]

RISK_PROFILES: List[dict] = [
    {
        "code": "L",
        "risk_score": 35,
        "risk_level": RiskLevel.LOW.value,
        "blocking_gap_count": 0,
        "days_delayed": 0,
        "export_history": ["PENDING", "SUCCESS"],
    },
    {
        "code": "M",
        "risk_score": 58,
        "risk_level": RiskLevel.MEDIUM.value,
        "blocking_gap_count": 1,
        "days_delayed": 1,
        "export_history": ["PENDING", "IN_PROGRESS"],
    },
    {
        "code": "H",
        "risk_score": 78,
        "risk_level": RiskLevel.HIGH.value,
        "blocking_gap_count": 2,
        "days_delayed": 4,
        "export_history": ["PENDING", "FAILED"],
    },
    {
        "code": "C",
        "risk_score": 92,
        "risk_level": RiskLevel.CRITICAL.value,
        "blocking_gap_count": 3,
        "days_delayed": 7,
        "export_history": ["PENDING", "IN_PROGRESS", "FAILED"],
    },
]


def build_demo_shipments(count: int) -> List[DemoShipment]:
    shipments: List[DemoShipment] = []
    idx = 1
    for corridor in CORRIDOR_PROFILES:
        for profile in RISK_PROFILES:
            shipment_id = f"{corridor['prefix']}-{profile['code']}-{idx:03d}"
            shipments.append(
                DemoShipment(
                    shipment_id=shipment_id,
                    corridor=corridor["corridor"],
                    mode=corridor["mode"],
                    incoterm=corridor["incoterm"],
                    risk_score=profile["risk_score"],
                    risk_level=profile["risk_level"],
                    blocking_gap_count=profile["blocking_gap_count"],
                    days_delayed=profile["days_delayed"],
                    export_history=profile["export_history"],
                )
            )
            idx += 1
            if len(shipments) >= count:
                return shipments
    return shipments


def seed_demo_data(records: List[DemoShipment]) -> None:
    init_db()
    session = SessionLocal()
    now = datetime.utcnow()
    try:
        for record in records:
            _upsert_shipment(session, record)
            _replace_snapshots(session, record)
            snapshot = DocumentHealthSnapshot(
                shipment_id=record.shipment_id,
                corridor_code=record.corridor,
                mode=record.mode,
                incoterm=record.incoterm,
                template_name="DEFAULT_GLOBAL",
                present_count=record.present_count,
                missing_count=TOTAL_DOCS - record.present_count,
                required_total=TOTAL_DOCS,
                optional_total=OPTIONAL_DOCS,
                blocking_gap_count=record.blocking_gap_count,
                completeness_pct=record.completeness_pct,
                risk_score=record.risk_score,
                risk_level=record.risk_level,
                created_at=now - timedelta(days=record.days_delayed),
            )
            session.add(snapshot)
            session.flush()
            _insert_export_history(session, snapshot, record)
        session.commit()
        print(f"Seeded {len(records)} ChainIQ demo shipments.")
    finally:
        session.close()


def _upsert_shipment(session: Session, record: DemoShipment) -> None:
    shipment = session.query(Shipment).filter(Shipment.id == record.shipment_id).first()
    if shipment is None:
        shipment = Shipment(
            id=record.shipment_id,
            corridor_code=record.corridor,
            mode=record.mode,
            incoterm=record.incoterm,
        )
        session.add(shipment)
    else:
        shipment.corridor_code = record.corridor
        shipment.mode = record.mode
        shipment.incoterm = record.incoterm


def _replace_snapshots(session: Session, record: DemoShipment) -> None:
    existing_snapshots = session.query(DocumentHealthSnapshot).filter(DocumentHealthSnapshot.shipment_id == record.shipment_id).all()
    for snapshot in existing_snapshots:
        session.query(SnapshotExportEvent).filter(SnapshotExportEvent.snapshot_id == snapshot.id).delete()
        session.delete(snapshot)
    session.flush()


def _insert_export_history(session: Session, snapshot: DocumentHealthSnapshot, record: DemoShipment) -> None:
    base_time = snapshot.created_at
    for idx, status in enumerate(record.export_history):
        timestamp = base_time + timedelta(hours=idx * 4)
        event = SnapshotExportEvent(
            snapshot_id=snapshot.id,
            target_system="BIS",
            status=status,
            created_at=timestamp,
            updated_at=timestamp,
            claimed_by="demo-worker" if status == "IN_PROGRESS" else None,
            claimed_at=timestamp if status == "IN_PROGRESS" else None,
            last_error="auto-generated demo failure" if status == "FAILED" else None,
            reason=f"delay={record.days_delayed}d gaps={record.blocking_gap_count}",
        )
        session.add(event)
    session.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed ChainIQ demo data")
    parser.add_argument(
        "--count",
        type=int,
        default=24,
        help="Number of demo shipments to seed (default: 24)",
    )
    args = parser.parse_args()
    shipments = build_demo_shipments(args.count)
    seed_demo_data(shipments)


if __name__ == "__main__":
    main()
