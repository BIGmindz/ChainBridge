"""
ChainBridge LLM Bridge - The Voice Box
========================================
Cryptographically deterministic reasoning engine for AgentClone instances.

Created: PAC-DEV-P50 (Cortex Resonance)
Updated: PAC-CRYPTO-P60 (Quantum Shield - Dilithium Signatures)
Purpose: Enable agents to "think" via LLM calls while enforcing SHA3-256 hash consistency
         with post-quantum signature attestation

Invariants:
- RESONANCE-01: Identical inputs MUST produce identical hashes
- RESONANCE-02: Different inputs MUST produce different hashes
- RESONANCE-03: Reasoning process MUST be auditable (chain-of-thought logging)
- PQC-01: All Resonance Hashes MUST be signed by Dilithium (PAC-P60)
"""

import asyncio
import hashlib
import json
import logging
from typing import Protocol, Optional, Dict, Any
from datetime import datetime

from core.swarm.types import Task, ReasoningResult, PrimeDirective
from core.crypto.quantum_signer import get_global_signer


class ReasoningEngine(Protocol):
    """Protocol for LLM-based decision engines."""
    
    async def reason(self, task: Task, context: Optional[Dict[str, Any]] = None) -> ReasoningResult:
        """
        Process a task through LLM reasoning.
        
        Args:
            task: Work unit to analyze
            context: Additional metadata (agent GID, directive, etc.)
            
        Returns:
            ReasoningResult with decision, reasoning, confidence, and hash
        """
        ...


class LLMBridge:
    """
    The Polyatomic Brain's Voice Box.
    
    Responsibilities:
    1. Accept Task objects from AgentClone
    2. Construct deterministic prompts from PrimeDirective + Task
    3. Call LLM API (OpenAI, Anthropic, or local model)
    4. Hash the LLM response for resonance verification
    5. Return ReasoningResult with cryptographic proof
    
    Design Philosophy:
    - "If 5 agents think the same thought, they produce the same hash"
    - "Dissonance is mathematically detectable"
    - "Every thought is auditable"
    """
    
    def __init__(
        self,
        model_name: str = "gpt-4",
        temperature: float = 0.0,  # Determinism: temperature=0
        max_tokens: int = 500,
        api_key: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize LLM Bridge.
        
        Args:
            model_name: LLM model identifier (e.g., "gpt-4", "claude-3-opus")
            temperature: Randomness control (0.0 = deterministic)
            max_tokens: Max response length
            api_key: LLM provider API key (or read from env)
            logger: Logging instance
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key or self._get_api_key()
        self.logger = logger or logging.getLogger("LLMBridge")
        
        # PAC-P60: Initialize Quantum Signer for hash attestation
        self.quantum_signer = get_global_signer()
        self.logger.info("✅ Quantum Shield active - all hashes will be signed with Dilithium")
        
        # Invariant enforcement
        if temperature != 0.0:
            self.logger.warning(
                f"NON-DETERMINISTIC TEMPERATURE: {temperature}. "
                f"Resonance verification may fail. Recommended: temperature=0.0"
            )
    
    def _get_api_key(self) -> Optional[str]:
        """Retrieve API key from environment."""
        import os
        return os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    
    def _build_prompt(self, task: Task, directive: Optional[PrimeDirective] = None) -> str:
        """
        Construct deterministic prompt from task + directive.
        
        Args:
            task: Work unit
            directive: Constitutional instructions
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        # Constitutional preamble
        if directive:
            prompt_parts.append(f"# PRIME DIRECTIVE\n{directive.mission}\n")
            if directive.constraints:
                prompt_parts.append(f"## Constraints:\n" + "\n".join(f"- {c}" for c in directive.constraints))
            if directive.success_criteria:
                prompt_parts.append(f"## Success Criteria:\n{json.dumps(directive.success_criteria, indent=2)}")
        
        # Task details
        prompt_parts.append(f"\n# TASK: {task.task_type}\n")
        prompt_parts.append(f"**Task ID**: {task.task_id}\n")
        prompt_parts.append(f"**Payload**:\n```json\n{json.dumps(task.payload, indent=2)}\n```\n")
        
        # Decision framework
        prompt_parts.append("\n# INSTRUCTIONS\n")
        prompt_parts.append("1. Analyze the task payload against the Prime Directive")
        prompt_parts.append("2. Reason step-by-step (chain-of-thought)")
        prompt_parts.append("3. Provide a final decision: APPROVE, REJECT, or ESCALATE")
        prompt_parts.append("4. Assign confidence score (0.0-1.0)")
        prompt_parts.append("\n**Output Format (JSON)**:")
        prompt_parts.append("```json")
        prompt_parts.append('{"decision": "APPROVE|REJECT|ESCALATE", "reasoning": "...", "confidence": 0.95}')
        prompt_parts.append("```")
        
        return "\n".join(prompt_parts)
    
    def _compute_hash(self, decision: str, reasoning: str) -> str:
        """
        Compute SHA3-256 hash of decision + reasoning.
        
        Args:
            decision: Final recommendation
            reasoning: Chain-of-thought explanation
            
        Returns:
            64-character hex hash
        """
        content = f"{decision}|{reasoning}"
        return hashlib.sha3_256(content.encode('utf-8')).hexdigest()
    
    def _sign_hash(self, hash_hex: str) -> bytes:
        """
        Sign resonance hash with post-quantum Dilithium signature.
        
        PAC-P60 (Invariant PQC-01 enforcement).
        
        Args:
            hash_hex: SHA3-256 hash as hex string
            
        Returns:
            Dilithium quantum-resistant signature
        """
        hash_bytes = bytes.fromhex(hash_hex)
        signature = self.quantum_signer.sign(hash_bytes)
        self.logger.debug(f"Signed hash {hash_hex[:16]}... with Dilithium ({len(signature)} bytes)")
        return signature
    
    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """
        Make actual LLM API call (mocked for now).
        
        Args:
            prompt: Formatted input
            
        Returns:
            Parsed LLM response as dict
        """
        # PRODUCTION: Replace with real OpenAI/Anthropic call
        # For now, simulate deterministic response
        self.logger.info(f"[MOCK] Calling LLM with prompt length: {len(prompt)} chars")
        
        # Deterministic mock response based on prompt hash
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:8]
        
        # Simulate async delay
        await asyncio.sleep(0.01)
        
        return {
            "decision": "APPROVE",
            "reasoning": f"Mock reasoning for prompt hash {prompt_hash}. "
                        f"In production, this would be the LLM's chain-of-thought analysis.",
            "confidence": 0.95
        }
    
    async def reason(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None
    ) -> ReasoningResult:
        """
        Process task through LLM reasoning pipeline.
        
        Args:
            task: Work unit to analyze
            context: Additional metadata (directive, agent GID, etc.)
            
        Returns:
            ReasoningResult with cryptographic hash
        """
        start_time = datetime.now()
        directive = context.get("directive") if context else None
        
        # Step 1: Build prompt
        prompt = self._build_prompt(task, directive)
        self.logger.debug(f"Prompt:\n{prompt}")
        
        # Step 2: Call LLM
        try:
            llm_response = await self._call_llm(prompt)
        except Exception as e:
            self.logger.error(f"LLM API call failed: {e}")
            # Fallback to safe default
            llm_response = {
                "decision": "ESCALATE",
                "reasoning": f"LLM call failed: {str(e)}. Escalating for manual review.",
                "confidence": 0.0
            }
        
        # Step 3: Compute resonance hash
        decision = llm_response["decision"]
        reasoning = llm_response["reasoning"]
        resonance_hash = self._compute_hash(decision, reasoning)
        
        # Step 3.5: PAC-P60 - Sign hash with Dilithium (PQC-01 enforcement)
        quantum_signature = self._sign_hash(resonance_hash)
        
        # Step 4: Package result
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        result = ReasoningResult(
            decision=decision,
            reasoning=reasoning,
            confidence=llm_response["confidence"],
            hash=resonance_hash,
            metadata={
                "model": self.model_name,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "latency_ms": elapsed_ms,
                "task_id": task.task_id,
                "task_type": task.task_type,
                # PAC-P60: Quantum attestation
                "quantum_signature": quantum_signature.hex(),
                "quantum_signature_len": len(quantum_signature),
                "pqc_public_key": self.quantum_signer.public_key_hex
            }
        )
        
        self.logger.info(
            f"Reasoning complete: task={task.task_id}, "
            f"decision={decision}, hash={resonance_hash[:16]}..., "
            f"latency={elapsed_ms:.2f}ms"
        )
        
        return result
    
    def verify_resonance(self, result1: ReasoningResult, result2: ReasoningResult) -> bool:
        """
        Check if two reasoning results are cryptographically identical.
        
        Args:
            result1: First reasoning result
            result2: Second reasoning result
            
        Returns:
            True if hashes match (resonance), False otherwise (dissonance)
        """
        return result1.hash == result2.hash


# Example usage (for documentation)
if __name__ == "__main__":
    async def demo():
        """Demonstrate LLMBridge usage."""
        # Initialize bridge
        bridge = LLMBridge(model_name="gpt-4", temperature=0.0)
        
        # Create test task
        task = Task(
            task_id="TASK-DEMO-001",
            task_type="GOVERNANCE_CHECK",
            payload={"transaction_id": "TXN-123", "amount_usd": 50000}
        )
        
        # Create directive
        directive = PrimeDirective(
            mission="Validate transaction compliance",
            constraints=["READ_ONLY", "MAX_AMOUNT_100K"],
            success_criteria={"pass_rate": 0.95}
        )
        
        # Reason about task
        result = await bridge.reason(task, context={"directive": directive})
        
        print(f"Decision: {result.decision}")
        print(f"Reasoning: {result.reasoning}")
        print(f"Confidence: {result.confidence}")
        print(f"Hash: {result.hash}")
        
        # Test resonance (identical task should produce same hash)
        result2 = await bridge.reason(task, context={"directive": directive})
        print(f"\nResonance Test: {bridge.verify_resonance(result, result2)}")
    
    asyncio.run(demo())
