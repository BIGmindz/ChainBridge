# core/risk/tri_glassbox_executor.py
"""
════════════════════════════════════════════════════════════════════════════════
TRI ⇄ Glass-Box Executor — Activation-Bound Risk Computation
════════════════════════════════════════════════════════════════════════════════

PAC ID: PAC-CODY-TRI-GLASSBOX-WIRING-IMPLEMENTATION-01
Author: CODY (GID-01) — Senior Backend Engineer
Version: 1.0.0

PURPOSE:
Implement TRI engine execution paths that consume the glass-box risk contract
and emit PDOs that are activation-bound, monotonic, and audit-grade.

WIRING CONTRACT:
1. TRI engine accepts TRIRiskInput (from integration spec)
2. Calls glass-box scoring function strictly via contract
3. Maps risk_score → RiskSeverityTier → TRIAction
4. Enforces monotonicity across repeated calls
5. Validates GlassBoxRiskOutput before return
6. Embeds required risk fields into PDO
7. Raises explicit IntegrationFailureMode on any violation

CONSTRAINTS (ABSOLUTE):
- Activation reference is MANDATORY — no fallback
- All failures are HARD FAIL
- No probabilistic logic
- No hidden defaults
- Monotonicity violations MUST raise
- Output MUST be PDO-embeddable

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from core.risk.tri_glassbox_integration import (
    ActivationReference,
    ConfidenceBand,
    FeatureContribution,
    GlassBoxRiskOutput,
    IntegrationFailure,
    IntegrationFailureMode,
    ModelIdentity,
    PDORiskEmbedding,
    RiskSeverityTier,
    TRIAction,
    TRIRiskInput,
    enforce_monotonicity,
    score_to_severity_tier,
    severity_tier_to_action,
    validate_pdo_risk_embedding,
)


# ============================================================================
# EXECUTOR FAILURE MODES — Extension of Integration Failures
# ============================================================================


class ExecutorFailureMode(str, Enum):
    """
    Executor-specific failure modes.
    
    These extend IntegrationFailureMode for execution-phase failures.
    """
    ACTIVATION_NOT_BOUND = "activation_not_bound"
    GLASS_BOX_EXECUTION_FAILED = "glass_box_execution_failed"
    OUTPUT_VALIDATION_FAILED = "output_validation_failed"
    PDO_EMBEDDING_FAILED = "pdo_embedding_failed"
    MONOTONICITY_CHECK_FAILED = "monotonicity_check_failed"
    PERSISTENCE_FAILED = "persistence_failed"


# ============================================================================
# EXECUTOR ERROR — HARD FAIL
# ============================================================================


class TRIExecutionError(Exception):
    """
    Raised when TRI execution fails.
    
    HARD FAIL — no recovery, no retry.
    """
    
    def __init__(
        self,
        message: str,
        failure_mode: ExecutorFailureMode | IntegrationFailureMode,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.failure_mode = failure_mode
        self.context = context or {}
        super().__init__(f"TRI EXECUTION FAILED [{failure_mode.value}]: {message}")


# ============================================================================
# EXECUTION RESULT — Full Provenance
# ============================================================================


@dataclass(frozen=True)
class TRIExecutionResult:
    """
    Complete execution result with full provenance chain.
    
    INVARIANTS:
    - activation_hash MUST be present
    - glass_box_output MUST be validated
    - pdo_embedding MUST be extractable
    - All timestamps MUST be UTC
    """
    execution_id: str
    request_id: str
    
    # Glass-box output (validated)
    glass_box_output: GlassBoxRiskOutput
    
    # PDO embedding (ready for persistence)
    pdo_embedding: PDORiskEmbedding
    
    # Provenance
    activation_hash: str
    execution_timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for audit trail."""
        return {
            "execution_id": self.execution_id,
            "request_id": self.request_id,
            "risk_score": self.glass_box_output.risk_score,
            "risk_tier": self.glass_box_output.risk_tier.value,
            "action": self.glass_box_output.action.value,
            "pdo_embedding": self.pdo_embedding.to_dict(),
            "activation_hash": self.activation_hash,
            "execution_timestamp": self.execution_timestamp.isoformat(),
        }


# ============================================================================
# MONOTONICITY TRACKER — Cross-Call Enforcement
# ============================================================================


@dataclass
class MonotonicityState:
    """
    Tracks monotonicity state across repeated calls.
    
    INVARIANT: Higher scores MUST NOT produce lower severity actions.
    """
    last_score: Optional[float] = None
    last_action: Optional[TRIAction] = None
    last_request_id: Optional[str] = None
    
    def check_and_update(
        self,
        score: float,
        action: TRIAction,
        request_id: str,
    ) -> Tuple[bool, Optional[IntegrationFailure]]:
        """
        Check monotonicity against previous call and update state.
        
        Returns:
            (True, None) if monotonicity holds
            (False, IntegrationFailure) if violated
        """
        if self.last_score is not None and self.last_action is not None:
            is_monotonic, failure = enforce_monotonicity(
                self.last_score,
                self.last_action,
                score,
                action,
            )
            if not is_monotonic:
                return (False, failure)
        
        # Update state
        self.last_score = score
        self.last_action = action
        self.last_request_id = request_id
        
        return (True, None)
    
    def reset(self) -> None:
        """Reset monotonicity state."""
        self.last_score = None
        self.last_action = None
        self.last_request_id = None


# ============================================================================
# GLASS-BOX SCORING INTERFACE — Contract-Bound
# ============================================================================


# Type alias for glass-box scoring function
GlassBoxScoringFn = Callable[
    [TRIRiskInput],
    Tuple[float, List[FeatureContribution], str],  # (score, contributors, explanation)
]


def default_glass_box_scoring(
    risk_input: TRIRiskInput,
) -> Tuple[float, List[FeatureContribution], str]:
    """
    Default glass-box scoring implementation.
    
    This is a placeholder that produces deterministic output.
    In production, this should be replaced by the actual ChainIQ scoring function.
    
    INVARIANT: Output is deterministic given input.
    """
    # Deterministic score based on entity_id hash
    import hashlib
    entity_hash = hashlib.sha256(risk_input.entity_id.encode()).hexdigest()
    score = (int(entity_hash[:8], 16) % 100) / 100.0
    
    # Build feature contributions
    contributors = [
        FeatureContribution(
            feature_id="entity_history",
            feature_value=score * 0.6,
            contribution=score * 0.6,
            contribution_direction="increasing",
            explanation=f"Entity history contributes {score * 0.6:.2f} to risk score",
        ),
        FeatureContribution(
            feature_id="temporal_pattern",
            feature_value=score * 0.4,
            contribution=score * 0.4,
            contribution_direction="increasing",
            explanation=f"Temporal pattern contributes {score * 0.4:.2f} to risk score",
        ),
    ]
    
    explanation = (
        f"Risk score of {score:.2f} computed from entity history and temporal patterns. "
        f"Entity {risk_input.entity_id} scored via deterministic glass-box model."
    )
    
    return (score, contributors, explanation)


# ============================================================================
# TRI GLASS-BOX EXECUTOR — Canonical Entry Point
# ============================================================================


class TRIGlassBoxExecutor:
    """
    TRI ⇄ Glass-Box executor with full contract enforcement.
    
    This is the CANONICAL entry point for all TRI risk computations.
    
    GUARANTEES:
    - Activation reference is validated FIRST
    - Glass-box output is validated before return
    - Monotonicity is enforced across calls
    - PDO embedding is extracted and validated
    - All failures are explicit and terminal
    """
    
    MODEL_ID = "glassbox-tri-v1"
    MODEL_VERSION = "1.0.0"
    
    def __init__(
        self,
        scoring_fn: Optional[GlassBoxScoringFn] = None,
        enforce_monotonicity: bool = True,
    ):
        """
        Initialize executor.
        
        Args:
            scoring_fn: Glass-box scoring function (defaults to placeholder)
            enforce_monotonicity: Whether to enforce cross-call monotonicity
        """
        self._scoring_fn = scoring_fn or default_glass_box_scoring
        self._enforce_monotonicity = enforce_monotonicity
        self._monotonicity_state = MonotonicityState()
    
    def execute(
        self,
        risk_input: TRIRiskInput,
    ) -> TRIExecutionResult:
        """
        Execute TRI risk computation with full contract enforcement.
        
        EXECUTION FLOW:
        1. Validate input (activation FIRST)
        2. Execute glass-box scoring
        3. Build GlassBoxRiskOutput
        4. Validate output
        5. Check monotonicity
        6. Extract PDO embedding
        7. Return execution result
        
        Args:
            risk_input: Validated TRIRiskInput
            
        Returns:
            TRIExecutionResult with full provenance
            
        Raises:
            TRIExecutionError: On any failure (HARD FAIL)
        """
        execution_id = str(uuid4())
        execution_timestamp = datetime.now(timezone.utc)
        
        # === STEP 1: VALIDATE INPUT (ACTIVATION FIRST) ===
        is_valid, failure = risk_input.validate()
        if not is_valid:
            raise TRIExecutionError(
                message=failure.message if failure else "Input validation failed",
                failure_mode=failure.mode if failure else ExecutorFailureMode.ACTIVATION_NOT_BOUND,
                context={"request_id": risk_input.request_id},
            )
        
        # === STEP 2: EXECUTE GLASS-BOX SCORING ===
        try:
            score, contributors, explanation = self._scoring_fn(risk_input)
        except Exception as e:
            raise TRIExecutionError(
                message=f"Glass-box scoring failed: {type(e).__name__}: {e}",
                failure_mode=ExecutorFailureMode.GLASS_BOX_EXECUTION_FAILED,
                context={"request_id": risk_input.request_id},
            ) from e
        
        # === STEP 3: VALIDATE SCORE BOUNDS ===
        if not (0.0 <= score <= 1.0):
            raise TRIExecutionError(
                message=f"Invalid risk score: {score} (must be in [0.0, 1.0])",
                failure_mode=IntegrationFailureMode.INVALID_RISK_SCORE,
                context={"request_id": risk_input.request_id, "score": score},
            )
        
        # === STEP 4: MAP SCORE TO TIER AND ACTION ===
        tier = score_to_severity_tier(score)
        action = severity_tier_to_action(tier)
        
        # === STEP 5: BUILD CONFIDENCE BAND ===
        # Confidence band width based on contributor count
        contributor_count = len(contributors)
        base_width = 0.05 if contributor_count >= 3 else 0.10
        confidence_band = ConfidenceBand(
            lower=max(0.0, score - base_width),
            point_estimate=score,
            upper=min(1.0, score + base_width),
            confidence_level=0.95,
        )
        
        # === STEP 6: BUILD MODEL IDENTITY ===
        model_identity = ModelIdentity(
            model_id=self.MODEL_ID,
            model_version=self.MODEL_VERSION,
            calibration_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            feature_count=contributor_count,
        )
        
        # === STEP 7: BUILD GLASS-BOX OUTPUT ===
        glass_box_output = GlassBoxRiskOutput(
            risk_score=score,
            risk_tier=tier,
            action=action,
            confidence_band=confidence_band,
            top_contributors=tuple(contributors),
            explanation_summary=explanation,
            model_identity=model_identity,
            request_id=risk_input.request_id,
            computation_timestamp=execution_timestamp,
            activation_hash=risk_input.activation_reference.activation_hash,
        )
        
        # === STEP 8: VALIDATE OUTPUT ===
        is_valid, failure = glass_box_output.validate()
        if not is_valid:
            raise TRIExecutionError(
                message=failure.message if failure else "Output validation failed",
                failure_mode=failure.mode if failure else ExecutorFailureMode.OUTPUT_VALIDATION_FAILED,
                context={"request_id": risk_input.request_id},
            )
        
        # === STEP 9: CHECK MONOTONICITY ===
        if self._enforce_monotonicity:
            is_monotonic, failure = self._monotonicity_state.check_and_update(
                score=score,
                action=action,
                request_id=risk_input.request_id,
            )
            if not is_monotonic:
                raise TRIExecutionError(
                    message=failure.message if failure else "Monotonicity violation",
                    failure_mode=ExecutorFailureMode.MONOTONICITY_CHECK_FAILED,
                    context={
                        "request_id": risk_input.request_id,
                        "current_score": score,
                        "current_action": action.value,
                        "previous_score": self._monotonicity_state.last_score,
                        "previous_action": self._monotonicity_state.last_action.value if self._monotonicity_state.last_action else None,
                    },
                )
        
        # === STEP 10: EXTRACT PDO EMBEDDING ===
        pdo_embedding = PDORiskEmbedding.from_glass_box_output(glass_box_output)
        
        # === STEP 11: VALIDATE PDO EMBEDDING ===
        is_valid, failure = validate_pdo_risk_embedding(pdo_embedding.to_dict())
        if not is_valid:
            raise TRIExecutionError(
                message=failure.message if failure else "PDO embedding validation failed",
                failure_mode=ExecutorFailureMode.PDO_EMBEDDING_FAILED,
                context={"request_id": risk_input.request_id},
            )
        
        # === STEP 12: BUILD AND RETURN RESULT ===
        return TRIExecutionResult(
            execution_id=execution_id,
            request_id=risk_input.request_id,
            glass_box_output=glass_box_output,
            pdo_embedding=pdo_embedding,
            activation_hash=risk_input.activation_reference.activation_hash,
            execution_timestamp=execution_timestamp,
        )
    
    def reset_monotonicity_state(self) -> None:
        """Reset monotonicity tracking state."""
        self._monotonicity_state.reset()


# ============================================================================
# FACTORY FUNCTIONS — Convenience Constructors
# ============================================================================


def create_activation_reference(
    agent_gid: str,
    activation_hash: str,
    scope_constraints: Optional[Tuple[str, ...]] = None,
) -> ActivationReference:
    """
    Create an ActivationReference with validation.
    
    Args:
        agent_gid: Agent GID (e.g., "GID-10")
        activation_hash: Hash of activation block
        scope_constraints: Permitted operation scopes
        
    Returns:
        Validated ActivationReference
        
    Raises:
        ValueError: If required fields are missing
    """
    if not agent_gid:
        raise ValueError("agent_gid is required")
    if not activation_hash:
        raise ValueError("activation_hash is required")
    
    return ActivationReference(
        agent_gid=agent_gid,
        activation_hash=activation_hash,
        activation_timestamp=datetime.now(timezone.utc),
        scope_constraints=scope_constraints or (),
    )


def create_tri_risk_input(
    entity_id: str,
    activation_reference: ActivationReference,
    event_window_hours: float = 24.0,
    domain_focus: Optional[str] = None,
) -> TRIRiskInput:
    """
    Create a TRIRiskInput with validation.
    
    Args:
        entity_id: Entity being scored
        activation_reference: Agent activation context
        event_window_hours: Analysis window size in hours
        domain_focus: Optional domain to emphasize
        
    Returns:
        Validated TRIRiskInput
        
    Raises:
        ValueError: If required fields are missing
    """
    if not entity_id:
        raise ValueError("entity_id is required")
    if activation_reference is None:
        raise ValueError("activation_reference is required")
    
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    
    return TRIRiskInput(
        activation_reference=activation_reference,
        event_window_start=now - timedelta(hours=event_window_hours),
        event_window_end=now,
        entity_id=entity_id,
        request_id=str(uuid4()),
        domain_focus=domain_focus,
    )


# ============================================================================
# EXPORTS
# ============================================================================


__all__ = [
    # Failure modes
    "ExecutorFailureMode",
    # Errors
    "TRIExecutionError",
    # Result types
    "TRIExecutionResult",
    "MonotonicityState",
    # Executor
    "TRIGlassBoxExecutor",
    "GlassBoxScoringFn",
    # Factory functions
    "create_activation_reference",
    "create_tri_risk_input",
    # Re-exports from integration contract
    "ActivationReference",
    "TRIRiskInput",
    "GlassBoxRiskOutput",
    "PDORiskEmbedding",
    "RiskSeverityTier",
    "TRIAction",
    "IntegrationFailureMode",
]
