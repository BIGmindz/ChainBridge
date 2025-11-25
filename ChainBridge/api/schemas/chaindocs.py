"""Pydantic models for ChainDocs dossier responses."""

from typing import List, Optional

from pydantic import BaseModel


class ChainDocsDocument(BaseModel):
    """Represents a document tracked within the ChainDocs spine."""

    document_id: str
    type: str  # e.g. "BILL_OF_LADING", "COMMERCIAL_INVOICE"
    status: str  # "VERIFIED" | "PRESENT" | "MISSING" | "REJECTED"
    version: int
    hash: str
    mletr: bool


class ChainDocsDossierResponse(BaseModel):
    """API response describing the documents associated with a shipment."""

    shipment_id: str
    documents: List[ChainDocsDocument]
    missing_documents: List[str] = []


class ChainDocsDocumentCreate(BaseModel):
    """Payload for inserting or updating a document."""

    document_id: str
    type: str
    status: str
    version: int = 1
    hash: str
    mletr: bool = False
    reason_code: Optional[str] = None
    created_by_party: Optional[str] = None
