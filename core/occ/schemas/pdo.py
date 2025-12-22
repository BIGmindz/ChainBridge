"""
PDO (Proof Decision Object) Schema — Immutable Evidence Records

PAC-CODY-PDO-HARDEN-01: PDO Write-Path Integrity & Immutability

PDOs are immutable, append-only evidence records that capture:
- Decision inputs at write time
- Cryptographic hash seal
- Provenance and lineage
- Verifiable timestamps

IMMUTABILITY CONTRACT:
- PDOs are CREATE-ONCE, APPEND-ONLY
- NO updates permitted (ever)
- NO deletes permitted (ever)
- Hash computed at write time and frozen
- Any tampering attempt must fail loudly

Author: CODY (GID-01) - Backend
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class PDOOutcome(str, Enum):
    """Deterministic outcomes for PDO decisions."""

    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    ESCALATED = "escalated"


class PDOSourceSystem(str, Enum):
    """Valid source systems for PDO generation."""

    GATEWAY = "gateway"
    OCC = "occ"
    CHAINIQ = "chainiq"
    CHAINPAY = "chainpay"
    MANUAL = "manual"


class PDORecord(BaseModel):
    """
    Immutable PDO Record Schema.

    This schema enforces:
    - All fields are frozen after creation
    - Hash is computed deterministically at write time
    - No update or delete operations are possible

    CRITICAL: This model uses frozen=True for immutability.
    """

    model_config = ConfigDict(
        frozen=True,  # CRITICAL: Makes all fields immutable
        extra="forbid",  # Reject unknown fields
        validate_default=True,
        str_strip_whitespace=True,
    )

    # =========================================================================
    # IDENTITY (immutable after creation)
    # =========================================================================

    pdo_id: UUID = Field(
        default_factory=uuid4,
        description="Canonical PDO identifier (immutable)",
    )

    version: str = Field(
        default="1.0",
        description="PDO schema version",
    )

    # =========================================================================
    # DECISION REFERENCES (immutable, establish what this PDO proves)
    # =========================================================================

    input_refs: List[str] = Field(
        default_factory=list,
        description="References to input artifacts/data used in decision",
    )

    decision_ref: str = Field(
        ...,
        min_length=1,
        description="Reference to the decision this PDO records",
    )

    outcome_ref: str = Field(
        ...,
        min_length=1,
        description="Reference to the outcome/result",
    )

    outcome: PDOOutcome = Field(
        ...,
        description="Decision outcome",
    )

    # =========================================================================
    # PROVENANCE (immutable, establishes trust chain)
    # =========================================================================

    source_system: PDOSourceSystem = Field(
        ...,
        description="System that generated this PDO",
    )

    actor: str = Field(
        ...,
        min_length=1,
        description="Actor (agent GID, user ID, or system) that created the PDO",
    )

    actor_type: str = Field(
        default="system",
        description="Actor type: 'agent', 'human', 'system'",
    )

    # =========================================================================
    # TIMESTAMPS (immutable, set at write time only)
    # =========================================================================

    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when PDO was recorded (write-time only)",
    )

    # =========================================================================
    # LINEAGE (immutable, for PDO chains)
    # =========================================================================

    previous_pdo_id: Optional[UUID] = Field(
        default=None,
        description="Previous PDO ID for lineage chains (nullable)",
    )

    correlation_id: Optional[str] = Field(
        default=None,
        description="Correlation ID linking related operations",
    )

    # =========================================================================
    # CRYPTOGRAPHIC SEAL (computed at write time, immutable)
    # =========================================================================

    hash: str = Field(
        default="",
        description="SHA-256 hash seal computed at write time (immutable)",
    )

    hash_algorithm: str = Field(
        default="sha256",
        description="Hash algorithm used for sealing",
    )

    # =========================================================================
    # METADATA (immutable, no derived or computed fields)
    # =========================================================================

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional immutable metadata",
    )

    tags: List[str] = Field(
        default_factory=list,
        description="Immutable categorization tags",
    )

    # =========================================================================
    # HASH COMPUTATION
    # =========================================================================

    def compute_hash(self) -> str:
        """
        Compute deterministic SHA-256 hash of PDO content.

        Hash covers:
        - pdo_id
        - input_refs
        - decision_ref
        - outcome_ref
        - outcome
        - source_system
        - actor
        - recorded_at
        - previous_pdo_id
        - correlation_id

        Returns:
            Hex-encoded SHA-256 hash string
        """
        # Canonical fields for hashing (excludes hash itself)
        canonical_data = {
            "pdo_id": str(self.pdo_id),
            "version": self.version,
            "input_refs": sorted(self.input_refs),
            "decision_ref": self.decision_ref,
            "outcome_ref": self.outcome_ref,
            "outcome": self.outcome.value,
            "source_system": self.source_system.value,
            "actor": self.actor,
            "actor_type": self.actor_type,
            "recorded_at": self.recorded_at.isoformat(),
            "previous_pdo_id": str(self.previous_pdo_id) if self.previous_pdo_id else None,
            "correlation_id": self.correlation_id,
        }

        # Deterministic JSON serialization
        canonical_json = json.dumps(
            canonical_data,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def verify_hash(self) -> bool:
        """
        Verify that the stored hash matches computed hash.

        Returns:
            True if hash is valid, False if tampering detected
        """
        if not self.hash:
            return False
        return self.compute_hash() == self.hash


class PDOCreate(BaseModel):
    """
    Schema for creating a new PDO.

    This is the ONLY way to create a PDO. The store will:
    1. Generate pdo_id if not provided
    2. Set recorded_at to current UTC time
    3. Compute and seal the hash
    4. Return an immutable PDORecord

    NO UPDATE SCHEMA EXISTS BY DESIGN.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    # Required fields
    input_refs: List[str] = Field(
        default_factory=list,
        description="References to input artifacts/data",
    )

    decision_ref: str = Field(
        ...,
        min_length=1,
        description="Reference to the decision",
    )

    outcome_ref: str = Field(
        ...,
        min_length=1,
        description="Reference to the outcome",
    )

    outcome: PDOOutcome = Field(
        ...,
        description="Decision outcome",
    )

    source_system: PDOSourceSystem = Field(
        ...,
        description="System generating this PDO",
    )

    actor: str = Field(
        ...,
        min_length=1,
        description="Actor creating the PDO",
    )

    actor_type: str = Field(
        default="system",
        description="Actor type",
    )

    # Optional fields
    previous_pdo_id: Optional[UUID] = Field(
        default=None,
        description="Previous PDO in chain",
    )

    correlation_id: Optional[str] = Field(
        default=None,
        description="Correlation ID",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    tags: List[str] = Field(
        default_factory=list,
        description="Tags",
    )


class PDOImmutabilityError(Exception):
    """
    Raised when an immutability violation is attempted.

    This exception is thrown for:
    - Attempted updates to existing PDOs
    - Attempted deletes of PDOs
    - Attempted hash modifications
    - Any mutation operation
    """

    def __init__(self, message: str, pdo_id: Optional[UUID] = None) -> None:
        super().__init__(message)
        self.pdo_id = pdo_id


class PDOTamperDetectedError(Exception):
    """
    Raised when PDO tampering is detected.

    This exception indicates:
    - Hash mismatch on verification
    - Unexpected field modifications
    - Integrity violation
    """

    def __init__(
        self,
        message: str,
        pdo_id: Optional[UUID] = None,
        expected_hash: Optional[str] = None,
        actual_hash: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.pdo_id = pdo_id
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash


class PDOListResponse(BaseModel):
    """Response for listing PDOs (read-only)."""

    items: List[PDORecord]
    count: int
    total: int
    limit: Optional[int]
    offset: int
