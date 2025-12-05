"""Pydantic schemas for Ricardian legal instruments."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel


class RicardianInstrumentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    TERMINATED = "TERMINATED"


class RicardianInstrumentType(str, Enum):
    BILL_OF_LADING = "BILL_OF_LADING"
    PLEDGE_AGREEMENT = "PLEDGE_AGREEMENT"
    FINANCING_AGREEMENT = "FINANCING_AGREEMENT"
    OTHER = "OTHER"


class RicardianInstrumentBase(BaseModel):
    instrument_type: RicardianInstrumentType
    physical_reference: str
    pdf_uri: AnyHttpUrl
    pdf_ipfs_uri: Optional[str] = None
    pdf_hash: str
    ricardian_version: str = "v1.1"
    governing_law: str
    supremacy_enabled: bool = True
    traditional_arbitration_uri: Optional[str] = None
    material_adverse_override: bool = False
    smart_contract_chain: Optional[str] = None
    smart_contract_address: Optional[str] = None
    ricardian_metadata: Optional[dict[str, Any]] = None


class RicardianInstrumentCreate(RicardianInstrumentBase):
    created_by: str


class RicardianInstrumentUpdate(BaseModel):
    smart_contract_chain: Optional[str] = None
    smart_contract_address: Optional[str] = None
    last_signed_tx_hash: Optional[str] = None
    status: Optional[RicardianInstrumentStatus] = None
    freeze_reason: Optional[str] = None
    ricardian_metadata: Optional[dict[str, Any]] = None


class RicardianInstrumentResponse(RicardianInstrumentBase):
    id: UUID
    status: RicardianInstrumentStatus
    freeze_reason: Optional[str]
    last_signed_tx_hash: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True
