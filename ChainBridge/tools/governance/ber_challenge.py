"""
BER Cognitive Friction Challenge-Response Module

PAC Reference: PAC-BENSON-P68-BER-COGNITIVE-FRICTION-CHALLENGE-RESPONSE-01
Authority: BENSON (GID-00)
Purpose: Implement challenge-response mechanism for BER approval
         to enforce cognitive engagement and prevent rubber-stamp approvals.

Invariants:
- CHALLENGE_MUST_BE_CONTENT_DERIVED
- CHALLENGE_MUST_BE_RANDOMIZED_PER_BER
- TIME_TO_ANSWER_MUST_BE_RECORDED
- CORRECT_ANSWER_HASH_BOUND_TO_BER
- FAIL_CLOSED_ON_MISMATCH_OR_TIMEOUT
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import hashlib
import secrets
import re


# =============================================================================
# ERROR CODES
# =============================================================================

class BERChallengeErrorCode(str, Enum):
    """Error codes for BER challenge-response system."""
    
    # Challenge generation errors (GS_300-309)
    GS_300 = "GS_300"  # CHALLENGE_GENERATION_FAILED
    GS_301 = "GS_301"  # BER_DATA_INSUFFICIENT
    GS_302 = "GS_302"  # CHALLENGE_TYPE_INVALID
    GS_303 = "GS_303"  # NONCE_GENERATION_FAILED
    
    # Response validation errors (GS_310-319)
    GS_310 = "GS_310"  # RESPONSE_INCORRECT
    GS_311 = "GS_311"  # RESPONSE_TIMEOUT
    GS_312 = "GS_312"  # RESPONSE_REPLAY_DETECTED
    GS_313 = "GS_313"  # RESPONSE_FORMAT_INVALID
    GS_314 = "GS_314"  # CHALLENGE_EXPIRED
    GS_315 = "GS_315"  # MINIMUM_LATENCY_NOT_MET
    
    # Proof binding errors (GS_320-329)
    GS_320 = "GS_320"  # PROOF_BINDING_FAILED
    GS_321 = "GS_321"  # PROOF_HASH_MISMATCH
    GS_322 = "GS_322"  # PROOF_TAMPERED
    
    # Approval errors (GS_330-339)
    GS_330 = "GS_330"  # APPROVAL_WITHOUT_CHALLENGE
    GS_331 = "GS_331"  # APPROVAL_CHALLENGE_INCOMPLETE
    GS_332 = "GS_332"  # APPROVAL_UNAUTHORIZED


# =============================================================================
# CHALLENGE TYPES
# =============================================================================

class ChallengeType(str, Enum):
    """Types of cognitive friction challenges."""
    
    # Task completion verification
    TASK_COUNT = "TASK_COUNT"           # "How many tasks were completed?"
    TASK_RECALL = "TASK_RECALL"         # "Which task involved [X]?"
    
    # Artifact verification
    FILE_COUNT = "FILE_COUNT"           # "How many files were created?"
    FILE_RECALL = "FILE_RECALL"         # "Which file contains [X]?"
    
    # Quality verification
    QUALITY_SCORE = "QUALITY_SCORE"     # "What was the quality score?"
    SCOPE_COMPLIANCE = "SCOPE_COMPLIANCE"  # "Was scope compliance achieved?"
    
    # Agent verification
    AGENT_IDENTITY = "AGENT_IDENTITY"   # "Which agent executed this?"
    AGENT_GID = "AGENT_GID"             # "What is the agent's GID?"
    
    # Content hash verification
    CONTENT_HASH_PREFIX = "CONTENT_HASH_PREFIX"  # "First 4 chars of hash?"


# =============================================================================
# SCHEMA DEFINITIONS
# =============================================================================

@dataclass
class BERChallenge:
    """
    A cognitive friction challenge derived from BER content.
    
    Challenges are randomized per-BER and require content-derived answers.
    """
    
    challenge_id: str
    ber_id: str
    challenge_type: ChallengeType
    question: str
    correct_answer: str  # Hashed for storage
    correct_answer_hash: str
    nonce: str  # Per-challenge randomness
    created_at: str
    expires_at: str
    
    # Anti-replay
    used: bool = False
    
    def __post_init__(self):
        """Validate challenge on creation."""
        if not self.nonce or len(self.nonce) < 32:
            raise ValueError(f"Invalid nonce: {BERChallengeErrorCode.GS_303}")
        if not self.ber_id:
            raise ValueError(f"BER ID required: {BERChallengeErrorCode.GS_301}")


@dataclass
class ChallengeResponse:
    """
    A response to a BER challenge.
    
    Includes timing information for latency enforcement.
    """
    
    challenge_id: str
    response: str
    response_hash: str
    submitted_at: str
    latency_ms: int
    
    def __post_init__(self):
        """Validate response on creation."""
        if self.latency_ms < 0:
            raise ValueError("Latency cannot be negative")


@dataclass
class BERChallengeProof:
    """
    Proof of cognitive engagement bound to BER.
    
    This artifact proves the reviewer demonstrated understanding
    of the BER content before approval was granted.
    """
    
    proof_id: str
    ber_id: str
    challenge_id: str
    challenge_type: ChallengeType
    question_hash: str
    response_hash: str
    latency_ms: int
    minimum_latency_met: bool
    response_correct: bool
    
    # Verification
    proof_hash: str = ""
    generated_at: str = ""
    verified_by: str = "BENSON (GID-00)"
    
    def __post_init__(self):
        """Generate proof hash after creation."""
        if not self.proof_hash:
            self.generated_at = datetime.now(timezone.utc).isoformat()
            self._compute_proof_hash()
    
    def _compute_proof_hash(self):
        """Compute tamper-evident hash of proof."""
        proof_data = (
            f"{self.proof_id}:{self.ber_id}:{self.challenge_id}:"
            f"{self.challenge_type}:{self.question_hash}:{self.response_hash}:"
            f"{self.latency_ms}:{self.minimum_latency_met}:{self.response_correct}:"
            f"{self.generated_at}"
        )
        self.proof_hash = hashlib.sha256(proof_data.encode()).hexdigest()
    
    def verify(self) -> bool:
        """Verify proof has not been tampered with."""
        expected_data = (
            f"{self.proof_id}:{self.ber_id}:{self.challenge_id}:"
            f"{self.challenge_type}:{self.question_hash}:{self.response_hash}:"
            f"{self.latency_ms}:{self.minimum_latency_met}:{self.response_correct}:"
            f"{self.generated_at}"
        )
        expected_hash = hashlib.sha256(expected_data.encode()).hexdigest()
        return expected_hash == self.proof_hash
    
    def is_valid_approval(self) -> bool:
        """Check if proof represents valid approval conditions."""
        return (
            self.response_correct and
            self.minimum_latency_met and
            self.verify()
        )


@dataclass
class BERApprovalResult:
    """Result of BER approval attempt with challenge verification."""
    
    ber_id: str
    approved: bool
    proof: Optional[BERChallengeProof]
    error_code: Optional[BERChallengeErrorCode]
    error_message: Optional[str]
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


# =============================================================================
# CHALLENGE GENERATOR
# =============================================================================

# Minimum review latency per GP-006 (5000ms)
MINIMUM_REVIEW_LATENCY_MS = 5000

# Challenge expiry time (5 minutes)
CHALLENGE_EXPIRY_SECONDS = 300


def _generate_nonce() -> str:
    """Generate cryptographically secure nonce."""
    return secrets.token_hex(32)


def _hash_answer(answer: str, nonce: str) -> str:
    """Hash answer with nonce for secure storage."""
    return hashlib.sha256(f"{answer}:{nonce}".encode()).hexdigest()


def _extract_task_count(ber_data: dict[str, Any]) -> Optional[int]:
    """Extract task count from BER data."""
    # Try various paths where task count might be stored
    if 'tasks_completed' in ber_data:
        tasks = ber_data['tasks_completed']
        return len(tasks) if isinstance(tasks, list) else tasks
    if 'task_analysis' in ber_data:
        return ber_data['task_analysis'].get('total_tasks', 0)
    if 'execution_summary' in ber_data:
        return ber_data['execution_summary'].get('tasks_completed', 0)
    return None


def _extract_file_count(ber_data: dict[str, Any]) -> Optional[int]:
    """Extract file count from BER data."""
    if 'files_created' in ber_data:
        files = ber_data['files_created']
        return len(files) if isinstance(files, list) else files
    if 'structural_validation' in ber_data:
        # Count blocks present
        return sum(1 for k, v in ber_data['structural_validation'].items() 
                   if v == 'PRESENT')
    return None


def _extract_quality_score(ber_data: dict[str, Any]) -> Optional[float]:
    """Extract quality score from BER data."""
    if 'quality_score' in ber_data:
        return ber_data['quality_score']
    if 'quality_assessment' in ber_data:
        return ber_data['quality_assessment'].get('structural_quality', 0.0)
    if 'execution_summary' in ber_data:
        return ber_data['execution_summary'].get('quality_score', 0.0)
    return None


def _extract_agent_name(ber_data: dict[str, Any]) -> Optional[str]:
    """Extract agent name from BER data."""
    if 'agent' in ber_data:
        return ber_data['agent']
    if 'agent_name' in ber_data:
        return ber_data['agent_name']
    return None


def _extract_agent_gid(ber_data: dict[str, Any]) -> Optional[str]:
    """Extract agent GID from BER data."""
    if 'gid' in ber_data:
        return ber_data['gid']
    if 'agent_gid' in ber_data:
        return ber_data['agent_gid']
    return None


def generate_ber_challenge(
    ber_id: str,
    ber_data: dict[str, Any],
    challenge_type: Optional[ChallengeType] = None
) -> BERChallenge:
    """
    Generate a content-derived challenge for BER review.
    
    Args:
        ber_id: The BER identifier
        ber_data: The BER content data
        challenge_type: Optional specific challenge type (random if not specified)
    
    Returns:
        BERChallenge ready for presentation
    
    Raises:
        ValueError: If challenge cannot be generated from BER data
    """
    
    if not ber_data:
        raise ValueError(f"BER data required: {BERChallengeErrorCode.GS_301}")
    
    # Generate nonce for this challenge
    nonce = _generate_nonce()
    
    # Select challenge type (random if not specified)
    if challenge_type is None:
        available_types = []
        
        if _extract_task_count(ber_data) is not None:
            available_types.append(ChallengeType.TASK_COUNT)
        if _extract_file_count(ber_data) is not None:
            available_types.append(ChallengeType.FILE_COUNT)
        if _extract_quality_score(ber_data) is not None:
            available_types.append(ChallengeType.QUALITY_SCORE)
        if _extract_agent_name(ber_data) is not None:
            available_types.append(ChallengeType.AGENT_IDENTITY)
        if _extract_agent_gid(ber_data) is not None:
            available_types.append(ChallengeType.AGENT_GID)
        
        if not available_types:
            raise ValueError(f"Cannot generate challenge: {BERChallengeErrorCode.GS_301}")
        
        # Secure random selection
        challenge_type = secrets.choice(available_types)
    
    # Generate question and answer based on type
    question = ""
    correct_answer = ""
    
    if challenge_type == ChallengeType.TASK_COUNT:
        count = _extract_task_count(ber_data)
        if count is None:
            raise ValueError(f"Task count not available: {BERChallengeErrorCode.GS_301}")
        question = "How many tasks were completed in this execution?"
        correct_answer = str(count)
        
    elif challenge_type == ChallengeType.FILE_COUNT:
        count = _extract_file_count(ber_data)
        if count is None:
            raise ValueError(f"File count not available: {BERChallengeErrorCode.GS_301}")
        question = "How many files were created in this execution?"
        correct_answer = str(count)
        
    elif challenge_type == ChallengeType.QUALITY_SCORE:
        score = _extract_quality_score(ber_data)
        if score is None:
            raise ValueError(f"Quality score not available: {BERChallengeErrorCode.GS_301}")
        question = "What was the quality score? (Enter as decimal, e.g., 1.0)"
        correct_answer = str(score)
        
    elif challenge_type == ChallengeType.AGENT_IDENTITY:
        name = _extract_agent_name(ber_data)
        if name is None:
            raise ValueError(f"Agent name not available: {BERChallengeErrorCode.GS_301}")
        question = "Which agent executed this PAC?"
        correct_answer = name.upper()
        
    elif challenge_type == ChallengeType.AGENT_GID:
        gid = _extract_agent_gid(ber_data)
        if gid is None:
            raise ValueError(f"Agent GID not available: {BERChallengeErrorCode.GS_301}")
        question = "What is the executing agent's GID?"
        correct_answer = gid.upper()
        
    else:
        raise ValueError(f"Unsupported challenge type: {BERChallengeErrorCode.GS_302}")
    
    # Create timestamps
    now = datetime.now(timezone.utc)
    expires = datetime.fromtimestamp(
        now.timestamp() + CHALLENGE_EXPIRY_SECONDS,
        tz=timezone.utc
    )
    
    # Hash the answer
    answer_hash = _hash_answer(correct_answer, nonce)
    
    # Generate challenge ID
    challenge_id = f"CHAL-{ber_id}-{secrets.token_hex(8)}"
    
    return BERChallenge(
        challenge_id=challenge_id,
        ber_id=ber_id,
        challenge_type=challenge_type,
        question=question,
        correct_answer=correct_answer,  # Store for validation
        correct_answer_hash=answer_hash,
        nonce=nonce,
        created_at=now.isoformat(),
        expires_at=expires.isoformat(),
        used=False
    )


# =============================================================================
# RESPONSE VALIDATOR
# =============================================================================

def validate_challenge_response(
    challenge: BERChallenge,
    response: str,
    response_timestamp: Optional[datetime] = None
) -> tuple[ChallengeResponse, bool, Optional[BERChallengeErrorCode]]:
    """
    Validate a response to a BER challenge.
    
    Args:
        challenge: The challenge being responded to
        response: The user's response
        response_timestamp: When response was submitted (defaults to now)
    
    Returns:
        Tuple of (ChallengeResponse, is_correct, error_code)
    """
    
    if response_timestamp is None:
        response_timestamp = datetime.now(timezone.utc)
    
    # Check for replay
    if challenge.used:
        return (
            ChallengeResponse(
                challenge_id=challenge.challenge_id,
                response=response,
                response_hash=hashlib.sha256(response.encode()).hexdigest(),
                submitted_at=response_timestamp.isoformat(),
                latency_ms=0
            ),
            False,
            BERChallengeErrorCode.GS_312
        )
    
    # Check expiry
    expires_at = datetime.fromisoformat(challenge.expires_at)
    if response_timestamp > expires_at:
        return (
            ChallengeResponse(
                challenge_id=challenge.challenge_id,
                response=response,
                response_hash=hashlib.sha256(response.encode()).hexdigest(),
                submitted_at=response_timestamp.isoformat(),
                latency_ms=0
            ),
            False,
            BERChallengeErrorCode.GS_314
        )
    
    # Calculate latency
    created_at = datetime.fromisoformat(challenge.created_at)
    latency_ms = int((response_timestamp - created_at).total_seconds() * 1000)
    
    # Create response object
    response_hash = hashlib.sha256(response.encode()).hexdigest()
    challenge_response = ChallengeResponse(
        challenge_id=challenge.challenge_id,
        response=response,
        response_hash=response_hash,
        submitted_at=response_timestamp.isoformat(),
        latency_ms=latency_ms
    )
    
    # Normalize response for comparison
    normalized_response = response.strip().upper()
    normalized_correct = challenge.correct_answer.strip().upper()
    
    # Check correctness
    is_correct = normalized_response == normalized_correct
    
    if not is_correct:
        return (challenge_response, False, BERChallengeErrorCode.GS_310)
    
    # Mark challenge as used (anti-replay)
    challenge.used = True
    
    return (challenge_response, True, None)


# =============================================================================
# PROOF BINDING
# =============================================================================

def create_challenge_proof(
    challenge: BERChallenge,
    response: ChallengeResponse,
    is_correct: bool
) -> BERChallengeProof:
    """
    Create a proof artifact binding the challenge-response to BER.
    
    Args:
        challenge: The challenge that was presented
        response: The response that was submitted
        is_correct: Whether the response was correct
    
    Returns:
        BERChallengeProof bound to the BER
    """
    
    minimum_latency_met = response.latency_ms >= MINIMUM_REVIEW_LATENCY_MS
    
    proof_id = f"PROOF-{challenge.ber_id}-{secrets.token_hex(8)}"
    
    return BERChallengeProof(
        proof_id=proof_id,
        ber_id=challenge.ber_id,
        challenge_id=challenge.challenge_id,
        challenge_type=challenge.challenge_type,
        question_hash=hashlib.sha256(challenge.question.encode()).hexdigest(),
        response_hash=response.response_hash,
        latency_ms=response.latency_ms,
        minimum_latency_met=minimum_latency_met,
        response_correct=is_correct,
        verified_by="BENSON (GID-00)"
    )


# =============================================================================
# BER APPROVAL WITH CHALLENGE
# =============================================================================

def approve_ber_with_challenge(
    ber_id: str,
    ber_data: dict[str, Any],
    response: str,
    challenge: Optional[BERChallenge] = None,
    response_timestamp: Optional[datetime] = None
) -> BERApprovalResult:
    """
    Attempt to approve a BER with cognitive friction challenge.
    
    This is the main entry point for BER approval with challenge-response.
    FAIL_CLOSED: Any error results in rejection.
    
    Args:
        ber_id: The BER to approve
        ber_data: The BER content data
        response: The challenge response
        challenge: Optional pre-generated challenge (generates new if not provided)
        response_timestamp: When response was submitted
    
    Returns:
        BERApprovalResult with proof if approved, error if rejected
    """
    
    try:
        # Generate challenge if not provided
        if challenge is None:
            challenge = generate_ber_challenge(ber_id, ber_data)
        
        # Validate response
        challenge_response, is_correct, error_code = validate_challenge_response(
            challenge, response, response_timestamp
        )
        
        if error_code:
            return BERApprovalResult(
                ber_id=ber_id,
                approved=False,
                proof=None,
                error_code=error_code,
                error_message=f"Challenge validation failed: {error_code.value}"
            )
        
        # Create proof
        proof = create_challenge_proof(challenge, challenge_response, is_correct)
        
        # Check minimum latency
        if not proof.minimum_latency_met:
            return BERApprovalResult(
                ber_id=ber_id,
                approved=False,
                proof=proof,
                error_code=BERChallengeErrorCode.GS_315,
                error_message=f"Minimum latency not met: {proof.latency_ms}ms < {MINIMUM_REVIEW_LATENCY_MS}ms"
            )
        
        # Check correctness
        if not proof.response_correct:
            return BERApprovalResult(
                ber_id=ber_id,
                approved=False,
                proof=proof,
                error_code=BERChallengeErrorCode.GS_310,
                error_message="Incorrect response"
            )
        
        # All checks passed
        return BERApprovalResult(
            ber_id=ber_id,
            approved=True,
            proof=proof,
            error_code=None,
            error_message=None
        )
        
    except ValueError as e:
        return BERApprovalResult(
            ber_id=ber_id,
            approved=False,
            proof=None,
            error_code=BERChallengeErrorCode.GS_300,
            error_message=str(e)
        )
    except Exception as e:
        # FAIL_CLOSED: Any unexpected error results in rejection
        return BERApprovalResult(
            ber_id=ber_id,
            approved=False,
            proof=None,
            error_code=BERChallengeErrorCode.GS_300,
            error_message=f"Unexpected error: {e}"
        )


# =============================================================================
# PROOF VERIFICATION
# =============================================================================

def verify_approval_proof(proof: BERChallengeProof) -> tuple[bool, Optional[BERChallengeErrorCode]]:
    """
    Verify a BER approval proof post-facto.
    
    Args:
        proof: The proof to verify
    
    Returns:
        Tuple of (is_valid, error_code)
    """
    
    # Check proof integrity
    if not proof.verify():
        return (False, BERChallengeErrorCode.GS_322)
    
    # Check approval conditions
    if not proof.response_correct:
        return (False, BERChallengeErrorCode.GS_310)
    
    if not proof.minimum_latency_met:
        return (False, BERChallengeErrorCode.GS_315)
    
    return (True, None)


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Error codes
    'BERChallengeErrorCode',
    
    # Types
    'ChallengeType',
    
    # Schemas
    'BERChallenge',
    'ChallengeResponse',
    'BERChallengeProof',
    'BERApprovalResult',
    
    # Functions
    'generate_ber_challenge',
    'validate_challenge_response',
    'create_challenge_proof',
    'approve_ber_with_challenge',
    'verify_approval_proof',
    
    # Constants
    'MINIMUM_REVIEW_LATENCY_MS',
    'CHALLENGE_EXPIRY_SECONDS',
]
