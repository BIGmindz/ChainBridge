"""
ChainFreight - Customs Clearing Module
=======================================
PAC: PAC-LOG-P140-CHAINFREIGHT
Lead Agent: Atlas (GID-11)
Vertical: ChainFreight (Logistics)

This module handles customs pre-clearance and document verification for
international freight movement.

RISK MITIGATION:
- Pre-clear customs data via API before the ship docks
- OCR pipeline for legacy paper document digitization

INVARIANTS ENFORCED:
- INV-LOG-002: MUST NOT release a container without CUSTOMS_CLEAR flag
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


class CustomsStatus(Enum):
    """Customs clearance lifecycle states."""
    PENDING = "PENDING"              # Awaiting submission
    SUBMITTED = "SUBMITTED"          # Documents submitted
    UNDER_REVIEW = "UNDER_REVIEW"    # Customs reviewing
    ADDITIONAL_DOCS = "ADDITIONAL_DOCS"  # More documents required
    INSPECTION_REQUIRED = "INSPECTION_REQUIRED"  # Physical inspection needed
    HOLD = "HOLD"                    # Government hold
    CLEARED = "CLEARED"              # Cleared for release
    REJECTED = "REJECTED"            # Clearance denied


class DocumentType(Enum):
    """Types of customs documents."""
    BILL_OF_LADING = "BILL_OF_LADING"
    COMMERCIAL_INVOICE = "COMMERCIAL_INVOICE"
    PACKING_LIST = "PACKING_LIST"
    CERTIFICATE_OF_ORIGIN = "CERTIFICATE_OF_ORIGIN"
    PHYTOSANITARY_CERT = "PHYTOSANITARY_CERT"
    DANGEROUS_GOODS_DECL = "DANGEROUS_GOODS_DECL"
    IMPORT_LICENSE = "IMPORT_LICENSE"
    INSURANCE_CERT = "INSURANCE_CERT"
    HS_CLASSIFICATION = "HS_CLASSIFICATION"


@dataclass
class CustomsDocument:
    """A document submitted for customs clearance."""
    doc_id: str
    doc_type: DocumentType
    filename: str
    uploaded_at: datetime
    file_hash: str  # SHA256 of document content
    verified: bool = False
    ocr_extracted: bool = False  # True if digitized from paper
    ocr_data: Optional[dict] = None
    
    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "doc_type": self.doc_type.value,
            "filename": self.filename,
            "uploaded_at": self.uploaded_at.isoformat(),
            "file_hash": self.file_hash,
            "verified": self.verified,
            "ocr_extracted": self.ocr_extracted,
            "ocr_data": self.ocr_data
        }


@dataclass
class HSCode:
    """Harmonized System code for cargo classification."""
    code: str  # e.g., "8471.30" for laptops
    description: str
    chapter: str
    duty_rate_pct: float
    requires_license: bool = False
    restricted: bool = False
    
    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "description": self.description,
            "chapter": self.chapter,
            "duty_rate_pct": self.duty_rate_pct,
            "requires_license": self.requires_license,
            "restricted": self.restricted
        }


@dataclass
class DutyCalculation:
    """Calculated duties and taxes for a shipment."""
    cargo_value_usd: float
    duty_rate_pct: float
    duty_amount_usd: float
    vat_rate_pct: float
    vat_amount_usd: float
    other_fees_usd: float
    total_payable_usd: float
    currency: str = "USD"
    
    def to_dict(self) -> dict:
        return {
            "cargo_value_usd": self.cargo_value_usd,
            "duty_rate_pct": self.duty_rate_pct,
            "duty_amount_usd": self.duty_amount_usd,
            "vat_rate_pct": self.vat_rate_pct,
            "vat_amount_usd": self.vat_amount_usd,
            "other_fees_usd": self.other_fees_usd,
            "total_payable_usd": self.total_payable_usd,
            "currency": self.currency
        }


class CustomsClearance:
    """
    Customs Clearance Handler for ChainFreight.
    
    Manages the entire customs process:
    1. Document collection and verification
    2. HS code classification
    3. Duty calculation
    4. Pre-clearance submission
    5. Status tracking
    
    RISK MITIGATION: Pre-clear before vessel arrives to minimize port delays.
    """
    
    def __init__(self, bol_id: str, destination_country: str):
        self.clearance_id: str = str(uuid4())
        self.bol_id: str = bol_id
        self.destination_country: str = destination_country
        self.status: CustomsStatus = CustomsStatus.PENDING
        self.created_at: datetime = datetime.utcnow()
        self.updated_at: datetime = datetime.utcnow()
        
        # Documents
        self.documents: list[CustomsDocument] = []
        self.required_documents: list[DocumentType] = self._get_required_docs()
        
        # Classification
        self.hs_codes: list[HSCode] = []
        
        # Duties
        self.duty_calculation: Optional[DutyCalculation] = None
        self.duty_paid: bool = False
        self.payment_reference: Optional[str] = None
        
        # Government interaction
        self.customs_reference: Optional[str] = None
        self.customs_office: Optional[str] = None
        self.inspection_date: Optional[datetime] = None
        self.hold_reason: Optional[str] = None
        
        # Timeline
        self.submitted_at: Optional[datetime] = None
        self.cleared_at: Optional[datetime] = None
        
        # Audit trail
        self.audit_log: list[dict] = []
    
    def _get_required_docs(self) -> list[DocumentType]:
        """Get required documents based on destination country."""
        # Base requirements for all shipments
        base_docs = [
            DocumentType.BILL_OF_LADING,
            DocumentType.COMMERCIAL_INVOICE,
            DocumentType.PACKING_LIST
        ]
        
        # Country-specific requirements (simplified)
        country_specific = {
            "US": [DocumentType.CERTIFICATE_OF_ORIGIN],
            "EU": [DocumentType.CERTIFICATE_OF_ORIGIN],
            "CN": [DocumentType.CERTIFICATE_OF_ORIGIN, DocumentType.IMPORT_LICENSE],
            "AU": [DocumentType.PHYTOSANITARY_CERT],
        }
        
        return base_docs + country_specific.get(self.destination_country, [])
    
    def add_document(
        self,
        doc_type: DocumentType,
        filename: str,
        content_hash: str,
        ocr_extracted: bool = False,
        ocr_data: Optional[dict] = None
    ) -> CustomsDocument:
        """Add a document to the clearance package."""
        doc = CustomsDocument(
            doc_id=str(uuid4()),
            doc_type=doc_type,
            filename=filename,
            uploaded_at=datetime.utcnow(),
            file_hash=content_hash,
            ocr_extracted=ocr_extracted,
            ocr_data=ocr_data
        )
        self.documents.append(doc)
        self._log_event("DOCUMENT_ADDED", {"doc_type": doc_type.value, "filename": filename})
        self.updated_at = datetime.utcnow()
        return doc
    
    def verify_document(self, doc_id: str) -> bool:
        """Mark a document as verified."""
        for doc in self.documents:
            if doc.doc_id == doc_id:
                doc.verified = True
                self._log_event("DOCUMENT_VERIFIED", {"doc_id": doc_id})
                return True
        return False
    
    def classify_cargo(self, hs_code: HSCode) -> None:
        """Add HS classification for cargo items."""
        self.hs_codes.append(hs_code)
        self._log_event("HS_CLASSIFIED", {"code": hs_code.code, "description": hs_code.description})
        self.updated_at = datetime.utcnow()
    
    def calculate_duties(
        self,
        cargo_value_usd: float,
        vat_rate_pct: float = 0.0,
        other_fees_usd: float = 0.0
    ) -> DutyCalculation:
        """Calculate duties and taxes based on HS codes and cargo value."""
        if not self.hs_codes:
            raise ValueError("No HS codes classified - cannot calculate duties")
        
        # Use highest duty rate from classified items
        max_duty_rate = max(hs.duty_rate_pct for hs in self.hs_codes)
        duty_amount = cargo_value_usd * (max_duty_rate / 100)
        
        # VAT calculated on (cargo value + duty)
        vat_base = cargo_value_usd + duty_amount
        vat_amount = vat_base * (vat_rate_pct / 100)
        
        total = duty_amount + vat_amount + other_fees_usd
        
        self.duty_calculation = DutyCalculation(
            cargo_value_usd=cargo_value_usd,
            duty_rate_pct=max_duty_rate,
            duty_amount_usd=round(duty_amount, 2),
            vat_rate_pct=vat_rate_pct,
            vat_amount_usd=round(vat_amount, 2),
            other_fees_usd=other_fees_usd,
            total_payable_usd=round(total, 2)
        )
        
        self._log_event("DUTIES_CALCULATED", self.duty_calculation.to_dict())
        return self.duty_calculation
    
    def check_ready_to_submit(self) -> dict:
        """Check if all requirements are met for submission."""
        missing_docs = []
        for req_doc in self.required_documents:
            if not any(d.doc_type == req_doc for d in self.documents):
                missing_docs.append(req_doc.value)
        
        unverified = [d.doc_id for d in self.documents if not d.verified]
        
        issues = []
        if missing_docs:
            issues.append(f"Missing documents: {', '.join(missing_docs)}")
        if unverified:
            issues.append(f"{len(unverified)} document(s) not verified")
        if not self.hs_codes:
            issues.append("No HS codes classified")
        if not self.duty_calculation:
            issues.append("Duties not calculated")
        
        return {
            "ready": len(issues) == 0,
            "issues": issues,
            "documents_submitted": len(self.documents),
            "documents_required": len(self.required_documents),
            "hs_codes_classified": len(self.hs_codes)
        }
    
    def submit(self, customs_office: str) -> str:
        """Submit clearance request to customs authority."""
        readiness = self.check_ready_to_submit()
        if not readiness["ready"]:
            raise ValueError(f"Not ready to submit: {readiness['issues']}")
        
        self.customs_office = customs_office
        self.submitted_at = datetime.utcnow()
        self.status = CustomsStatus.SUBMITTED
        
        # Generate customs reference number
        ref_data = f"{self.clearance_id}:{customs_office}:{self.submitted_at.isoformat()}"
        self.customs_reference = f"CUS-{hashlib.sha256(ref_data.encode()).hexdigest()[:12].upper()}"
        
        self._log_event("SUBMITTED", {
            "customs_office": customs_office,
            "reference": self.customs_reference
        })
        self.updated_at = datetime.utcnow()
        
        return self.customs_reference
    
    def update_status(self, new_status: CustomsStatus, reason: Optional[str] = None) -> None:
        """Update clearance status (typically from customs API callback)."""
        old_status = self.status
        self.status = new_status
        
        if new_status == CustomsStatus.HOLD:
            self.hold_reason = reason
        elif new_status == CustomsStatus.CLEARED:
            self.cleared_at = datetime.utcnow()
        
        self._log_event("STATUS_CHANGE", {
            "from": old_status.value,
            "to": new_status.value,
            "reason": reason
        })
        self.updated_at = datetime.utcnow()
    
    def record_duty_payment(self, payment_reference: str) -> None:
        """Record that duties have been paid."""
        if not self.duty_calculation:
            raise ValueError("No duties calculated")
        
        self.duty_paid = True
        self.payment_reference = payment_reference
        self._log_event("DUTY_PAID", {
            "amount": self.duty_calculation.total_payable_usd,
            "reference": payment_reference
        })
        self.updated_at = datetime.utcnow()
    
    def is_cleared(self) -> bool:
        """
        Check if customs is fully cleared.
        
        INVARIANT INV-LOG-002: This is the gate for container release.
        """
        return (
            self.status == CustomsStatus.CLEARED and
            self.duty_paid and
            self.cleared_at is not None
        )
    
    def _log_event(self, event_type: str, data: dict) -> None:
        """Add event to audit log."""
        self.audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": data
        })
    
    def to_dict(self) -> dict:
        """Serialize clearance to dictionary."""
        return {
            "clearance_id": self.clearance_id,
            "bol_id": self.bol_id,
            "destination_country": self.destination_country,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "documents": [d.to_dict() for d in self.documents],
            "required_documents": [d.value for d in self.required_documents],
            "hs_codes": [hs.to_dict() for hs in self.hs_codes],
            "duty_calculation": self.duty_calculation.to_dict() if self.duty_calculation else None,
            "duty_paid": self.duty_paid,
            "payment_reference": self.payment_reference,
            "customs_reference": self.customs_reference,
            "customs_office": self.customs_office,
            "hold_reason": self.hold_reason,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "cleared_at": self.cleared_at.isoformat() if self.cleared_at else None,
            "is_cleared": self.is_cleared(),
            "audit_log": self.audit_log
        }
    
    def to_json(self) -> str:
        """Serialize clearance to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class OCRPipeline:
    """
    OCR Pipeline for digitizing legacy paper documents.
    
    RISK MITIGATION: Real-world logistics still runs on PDF/Paper.
    Atlas builds this pipeline to convert legacy paperwork into JSON.
    
    In production, this would integrate with:
    - Tesseract OCR
    - Google Cloud Vision
    - AWS Textract
    - Azure Form Recognizer
    """
    
    def __init__(self):
        self.supported_formats = ["pdf", "png", "jpg", "jpeg", "tiff"]
        self.extraction_templates = self._load_templates()
    
    def _load_templates(self) -> dict:
        """Load extraction templates for different document types."""
        return {
            DocumentType.BILL_OF_LADING: {
                "fields": ["bol_number", "shipper", "consignee", "vessel", 
                          "port_of_loading", "port_of_discharge", "container_no"],
                "regions": {}  # Would define bounding boxes in production
            },
            DocumentType.COMMERCIAL_INVOICE: {
                "fields": ["invoice_number", "seller", "buyer", "items", 
                          "total_value", "currency", "incoterm"],
                "regions": {}
            },
            DocumentType.PACKING_LIST: {
                "fields": ["packages", "gross_weight", "net_weight", 
                          "dimensions", "marks_and_numbers"],
                "regions": {}
            }
        }
    
    def process_document(
        self,
        file_path: str,
        doc_type: DocumentType
    ) -> dict:
        """
        Process a document through OCR and extract structured data.
        
        In production, this would:
        1. Load the document image/PDF
        2. Pre-process (deskew, denoise)
        3. Run OCR to extract text
        4. Apply template matching to extract fields
        5. Validate extracted data
        6. Return structured JSON
        
        For now, returns a mock extraction result.
        """
        # Mock OCR result for development
        mock_results = {
            DocumentType.BILL_OF_LADING: {
                "bol_number": "MOCK-BOL-001",
                "shipper": "Extracted Shipper Name",
                "consignee": "Extracted Consignee Name",
                "vessel": "MSC OSCAR",
                "port_of_loading": "SHANGHAI",
                "port_of_discharge": "LOS ANGELES",
                "container_no": "MSCU1234567",
                "confidence": 0.89
            },
            DocumentType.COMMERCIAL_INVOICE: {
                "invoice_number": "INV-2026-001",
                "seller": "Extracted Seller",
                "buyer": "Extracted Buyer",
                "total_value": 125000.00,
                "currency": "USD",
                "incoterm": "FOB",
                "confidence": 0.92
            },
            DocumentType.PACKING_LIST: {
                "packages": 42,
                "gross_weight": 18500.0,
                "net_weight": 17800.0,
                "confidence": 0.87
            }
        }
        
        template = self.extraction_templates.get(doc_type)
        if not template:
            raise ValueError(f"No template for document type: {doc_type.value}")
        
        return {
            "file_path": file_path,
            "doc_type": doc_type.value,
            "extracted_at": datetime.utcnow().isoformat(),
            "ocr_engine": "MOCK_OCR_V1",
            "data": mock_results.get(doc_type, {}),
            "validation_status": "PENDING_REVIEW"
        }
    
    def validate_extraction(self, extraction: dict, expected: dict) -> dict:
        """Validate OCR extraction against expected values."""
        mismatches = []
        for field, expected_value in expected.items():
            extracted_value = extraction.get("data", {}).get(field)
            if extracted_value != expected_value:
                mismatches.append({
                    "field": field,
                    "expected": expected_value,
                    "extracted": extracted_value
                })
        
        return {
            "valid": len(mismatches) == 0,
            "mismatches": mismatches,
            "confidence": extraction.get("data", {}).get("confidence", 0)
        }


# Atlas Command Interface
def atlas_create_clearance(bol_id: str, destination_country: str) -> CustomsClearance:
    """
    Atlas (GID-11) Command: Create a customs clearance case.
    """
    return CustomsClearance(bol_id=bol_id, destination_country=destination_country)


def atlas_preClear(clearance: CustomsClearance, customs_office: str) -> dict:
    """
    Atlas (GID-11) Command: Submit pre-clearance before vessel arrival.
    
    RISK MITIGATION: Pre-clear customs data via API before the ship docks.
    """
    readiness = clearance.check_ready_to_submit()
    if not readiness["ready"]:
        return {
            "success": False,
            "status": "NOT_READY",
            "issues": readiness["issues"]
        }
    
    ref = clearance.submit(customs_office)
    return {
        "success": True,
        "status": "SUBMITTED",
        "customs_reference": ref,
        "office": customs_office,
        "submitted_at": clearance.submitted_at.isoformat()
    }


def atlas_check_release_gate(clearance: CustomsClearance) -> dict:
    """
    Atlas (GID-11) Command: Check if container can be released.
    
    INVARIANT INV-LOG-002: MUST NOT release without CUSTOMS_CLEAR flag.
    """
    can_release = clearance.is_cleared()
    
    blockers = []
    if clearance.status != CustomsStatus.CLEARED:
        blockers.append(f"Status is {clearance.status.value}, not CLEARED")
    if not clearance.duty_paid:
        blockers.append("Duties not paid")
    if clearance.hold_reason:
        blockers.append(f"Hold: {clearance.hold_reason}")
    
    return {
        "can_release": can_release,
        "status": clearance.status.value,
        "duty_paid": clearance.duty_paid,
        "blockers": blockers,
        "customs_reference": clearance.customs_reference
    }
