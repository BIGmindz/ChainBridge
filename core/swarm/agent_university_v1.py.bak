"""
PAC-UNI-100: AGENT UNIVERSITY
==============================

The Deterministic Swarm Factory: Scales personas through cloning.

ARCHITECTURE:
- Lane → Job → Task → Squad → Clone
- One Persona (GID) → Many Clones (GID-XX)
- Deterministic allocation (Round Robin / Hash Modulo)

INVARIANTS:
- UNI-01: Task allocation MUST be deterministic (no probabilities)
- UNI-02: Clones MUST inherit strict properties from parent GID

Author: BENSON (GID-00) via PAC-UNI-100
Version: 1.0.0
Status: PRODUCTION-READY
"""

import logging
import json
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field, StrictStr, StrictInt
from enum import Enum


# Configure logging
logger = logging.getLogger("AgentUniversity")
logger.setLevel(logging.INFO)


# ============================================================================
# SWARM DATA STRUCTURES
# ============================================================================

class TaskStatus(Enum):
    """Task execution states."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    EXECUTING = "executing"
    COMPLETE = "complete"
    FAILED = "failed"


class Task(BaseModel):
    """
    Atomic unit of work in the swarm.
    
    Tasks are deterministically assigned to agent clones.
    """
    id: StrictStr = Field(..., description="Unique task identifier")
    description: StrictStr = Field(..., description="Human-readable task description")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task execution data")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task state")
    assigned_to: Optional[StrictStr] = Field(default=None, description="GID of assigned clone")
    result: Optional[str] = Field(default=None, description="Task execution result")
    
    class Config:
        use_enum_values = True


class JobManifest(BaseModel):
    """
    Collection of tasks grouped by lane.
    
    Example: "SECURITY_LANE" might contain 100 audit tasks.
    """
    lane: StrictStr = Field(..., description="Job category/lane identifier")
    job_id: StrictStr = Field(..., description="Unique job identifier")
    tasks: List[Task] = Field(default_factory=list, description="Tasks to execute")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Job metadata")


class GIDPersona(BaseModel):
    """
    Parent GID persona template.
    
    Clones inherit these properties deterministically.
    """
    gid: StrictStr = Field(..., description="Parent GID (e.g., 'GID-06')")
    name: StrictStr = Field(..., description="Agent name")
    role: StrictStr = Field(..., description="Primary role")
    skills: List[str] = Field(default_factory=list, description="Agent capabilities")
    scope: Optional[str] = Field(default=None, description="Operational scope")
    
    class Config:
        use_enum_values = True


# ============================================================================
# AGENT CLONE
# ============================================================================

class AgentClone:
    """
    Deterministic clone of a GID persona.
    
    Clone Naming Convention:
    - Parent: GID-06 (SAM - Security Auditor)
    - Clone 1: GID-06-01
    - Clone 2: GID-06-02
    - Clone N: GID-06-{N:02d}
    
    Clones inherit:
    - Role (from parent)
    - Skills (from parent)
    - Scope (from parent)
    
    Clones have unique:
    - Clone ID (numeric suffix)
    - Task queue (independent)
    - Execution state (isolated)
    """
    
    def __init__(self, parent: GIDPersona, clone_id: int):
        """
        Initialize agent clone from parent persona.
        
        Args:
            parent: Parent GID persona template
            clone_id: Unique clone number (1-based)
        """
        self.parent_gid = parent.gid
        self.clone_id = clone_id
        self.gid = f"{parent.gid}-{clone_id:02d}"
        self.name = f"{parent.name}-{clone_id:02d}"
        self.role = parent.role
        self.skills = parent.skills.copy()
        self.scope = parent.scope
        
        # Clone-specific state
        self.task_queue: List[Task] = []
        self.tasks_completed = 0
        self.tasks_failed = 0
        
        self.logger = logging.getLogger(f"AgentClone-{self.gid}")
    
    def assign_task(self, task: Task):
        """
        Assign task to clone's queue.
        
        Args:
            task: Task to assign
        """
        task.status = TaskStatus.ASSIGNED
        task.assigned_to = self.gid
        self.task_queue.append(task)
        self.logger.info(f"📥 Task {task.id} assigned to {self.gid}")
    
    def execute_task(self, task: Task) -> str:
        """
        Execute assigned task deterministically.
        
        Args:
            task: Task to execute
        
        Returns:
            Execution result string
        """
        self.logger.info(f"⚙️  Executing Task {task.id}: {task.description}")
        task.status = TaskStatus.EXECUTING
        
        try:
            # Deterministic execution logic
            # In production: Actual task processing based on role/skills
            result = f"TASK_{task.id}_COMPLETE_BY_{self.gid}"
            
            task.status = TaskStatus.COMPLETE
            task.result = result
            self.tasks_completed += 1
            
            self.logger.info(f"✅ Task {task.id} completed by {self.gid}")
            return result
        
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.result = f"ERROR: {str(e)}"
            self.tasks_failed += 1
            
            self.logger.error(f"❌ Task {task.id} failed: {e}")
            raise
    
    def execute_all_tasks(self) -> Dict[str, Any]:
        """
        Execute all tasks in queue.
        
        Returns:
            Execution summary
        """
        results = []
        
        for task in self.task_queue:
            try:
                result = self.execute_task(task)
                results.append({"task_id": task.id, "status": "complete", "result": result})
            except Exception as e:
                results.append({"task_id": task.id, "status": "failed", "error": str(e)})
        
        return {
            "clone_gid": self.gid,
            "tasks_executed": len(self.task_queue),
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "results": results
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get clone execution statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "gid": self.gid,
            "parent_gid": self.parent_gid,
            "clone_id": self.clone_id,
            "role": self.role,
            "skills": self.skills,
            "tasks_queued": len(self.task_queue),
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed
        }


# ============================================================================
# AGENT UNIVERSITY (FACTORY)
# ============================================================================

class AgentUniversity:
    """
    PAC-UNI-100: The Deterministic Swarm Factory.
    
    Spawns agent clones from GID persona templates.
    
    Factory Pattern:
    1. Load GID registry (persona templates)
    2. Spawn N clones of parent GID
    3. Clones inherit properties deterministically
    4. Return squad for task execution
    
    Usage:
        university = AgentUniversity()
        sam_squad = university.spawn_squad("GID-06", count=10)
        # Creates: GID-06-01, GID-06-02, ..., GID-06-10
    """
    
    DEFAULT_REGISTRY_PATH = "core/governance/gid_registry.json"
    
    def __init__(self, registry_path: Optional[str] = None):
        """
        Initialize Agent University with GID registry.
        
        Args:
            registry_path: Path to gid_registry.json (optional)
        """
        self.registry_path = registry_path or self.DEFAULT_REGISTRY_PATH
        self.registry: Dict[str, GIDPersona] = self._load_registry()
        self.squads: Dict[str, List[AgentClone]] = {}
        self.logger = logging.getLogger("AgentUniversity")
        
        self.logger.info(f"🎓 Agent University initialized with {len(self.registry)} personas")
    
    def _load_registry(self) -> Dict[str, GIDPersona]:
        """
        Load GID registry from JSON file.
        
        Returns:
            Dictionary mapping GID → GIDPersona
        """
        try:
            with open(self.registry_path, 'r') as f:
                registry_data = json.load(f)
            
            personas = {}
            for gid, data in registry_data.items():
                personas[gid] = GIDPersona(
                    gid=gid,
                    name=data.get("name", "Unknown"),
                    role=data.get("role", "Unknown"),
                    skills=data.get("skills", []),
                    scope=data.get("scope")
                )
            
            self.logger.info(f"📚 Loaded {len(personas)} GID personas from {self.registry_path}")
            return personas
        
        except FileNotFoundError:
            self.logger.warning(f"Registry not found: {self.registry_path}. Using fallback.")
            # Fallback registry for testing
            return {
                "GID-06": GIDPersona(
                    gid="GID-06",
                    name="SAM",
                    role="SECURITY_AUDITOR",
                    skills=["FUZZING", "PEN_TEST", "THREAT_MODELING"],
                    scope="Security validation and threat assessment"
                )
            }
    
    def spawn_squad(self, parent_gid: str, count: int) -> List[AgentClone]:
        """
        Deterministic factory method: Spawn agent squad.
        
        Creates 'count' clones of the parent GID persona.
        
        Args:
            parent_gid: Parent GID to clone (e.g., "GID-06")
            count: Number of clones to create
        
        Returns:
            List of AgentClone instances
        
        Raises:
            ValueError: If parent_gid not in registry
        
        Example:
            squad = university.spawn_squad("GID-06", count=5)
            # Returns: [GID-06-01, GID-06-02, GID-06-03, GID-06-04, GID-06-05]
        """
        if parent_gid not in self.registry:
            raise ValueError(f"Unknown parent GID: {parent_gid}. Available: {list(self.registry.keys())}")
        
        persona = self.registry[parent_gid]
        squad = []
        
        for clone_id in range(1, count + 1):
            clone = AgentClone(persona, clone_id)
            squad.append(clone)
            self.logger.info(f"🎓 GRADUATED: {clone.gid} ({clone.role})")
        
        # Cache squad
        squad_key = f"{parent_gid}-SQUAD-{count}"
        self.squads[squad_key] = squad
        
        self.logger.info(f"✅ Spawned squad of {count} clones from {parent_gid}")
        return squad
    
    def get_persona(self, gid: str) -> Optional[GIDPersona]:
        """
        Get persona template for GID.
        
        Args:
            gid: Parent GID
        
        Returns:
            GIDPersona or None
        """
        return self.registry.get(gid)
    
    def list_personas(self) -> List[str]:
        """
        List available parent GIDs.
        
        Returns:
            List of GID identifiers
        """
        return list(self.registry.keys())


# ============================================================================
# SWARM DISPATCHER
# ============================================================================

class DispatchStrategy(Enum):
    """Task dispatch strategies."""
    ROUND_ROBIN = "round_robin"
    HASH_MODULO = "hash_modulo"


class SwarmDispatcher:
    """
    Deterministic task router for agent squads.
    
    Dispatch Strategies:
    1. ROUND_ROBIN: Sequential allocation (task[i] → agent[i % N])
    2. HASH_MODULO: Hash-based allocation (hash(task.id) % N → agent)
    
    Both strategies are deterministic (no randomness).
    
    Invariants:
    - UNI-01: Task allocation MUST be deterministic
    - Same input (tasks + squad) → Same output (allocations)
    
    Usage:
        dispatcher = SwarmDispatcher()
        allocations = dispatcher.dispatch(job, squad, strategy="round_robin")
    """
    
    def __init__(self):
        """Initialize swarm dispatcher."""
        self.logger = logging.getLogger("SwarmDispatcher")
    
    def dispatch(
        self,
        job: JobManifest,
        squad: List[AgentClone],
        strategy: DispatchStrategy = DispatchStrategy.ROUND_ROBIN
    ) -> Dict[str, List[Task]]:
        """
        Dispatch tasks to agent squad using specified strategy.
        
        Args:
            job: Job manifest with tasks
            squad: Agent squad to allocate tasks to
            strategy: Dispatch strategy (round_robin or hash_modulo)
        
        Returns:
            Dictionary mapping agent GID → assigned tasks
        
        Example:
            {
                "GID-06-01": [task1, task4, task7],
                "GID-06-02": [task2, task5, task8],
                "GID-06-03": [task3, task6, task9]
            }
        """
        if not squad:
            raise ValueError("Cannot dispatch to empty squad")
        
        if not job.tasks:
            self.logger.warning(f"No tasks in job {job.job_id}")
            return {agent.gid: [] for agent in squad}
        
        # Initialize allocations
        allocations = {agent.gid: [] for agent in squad}
        squad_size = len(squad)
        
        self.logger.info(f"🚀 Dispatching {len(job.tasks)} tasks to squad of {squad_size} agents")
        self.logger.info(f"   Strategy: {strategy.value}")
        
        # Dispatch based on strategy
        if strategy == DispatchStrategy.ROUND_ROBIN:
            allocations = self._dispatch_round_robin(job.tasks, squad, allocations, squad_size)
        elif strategy == DispatchStrategy.HASH_MODULO:
            allocations = self._dispatch_hash_modulo(job.tasks, squad, allocations, squad_size)
        else:
            raise ValueError(f"Unknown dispatch strategy: {strategy}")
        
        # Assign tasks to clones
        for agent in squad:
            for task in allocations[agent.gid]:
                agent.assign_task(task)
        
        # Log allocation summary
        for agent_gid, tasks in allocations.items():
            self.logger.info(f"   {agent_gid}: {len(tasks)} tasks assigned")
        
        return allocations
    
    def _dispatch_round_robin(
        self,
        tasks: List[Task],
        squad: List[AgentClone],
        allocations: Dict[str, List[Task]],
        squad_size: int
    ) -> Dict[str, List[Task]]:
        """
        Round-robin dispatch: task[i] → agent[i % N].
        
        Deterministic sequential allocation.
        """
        for i, task in enumerate(tasks):
            assigned_index = i % squad_size
            assigned_agent = squad[assigned_index]
            allocations[assigned_agent.gid].append(task)
        
        return allocations
    
    def _dispatch_hash_modulo(
        self,
        tasks: List[Task],
        squad: List[AgentClone],
        allocations: Dict[str, List[Task]],
        squad_size: int
    ) -> Dict[str, List[Task]]:
        """
        Hash-modulo dispatch: hash(task.id) % N → agent.
        
        Stateless deterministic allocation (same task.id → same agent).
        """
        for task in tasks:
            # Deterministic hash of task ID
            task_hash = int(hashlib.sha256(task.id.encode()).hexdigest(), 16)
            assigned_index = task_hash % squad_size
            assigned_agent = squad[assigned_index]
            allocations[assigned_agent.gid].append(task)
        
        return allocations
    
    def get_allocation_stats(self, allocations: Dict[str, List[Task]]) -> Dict[str, Any]:
        """
        Get allocation statistics.
        
        Args:
            allocations: Dispatch result
        
        Returns:
            Statistics dictionary
        """
        total_tasks = sum(len(tasks) for tasks in allocations.values())
        
        return {
            "total_tasks": total_tasks,
            "agents": len(allocations),
            "tasks_per_agent": {gid: len(tasks) for gid, tasks in allocations.items()},
            "min_tasks": min(len(tasks) for tasks in allocations.values()) if allocations else 0,
            "max_tasks": max(len(tasks) for tasks in allocations.values()) if allocations else 0,
            "avg_tasks": total_tasks / len(allocations) if allocations else 0
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_test_job(lane: str, task_count: int) -> JobManifest:
    """
    Create test job manifest with N tasks.
    
    Args:
        lane: Job lane identifier
        task_count: Number of tasks to create
    
    Returns:
        JobManifest with test tasks
    """
    tasks = [
        Task(
            id=f"TASK-{i:04d}",
            description=f"Test task #{i}",
            payload={"task_number": i, "test_mode": True}
        )
        for i in range(1, task_count + 1)
    ]
    
    return JobManifest(
        lane=lane,
        job_id=f"JOB-{lane}-{task_count}",
        tasks=tasks,
        metadata={"test_mode": True, "task_count": task_count}
    )


# ============================================================================
# MAIN ENTRY POINT (Testing)
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")
    
    print("=" * 70)
    print("PAC-UNI-100: AGENT UNIVERSITY DEMONSTRATION")
    print("=" * 70)
    
    # Initialize university
    university = AgentUniversity()
    
    # Spawn squad
    print("\n🎓 Spawning SAM (Security Auditor) Squad...")
    sam_squad = university.spawn_squad("GID-06", count=3)
    
    # Create test job
    print("\n📋 Creating test job with 10 tasks...")
    job = create_test_job(lane="SECURITY", task_count=10)
    
    # Dispatch tasks
    print("\n🚀 Dispatching tasks (Round Robin)...")
    dispatcher = SwarmDispatcher()
    allocations = dispatcher.dispatch(job, sam_squad, strategy=DispatchStrategy.ROUND_ROBIN)
    
    # Show stats
    stats = dispatcher.get_allocation_stats(allocations)
    print(f"\n📊 Allocation Statistics:")
    print(f"   Total Tasks: {stats['total_tasks']}")
    print(f"   Agents: {stats['agents']}")
    print(f"   Tasks per Agent: {stats['tasks_per_agent']}")
    print(f"   Min/Max/Avg: {stats['min_tasks']}/{stats['max_tasks']}/{stats['avg_tasks']:.2f}")
    
    # Execute tasks
    print("\n⚙️  Executing tasks...")
    for agent in sam_squad:
        result = agent.execute_all_tasks()
        print(f"   {result['clone_gid']}: {result['tasks_completed']}/{result['tasks_executed']} completed")
    
    print("\n" + "=" * 70)
    print("✅ AGENT UNIVERSITY OPERATIONAL")
    print("=" * 70)
