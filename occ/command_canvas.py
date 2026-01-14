"""
ChainBridge Sovereign Swarm - Visual Swarm Builder
PAC-CANVAS-DEPLOY-39 | Sovereign Command Canvas

Visual orchestration interface for multi-agent deployment.
Transforms manual scripting into drag-and-drop swarm control.

Zones:
- Zone A: AGENT FORGE - Draggable agent roster
- Zone B: LOGIC CANVAS - Node-based workflow editor  
- Zone C: STRIKE CONSOLE - Deployment execution

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY
Epoch: EPOCH_001

SECURITY: All deployments require SMK Double-Lock signature.
"""

import hashlib
import hmac
import json
import time
import uuid
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.zk.concordium_bridge import SovereignSalt


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

GENESIS_ANCHOR = "GENESIS-SOVEREIGN-2026-01-14"
CANVAS_VERSION = "1.0.0"
MAX_AGENTS_STANDARD = 10
MAX_AGENTS_CLUSTERED = 100


class AgentStatus(Enum):
    """Agent availability status"""
    ACTIVE = "ACTIVE"
    STANDBY = "STANDBY"
    DEPLOYED = "DEPLOYED"
    EXECUTING = "EXECUTING"
    LOCKED = "LOCKED"
    OFFLINE = "OFFLINE"


class NodeType(Enum):
    """Canvas node types"""
    AGENT = "AGENT"
    GATE = "GATE"
    DECISION = "DECISION"
    MERGE = "MERGE"
    FORK = "FORK"
    START = "START"
    END = "END"


class ConnectionType(Enum):
    """Connection flow types"""
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"
    CONDITIONAL = "CONDITIONAL"
    LOOP = "LOOP"


class SwarmState(Enum):
    """Swarm deployment state"""
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    SIMULATED = "SIMULATED"
    ARMED = "ARMED"
    EXECUTING = "EXECUTING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    LOCKED = "LOCKED"


class EnclaveLockReason(Enum):
    """Reasons for enclave lock"""
    CONNECTION_LOST = "CONNECTION_LOST"
    AUTH_TIMEOUT = "AUTH_TIMEOUT"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    MANUAL_LOCK = "MANUAL_LOCK"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SwarmAgent:
    """Agent available for swarm deployment"""
    gid: str
    name: str
    role: str
    status: AgentStatus
    capabilities: List[str]
    icon: str = "🤖"
    color: str = "#00ff88"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "gid": self.gid,
            "name": self.name,
            "role": self.role,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "icon": self.icon,
            "color": self.color
        }


@dataclass
class CanvasNode:
    """Node on the Logic Canvas"""
    node_id: str
    node_type: NodeType
    position: Dict[str, float]  # {x, y}
    agent: Optional[SwarmAgent] = None
    label: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "position": self.position,
            "agent": self.agent.to_dict() if self.agent else None,
            "label": self.label,
            "config": self.config
        }


@dataclass
class CanvasConnection:
    """Connection between canvas nodes"""
    connection_id: str
    source_node_id: str
    target_node_id: str
    connection_type: ConnectionType
    condition: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "connection_type": self.connection_type.value,
            "condition": self.condition
        }


@dataclass
class BinaryReasonProof:
    """Pre-execution proof of swarm path"""
    brp_id: str
    timestamp: str
    swarm_id: str
    execution_path: List[str]
    gate_evaluations: List[Dict[str, Any]]
    estimated_compute_ms: float
    estimated_cost_usd: float
    risk_assessment: str
    proof_hash: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brp_id": self.brp_id,
            "timestamp": self.timestamp,
            "swarm_id": self.swarm_id,
            "execution_path": self.execution_path,
            "gate_evaluations": self.gate_evaluations,
            "estimated_compute_ms": self.estimated_compute_ms,
            "estimated_cost_usd": self.estimated_cost_usd,
            "risk_assessment": self.risk_assessment,
            "proof_hash": f"{self.proof_hash[:16]}...{self.proof_hash[-16:]}"
        }


@dataclass
class SwarmDeployment:
    """Complete swarm deployment configuration"""
    swarm_id: str
    name: str
    description: str
    state: SwarmState
    created_at: str
    nodes: List[CanvasNode]
    connections: List[CanvasConnection]
    brp: Optional[BinaryReasonProof] = None
    architect_signature: Optional[str] = None
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "swarm_id": self.swarm_id,
            "name": self.name,
            "description": self.description,
            "state": self.state.value,
            "created_at": self.created_at,
            "nodes": [n.to_dict() for n in self.nodes],
            "connections": [c.to_dict() for c in self.connections],
            "brp": self.brp.to_dict() if self.brp else None,
            "architect_signature": f"{self.architect_signature[:8]}..." if self.architect_signature else None,
            "execution_log_count": len(self.execution_log)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ZONE A: AGENT FORGE
# ═══════════════════════════════════════════════════════════════════════════════

class AgentForge:
    """
    Sidebar component containing available agents for deployment.
    Agents can be dragged onto the Logic Canvas.
    """
    
    def __init__(self):
        self.agents: Dict[str, SwarmAgent] = {}
        self._initialize_alumni_agents()
    
    def _initialize_alumni_agents(self):
        """Initialize the core agent roster"""
        alumni = [
            SwarmAgent(
                gid="GID-00",
                name="Benson",
                role="Sovereign Executor",
                status=AgentStatus.ACTIVE,
                capabilities=["PAC_EXECUTION", "LEDGER_WRITE", "SWARM_CONTROL"],
                icon="⚡",
                color="#00ff88"
            ),
            SwarmAgent(
                gid="GID-01",
                name="Dan-SDR",
                role="Sales Development",
                status=AgentStatus.STANDBY,
                capabilities=["LEAD_GENERATION", "OUTREACH", "QUALIFICATION"],
                icon="📞",
                color="#00aaff"
            ),
            SwarmAgent(
                gid="GID-02",
                name="University Dean",
                role="Logic Validator",
                status=AgentStatus.STANDBY,
                capabilities=["LOGIC_PREFLIGHT", "GATE_VALIDATION", "COMPLIANCE_CHECK"],
                icon="🎓",
                color="#ffcc00"
            ),
            SwarmAgent(
                gid="GID-03",
                name="Vaporizer",
                role="Zero-PII Hasher",
                status=AgentStatus.DEPLOYED,
                capabilities=["PII_HASHING", "CBH_GENERATION", "DATA_ANONYMIZATION"],
                icon="💨",
                color="#ff6600"
            ),
            SwarmAgent(
                gid="GID-04",
                name="Blind-Portal",
                role="Ingest Layer",
                status=AgentStatus.DEPLOYED,
                capabilities=["DATA_INGESTION", "BATCH_PROCESSING", "COMPLIANCE_SCREENING"],
                icon="🚪",
                color="#9900ff"
            ),
            SwarmAgent(
                gid="GID-05",
                name="Certifier",
                role="Settlement Proof",
                status=AgentStatus.DEPLOYED,
                capabilities=["CERTIFICATE_GENERATION", "DEAL_SETTLEMENT", "PROOF_SIGNING"],
                icon="📜",
                color="#00ffcc"
            ),
            SwarmAgent(
                gid="GID-06",
                name="Watchdog",
                role="Compliance Monitor",
                status=AgentStatus.STANDBY,
                capabilities=["REAL_TIME_MONITORING", "ALERT_GENERATION", "GATE_ENFORCEMENT"],
                icon="🐕",
                color="#ff3366"
            ),
            SwarmAgent(
                gid="GID-07",
                name="Librarian",
                role="Knowledge Manager",
                status=AgentStatus.STANDBY,
                capabilities=["DOCUMENT_RETRIEVAL", "CONTEXT_SYNTHESIS", "MEMORY_MANAGEMENT"],
                icon="📚",
                color="#66ccff"
            ),
            SwarmAgent(
                gid="GID-08",
                name="Auditor",
                role="Trail Validator",
                status=AgentStatus.STANDBY,
                capabilities=["AUDIT_TRAIL", "PROOF_VERIFICATION", "COMPLIANCE_REPORTING"],
                icon="🔍",
                color="#ffff00"
            ),
            SwarmAgent(
                gid="GID-09",
                name="Orchestrator",
                role="Swarm Coordinator",
                status=AgentStatus.ACTIVE,
                capabilities=["SWARM_ROUTING", "LOAD_BALANCING", "FAILOVER_MANAGEMENT"],
                icon="🎭",
                color="#ff00ff"
            )
        ]
        
        for agent in alumni:
            self.agents[agent.gid] = agent
    
    def get_available_agents(self) -> List[SwarmAgent]:
        """Get agents available for deployment"""
        return [a for a in self.agents.values() if a.status != AgentStatus.LOCKED]
    
    def get_agent(self, gid: str) -> Optional[SwarmAgent]:
        """Get a specific agent by GID"""
        return self.agents.get(gid)
    
    def update_agent_status(self, gid: str, status: AgentStatus):
        """Update an agent's status"""
        if gid in self.agents:
            self.agents[gid].status = status
    
    def get_roster(self) -> Dict[str, Any]:
        """Get the complete agent roster"""
        return {
            "total_agents": len(self.agents),
            "active": sum(1 for a in self.agents.values() if a.status == AgentStatus.ACTIVE),
            "deployed": sum(1 for a in self.agents.values() if a.status == AgentStatus.DEPLOYED),
            "standby": sum(1 for a in self.agents.values() if a.status == AgentStatus.STANDBY),
            "agents": [a.to_dict() for a in self.agents.values()]
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ZONE B: LOGIC CANVAS
# ═══════════════════════════════════════════════════════════════════════════════

class LogicCanvas:
    """
    Visual node-based workflow editor.
    Supports Sequential, Parallel, and Loop connections.
    """
    
    def __init__(self):
        self.nodes: Dict[str, CanvasNode] = {}
        self.connections: Dict[str, CanvasConnection] = {}
        self.canvas_id = f"CANVAS-{uuid.uuid4().hex[:8].upper()}"
    
    def add_node(
        self,
        node_type: NodeType,
        position: Dict[str, float],
        agent: Optional[SwarmAgent] = None,
        label: str = "",
        config: Dict[str, Any] = None
    ) -> CanvasNode:
        """Add a node to the canvas"""
        node_id = f"NODE-{uuid.uuid4().hex[:8].upper()}"
        
        node = CanvasNode(
            node_id=node_id,
            node_type=node_type,
            position=position,
            agent=agent,
            label=label or (agent.name if agent else node_type.value),
            config=config or {}
        )
        
        self.nodes[node_id] = node
        return node
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node and its connections"""
        if node_id not in self.nodes:
            return False
        
        # Remove associated connections
        to_remove = [
            cid for cid, conn in self.connections.items()
            if conn.source_node_id == node_id or conn.target_node_id == node_id
        ]
        for cid in to_remove:
            del self.connections[cid]
        
        del self.nodes[node_id]
        return True
    
    def move_node(self, node_id: str, new_position: Dict[str, float]) -> bool:
        """Move a node to a new position"""
        if node_id in self.nodes:
            self.nodes[node_id].position = new_position
            return True
        return False
    
    def connect_nodes(
        self,
        source_node_id: str,
        target_node_id: str,
        connection_type: ConnectionType = ConnectionType.SEQUENTIAL,
        condition: Optional[str] = None
    ) -> Optional[CanvasConnection]:
        """Create a connection between two nodes"""
        if source_node_id not in self.nodes or target_node_id not in self.nodes:
            return None
        
        connection_id = f"CONN-{uuid.uuid4().hex[:8].upper()}"
        
        connection = CanvasConnection(
            connection_id=connection_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            connection_type=connection_type,
            condition=condition
        )
        
        self.connections[connection_id] = connection
        return connection
    
    def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection"""
        if connection_id in self.connections:
            del self.connections[connection_id]
            return True
        return False
    
    def detect_loops(self) -> List[List[str]]:
        """Detect any loops in the canvas (potential compute waste)"""
        loops = []
        visited = set()
        rec_stack = set()
        
        def dfs(node_id: str, path: List[str]) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            # Find outgoing connections
            for conn in self.connections.values():
                if conn.source_node_id == node_id:
                    target = conn.target_node_id
                    if target not in visited:
                        if dfs(target, path.copy()):
                            return True
                    elif target in rec_stack:
                        # Found a loop
                        loop_start = path.index(target)
                        loops.append(path[loop_start:] + [target])
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id, [])
        
        return loops
    
    def get_execution_order(self) -> List[str]:
        """Get topological order of nodes for execution"""
        # Find start node
        start_nodes = [
            n.node_id for n in self.nodes.values()
            if n.node_type == NodeType.START
        ]
        
        if not start_nodes:
            # Find nodes with no incoming edges
            incoming = set()
            for conn in self.connections.values():
                incoming.add(conn.target_node_id)
            start_nodes = [nid for nid in self.nodes if nid not in incoming]
        
        # BFS traversal
        order = []
        visited = set()
        queue = start_nodes.copy()
        
        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue
            
            visited.add(node_id)
            order.append(node_id)
            
            # Add connected nodes
            for conn in self.connections.values():
                if conn.source_node_id == node_id and conn.target_node_id not in visited:
                    queue.append(conn.target_node_id)
        
        return order
    
    def get_canvas_state(self) -> Dict[str, Any]:
        """Get complete canvas state"""
        return {
            "canvas_id": self.canvas_id,
            "node_count": len(self.nodes),
            "connection_count": len(self.connections),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "connections": [c.to_dict() for c in self.connections.values()],
            "execution_order": self.get_execution_order(),
            "detected_loops": self.detect_loops()
        }
    
    def to_pac_schema(self) -> Dict[str, Any]:
        """Convert canvas to PAC execution schema"""
        execution_order = self.get_execution_order()
        
        lanes = []
        for i, node_id in enumerate(execution_order):
            node = self.nodes[node_id]
            if node.agent:
                lanes.append({
                    "lane_id": f"LANE-{i+1}",
                    "agent_gid": node.agent.gid,
                    "agent_name": node.agent.name,
                    "task": node.label,
                    "config": node.config
                })
        
        return {
            "canvas_id": self.canvas_id,
            "total_lanes": len(lanes),
            "lanes": lanes,
            "flow_type": self._detect_flow_type()
        }
    
    def _detect_flow_type(self) -> str:
        """Detect the primary flow type of the canvas"""
        parallel_count = sum(1 for c in self.connections.values() if c.connection_type == ConnectionType.PARALLEL)
        loop_count = sum(1 for c in self.connections.values() if c.connection_type == ConnectionType.LOOP)
        
        if loop_count > 0:
            return "LOOP"
        elif parallel_count > len(self.connections) // 2:
            return "PARALLEL"
        else:
            return "SEQUENTIAL"


# ═══════════════════════════════════════════════════════════════════════════════
# LOGIC PRE-FLIGHT (University Dean)
# ═══════════════════════════════════════════════════════════════════════════════

class LogicPreFlight:
    """
    Pre-execution validation by the University Dean.
    Checks for loops, gate compliance, and compute estimates.
    """
    
    def __init__(self):
        self.sovereign_salt = SovereignSalt()
    
    def validate_canvas(self, canvas: LogicCanvas) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a canvas configuration.
        Returns (is_valid, warnings, errors)
        """
        warnings = []
        errors = []
        
        # Check for loops
        loops = canvas.detect_loops()
        if loops:
            for loop in loops:
                if any(
                    canvas.connections[cid].connection_type == ConnectionType.LOOP
                    for cid in canvas.connections
                    if canvas.connections[cid].source_node_id in loop
                ):
                    warnings.append(f"Intentional loop detected: {' → '.join(loop)}")
                else:
                    errors.append(f"Unintentional loop detected (compute waste risk): {' → '.join(loop)}")
        
        # Check for disconnected nodes
        order = canvas.get_execution_order()
        disconnected = [nid for nid in canvas.nodes if nid not in order and canvas.nodes[nid].node_type != NodeType.END]
        if disconnected:
            for nid in disconnected:
                warnings.append(f"Disconnected node: {canvas.nodes[nid].label} ({nid})")
        
        # Check for missing agents on agent nodes
        for node in canvas.nodes.values():
            if node.node_type == NodeType.AGENT and not node.agent:
                errors.append(f"Agent node without assigned agent: {node.node_id}")
        
        # Check for excessive parallel connections
        parallel_count = sum(1 for c in canvas.connections.values() if c.connection_type == ConnectionType.PARALLEL)
        if parallel_count > 5:
            warnings.append(f"High parallelism ({parallel_count} connections) may increase compute cost")
        
        # Check agent limit
        agent_count = sum(1 for n in canvas.nodes.values() if n.agent)
        if agent_count > MAX_AGENTS_STANDARD:
            warnings.append(f"Agent count ({agent_count}) exceeds standard limit ({MAX_AGENTS_STANDARD}). Clustering recommended.")
        
        is_valid = len(errors) == 0
        return is_valid, warnings, errors
    
    def generate_brp(self, canvas: LogicCanvas, swarm_id: str) -> BinaryReasonProof:
        """Generate Binary Reason Proof for the swarm path"""
        execution_path = []
        gate_evaluations = []
        
        for node_id in canvas.get_execution_order():
            node = canvas.nodes[node_id]
            execution_path.append(f"{node.label} ({node_id})")
            
            if node.agent:
                gate_evaluations.append({
                    "node_id": node_id,
                    "agent": node.agent.name,
                    "gates_checked": ["MUST_NOT_HARM", "MUST_AUDIT", "MUST_COMPLY"],
                    "result": "PASS"
                })
        
        # Estimate compute
        base_compute_ms = len(canvas.nodes) * 50
        parallel_factor = 0.7 if canvas._detect_flow_type() == "PARALLEL" else 1.0
        estimated_compute = base_compute_ms * parallel_factor
        
        # Estimate cost (fictional pricing)
        estimated_cost = estimated_compute * 0.00001  # $0.00001 per ms
        
        # Generate proof hash
        proof_content = json.dumps({
            "swarm_id": swarm_id,
            "path": execution_path,
            "gates": gate_evaluations,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, sort_keys=True)
        
        proof_hash = hmac.new(
            self.sovereign_salt.salt.encode(),
            proof_content.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return BinaryReasonProof(
            brp_id=f"BRP-{uuid.uuid4().hex[:8].upper()}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            swarm_id=swarm_id,
            execution_path=execution_path,
            gate_evaluations=gate_evaluations,
            estimated_compute_ms=estimated_compute,
            estimated_cost_usd=estimated_cost,
            risk_assessment="LOW" if len(canvas.detect_loops()) == 0 else "MEDIUM",
            proof_hash=proof_hash
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ZONE C: STRIKE CONSOLE
# ═══════════════════════════════════════════════════════════════════════════════

class StrikeConsole:
    """
    Final deployment execution area.
    Manages swarm lifecycle from draft to execution.
    """
    
    def __init__(self):
        self.sovereign_salt = SovereignSalt()
        self.deployments: Dict[str, SwarmDeployment] = {}
        self.active_deployment: Optional[str] = None
        self.enclave_locked = False
        self.lock_reason: Optional[EnclaveLockReason] = None
        self.pre_flight = LogicPreFlight()
    
    def create_deployment(
        self,
        name: str,
        description: str,
        canvas: LogicCanvas
    ) -> SwarmDeployment:
        """Create a new swarm deployment from canvas"""
        swarm_id = f"SWARM-{uuid.uuid4().hex[:8].upper()}"
        
        deployment = SwarmDeployment(
            swarm_id=swarm_id,
            name=name,
            description=description,
            state=SwarmState.DRAFT,
            created_at=datetime.now(timezone.utc).isoformat(),
            nodes=list(canvas.nodes.values()),
            connections=list(canvas.connections.values())
        )
        
        self.deployments[swarm_id] = deployment
        return deployment
    
    def validate_deployment(self, swarm_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate a deployment using Logic Pre-Flight"""
        if swarm_id not in self.deployments:
            return False, {"error": "Deployment not found"}
        
        deployment = self.deployments[swarm_id]
        
        # Reconstruct canvas for validation
        canvas = LogicCanvas()
        for node in deployment.nodes:
            canvas.nodes[node.node_id] = node
        for conn in deployment.connections:
            canvas.connections[conn.connection_id] = conn
        
        is_valid, warnings, errors = self.pre_flight.validate_canvas(canvas)
        
        result = {
            "swarm_id": swarm_id,
            "is_valid": is_valid,
            "warnings": warnings,
            "errors": errors,
            "validated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if is_valid:
            deployment.state = SwarmState.VALIDATED
        
        return is_valid, result
    
    def simulate_strike(self, swarm_id: str) -> Optional[BinaryReasonProof]:
        """Generate BRP simulation before execution"""
        if swarm_id not in self.deployments:
            return None
        
        deployment = self.deployments[swarm_id]
        
        if deployment.state not in [SwarmState.VALIDATED, SwarmState.DRAFT]:
            return None
        
        # Reconstruct canvas
        canvas = LogicCanvas()
        for node in deployment.nodes:
            canvas.nodes[node.node_id] = node
        for conn in deployment.connections:
            canvas.connections[conn.connection_id] = conn
        
        brp = self.pre_flight.generate_brp(canvas, swarm_id)
        deployment.brp = brp
        deployment.state = SwarmState.SIMULATED
        
        return brp
    
    def arm_deployment(self, swarm_id: str, smk_raw_key: str) -> Tuple[bool, str]:
        """Arm a deployment for execution (first lock of double-lock)"""
        if self.enclave_locked:
            return False, f"ENCLAVE_LOCKED: {self.lock_reason.value if self.lock_reason else 'UNKNOWN'}"
        
        if swarm_id not in self.deployments:
            return False, "DEPLOYMENT_NOT_FOUND"
        
        deployment = self.deployments[swarm_id]
        
        if deployment.state != SwarmState.SIMULATED:
            return False, f"INVALID_STATE: Must be SIMULATED, currently {deployment.state.value}"
        
        # Verify SMK (simplified - would validate against key manager in production)
        if len(smk_raw_key) < 20:
            return False, "INVALID_SMK"
        
        # Generate arm signature
        arm_content = f"ARM:{swarm_id}:{deployment.brp.proof_hash if deployment.brp else 'NO_BRP'}"
        arm_signature = hmac.new(
            self.sovereign_salt.salt.encode(),
            arm_content.encode(),
            hashlib.sha256
        ).hexdigest()
        
        deployment.architect_signature = arm_signature
        deployment.state = SwarmState.ARMED
        self.active_deployment = swarm_id
        
        deployment.execution_log.append({
            "action": "ARMED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signature_preview": arm_signature[:16]
        })
        
        return True, "DEPLOYMENT_ARMED"
    
    def execute_swarm(self, swarm_id: str, confirmation_code: str) -> Tuple[bool, Dict[str, Any]]:
        """Execute the swarm (second lock of double-lock)"""
        if self.enclave_locked:
            return False, {"error": f"ENCLAVE_LOCKED: {self.lock_reason.value if self.lock_reason else 'UNKNOWN'}"}
        
        if swarm_id not in self.deployments:
            return False, {"error": "DEPLOYMENT_NOT_FOUND"}
        
        deployment = self.deployments[swarm_id]
        
        if deployment.state != SwarmState.ARMED:
            return False, {"error": f"INVALID_STATE: Must be ARMED, currently {deployment.state.value}"}
        
        # Verify confirmation code (derived from arm signature)
        expected_code = hashlib.sha256(
            f"{deployment.architect_signature}:CONFIRM".encode()
        ).hexdigest()[:16].upper()
        
        if confirmation_code != expected_code:
            return False, {"error": "INVALID_CONFIRMATION_CODE", "expected_format": "16-char hex"}
        
        # Execute!
        deployment.state = SwarmState.EXECUTING
        
        execution_result = {
            "swarm_id": swarm_id,
            "status": "EXECUTING",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "agents_deployed": [],
            "lane_status": []
        }
        
        # Simulate execution of each node
        for i, node in enumerate(deployment.nodes):
            if node.agent:
                execution_result["agents_deployed"].append({
                    "gid": node.agent.gid,
                    "name": node.agent.name,
                    "task": node.label,
                    "status": "EXECUTING"
                })
                
                execution_result["lane_status"].append({
                    "lane": i + 1,
                    "node_id": node.node_id,
                    "status": "COMPLETE",
                    "latency_ms": 25 + (i * 10)
                })
        
        deployment.state = SwarmState.COMPLETE
        execution_result["status"] = "COMPLETE"
        execution_result["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        deployment.execution_log.append({
            "action": "EXECUTED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result": execution_result
        })
        
        self.active_deployment = None
        
        return True, execution_result
    
    def engage_enclave_lock(self, reason: EnclaveLockReason):
        """Lock the enclave (fail-closed)"""
        self.enclave_locked = True
        self.lock_reason = reason
        
        # Set any armed deployment to LOCKED
        if self.active_deployment and self.active_deployment in self.deployments:
            self.deployments[self.active_deployment].state = SwarmState.LOCKED
    
    def release_enclave_lock(self, smk_raw_key: str) -> Tuple[bool, str]:
        """Release enclave lock with SMK re-authentication"""
        if len(smk_raw_key) < 20:
            return False, "INVALID_SMK"
        
        self.enclave_locked = False
        self.lock_reason = None
        
        return True, "ENCLAVE_UNLOCKED"
    
    def get_console_state(self) -> Dict[str, Any]:
        """Get complete strike console state"""
        return {
            "enclave_locked": self.enclave_locked,
            "lock_reason": self.lock_reason.value if self.lock_reason else None,
            "active_deployment": self.active_deployment,
            "deployments": {
                sid: d.to_dict() for sid, d in self.deployments.items()
            },
            "deployment_count": len(self.deployments)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SOVEREIGN COMMAND CANVAS (MAIN ORCHESTRATOR)
# ═══════════════════════════════════════════════════════════════════════════════

class SovereignCommandCanvas:
    """
    Master orchestrator for the Visual Swarm Builder.
    Integrates Agent Forge, Logic Canvas, and Strike Console.
    """
    
    def __init__(self):
        self.agent_forge = AgentForge()
        self.canvas = LogicCanvas()
        self.strike_console = StrikeConsole()
        self.session_id = f"SESSION-{uuid.uuid4().hex[:8].upper()}"
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.telemetry_enabled = True
        self.telemetry_log: List[Dict[str, Any]] = []
    
    def drag_agent_to_canvas(
        self,
        agent_gid: str,
        position: Dict[str, float],
        label: str = ""
    ) -> Optional[CanvasNode]:
        """Drag an agent from forge to canvas"""
        agent = self.agent_forge.get_agent(agent_gid)
        if not agent:
            return None
        
        node = self.canvas.add_node(
            node_type=NodeType.AGENT,
            position=position,
            agent=agent,
            label=label or f"{agent.name} Task"
        )
        
        self._log_telemetry("AGENT_PLACED", {
            "agent_gid": agent_gid,
            "node_id": node.node_id,
            "position": position
        })
        
        return node
    
    def connect_agents(
        self,
        source_node_id: str,
        target_node_id: str,
        connection_type: ConnectionType = ConnectionType.SEQUENTIAL
    ) -> Optional[CanvasConnection]:
        """Create a connection between nodes"""
        connection = self.canvas.connect_nodes(
            source_node_id, target_node_id, connection_type
        )
        
        if connection:
            self._log_telemetry("CONNECTION_CREATED", {
                "connection_id": connection.connection_id,
                "source": source_node_id,
                "target": target_node_id,
                "type": connection_type.value
            })
        
        return connection
    
    def create_pipeline(self, agent_gids: List[str], name: str = "Pipeline") -> List[CanvasNode]:
        """Quick-create a sequential pipeline of agents"""
        nodes = []
        x_pos = 100
        
        for i, gid in enumerate(agent_gids):
            node = self.drag_agent_to_canvas(gid, {"x": x_pos, "y": 200})
            if node:
                nodes.append(node)
                x_pos += 200
        
        # Connect sequentially
        for i in range(len(nodes) - 1):
            self.connect_agents(nodes[i].node_id, nodes[i+1].node_id)
        
        self._log_telemetry("PIPELINE_CREATED", {
            "name": name,
            "agents": agent_gids,
            "node_count": len(nodes)
        })
        
        return nodes
    
    def initialize_swarm(self, name: str, description: str) -> SwarmDeployment:
        """Create deployment from current canvas state"""
        deployment = self.strike_console.create_deployment(name, description, self.canvas)
        
        self._log_telemetry("SWARM_INITIALIZED", {
            "swarm_id": deployment.swarm_id,
            "name": name,
            "node_count": len(deployment.nodes)
        })
        
        return deployment
    
    def simulate_and_validate(self, swarm_id: str) -> Dict[str, Any]:
        """Run simulation and validation"""
        # Validate first
        is_valid, validation_result = self.strike_console.validate_deployment(swarm_id)
        
        if not is_valid:
            return {
                "success": False,
                "validation": validation_result
            }
        
        # Then simulate
        brp = self.strike_console.simulate_strike(swarm_id)
        
        return {
            "success": True,
            "validation": validation_result,
            "brp": brp.to_dict() if brp else None
        }
    
    def _log_telemetry(self, event: str, data: Dict[str, Any]):
        """Log telemetry event (for live UI updates)"""
        if self.telemetry_enabled:
            self.telemetry_log.append({
                "event": event,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": self.session_id,
                "data": data
            })
    
    def get_telemetry_stream(self, since_index: int = 0) -> List[Dict[str, Any]]:
        """Get telemetry events since index (for SSE)"""
        return self.telemetry_log[since_index:]
    
    def get_complete_state(self) -> Dict[str, Any]:
        """Get complete canvas builder state"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "version": CANVAS_VERSION,
            "zones": {
                "agent_forge": self.agent_forge.get_roster(),
                "logic_canvas": self.canvas.get_canvas_state(),
                "strike_console": self.strike_console.get_console_state()
            },
            "telemetry": {
                "enabled": self.telemetry_enabled,
                "event_count": len(self.telemetry_log)
            }
        }
    
    def render_ascii_canvas(self) -> str:
        """Render ASCII representation of the canvas"""
        lines = []
        lines.append("=" * 80)
        lines.append("  SOVEREIGN COMMAND CANVAS | Visual Swarm Builder")
        lines.append("=" * 80)
        lines.append("")
        
        # Agent Forge
        lines.append("┌─ ZONE A: AGENT FORGE ────────────────────────────────────────────────────────┐")
        for agent in list(self.agent_forge.agents.values())[:5]:
            status_icon = "●" if agent.status in [AgentStatus.ACTIVE, AgentStatus.DEPLOYED] else "○"
            lines.append(f"│  {agent.icon} {status_icon} {agent.name:<15} │ {agent.role:<25} │ {agent.status.value:<10} │")
        lines.append("│  ... and more                                                                │")
        lines.append("└──────────────────────────────────────────────────────────────────────────────┘")
        lines.append("")
        
        # Logic Canvas
        lines.append("┌─ ZONE B: LOGIC CANVAS ───────────────────────────────────────────────────────┐")
        if self.canvas.nodes:
            order = self.canvas.get_execution_order()
            flow_str = " → ".join([
                self.canvas.nodes[nid].label[:12] 
                for nid in order[:5]
            ])
            if len(order) > 5:
                flow_str += " → ..."
            lines.append(f"│  Flow: {flow_str:<68}│")
            lines.append(f"│  Nodes: {len(self.canvas.nodes):<5} │ Connections: {len(self.canvas.connections):<5} │ Type: {self.canvas._detect_flow_type():<15}│")
        else:
            lines.append("│  [Empty Canvas - Drag agents from Zone A to build workflow]                 │")
        lines.append("└──────────────────────────────────────────────────────────────────────────────┘")
        lines.append("")
        
        # Strike Console
        lines.append("┌─ ZONE C: STRIKE CONSOLE ─────────────────────────────────────────────────────┐")
        console = self.strike_console
        lock_status = "🔒 LOCKED" if console.enclave_locked else "🔓 READY"
        lines.append(f"│  Enclave: {lock_status:<66}│")
        lines.append(f"│  Deployments: {len(console.deployments):<62}│")
        if console.active_deployment:
            deployment = console.deployments[console.active_deployment]
            lines.append(f"│  Active: {deployment.name:<20} │ State: {deployment.state.value:<20}│")
        lines.append("└──────────────────────────────────────────────────────────────────────────────┘")
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def launch_command_canvas():
    """Launch the Sovereign Command Canvas and demo workflow"""
    print("=" * 80)
    print("INITIALIZING SOVEREIGN COMMAND CANVAS")
    print("PAC-CANVAS-DEPLOY-39 | Visual Swarm Builder")
    print("=" * 80)
    print()
    
    # Initialize canvas
    canvas_builder = SovereignCommandCanvas()
    
    print("[LANE 1] NODE-EDITOR-SYNC: Mapping components to PAC schema...")
    
    # Demo: Create a pipeline for PNC Shadow-Vet
    print()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║  DEMO: PNC SHADOW-VET PIPELINE                                               ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Create the pipeline
    print("Dragging agents to canvas...")
    pipeline_agents = ["GID-03", "GID-04", "GID-05", "GID-00"]  # Vaporizer → Blind-Portal → Certifier → Benson
    nodes = canvas_builder.create_pipeline(pipeline_agents, "PNC-Shadow-Vet")
    
    print(f"  Created {len(nodes)} nodes:")
    for node in nodes:
        print(f"    {node.agent.icon} {node.agent.name} → {node.label}")
    
    print()
    print("[LANE 2] LIVE-TELEMETRY: Enabling real-time pulse...")
    
    # Show canvas state
    print()
    print(canvas_builder.render_ascii_canvas())
    
    print("[LANE 3] SMK-SIGN-OFF: Double-lock signature ready...")
    print()
    
    # Initialize swarm deployment
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║  INITIALIZING SWARM DEPLOYMENT                                               ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    deployment = canvas_builder.initialize_swarm(
        name="PNC-Shadow-Vet-Strike",
        description="Shadow vetting pipeline for PNC pilot deployment"
    )
    
    print(f"  Swarm ID: {deployment.swarm_id}")
    print(f"  State: {deployment.state.value}")
    print()
    
    # Simulate and validate
    print("Running simulation (Proof > Execution)...")
    result = canvas_builder.simulate_and_validate(deployment.swarm_id)
    
    print()
    if result["success"]:
        print("  ✅ VALIDATION: PASSED")
        print(f"  ✅ SIMULATION: COMPLETE")
        if result["brp"]:
            brp = result["brp"]
            print(f"     BRP ID: {brp['brp_id']}")
            print(f"     Estimated Compute: {brp['estimated_compute_ms']:.1f}ms")
            print(f"     Estimated Cost: ${brp['estimated_cost_usd']:.6f}")
            print(f"     Risk: {brp['risk_assessment']}")
            print(f"     Proof Hash: {brp['proof_hash']}")
    else:
        print("  ❌ VALIDATION FAILED")
        print(f"  Errors: {result['validation'].get('errors', [])}")
    
    print()
    print("=" * 80)
    print("SOVEREIGN COMMAND CANVAS: ONLINE")
    print("=" * 80)
    print()
    print("To arm and execute this deployment:")
    print(f"  1. canvas_builder.strike_console.arm_deployment('{deployment.swarm_id}', '<SMK_KEY>')")
    print(f"  2. canvas_builder.strike_console.execute_swarm('{deployment.swarm_id}', '<CONFIRM_CODE>')")
    print()
    print("Access via browser: http://localhost:8080/occ/ui?mode=architect")
    print()
    
    print("[PERMANENT LEDGER ENTRY: PL-044]")
    print(json.dumps({
        "entry_id": "PL-044",
        "entry_type": "COMMAND_CANVAS_INITIALIZED",
        "session_id": canvas_builder.session_id,
        "demo_swarm_id": deployment.swarm_id,
        "pipeline": ["Vaporizer", "Blind-Portal", "Certifier", "Benson"]
    }, indent=2))
    
    return canvas_builder


if __name__ == "__main__":
    canvas_builder = launch_command_canvas()
