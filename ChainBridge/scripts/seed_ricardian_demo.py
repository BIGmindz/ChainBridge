"""Seed demo Ricardian instruments for QA."""
from __future__ import annotations

from api.database import SessionLocal, init_db
from api.models.legal import RicardianInstrument


def seed() -> None:
    init_db()
    session = SessionLocal()
    try:
        session.query(RicardianInstrument).delete()
        demos = [
            dict(
                id="RIC-ACTIVE-001",
                instrument_type="BILL_OF_LADING",
                physical_reference="SHIPMENT_ACTIVE_001",
                pdf_uri="https://example.com/legal-active.pdf",
                pdf_hash="hash_active_demo",
                ricardian_version="v1.1",
                governing_law="US_UCC_Article_7",
                status="ACTIVE",
                created_by="seed",
                supremacy_enabled=True,
                material_adverse_override=False,
            ),
            dict(
                id="RIC-FROZEN-001",
                instrument_type="BILL_OF_LADING",
                physical_reference="SHIPMENT_FROZEN_001",
                pdf_uri="https://example.com/legal-frozen.pdf",
                pdf_hash="hash_frozen_demo",
                ricardian_version="v1.1",
                governing_law="US_UCC_Article_7",
                status="FROZEN",
                freeze_reason="Court order XYZ/123",
                created_by="seed",
                supremacy_enabled=True,
                material_adverse_override=True,
            ),
            dict(
                id="RIC-TERM-001",
                instrument_type="BILL_OF_LADING",
                physical_reference="SHIPMENT_TERM_001",
                pdf_uri="https://example.com/legal-term.pdf",
                pdf_hash="hash_term_demo",
                ricardian_version="v1.1",
                governing_law="US_UCC_Article_7",
                status="TERMINATED",
                created_by="seed",
                supremacy_enabled=True,
                material_adverse_override=False,
            ),
        ]
        for payload in demos:
            session.merge(RicardianInstrument(**payload))
        session.merge(
            RicardianInstrument(
                id="RIC-SUPREMACY-01",
                instrument_type="BILL_OF_LADING",
                physical_reference="SHIP-SUPREMACY-001",
                pdf_uri="https://example.com/legal-supremacy.pdf",
                pdf_hash="hash_supremacy_demo",
                ricardian_version="v1.1",
                governing_law="US_UCC_Article_7",
                status="ACTIVE",
                created_by="seed",
                supremacy_enabled=True,
                material_adverse_override=False,
            )
        )
        session.commit()
        print("Seeded Ricardian demo instruments.")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
