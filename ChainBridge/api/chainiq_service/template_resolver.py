"""Helpers for resolving shipment document requirements."""

from typing import List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from api.models.chaindocs import DocumentType, Shipment, ShipmentDocRequirement

DEFAULT_TEMPLATE_NAME = "DEFAULT_GLOBAL"
DEFAULT_DOCUMENT_TYPES = [
    {
        "code": "BILL_OF_LADING",
        "description": "Bill of Lading",
    },
    {
        "code": "COMMERCIAL_INVOICE",
        "description": "Commercial Invoice",
    },
    {
        "code": "PACKING_LIST",
        "description": "Packing List",
    },
    {
        "code": "INSURANCE_CERTIFICATE",
        "description": "Insurance Certificate",
    },
]


def seed_default_doc_templates(db: Session) -> Sequence[ShipmentDocRequirement]:
    """Ensure baseline document types and requirements exist."""
    for doc in DEFAULT_DOCUMENT_TYPES:
        if not db.get(DocumentType, doc["code"]):
            db.add(
                DocumentType(
                    code=doc["code"],
                    description=doc["description"],
                    mode=None,
                    direction="BOTH",
                )
            )

    db.flush()

    existing_requirements = db.query(ShipmentDocRequirement).filter(ShipmentDocRequirement.template_name == DEFAULT_TEMPLATE_NAME).all()
    if not existing_requirements:
        for doc in DEFAULT_DOCUMENT_TYPES:
            db.add(
                ShipmentDocRequirement(
                    template_name=DEFAULT_TEMPLATE_NAME,
                    corridor_code=None,
                    mode=None,
                    incoterm=None,
                    doc_type_code=doc["code"],
                    required_flag=True,
                    blocking_flag=True,
                    milestone_code=None,
                )
            )
        db.flush()
        existing_requirements = db.query(ShipmentDocRequirement).filter(ShipmentDocRequirement.template_name == DEFAULT_TEMPLATE_NAME).all()

    db.commit()
    return existing_requirements


def resolve_required_docs_for_shipment(
    db: Session,
    shipment: Optional[Shipment],
) -> Tuple[List[ShipmentDocRequirement], Optional[str]]:
    """
    Determine applicable document requirements for a shipment.

    Falls back to DEFAULT_GLOBAL template when no corridor-specific requirements exist.
    """
    requirements: List[ShipmentDocRequirement] = []
    template_name: Optional[str] = None
    if shipment:
        query = db.query(ShipmentDocRequirement)
        if shipment.corridor_code:
            query = query.filter(
                (ShipmentDocRequirement.corridor_code == shipment.corridor_code) | (ShipmentDocRequirement.corridor_code.is_(None))
            )
        else:
            query = query.filter(ShipmentDocRequirement.corridor_code.is_(None))

        if shipment.mode:
            query = query.filter((ShipmentDocRequirement.mode == shipment.mode) | (ShipmentDocRequirement.mode.is_(None)))
        else:
            query = query.filter(ShipmentDocRequirement.mode.is_(None))

        if shipment.incoterm:
            query = query.filter((ShipmentDocRequirement.incoterm == shipment.incoterm) | (ShipmentDocRequirement.incoterm.is_(None)))
        else:
            query = query.filter(ShipmentDocRequirement.incoterm.is_(None))

        requirements = query.all()
        if requirements:
            template_name = requirements[0].template_name

    if not requirements:
        requirements = db.query(ShipmentDocRequirement).filter(ShipmentDocRequirement.template_name == DEFAULT_TEMPLATE_NAME).all()
        if requirements:
            template_name = DEFAULT_TEMPLATE_NAME

    if not requirements:
        requirements = list(seed_default_doc_templates(db))
        template_name = DEFAULT_TEMPLATE_NAME

    return requirements, template_name
