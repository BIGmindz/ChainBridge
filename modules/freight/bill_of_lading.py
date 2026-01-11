"""
ChainFreight - Bill of Lading Module
=====================================
PAC: PAC-LOG-P140-CHAINFREIGHT
Lead Agent: Atlas (GID-11)
Vertical: ChainFreight (Logistics)

This module implements the Digital Bill of Lading (dBoL) - the legal document
that represents ownership and chain of custody for physical cargo.

INVARIANTS ENFORCED:
- INV-LOG-001: Immutable Bill of Lading - MUST NOT edit after signing
- INV-LOG-002: Customs Gate - MUST NOT release without CUSTOMS_CLEAR flag

TRINITY INTEGRATION:
- ChainSense: Condition monitoring (temperature, location, shock)
- ChainPay: Escrow release upon delivery confirmation
- ChainFreight: Legal custody chain (THIS MODULE)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


class BoLStatus(Enum):
    """Bill of Lading lifecycle states."""
    DRAFT = "DRAFT"                    # Being prepared, editable
    ISSUED = "ISSUED"                  # Signed by shipper, carrier acknowledged
    IN_TRANSIT = "IN_TRANSIT"          # Cargo on the move
    ARRIVED = "ARRIVED"                # At destination port/terminal
    CUSTOMS_HOLD = "CUSTOMS_HOLD"      # Awaiting customs clearance
    CUSTOMS_CLEARED = "CUSTOMS_CLEARED"  # Cleared for release
    DELIVERED = "DELIVERED"            # Consignee has taken possession
    DISTRESSED = "DISTRESSED"          # Chain of custody broken - FREEZE


class Party(Enum):
    """Parties involved in a Bill of Lading."""
    SHIPPER = "SHIPPER"        # Sender of goods
    CARRIER = "CARRIER"        # Transport company (Maersk, MSC, etc.)
    CONSIGNEE = "CONSIGNEE"    # Receiver of goods
    NOTIFY = "NOTIFY"          # Party to notify upon arrival


@dataclass
class Signature:
    """Digital signature for BoL authorization."""
    party: Party
    party_name: str
    timestamp: datetime
    signature_hash: str
    authorized: bool = True
    
    def to_dict(self) -> dict:
        return {
            "party": self.party.value,
            "party_name": self.party_name,
            "timestamp": self.timestamp.isoformat(),
            "signature_hash": self.signature_hash,
            "authorized": self.authorized
        }


@dataclass
class CargoItem:
    """Individual cargo item on the Bill of Lading."""
    item_id: str
    description: str
    quantity: int
    unit: str  # e.g., "TEU", "KG", "PALLET"
    weight_kg: float
    value_usd: Optional[float] = None
    hs_code: Optional[str] = None  # Harmonized System code for customs
    hazmat_class: Optional[str] = None  # If hazardous materials
    
    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "description": self.description,
            "quantity": self.quantity,
            "unit": self.unit,
            "weight_kg": self.weight_kg,
            "value_usd": self.value_usd,
            "hs_code": self.hs_code,
            "hazmat_class": self.hazmat_class
        }


@dataclass
class Route:
    """Shipping route information."""
    origin_port: str
    origin_country: str
    destination_port: str
    destination_country: str
    vessel_name: Optional[str] = None
    voyage_number: Optional[str] = None
    estimated_departure: Optional[datetime] = None
    estimated_arrival: Optional[datetime] = None
    transit_ports: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "origin_port": self.origin_port,
            "origin_country": self.origin_country,
            "destination_port": self.destination_port,
            "destination_country": self.destination_country,
            "vessel_name": self.vessel_name,
            "voyage_number": self.voyage_number,
            "estimated_departure": self.estimated_departure.isoformat() if self.estimated_departure else None,
            "estimated_arrival": self.estimated_arrival.isoformat() if self.estimated_arrival else None,
            "transit_ports": self.transit_ports
        }


@dataclass
class CustodyEvent:
    """Chain of custody handover event."""
    event_id: str
    timestamp: datetime
    from_party: Party
    to_party: Party
    location: str
    container_id: str
    event_type: str  # "PICKUP", "HANDOVER", "DELIVERY", "INSPECTION"
    verified: bool = False
    chainsense_proof: Optional[str] = None  # Link to IoT attestation
    
    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "from_party": self.from_party.value,
            "to_party": self.to_party.value,
            "location": self.location,
            "container_id": self.container_id,
            "event_type": self.event_type,
            "verified": self.verified,
            "chainsense_proof": self.chainsense_proof
        }


class DigitalBillOfLading:
    """
    Digital Bill of Lading (dBoL) - The core document of ChainFreight.
    
    This is the legal contract that defines:
    - WHO owns the cargo (Shipper -> Consignee)
    - WHAT is being shipped (Cargo manifest)
    - WHERE it's going (Route)
    - HOW custody transfers (Chain of custody events)
    
    INVARIANT: Once signed (status != DRAFT), the BoL is IMMUTABLE.
    Any modification attempt after signing results in DISTRESSED status.
    """
    
    def __init__(
        self,
        bol_number: Optional[str] = None,
        shipper_name: str = "",
        consignee_name: str = "",
        carrier_name: str = ""
    ):
        self.bol_id: str = str(uuid4())
        self.bol_number: str = bol_number or f"BOL-{datetime.utcnow().strftime('%Y%m%d')}-{self.bol_id[:8].upper()}"
        self.status: BoLStatus = BoLStatus.DRAFT
        self.created_at: datetime = datetime.utcnow()
        self.updated_at: datetime = datetime.utcnow()
        
        # Parties
        self.shipper_name: str = shipper_name
        self.consignee_name: str = consignee_name
        self.carrier_name: str = carrier_name
        self.notify_party: Optional[str] = None
        
        # Cargo & Container
        self.container_id: Optional[str] = None
        self.seal_number: Optional[str] = None
        self.cargo_items: list[CargoItem] = []
        self.total_weight_kg: float = 0.0
        self.total_value_usd: float = 0.0
        
        # Route
        self.route: Optional[Route] = None
        
        # Signatures (required for issuance)
        self.signatures: list[Signature] = []
        
        # Chain of Custody
        self.custody_chain: list[CustodyEvent] = []
        
        # Customs
        self.customs_cleared: bool = False
        self.customs_reference: Optional[str] = None
        
        # ChainBridge Integration
        self.chainpay_escrow_id: Optional[str] = None
        self.chainsense_device_ids: list[str] = []
        
        # Immutability Hash (computed on signing)
        self._signed_hash: Optional[str] = None
    
    def add_cargo(self, item: CargoItem) -> None:
        """Add cargo item to the BoL. Only allowed in DRAFT status."""
        self._enforce_mutable()
        self.cargo_items.append(item)
        self.total_weight_kg = sum(c.weight_kg * c.quantity for c in self.cargo_items)
        self.total_value_usd = sum((c.value_usd or 0) * c.quantity for c in self.cargo_items)
        self.updated_at = datetime.utcnow()
    
    def set_route(self, route: Route) -> None:
        """Set the shipping route. Only allowed in DRAFT status."""
        self._enforce_mutable()
        self.route = route
        self.updated_at = datetime.utcnow()
    
    def set_container(self, container_id: str, seal_number: str) -> None:
        """Assign container and seal. Only allowed in DRAFT status."""
        self._enforce_mutable()
        self.container_id = container_id
        self.seal_number = seal_number
        self.updated_at = datetime.utcnow()
    
    def sign(self, party: Party, party_name: str) -> Signature:
        """
        Sign the Bill of Lading.
        
        Required signatures for ISSUED status:
        - SHIPPER: Confirms cargo description and value
        - CARRIER: Acknowledges receipt and transport obligation
        
        Once both sign, the BoL becomes IMMUTABLE.
        """
        if self.status not in [BoLStatus.DRAFT, BoLStatus.ISSUED]:
            raise ValueError(f"Cannot sign BoL in {self.status.value} status")
        
        # Generate signature hash
        sig_data = f"{party.value}:{party_name}:{self.bol_id}:{datetime.utcnow().isoformat()}"
        sig_hash = hashlib.sha256(sig_data.encode()).hexdigest()
        
        signature = Signature(
            party=party,
            party_name=party_name,
            timestamp=datetime.utcnow(),
            signature_hash=sig_hash
        )
        self.signatures.append(signature)
        
        # Check if we have required signatures for issuance
        parties_signed = {s.party for s in self.signatures}
        if Party.SHIPPER in parties_signed and Party.CARRIER in parties_signed:
            self._issue()
        
        return signature
    
    def _issue(self) -> None:
        """Issue the BoL - makes it immutable."""
        self.status = BoLStatus.ISSUED
        self._signed_hash = self._compute_hash()
        self.updated_at = datetime.utcnow()
    
    def record_custody_event(self, event: CustodyEvent) -> None:
        """
        Record a chain of custody handover event.
        
        This is allowed after issuance - custody transfers are part of
        the BoL lifecycle, not the core document.
        """
        if self.status == BoLStatus.DRAFT:
            raise ValueError("Cannot record custody events on DRAFT BoL")
        
        if self.status == BoLStatus.DISTRESSED:
            raise ValueError("BoL is DISTRESSED - no further events allowed")
        
        # Verify container ID matches
        if event.container_id != self.container_id:
            self._mark_distressed("Container ID mismatch in custody event")
            raise ValueError("FAIL_CLOSED: Container ID does not match BoL")
        
        self.custody_chain.append(event)
        
        # Update status based on event
        if event.event_type == "PICKUP" and self.status == BoLStatus.ISSUED:
            self.status = BoLStatus.IN_TRANSIT
        elif event.event_type == "ARRIVAL":
            self.status = BoLStatus.ARRIVED
        elif event.event_type == "DELIVERY" and self.customs_cleared:
            self.status = BoLStatus.DELIVERED
        
        self.updated_at = datetime.utcnow()
    
    def clear_customs(self, reference: str) -> None:
        """Mark customs as cleared. Required before delivery."""
        if self.status not in [BoLStatus.ARRIVED, BoLStatus.CUSTOMS_HOLD]:
            raise ValueError(f"Cannot clear customs in {self.status.value} status")
        
        self.customs_cleared = True
        self.customs_reference = reference
        self.status = BoLStatus.CUSTOMS_CLEARED
        self.updated_at = datetime.utcnow()
    
    def hold_customs(self, reason: str) -> None:
        """Place BoL on customs hold."""
        if self.status not in [BoLStatus.ARRIVED, BoLStatus.IN_TRANSIT]:
            raise ValueError(f"Cannot hold customs in {self.status.value} status")
        
        self.status = BoLStatus.CUSTOMS_HOLD
        self.updated_at = datetime.utcnow()
    
    def link_chainpay(self, escrow_id: str) -> None:
        """Link to ChainPay escrow for payment release on delivery."""
        self.chainpay_escrow_id = escrow_id
    
    def link_chainsense(self, device_id: str) -> None:
        """Link to ChainSense IoT device for condition monitoring."""
        self.chainsense_device_ids.append(device_id)
    
    def can_release_payment(self) -> bool:
        """
        Check if payment can be released via ChainPay.
        
        Trinity Logic:
        - ChainSense says "Arrived" ✓
        - Atlas says "Papers Signed" ✓
        - ChainPay releases cash
        """
        return (
            self.status == BoLStatus.DELIVERED and
            self.customs_cleared and
            len([s for s in self.signatures if s.party == Party.CONSIGNEE]) > 0
        )
    
    def _enforce_mutable(self) -> None:
        """Ensure BoL can still be modified."""
        if self.status != BoLStatus.DRAFT:
            self._mark_distressed("Modification attempted on immutable BoL")
            raise ValueError("INV-LOG-001 VIOLATION: Cannot modify signed Bill of Lading")
    
    def _mark_distressed(self, reason: str) -> None:
        """Mark BoL as distressed - chain of custody broken."""
        self.status = BoLStatus.DISTRESSED
        self.updated_at = datetime.utcnow()
        # Log the distress event
        print(f"⚠️ BOL DISTRESSED: {self.bol_number} - {reason}")
    
    def _compute_hash(self) -> str:
        """Compute immutability hash of the core BoL data."""
        core_data = {
            "bol_id": self.bol_id,
            "bol_number": self.bol_number,
            "shipper": self.shipper_name,
            "consignee": self.consignee_name,
            "carrier": self.carrier_name,
            "container_id": self.container_id,
            "seal_number": self.seal_number,
            "cargo": [c.to_dict() for c in self.cargo_items],
            "route": self.route.to_dict() if self.route else None,
            "total_weight_kg": self.total_weight_kg,
            "total_value_usd": self.total_value_usd
        }
        return hashlib.sha256(json.dumps(core_data, sort_keys=True).encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """Verify the BoL has not been tampered with since signing."""
        if not self._signed_hash:
            return True  # DRAFT BoLs have no hash yet
        return self._compute_hash() == self._signed_hash
    
    def to_dict(self) -> dict:
        """Serialize BoL to dictionary."""
        return {
            "bol_id": self.bol_id,
            "bol_number": self.bol_number,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "parties": {
                "shipper": self.shipper_name,
                "consignee": self.consignee_name,
                "carrier": self.carrier_name,
                "notify": self.notify_party
            },
            "container": {
                "id": self.container_id,
                "seal_number": self.seal_number
            },
            "cargo": [c.to_dict() for c in self.cargo_items],
            "totals": {
                "weight_kg": self.total_weight_kg,
                "value_usd": self.total_value_usd
            },
            "route": self.route.to_dict() if self.route else None,
            "signatures": [s.to_dict() for s in self.signatures],
            "custody_chain": [e.to_dict() for e in self.custody_chain],
            "customs": {
                "cleared": self.customs_cleared,
                "reference": self.customs_reference
            },
            "chainbridge_integration": {
                "chainpay_escrow_id": self.chainpay_escrow_id,
                "chainsense_device_ids": self.chainsense_device_ids
            },
            "integrity": {
                "signed_hash": self._signed_hash,
                "verified": self.verify_integrity()
            }
        }
    
    def to_json(self) -> str:
        """Serialize BoL to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: dict) -> DigitalBillOfLading:
        """Deserialize BoL from dictionary."""
        bol = cls(
            bol_number=data.get("bol_number"),
            shipper_name=data.get("parties", {}).get("shipper", ""),
            consignee_name=data.get("parties", {}).get("consignee", ""),
            carrier_name=data.get("parties", {}).get("carrier", "")
        )
        bol.bol_id = data.get("bol_id", bol.bol_id)
        bol.status = BoLStatus(data.get("status", "DRAFT"))
        bol.container_id = data.get("container", {}).get("id")
        bol.seal_number = data.get("container", {}).get("seal_number")
        bol._signed_hash = data.get("integrity", {}).get("signed_hash")
        return bol


# Atlas Command Interface
def atlas_create_bol(
    shipper: str,
    consignee: str,
    carrier: str,
    container_id: str,
    seal_number: str
) -> DigitalBillOfLading:
    """
    Atlas (GID-11) Command: Create a new Bill of Lading.
    
    This is the entry point for all freight operations in ChainBridge.
    """
    bol = DigitalBillOfLading(
        shipper_name=shipper,
        consignee_name=consignee,
        carrier_name=carrier
    )
    bol.set_container(container_id, seal_number)
    return bol


def atlas_validate_custody_chain(bol: DigitalBillOfLading) -> dict:
    """
    Atlas (GID-11) Command: Validate the chain of custody.
    
    Returns validation report indicating if custody chain is intact.
    """
    if not bol.custody_chain:
        return {
            "valid": True,
            "status": "NO_EVENTS",
            "message": "No custody events recorded yet"
        }
    
    # Verify sequential handovers
    issues = []
    for i, event in enumerate(bol.custody_chain):
        if not event.verified:
            issues.append(f"Event {i+1} ({event.event_type}) not verified")
        if event.container_id != bol.container_id:
            issues.append(f"Event {i+1} has container ID mismatch")
    
    return {
        "valid": len(issues) == 0,
        "status": "VALID" if len(issues) == 0 else "CUSTODY_BREAK",
        "issues": issues,
        "event_count": len(bol.custody_chain),
        "container_id": bol.container_id
    }
