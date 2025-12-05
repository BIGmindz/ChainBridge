"""
ChainBridge Token Router

Maps events to LST-01 token types and enforces lifecycle transitions.
Deterministic routing from normalized events to token state machines.

Version: 1.0.0
Owner: GID-01 Cody (Senior Backend Engineer)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from chainbridge.tokens.base_token import (
    BaseToken,
    InvalidTransitionError,
    RelationValidationError,
    TokenValidationError,
)
from chainbridge.tokens.registry import TokenRegistry

from .schemas import (
    BaseEvent,
    EDI214Payload,
    EventType,
    GovernancePayload,
)

logger = logging.getLogger(__name__)


# =============================================================================
# ROUTING RULES
# =============================================================================


class TokenImpact(str, Enum):
    """Types of token impacts an event can have."""

    CREATE = "CREATE"
    TRANSITION = "TRANSITION"
    ATTACH_PROOF = "ATTACH_PROOF"
    ADD_RELATION = "ADD_RELATION"
    UPDATE_METADATA = "UPDATE_METADATA"
    NO_OP = "NO_OP"


@dataclass
class TokenRoutingRule:
    """Defines how an event maps to token operations."""

    event_type: EventType
    target_token_type: str
    impact: TokenImpact
    required_state: Optional[str] = None  # Current state required for transition
    new_state: Optional[str] = None  # Target state after transition
    requires_proof: bool = False
    requires_governance: bool = False
    metadata_fields: List[str] = field(default_factory=list)


# Master routing table: Event Type → Token Type → Impact
ROUTING_RULES: Dict[EventType, List[TokenRoutingRule]] = {
    # IoT Telemetry → MT-01 generation
    EventType.IOT_TELEMETRY: [
        TokenRoutingRule(
            event_type=EventType.IOT_TELEMETRY,
            target_token_type="MT-01",
            impact=TokenImpact.CREATE,
            metadata_fields=["milestone_type", "timestamp", "location", "telemetry_snapshot"],
        ),
    ],
    # IoT Geofence Enter → MT-01 (Terminal Arrived) or ST-01 transition
    EventType.IOT_GEOFENCE_ENTER: [
        TokenRoutingRule(
            event_type=EventType.IOT_GEOFENCE_ENTER,
            target_token_type="MT-01",
            impact=TokenImpact.CREATE,
            metadata_fields=["milestone_type", "timestamp", "location"],
        ),
        TokenRoutingRule(
            event_type=EventType.IOT_GEOFENCE_ENTER,
            target_token_type="ST-01",
            impact=TokenImpact.TRANSITION,
            required_state="IN_TRANSIT",
            new_state="ARRIVED",
        ),
    ],
    # IoT Geofence Exit → MT-01 (Departure) or ST-01 transition
    EventType.IOT_GEOFENCE_EXIT: [
        TokenRoutingRule(
            event_type=EventType.IOT_GEOFENCE_EXIT,
            target_token_type="MT-01",
            impact=TokenImpact.CREATE,
            metadata_fields=["milestone_type", "timestamp", "location"],
        ),
        TokenRoutingRule(
            event_type=EventType.IOT_GEOFENCE_EXIT,
            target_token_type="ST-01",
            impact=TokenImpact.TRANSITION,
            required_state="DISPATCHED",
            new_state="IN_TRANSIT",
        ),
    ],
    # IoT Critical Alert → Update existing MT-01 or flag anomaly
    EventType.IOT_ALERT_CRITICAL: [
        TokenRoutingRule(
            event_type=EventType.IOT_ALERT_CRITICAL,
            target_token_type="MT-01",
            impact=TokenImpact.UPDATE_METADATA,
            metadata_fields=["alert_type", "severity", "message"],
        ),
    ],
    # EDI 214 Status Update → ST-01 transition
    EventType.EDI_STATUS_UPDATE: [
        TokenRoutingRule(
            event_type=EventType.EDI_STATUS_UPDATE,
            target_token_type="ST-01",
            impact=TokenImpact.TRANSITION,
        ),
        TokenRoutingRule(
            event_type=EventType.EDI_STATUS_UPDATE,
            target_token_type="MT-01",
            impact=TokenImpact.CREATE,
            metadata_fields=["milestone_type", "timestamp", "location"],
        ),
    ],
    # EDI 204 Tender Request → ST-01 creation
    EventType.EDI_TENDER_REQUEST: [
        TokenRoutingRule(
            event_type=EventType.EDI_TENDER_REQUEST,
            target_token_type="ST-01",
            impact=TokenImpact.CREATE,
            metadata_fields=["origin", "destination", "carrier_id", "broker_id", "customer_id"],
        ),
        TokenRoutingRule(
            event_type=EventType.EDI_TENDER_REQUEST,
            target_token_type="QT-01",
            impact=TokenImpact.CREATE,
            metadata_fields=["rate_amount", "rate_currency", "equipment_type"],
        ),
    ],
    # Token Transition → Direct token state change
    EventType.TOKEN_TRANSITION: [
        TokenRoutingRule(
            event_type=EventType.TOKEN_TRANSITION,
            target_token_type="*",  # Any token type
            impact=TokenImpact.TRANSITION,
        ),
    ],
    # Token Proof Attached → Proof attachment
    EventType.TOKEN_PROOF_ATTACHED: [
        TokenRoutingRule(
            event_type=EventType.TOKEN_PROOF_ATTACHED,
            target_token_type="*",
            impact=TokenImpact.ATTACH_PROOF,
            requires_proof=True,
        ),
    ],
    # Proof Computed → Update token with proof
    EventType.PROOF_COMPUTED: [
        TokenRoutingRule(
            event_type=EventType.PROOF_COMPUTED,
            target_token_type="*",
            impact=TokenImpact.ATTACH_PROOF,
            requires_proof=True,
        ),
    ],
    # Proof Validated → Transition token (e.g., AT-02 PROOF_ATTACHED → VERIFIED)
    EventType.PROOF_VALIDATED: [
        TokenRoutingRule(
            event_type=EventType.PROOF_VALIDATED,
            target_token_type="AT-02",
            impact=TokenImpact.TRANSITION,
            required_state="PROOF_ATTACHED",
            new_state="VERIFIED",
            requires_governance=True,
        ),
    ],
    # Governance Approval → Transition token
    EventType.GOVERNANCE_APPROVAL: [
        TokenRoutingRule(
            event_type=EventType.GOVERNANCE_APPROVAL,
            target_token_type="*",
            impact=TokenImpact.TRANSITION,
            requires_governance=True,
        ),
    ],
    # Settlement Initiated → PT-01 creation
    EventType.SETTLEMENT_INITIATED: [
        TokenRoutingRule(
            event_type=EventType.SETTLEMENT_INITIATED,
            target_token_type="PT-01",
            impact=TokenImpact.CREATE,
            metadata_fields=["payment_reference", "currency", "amount", "escrow_account"],
        ),
    ],
    # Settlement Complete → PT-01 and ST-01 transitions
    EventType.SETTLEMENT_COMPLETE: [
        TokenRoutingRule(
            event_type=EventType.SETTLEMENT_COMPLETE,
            target_token_type="PT-01",
            impact=TokenImpact.TRANSITION,
            new_state="COMPLETE",
        ),
        TokenRoutingRule(
            event_type=EventType.SETTLEMENT_COMPLETE,
            target_token_type="ST-01",
            impact=TokenImpact.TRANSITION,
            required_state="DELIVERED",
            new_state="SETTLED",
        ),
    ],
}


# EDI 214 Status Code → ST-01 State Mapping
EDI_STATUS_TO_ST01_STATE: Dict[str, Tuple[str, str]] = {
    "AG": ("CREATED", "DISPATCHED"),  # Carrier pickup
    "AF": ("DISPATCHED", "IN_TRANSIT"),  # Arrived at pickup, departed
    "X1": ("IN_TRANSIT", "ARRIVED"),  # Arrived at destination
    "D1": ("ARRIVED", "DELIVERED"),  # Delivered
    "X3": ("IN_TRANSIT", "IN_TRANSIT"),  # Departed intermediate (no state change)
    "X6": ("IN_TRANSIT", "IN_TRANSIT"),  # Arrived at checkpoint
}

# EDI 214 Status Code → MT-01 Milestone Type
EDI_STATUS_TO_MILESTONE: Dict[str, str] = {
    "AG": "PICKUP_DEPARTED",
    "AF": "IN_TRANSIT",
    "X1": "TERMINAL_ARRIVED",
    "X3": "TERMINAL_DEPARTED",
    "X6": "CHECKPOINT_ARRIVED",
    "D1": "DELIVERED",
}


# =============================================================================
# TOKEN ROUTING RESULT
# =============================================================================


@dataclass
class TokenRoutingResult:
    """Result of token routing operation."""

    success: bool
    tokens_created: List[BaseToken] = field(default_factory=list)
    tokens_transitioned: List[Tuple[str, str, str]] = field(default_factory=list)  # (token_id, from_state, to_state)
    tokens_updated: List[str] = field(default_factory=list)
    proof_required: bool = False
    governance_required: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    downstream_events: List[BaseEvent] = field(default_factory=list)


# =============================================================================
# TOKEN ROUTER
# =============================================================================


class TokenRouter:
    """
    Routes events to LST-01 token operations.

    Enforces:
    - Lifecycle state machine rules
    - Proof requirements
    - Governance gates
    - Relation integrity
    """

    def __init__(
        self,
        token_store: Optional[Dict[str, BaseToken]] = None,
        governance_enabled: bool = True,
    ):
        """
        Initialize token router.

        Args:
            token_store: In-memory token store (for testing). Production uses DB.
            governance_enabled: Enable ALEX governance checks.
        """
        self._token_store: Dict[str, BaseToken] = token_store or {}
        self._shipment_tokens: Dict[str, Dict[str, List[str]]] = {}  # shipment_id → {token_type → [token_ids]}
        self._governance_enabled = governance_enabled

    # -------------------------------------------------------------------------
    # Public Interface
    # -------------------------------------------------------------------------

    async def route(self, event: BaseEvent) -> TokenRoutingResult:
        """
        Route an event to appropriate token operations.

        Args:
            event: The event to route.

        Returns:
            TokenRoutingResult with created/transitioned tokens.
        """
        result = TokenRoutingResult(success=True)

        rules = ROUTING_RULES.get(event.event_type, [])
        if not rules:
            logger.warning("No routing rules for event type: %s", event.event_type)
            result.warnings.append(f"No routing rules for {event.event_type}")
            return result

        for rule in rules:
            try:
                await self._apply_rule(event, rule, result)
            except (TokenValidationError, InvalidTransitionError, RelationValidationError) as e:
                result.errors.append(f"Rule {rule.target_token_type}: {e}")
                result.success = False
                logger.error("Token routing error: %s", e)

        return result

    async def get_token(self, token_id: str) -> Optional[BaseToken]:
        """Retrieve a token by ID."""
        return self._token_store.get(token_id)

    async def get_shipment_tokens(self, shipment_id: str, token_type: Optional[str] = None) -> List[BaseToken]:
        """Retrieve all tokens for a shipment, optionally filtered by type."""
        token_map = self._shipment_tokens.get(shipment_id, {})
        if token_type:
            token_ids = token_map.get(token_type, [])
        else:
            token_ids = [tid for tids in token_map.values() for tid in tids]
        return [self._token_store[tid] for tid in token_ids if tid in self._token_store]

    # -------------------------------------------------------------------------
    # Rule Application
    # -------------------------------------------------------------------------

    async def _apply_rule(self, event: BaseEvent, rule: TokenRoutingRule, result: TokenRoutingResult) -> None:
        """Apply a single routing rule."""
        if rule.impact == TokenImpact.CREATE:
            await self._handle_create(event, rule, result)
        elif rule.impact == TokenImpact.TRANSITION:
            await self._handle_transition(event, rule, result)
        elif rule.impact == TokenImpact.ATTACH_PROOF:
            await self._handle_attach_proof(event, rule, result)
        elif rule.impact == TokenImpact.UPDATE_METADATA:
            await self._handle_update_metadata(event, rule, result)
        elif rule.impact == TokenImpact.ADD_RELATION:
            await self._handle_add_relation(event, rule, result)

    async def _handle_create(self, event: BaseEvent, rule: TokenRoutingRule, result: TokenRoutingResult) -> None:
        """Handle token creation."""
        token_type = rule.target_token_type
        token_cls = TokenRegistry.get(token_type)

        # Build metadata from event payload
        metadata = self._extract_metadata(event, rule)

        # Build relations
        relations = {"st01_id": event.parent_shipment_id}
        if hasattr(event, "device_id") and event.device_id:
            relations["iot_event_id"] = event.event_id
        if event.event_type in (EventType.EDI_STATUS_UPDATE, EventType.EDI_TENDER_REQUEST):
            relations["seeburger_event_id"] = event.event_id

        try:
            token = token_cls(
                parent_shipment_id=event.parent_shipment_id,
                metadata=metadata,
                relations=relations,
            )
            self._store_token(token)
            result.tokens_created.append(token)
            logger.info(
                "Created %s token %s for shipment %s",
                token_type,
                token.token_id,
                event.parent_shipment_id,
            )
        except TokenValidationError as e:
            result.errors.append(f"Failed to create {token_type}: {e}")
            raise

    async def _handle_transition(self, event: BaseEvent, rule: TokenRoutingRule, result: TokenRoutingResult) -> None:
        """Handle token state transition."""
        # Determine target token and new state
        target_token_type = self._resolve_token_type(event, rule)
        target_token = await self._find_target_token(event, target_token_type, rule)

        if not target_token:
            result.warnings.append(f"No {target_token_type} token found for transition")
            return

        # Determine new state
        new_state = self._resolve_new_state(event, rule, target_token)
        if not new_state:
            result.warnings.append("Could not determine new state for transition")
            return

        # Check governance requirement
        if rule.requires_governance and self._governance_enabled:
            if not self._check_governance(event, target_token, new_state):
                result.governance_required = True
                result.warnings.append(f"Governance approval required for {target_token_type} transition to {new_state}")
                return

        # Perform transition
        previous_state = target_token.state
        try:
            target_token.transition(new_state)
            result.tokens_transitioned.append((target_token.token_id, previous_state, new_state))
            logger.info(
                "Transitioned %s %s: %s → %s",
                target_token_type,
                target_token.token_id,
                previous_state,
                new_state,
            )
        except InvalidTransitionError as e:
            result.errors.append(f"Invalid transition: {e}")
            raise

    async def _handle_attach_proof(self, event: BaseEvent, rule: TokenRoutingRule, result: TokenRoutingResult) -> None:
        """Handle proof attachment to token."""
        payload = event.payload
        if hasattr(payload, "target_token_id"):
            token = self._token_store.get(payload.target_token_id)
        else:
            token = await self._find_target_token(event, self._resolve_token_type(event, rule), rule)

        if not token:
            result.warnings.append("No token found for proof attachment")
            return

        proof_hash = getattr(payload, "proof_hash", None)
        if not proof_hash:
            result.errors.append("Proof hash missing in event payload")
            return

        proof_metadata = {
            "proof_id": getattr(payload, "proof_id", None),
            "proof_type": getattr(payload, "proof_type", None),
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

        token.attach_proof(
            proof_hash=proof_hash,
            source="SxT",
            metadata=proof_metadata,
        )
        result.tokens_updated.append(token.token_id)
        result.proof_required = True
        logger.info("Attached proof to token %s", token.token_id)

    async def _handle_update_metadata(self, event: BaseEvent, rule: TokenRoutingRule, result: TokenRoutingResult) -> None:
        """Handle metadata update on existing token."""
        target_token = await self._find_target_token(event, self._resolve_token_type(event, rule), rule)

        if not target_token:
            result.warnings.append("No token found for metadata update")
            return

        metadata_updates = self._extract_metadata(event, rule)
        for key, value in metadata_updates.items():
            target_token.metadata[key] = value
        target_token.updated_at = datetime.now(timezone.utc)

        result.tokens_updated.append(target_token.token_id)
        logger.info("Updated metadata on token %s", target_token.token_id)

    async def _handle_add_relation(self, event: BaseEvent, rule: TokenRoutingRule, result: TokenRoutingResult) -> None:
        """Handle adding relation to token."""
        # Implementation depends on specific relation requirements
        pass

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _store_token(self, token: BaseToken) -> None:
        """Store token in memory."""
        self._token_store[token.token_id] = token

        # Index by shipment
        if token.parent_shipment_id not in self._shipment_tokens:
            self._shipment_tokens[token.parent_shipment_id] = {}
        shipment_map = self._shipment_tokens[token.parent_shipment_id]
        if token.token_type not in shipment_map:
            shipment_map[token.token_type] = []
        shipment_map[token.token_type].append(token.token_id)

    def _resolve_token_type(self, event: BaseEvent, rule: TokenRoutingRule) -> str:
        """Resolve token type from rule or event payload."""
        if rule.target_token_type != "*":
            return rule.target_token_type

        # For wildcard rules, get from event payload
        payload = event.payload
        if hasattr(payload, "token_type"):
            return payload.token_type
        if hasattr(payload, "target_token_type"):
            return payload.target_token_type

        raise TokenValidationError("Cannot resolve target token type")

    async def _find_target_token(self, event: BaseEvent, token_type: str, rule: TokenRoutingRule) -> Optional[BaseToken]:
        """Find the target token for an operation."""
        # Check if event payload specifies token_id directly
        payload = event.payload
        if hasattr(payload, "token_id"):
            return self._token_store.get(payload.token_id)
        if hasattr(payload, "target_token_id"):
            return self._token_store.get(payload.target_token_id)

        # Find by shipment and type
        tokens = await self.get_shipment_tokens(event.parent_shipment_id, token_type)
        if not tokens:
            return None

        # For transitions, find token in required state
        if rule.required_state:
            for token in tokens:
                if token.state == rule.required_state:
                    return token
            return None

        # Return most recent token of type
        return tokens[-1] if tokens else None

    def _resolve_new_state(self, event: BaseEvent, rule: TokenRoutingRule, token: BaseToken) -> Optional[str]:
        """Resolve the new state for a transition."""
        # Rule specifies exact new state
        if rule.new_state:
            return rule.new_state

        # Event payload specifies new state
        payload = event.payload
        if hasattr(payload, "new_state"):
            return payload.new_state

        # EDI status mapping
        if event.event_type == EventType.EDI_STATUS_UPDATE:
            if isinstance(payload, EDI214Payload):
                status_code = payload.status_code
                if status_code in EDI_STATUS_TO_ST01_STATE:
                    required, new = EDI_STATUS_TO_ST01_STATE[status_code]
                    if token.state == required:
                        return new

        return None

    def _extract_metadata(self, event: BaseEvent, rule: TokenRoutingRule) -> Dict[str, Any]:
        """Extract metadata from event payload based on rule."""
        metadata: Dict[str, Any] = {}
        payload = event.payload

        # For IoT events
        if event.event_type in (
            EventType.IOT_TELEMETRY,
            EventType.IOT_GEOFENCE_ENTER,
            EventType.IOT_GEOFENCE_EXIT,
        ):
            metadata["milestone_type"] = self._derive_milestone_type(event)
            metadata["timestamp"] = event.timestamp.isoformat()
            if hasattr(payload, "latitude") and hasattr(payload, "longitude"):
                metadata["location"] = {
                    "lat": payload.latitude,
                    "lon": payload.longitude,
                }
            if hasattr(payload, "location"):
                metadata["location"] = payload.location

        # For EDI events
        if event.event_type == EventType.EDI_STATUS_UPDATE:
            if isinstance(payload, EDI214Payload):
                metadata["milestone_type"] = EDI_STATUS_TO_MILESTONE.get(payload.status_code, "UNKNOWN")
                metadata["timestamp"] = event.timestamp.isoformat()
                if payload.location_name:
                    metadata["location"] = {"name": payload.location_name}
                metadata["edi_status_code"] = payload.status_code

        # For EDI Tender
        if event.event_type == EventType.EDI_TENDER_REQUEST:
            if hasattr(payload, "origin"):
                metadata["origin"] = payload.origin
            if hasattr(payload, "destination"):
                metadata["destination"] = payload.destination
            if hasattr(payload, "carrier_id"):
                metadata["carrier_id"] = payload.carrier_id

        # Copy specified fields from payload
        for field_name in rule.metadata_fields:
            if hasattr(payload, field_name):
                metadata[field_name] = getattr(payload, field_name)
            elif isinstance(payload, dict) and field_name in payload:
                metadata[field_name] = payload[field_name]

        return metadata

    def _derive_milestone_type(self, event: BaseEvent) -> str:
        """Derive milestone type from IoT event."""
        if event.event_type == EventType.IOT_GEOFENCE_ENTER:
            payload = event.payload
            if hasattr(payload, "geofence_type"):
                geofence_type = payload.geofence_type
                if geofence_type == "TERMINAL":
                    return "TERMINAL_ARRIVED"
                if geofence_type == "CONSIGNEE":
                    return "DELIVERED"
                if geofence_type == "SHIPPER_PICKUP":
                    return "PICKUP_ARRIVED"
        if event.event_type == EventType.IOT_GEOFENCE_EXIT:
            payload = event.payload
            if hasattr(payload, "geofence_type"):
                geofence_type = payload.geofence_type
                if geofence_type == "SHIPPER_PICKUP":
                    return "IN_TRANSIT"
                if geofence_type == "TERMINAL":
                    return "TERMINAL_DEPARTED"
        if event.event_type == EventType.IOT_TELEMETRY:
            return "IN_TRANSIT"
        return "UNKNOWN"

    def _check_governance(self, event: BaseEvent, token: BaseToken, new_state: str) -> bool:
        """Check if governance approval exists for transition."""
        # Check if event is a governance approval
        if event.event_type == EventType.GOVERNANCE_APPROVAL:
            payload = event.payload
            if isinstance(payload, GovernancePayload):
                return payload.decision == "APPROVED"

        # Check if token already has governance approval
        if token.metadata.get("policy_match_id"):
            return True

        return False


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "TokenRouter",
    "TokenRoutingResult",
    "TokenRoutingRule",
    "TokenImpact",
    "ROUTING_RULES",
    "EDI_STATUS_TO_ST01_STATE",
    "EDI_STATUS_TO_MILESTONE",
]
