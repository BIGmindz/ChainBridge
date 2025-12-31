# ═══════════════════════════════════════════════════════════════════════════════
# AML Evidence Graph — Entity Resolution & Relationship Mapping
# PAC-BENSON-P28: AML GOVERNED AGENT PROGRAM
# Agent: CODY (GID-01)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML Evidence Graph — Entity Resolution & Risk Signal Correlation

PURPOSE:
    Provide graph-based evidence correlation for AML cases including:
    - Entity resolution and disambiguation
    - Relationship mapping (beneficial owners, associates, etc.)
    - Risk signal aggregation
    - Evidence strength scoring

CONSTRAINTS:
    - Read-only analysis (no persistent state mutation)
    - All signals require evidence backing
    - SHADOW MODE: No live inference
    - Explainable rationale required

LANE: EXECUTION (AML EVIDENCE)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# EVIDENCE GRAPH ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class EntityType(Enum):
    """Type of entity in the evidence graph."""

    INDIVIDUAL = "INDIVIDUAL"
    ORGANIZATION = "ORGANIZATION"
    ACCOUNT = "ACCOUNT"
    TRANSACTION = "TRANSACTION"
    ADDRESS = "ADDRESS"
    DOCUMENT = "DOCUMENT"
    LIST_ENTRY = "LIST_ENTRY"  # Sanctions/PEP list entry
    MEDIA_ARTICLE = "MEDIA_ARTICLE"


class RelationType(Enum):
    """Type of relationship between entities."""

    OWNS = "OWNS"
    CONTROLS = "CONTROLS"
    BENEFICIAL_OWNER = "BENEFICIAL_OWNER"
    DIRECTOR = "DIRECTOR"
    EMPLOYEE = "EMPLOYEE"
    FAMILY = "FAMILY"
    ASSOCIATE = "ASSOCIATE"
    TRANSACTED_WITH = "TRANSACTED_WITH"
    LOCATED_AT = "LOCATED_AT"
    MENTIONED_IN = "MENTIONED_IN"
    MATCHED_TO = "MATCHED_TO"
    SAME_AS = "SAME_AS"  # Entity resolution link


class EvidenceStrength(Enum):
    """Strength of evidence supporting a claim."""

    VERIFIED = "VERIFIED"  # Confirmed from authoritative source
    STRONG = "STRONG"  # Multiple corroborating sources
    MODERATE = "MODERATE"  # Single reliable source
    WEAK = "WEAK"  # Inferred or partial match
    UNVERIFIED = "UNVERIFIED"  # Not yet validated


class RiskIndicator(Enum):
    """Type of risk indicator."""

    # Sanctions-related
    SANCTIONS_MATCH = "SANCTIONS_MATCH"
    SANCTIONS_ASSOCIATE = "SANCTIONS_ASSOCIATE"
    SANCTIONS_OWNED_ENTITY = "SANCTIONS_OWNED_ENTITY"

    # PEP-related
    PEP_MATCH = "PEP_MATCH"
    PEP_FAMILY = "PEP_FAMILY"
    PEP_ASSOCIATE = "PEP_ASSOCIATE"

    # Adverse media
    NEGATIVE_NEWS = "NEGATIVE_NEWS"
    FRAUD_ALLEGATION = "FRAUD_ALLEGATION"
    CORRUPTION_ALLEGATION = "CORRUPTION_ALLEGATION"

    # Behavioral
    UNUSUAL_ACTIVITY = "UNUSUAL_ACTIVITY"
    STRUCTURING = "STRUCTURING"
    RAPID_MOVEMENT = "RAPID_MOVEMENT"

    # Jurisdictional
    HIGH_RISK_JURISDICTION = "HIGH_RISK_JURISDICTION"
    TAX_HAVEN = "TAX_HAVEN"

    # KYC gaps
    INCOMPLETE_KYC = "INCOMPLETE_KYC"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"


# ═══════════════════════════════════════════════════════════════════════════════
# ENTITY
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Entity:
    """
    Entity in the evidence graph.

    Represents an individual, organization, account, or other
    entity relevant to AML analysis.
    """

    entity_id: str
    entity_type: EntityType
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)
    identifiers: Dict[str, str] = field(default_factory=dict)  # type -> value
    source_refs: List[str] = field(default_factory=list)
    confidence: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.entity_id.startswith("ENT-"):
            raise ValueError(f"Entity ID must start with 'ENT-': {self.entity_id}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0: {self.confidence}")

    def compute_entity_hash(self) -> str:
        """Compute deterministic hash of entity."""
        data = {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "identifiers": self.identifiers,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "attributes": self.attributes,
            "aliases": self.aliases,
            "identifiers": self.identifiers,
            "source_refs": self.source_refs,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "entity_hash": self.compute_entity_hash(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# RELATIONSHIP
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Relationship:
    """
    Relationship between two entities.

    Represents a directed edge in the evidence graph with
    associated evidence and confidence.
    """

    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: RelationType
    strength: EvidenceStrength
    evidence_refs: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.relationship_id.startswith("REL-"):
            raise ValueError(f"Relationship ID must start with 'REL-': {self.relationship_id}")

    @property
    def is_active(self) -> bool:
        """Check if relationship is currently active."""
        return self.end_date is None

    def compute_relationship_hash(self) -> str:
        """Compute deterministic hash of relationship."""
        data = {
            "relationship_id": self.relationship_id,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "relation_type": self.relation_type.value,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "relation_type": self.relation_type.value,
            "strength": self.strength.value,
            "evidence_refs": self.evidence_refs,
            "attributes": self.attributes,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "relationship_hash": self.compute_relationship_hash(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EVIDENCE NODE
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class EvidenceNode:
    """
    Evidence node in the graph.

    Represents a piece of evidence that supports entities
    and relationships in the graph.
    """

    node_id: str
    evidence_type: str
    source: str
    content: Dict[str, Any]
    strength: EvidenceStrength
    extracted_at: str
    supports_entities: List[str] = field(default_factory=list)
    supports_relationships: List[str] = field(default_factory=list)
    provenance_uri: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.node_id.startswith("EVNODE-"):
            raise ValueError(f"Evidence node ID must start with 'EVNODE-': {self.node_id}")

    def compute_node_hash(self) -> str:
        """Compute deterministic hash of evidence node."""
        data = {
            "node_id": self.node_id,
            "evidence_type": self.evidence_type,
            "source": self.source,
            "content": self.content,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "evidence_type": self.evidence_type,
            "source": self.source,
            "content": self.content,
            "strength": self.strength.value,
            "extracted_at": self.extracted_at,
            "supports_entities": self.supports_entities,
            "supports_relationships": self.supports_relationships,
            "provenance_uri": self.provenance_uri,
            "node_hash": self.compute_node_hash(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# RISK SIGNAL
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class RiskSignal:
    """
    Risk signal identified in the evidence.

    Represents a specific risk indicator with supporting
    evidence and severity assessment.
    """

    signal_id: str
    indicator: RiskIndicator
    severity: float  # 0.0 to 1.0
    entity_id: str
    description: str
    evidence_refs: List[str] = field(default_factory=list)
    mitigated: bool = False
    mitigation_reason: Optional[str] = None
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.signal_id.startswith("SIG-"):
            raise ValueError(f"Signal ID must start with 'SIG-': {self.signal_id}")
        if not 0.0 <= self.severity <= 1.0:
            raise ValueError(f"Severity must be between 0.0 and 1.0: {self.severity}")

    @property
    def is_high_severity(self) -> bool:
        """Check if signal is high severity."""
        return self.severity >= 0.7

    @property
    def is_actionable(self) -> bool:
        """Check if signal requires action (not mitigated)."""
        return not self.mitigated

    def mitigate(self, reason: str) -> None:
        """Mark signal as mitigated."""
        self.mitigated = True
        self.mitigation_reason = reason

    def compute_signal_hash(self) -> str:
        """Compute deterministic hash of signal."""
        data = {
            "signal_id": self.signal_id,
            "indicator": self.indicator.value,
            "entity_id": self.entity_id,
            "severity": self.severity,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "indicator": self.indicator.value,
            "severity": self.severity,
            "entity_id": self.entity_id,
            "description": self.description,
            "evidence_refs": self.evidence_refs,
            "mitigated": self.mitigated,
            "mitigation_reason": self.mitigation_reason,
            "is_high_severity": self.is_high_severity,
            "is_actionable": self.is_actionable,
            "detected_at": self.detected_at,
            "signal_hash": self.compute_signal_hash(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EVIDENCE GRAPH
# ═══════════════════════════════════════════════════════════════════════════════


class EvidenceGraph:
    """
    Graph structure for evidence correlation.

    Provides:
    - Entity and relationship management
    - Graph traversal
    - Risk signal aggregation
    - Path finding
    """

    def __init__(self, graph_id: str = "GRAPH-001") -> None:
        if not graph_id.startswith("GRAPH-"):
            raise ValueError(f"Graph ID must start with 'GRAPH-': {graph_id}")

        self._graph_id = graph_id
        self._entities: Dict[str, Entity] = {}
        self._relationships: Dict[str, Relationship] = {}
        self._evidence_nodes: Dict[str, EvidenceNode] = {}
        self._signals: Dict[str, RiskSignal] = {}

        # Adjacency lists for graph traversal
        self._outgoing: Dict[str, Set[str]] = {}  # entity_id -> set of relationship_ids
        self._incoming: Dict[str, Set[str]] = {}  # entity_id -> set of relationship_ids

        # Counters
        self._entity_counter = 0
        self._relationship_counter = 0
        self._evidence_counter = 0
        self._signal_counter = 0

    @property
    def graph_id(self) -> str:
        return self._graph_id

    @property
    def entity_count(self) -> int:
        return len(self._entities)

    @property
    def relationship_count(self) -> int:
        return len(self._relationships)

    # ───────────────────────────────────────────────────────────────────────────
    # ENTITY MANAGEMENT
    # ───────────────────────────────────────────────────────────────────────────

    def add_entity(
        self,
        entity_type: EntityType,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        aliases: Optional[List[str]] = None,
        identifiers: Optional[Dict[str, str]] = None,
        confidence: float = 1.0,
    ) -> Entity:
        """Add an entity to the graph."""
        self._entity_counter += 1
        entity_id = f"ENT-{self._entity_counter:08d}"

        entity = Entity(
            entity_id=entity_id,
            entity_type=entity_type,
            name=name,
            attributes=attributes or {},
            aliases=aliases or [],
            identifiers=identifiers or {},
            confidence=confidence,
        )

        self._entities[entity_id] = entity
        self._outgoing[entity_id] = set()
        self._incoming[entity_id] = set()

        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self._entities.get(entity_id)

    def find_entities_by_name(self, name: str, fuzzy: bool = False) -> List[Entity]:
        """Find entities by name."""
        if fuzzy:
            name_lower = name.lower()
            return [
                e for e in self._entities.values()
                if name_lower in e.name.lower() or any(name_lower in a.lower() for a in e.aliases)
            ]
        return [e for e in self._entities.values() if e.name == name]

    # ───────────────────────────────────────────────────────────────────────────
    # RELATIONSHIP MANAGEMENT
    # ───────────────────────────────────────────────────────────────────────────

    def add_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relation_type: RelationType,
        strength: EvidenceStrength,
        evidence_refs: Optional[List[str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Relationship:
        """Add a relationship between entities."""
        if source_entity_id not in self._entities:
            raise ValueError(f"Source entity not found: {source_entity_id}")
        if target_entity_id not in self._entities:
            raise ValueError(f"Target entity not found: {target_entity_id}")

        self._relationship_counter += 1
        relationship_id = f"REL-{self._relationship_counter:08d}"

        relationship = Relationship(
            relationship_id=relationship_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relation_type=relation_type,
            strength=strength,
            evidence_refs=evidence_refs or [],
            attributes=attributes or {},
        )

        self._relationships[relationship_id] = relationship
        self._outgoing[source_entity_id].add(relationship_id)
        self._incoming[target_entity_id].add(relationship_id)

        return relationship

    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Get a relationship by ID."""
        return self._relationships.get(relationship_id)

    def get_relationships_from(self, entity_id: str) -> List[Relationship]:
        """Get all relationships originating from an entity."""
        rel_ids = self._outgoing.get(entity_id, set())
        return [self._relationships[rid] for rid in rel_ids]

    def get_relationships_to(self, entity_id: str) -> List[Relationship]:
        """Get all relationships pointing to an entity."""
        rel_ids = self._incoming.get(entity_id, set())
        return [self._relationships[rid] for rid in rel_ids]

    # ───────────────────────────────────────────────────────────────────────────
    # EVIDENCE MANAGEMENT
    # ───────────────────────────────────────────────────────────────────────────

    def add_evidence_node(
        self,
        evidence_type: str,
        source: str,
        content: Dict[str, Any],
        strength: EvidenceStrength,
        supports_entities: Optional[List[str]] = None,
        supports_relationships: Optional[List[str]] = None,
        provenance_uri: Optional[str] = None,
    ) -> EvidenceNode:
        """Add an evidence node to the graph."""
        self._evidence_counter += 1
        node_id = f"EVNODE-{self._evidence_counter:08d}"

        node = EvidenceNode(
            node_id=node_id,
            evidence_type=evidence_type,
            source=source,
            content=content,
            strength=strength,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            supports_entities=supports_entities or [],
            supports_relationships=supports_relationships or [],
            provenance_uri=provenance_uri,
        )

        self._evidence_nodes[node_id] = node
        return node

    # ───────────────────────────────────────────────────────────────────────────
    # RISK SIGNAL MANAGEMENT
    # ───────────────────────────────────────────────────────────────────────────

    def add_risk_signal(
        self,
        indicator: RiskIndicator,
        severity: float,
        entity_id: str,
        description: str,
        evidence_refs: Optional[List[str]] = None,
    ) -> RiskSignal:
        """Add a risk signal to the graph."""
        if entity_id not in self._entities:
            raise ValueError(f"Entity not found: {entity_id}")

        self._signal_counter += 1
        signal_id = f"SIG-{self._signal_counter:08d}"

        signal = RiskSignal(
            signal_id=signal_id,
            indicator=indicator,
            severity=severity,
            entity_id=entity_id,
            description=description,
            evidence_refs=evidence_refs or [],
        )

        self._signals[signal_id] = signal
        return signal

    def get_signals_for_entity(self, entity_id: str) -> List[RiskSignal]:
        """Get all risk signals for an entity."""
        return [s for s in self._signals.values() if s.entity_id == entity_id]

    def get_actionable_signals(self) -> List[RiskSignal]:
        """Get all actionable (non-mitigated) risk signals."""
        return [s for s in self._signals.values() if s.is_actionable]

    def get_high_severity_signals(self) -> List[RiskSignal]:
        """Get all high severity signals."""
        return [s for s in self._signals.values() if s.is_high_severity]

    # ───────────────────────────────────────────────────────────────────────────
    # GRAPH TRAVERSAL
    # ───────────────────────────────────────────────────────────────────────────

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> Optional[List[Tuple[str, str]]]:
        """
        Find a path between two entities.

        Returns list of (entity_id, relationship_id) tuples or None if no path.
        """
        if source_id not in self._entities or target_id not in self._entities:
            return None

        visited: Set[str] = set()
        queue: List[Tuple[str, List[Tuple[str, str]]]] = [(source_id, [(source_id, "")])]

        while queue:
            current_id, path = queue.pop(0)

            if current_id == target_id:
                return path

            if current_id in visited or len(path) > max_depth:
                continue

            visited.add(current_id)

            for rel_id in self._outgoing.get(current_id, set()):
                rel = self._relationships[rel_id]
                if rel.target_entity_id not in visited:
                    queue.append((rel.target_entity_id, path + [(rel.target_entity_id, rel_id)]))

        return None

    def get_connected_entities(self, entity_id: str, max_depth: int = 2) -> Set[str]:
        """Get all entities connected to a given entity within depth."""
        connected: Set[str] = set()
        visited: Set[str] = set()
        queue: List[Tuple[str, int]] = [(entity_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)
            connected.add(current_id)

            # Follow outgoing relationships
            for rel_id in self._outgoing.get(current_id, set()):
                rel = self._relationships[rel_id]
                if rel.target_entity_id not in visited:
                    queue.append((rel.target_entity_id, depth + 1))

            # Follow incoming relationships
            for rel_id in self._incoming.get(current_id, set()):
                rel = self._relationships[rel_id]
                if rel.source_entity_id not in visited:
                    queue.append((rel.source_entity_id, depth + 1))

        return connected

    # ───────────────────────────────────────────────────────────────────────────
    # RISK SCORING
    # ───────────────────────────────────────────────────────────────────────────

    def compute_entity_risk_score(self, entity_id: str) -> float:
        """
        Compute aggregate risk score for an entity.

        Considers:
        - Direct risk signals
        - Connected entity risks (weighted by relationship strength)
        """
        if entity_id not in self._entities:
            return 0.0

        # Direct signals
        direct_signals = self.get_signals_for_entity(entity_id)
        direct_score = sum(s.severity for s in direct_signals if s.is_actionable)

        # Connected entity risks (discounted)
        connected_score = 0.0
        for rel_id in self._outgoing.get(entity_id, set()):
            rel = self._relationships[rel_id]
            connected_signals = self.get_signals_for_entity(rel.target_entity_id)
            discount = 0.5 if rel.strength in (EvidenceStrength.VERIFIED, EvidenceStrength.STRONG) else 0.3
            connected_score += discount * sum(s.severity for s in connected_signals if s.is_actionable)

        # Normalize to 0-1 range
        total = direct_score + connected_score
        return min(1.0, total)

    # ───────────────────────────────────────────────────────────────────────────
    # SERIALIZATION
    # ───────────────────────────────────────────────────────────────────────────

    def compute_graph_hash(self) -> str:
        """Compute deterministic hash of entire graph state."""
        entity_hashes = sorted([e.compute_entity_hash() for e in self._entities.values()])
        rel_hashes = sorted([r.compute_relationship_hash() for r in self._relationships.values()])
        data = {
            "graph_id": self._graph_id,
            "entity_hashes": entity_hashes,
            "relationship_hashes": rel_hashes,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self._graph_id,
            "entity_count": self.entity_count,
            "relationship_count": self.relationship_count,
            "evidence_node_count": len(self._evidence_nodes),
            "signal_count": len(self._signals),
            "entities": [e.to_dict() for e in self._entities.values()],
            "relationships": [r.to_dict() for r in self._relationships.values()],
            "evidence_nodes": [n.to_dict() for n in self._evidence_nodes.values()],
            "signals": [s.to_dict() for s in self._signals.values()],
            "graph_hash": self.compute_graph_hash(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EVIDENCE GRAPH SERVICE
# ═══════════════════════════════════════════════════════════════════════════════


class EvidenceGraphService:
    """
    Service for managing evidence graphs across cases.

    Provides:
    - Graph creation and lifecycle
    - Cross-case entity resolution
    - Aggregate risk analysis
    """

    def __init__(self) -> None:
        self._graphs: Dict[str, EvidenceGraph] = {}
        self._graph_counter = 0

    def create_graph(self, case_id: Optional[str] = None) -> EvidenceGraph:
        """Create a new evidence graph."""
        self._graph_counter += 1
        graph_id = f"GRAPH-{self._graph_counter:08d}"
        if case_id:
            graph_id = f"GRAPH-{case_id}"

        graph = EvidenceGraph(graph_id=graph_id)
        self._graphs[graph_id] = graph
        return graph

    def get_graph(self, graph_id: str) -> Optional[EvidenceGraph]:
        """Get a graph by ID."""
        return self._graphs.get(graph_id)

    def generate_report(self) -> Dict[str, Any]:
        """Generate service report."""
        total_entities = sum(g.entity_count for g in self._graphs.values())
        total_relationships = sum(g.relationship_count for g in self._graphs.values())

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_graphs": len(self._graphs),
            "total_entities": total_entities,
            "total_relationships": total_relationships,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "EntityType",
    "RelationType",
    "EvidenceStrength",
    "RiskIndicator",
    # Data Classes
    "Entity",
    "Relationship",
    "EvidenceNode",
    "RiskSignal",
    # Services
    "EvidenceGraph",
    "EvidenceGraphService",
]
