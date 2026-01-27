"""
PAC-DEV-P50: Cortex Resonance Tests
====================================
Validates LLMBridge determinism and AgentClone integration.

Test Coverage:
1. test_llm_bridge_resonance: Identical inputs → Identical hashes
2. test_llm_bridge_dissonance: Different inputs → Different hashes
3. test_agent_clone_wiring: AgentClone + LLMBridge integration

Invariants:
- RESONANCE-01: Same task → Same hash (determinism)
- RESONANCE-02: Different task → Different hash (uniqueness)
- RESONANCE-03: Agent can reason with LLMBridge (wiring)
"""

import pytest
import asyncio
from core.intelligence.llm_bridge import LLMBridge
from core.swarm.types import Task, PrimeDirective
from core.swarm.agent_university import AgentClone, GIDPersona


@pytest.mark.asyncio
async def test_llm_bridge_resonance():
    """
    RESONANCE-01: Identical inputs MUST produce identical hashes.
    
    Test Scenario:
    - Create two identical tasks
    - Process both through LLMBridge
    - Verify hashes match (cryptographic resonance)
    """
    # Arrange: Create LLMBridge with deterministic settings
    bridge = LLMBridge(model_name="gpt-4", temperature=0.0)
    
    # Create identical tasks
    task1 = Task(
        task_id="TASK-RESONANCE-001",
        task_type="GOVERNANCE_CHECK",
        payload={"transaction_id": "TXN-123", "amount_usd": 50000}
    )
    
    task2 = Task(
        task_id="TASK-RESONANCE-001",  # Same ID
        task_type="GOVERNANCE_CHECK",
        payload={"transaction_id": "TXN-123", "amount_usd": 50000}  # Same payload
    )
    
    directive = PrimeDirective(
        mission="Validate transaction compliance",
        constraints=["READ_ONLY", "MAX_AMOUNT_100K"]
    )
    
    context = {"directive": directive}
    
    # Act: Process both tasks
    result1 = await bridge.reason(task1, context)
    result2 = await bridge.reason(task2, context)
    
    # Assert: Hashes MUST match (resonance)
    assert result1.hash == result2.hash, (
        f"RESONANCE FAILURE: Identical tasks produced different hashes.\n"
        f"Hash 1: {result1.hash}\n"
        f"Hash 2: {result2.hash}\n"
        f"Decision 1: {result1.decision} | Decision 2: {result2.decision}\n"
        f"Reasoning 1: {result1.reasoning[:100]}...\n"
        f"Reasoning 2: {result2.reasoning[:100]}..."
    )
    
    # Verify using bridge's resonance checker
    assert bridge.verify_resonance(result1, result2), "Bridge resonance verification failed"
    
    print(f"✅ RESONANCE-01 PASSED: Hash = {result1.hash[:16]}...")


@pytest.mark.asyncio
async def test_llm_bridge_dissonance():
    """
    RESONANCE-02: Different inputs MUST produce different hashes.
    
    Test Scenario:
    - Create two different tasks
    - Process both through LLMBridge
    - Verify hashes differ (cryptographic uniqueness)
    """
    # Arrange
    bridge = LLMBridge(model_name="gpt-4", temperature=0.0)
    
    # Create different tasks
    task1 = Task(
        task_id="TASK-DISSONANCE-001",
        task_type="GOVERNANCE_CHECK",
        payload={"transaction_id": "TXN-123", "amount_usd": 50000}
    )
    
    task2 = Task(
        task_id="TASK-DISSONANCE-002",  # Different ID
        task_type="RISK_ASSESSMENT",    # Different type
        payload={"transaction_id": "TXN-456", "amount_usd": 99000}  # Different payload
    )
    
    directive = PrimeDirective(
        mission="Validate transaction compliance",
        constraints=["READ_ONLY"]
    )
    
    context = {"directive": directive}
    
    # Act
    result1 = await bridge.reason(task1, context)
    result2 = await bridge.reason(task2, context)
    
    # Assert: Hashes MUST differ (dissonance)
    assert result1.hash != result2.hash, (
        f"DISSONANCE FAILURE: Different tasks produced identical hashes.\n"
        f"Hash: {result1.hash}\n"
        f"Task 1: {task1.task_id} ({task1.task_type})\n"
        f"Task 2: {task2.task_id} ({task2.task_type})"
    )
    
    # Verify using bridge's resonance checker (should return False)
    assert not bridge.verify_resonance(result1, result2), "Bridge incorrectly detected resonance"
    
    print(f"✅ RESONANCE-02 PASSED: Hash1 = {result1.hash[:16]}... != Hash2 = {result2.hash[:16]}...")


@pytest.mark.asyncio
async def test_agent_clone_wiring():
    """
    RESONANCE-03: AgentClone can execute tasks via LLMBridge.
    
    Test Scenario:
    - Create AgentClone with injected LLMBridge
    - Execute task using execute_task_intelligent()
    - Verify result contains decision, hash, and reasoning
    """
    # Arrange: Create parent persona
    parent = GIDPersona(
        gid="GID-06",
        name="SAM",
        role="Security Auditor",
        skills=["Risk Assessment", "Compliance Validation"],
        scope="Transaction security and governance compliance"
    )
    
    # Create directive
    directive = PrimeDirective(
        mission="Audit high-value transactions",
        constraints=["READ_ONLY", "ESCALATE_IF_AMOUNT_EXCEEDS_100K"],
        success_criteria={"accuracy": 0.95},
        metadata={"pac_id": "PAC-DEV-P50"}
    )
    
    # Create clone
    clone = AgentClone(parent, clone_id=1, directive=directive)
    
    # Create reasoning engine
    bridge = LLMBridge(model_name="gpt-4", temperature=0.0)
    
    # Wire engine to clone
    clone.set_reasoning_engine(bridge)
    
    # Create test task
    task = Task(
        task_id="TASK-WIRING-001",
        task_type="GOVERNANCE_CHECK",
        payload={"transaction_id": "TXN-789", "amount_usd": 75000},
        priority=1
    )
    
    # Act: Execute task with reasoning
    result = await clone.execute_task_intelligent(task)
    
    # Assert: Result should contain LLM decision components
    assert "DECISION:" in result, "Result missing decision"
    assert "CONFIDENCE:" in result, "Result missing confidence"
    assert "HASH:" in result, "Result missing hash"
    assert "REASONING:" in result, "Result missing reasoning"
    
    # Verify task completion
    assert clone.tasks_completed == 1, "Task completion counter not incremented"
    assert clone.tasks_failed == 0, "Task should not have failed"
    
    print(f"✅ RESONANCE-03 PASSED: Clone {clone.gid} executed task via LLMBridge")
    print(f"   Result: {result[:150]}...")


# Run tests standalone
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
