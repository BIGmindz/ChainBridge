"""Ricardian legal wrapper schema."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, validator


class GoverningLaw(str, Enum):
    UCC_7_106 = "US_UCC_ARTICLE_7_106"
    UK_ETDA_2023 = "UK_ELECTRONIC_TRADE_DOCUMENTS_ACT_2023"


class RicardianAsset(BaseModel):
    """
    The Legal Wrapper. Maps 1:1 to the IPFS JSON.
    """

    name: str = Field(..., description="Shipment ID")
    legal_document_uri: HttpUrl = Field(..., description="IPFS Link to PDF")
    legal_document_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 Hash of the PDF")
    governing_law: GoverningLaw

    # Audit Trail
    validator_node: str
    mint_timestamp: int

    @validator("legal_document_hash")
    def validate_hash(cls, v: str) -> str:
        if len(v) != 64:
            raise ValueError("Invalid SHA-256 Hash")
        # ensure hex
        try:
            int(v, 16)
        except ValueError:
            raise ValueError("Invalid SHA-256 Hash")
        return v
