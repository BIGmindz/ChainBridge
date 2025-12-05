"""Base token models and lifecycle enforcement for LST-01 primitives."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4


class TokenError(Exception):
    """Base exception for token errors."""


class TokenValidationError(TokenError):
    """Raised when a token payload fails validation."""


class InvalidTransitionError(TokenError):
    """Raised when a lifecycle transition is not permitted."""


class RelationValidationError(TokenError):
    """Raised when token relations are missing or invalid."""


class BaseToken:
    """Deterministic token representation shared across backend services."""

    TOKEN_TYPE = "BASE"
    VERSION = "1.0"
    INITIAL_STATE = "CREATED"
    STATE_MACHINE: Dict[str, List[str]] = {}
    REQUIRED_FIELDS: Dict[str, Any] = {}
    OPTIONAL_FIELDS: Dict[str, Any] = {}
    REQUIRED_RELATIONS: Iterable[str] = ()

    def __init__(
        self,
        *,
        parent_shipment_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        relations: Optional[Dict[str, Any]] = None,
        state: Optional[str] = None,
        version: Optional[str] = None,
        token_id: Optional[str] = None,
        proof: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        if not parent_shipment_id:
            raise TokenValidationError("parent_shipment_id is required for all tokens")

        self.token_id = token_id or str(uuid4())
        self.token_type = self.TOKEN_TYPE
        self.version = version or self.VERSION
        self.parent_shipment_id = parent_shipment_id
        self.metadata: Dict[str, Any] = deepcopy(metadata) if metadata else {}
        self.state = state or self.INITIAL_STATE
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or self.created_at
        self.relations: Dict[str, Any] = deepcopy(relations) if relations else {}
        self.relations.setdefault("st01_id", parent_shipment_id)

        proof = proof or {}
        self.proof_hash = proof.get("hash")
        self.proof_source = proof.get("source")
        self.proof_metadata = proof.get("metadata")
        self.proof_validated = bool(proof.get("validated"))

        self.validate()

    # ---------------------------------------------------------------------
    # Validation + transitions
    # ---------------------------------------------------------------------
    def validate(self) -> None:
        """Validate the token payload, relations, and lifecycle state."""
        if self.state not in self.STATE_MACHINE:
            raise InvalidTransitionError(f"{self.token_type} has undefined state '{self.state}'")
        self._validate_required_fields()
        self._validate_relations()
        self.validate_state_constraints()

    def _validate_required_fields(self) -> None:
        for field in self.REQUIRED_FIELDS:
            if field not in self.metadata or self.metadata[field] in (None, ""):
                raise TokenValidationError(f"{self.token_type} missing required field '{field}'")

    def _validate_relations(self) -> None:
        required = set(self.REQUIRED_RELATIONS or []) | {"st01_id"}
        missing = [relation for relation in required if relation not in self.relations]
        if missing:
            raise RelationValidationError(f"{self.token_type} missing relation(s): {', '.join(missing)}")
        if self.relations.get("st01_id") != self.parent_shipment_id:
            raise RelationValidationError(f"{self.token_type} relation st01_id must match parent_shipment_id")

    def validate_state_constraints(self) -> None:
        """Hook for subclasses to add state-specific validations."""

    def transition(self, new_state: str) -> None:
        """Transition to a new lifecycle state after validation."""
        allowed = self.STATE_MACHINE.get(self.state, [])
        if new_state not in allowed:
            raise InvalidTransitionError(f"{self.token_type}: cannot transition from {self.state} to {new_state}")
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)
        self.validate_state_constraints()

    # ------------------------------------------------------------------
    # Proof helpers
    # ------------------------------------------------------------------
    def attach_proof(self, *, proof_hash: str, source: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Attach a proof artifact to the token."""
        self.proof_hash = proof_hash
        self.proof_source = source or "SxT"
        self.proof_metadata = deepcopy(metadata) if metadata else None
        self.proof_validated = False
        self.updated_at = datetime.now(timezone.utc)

    def mark_proof_validated(self) -> None:
        """Mark the currently attached proof artifact as validated."""
        if not self.proof_hash:
            raise TokenValidationError("Cannot validate proof before attaching it")
        self.proof_validated = True
        self.updated_at = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_id": self.token_id,
            "type": self.token_type,
            "version": self.version,
            "state": self.state,
            "parent_shipment_id": self.parent_shipment_id,
            "metadata": deepcopy(self.metadata),
            "proof": {
                "hash": self.proof_hash,
                "source": self.proof_source,
                "metadata": deepcopy(self.proof_metadata) if self.proof_metadata else None,
                "validated": self.proof_validated,
            },
            "relations": deepcopy(self.relations),
            "timestamps": {
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
            },
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "BaseToken":
        timestamps = payload.get("timestamps", {})
        created_at = _parse_timestamp(timestamps.get("created_at"))
        updated_at = _parse_timestamp(timestamps.get("updated_at"))
        return cls(
            parent_shipment_id=payload["parent_shipment_id"],
            metadata=payload.get("metadata", {}),
            relations=payload.get("relations"),
            state=payload.get("state"),
            version=payload.get("version"),
            token_id=payload.get("token_id"),
            proof=payload.get("proof"),
            created_at=created_at,
            updated_at=updated_at,
        )


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise TokenValidationError(f"Invalid timestamp format: {value}") from exc
