//! # Cognitive Friction Module (PAC-OCC-P21)
//!
//! This module implements Constitutional Cognitive Friction to protect operators
//! from "rubber-stamping" decisions during high-velocity events.
//!
//! ## Threat Model: The "Fast Click" Vulnerability
//!
//! In Swarm events (P17), a flood of requests could cause operators to auto-approve
//! without reading. Speed is interpreted as **NEGLIGENCE** by the Constitution.
//!
//! ## Design Principles
//!
//! 1. **Dwell Time**: Minimum review duration before approval is accepted
//! 2. **Challenge-Response**: Semantic challenges for critical gates
//! 3. **Tier-Based Friction**: LAW-tier requires maximum friction
//! 4. **No Shortcuts**: "Remember this choice" is FORBIDDEN for LAW-tier
//!
//! ## Integration with Sovereign Gate
//!
//! ```text
//! ┌─────────────────────────────────────────────────────────────┐
//! │                    SOVEREIGN GATE                           │
//! ├─────────────────────────────────────────────────────────────┤
//! │  Soul (P20)  │  Body (P16)  │  Mind (P21)                  │
//! │  ──────────  │  ──────────  │  ──────────                  │
//! │  Kernel      │  HAL/HSM     │  CognitiveGate               │
//! │  Validator   │  SecureMem   │  FrictionTimer               │
//! │  PDO         │  Attestation │  ChallengeResponse           │
//! └─────────────────────────────────────────────────────────────┘
//! ```
//!
//! ## Constitutional Invariants
//!
//! - **CF-001**: LAW-tier decisions require minimum 5 second dwell time
//! - **CF-002**: Challenge failures MUST reject the decision
//! - **CF-003**: No "Remember" shortcuts for LAW/POLICY tiers
//! - **CF-004**: UI cannot bypass Kernel friction timer
//! - **CF-005**: Velocity violations trigger automatic rejection

pub mod challenge;
pub mod decision;
pub mod timer;

use std::time::Duration;

pub use challenge::{Challenge, ChallengeResponse, ChallengeType, ChallengeVerifier};
pub use decision::{DecisionGate, DecisionOutcome, DecisionRequest, ReviewState};
pub use timer::{DwellRequirement, FrictionTimer, TimerState};

/// Governance tier determines friction intensity.
/// Higher tiers require more cognitive friction.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum FrictionTier {
    /// LAW-tier: Maximum friction, no shortcuts allowed
    /// Minimum dwell: 5 seconds, challenge required
    Law,

    /// POLICY-tier: High friction, limited shortcuts
    /// Minimum dwell: 3 seconds, challenge optional
    Policy,

    /// GUIDANCE-tier: Moderate friction
    /// Minimum dwell: 2 seconds, no challenge
    Guidance,

    /// OPERATIONAL-tier: Minimal friction
    /// Minimum dwell: 1 second, no challenge
    Operational,
}

impl FrictionTier {
    /// Minimum dwell time before approval is valid.
    ///
    /// # Constitutional Invariant CF-001
    /// LAW-tier MUST have minimum 5 second dwell time.
    pub const fn minimum_dwell(&self) -> Duration {
        match self {
            FrictionTier::Law => Duration::from_secs(5),
            FrictionTier::Policy => Duration::from_secs(3),
            FrictionTier::Guidance => Duration::from_secs(2),
            FrictionTier::Operational => Duration::from_secs(1),
        }
    }

    /// Whether a challenge is required for this tier.
    pub const fn requires_challenge(&self) -> bool {
        matches!(self, FrictionTier::Law)
    }

    /// Whether a challenge is recommended (but not required).
    pub const fn challenge_recommended(&self) -> bool {
        matches!(self, FrictionTier::Law | FrictionTier::Policy)
    }

    /// Whether "Remember this choice" shortcuts are allowed.
    ///
    /// # Constitutional Invariant CF-003
    /// LAW and POLICY tiers MUST NOT allow remember shortcuts.
    pub const fn allows_remember_shortcut(&self) -> bool {
        matches!(self, FrictionTier::Guidance | FrictionTier::Operational)
    }

    /// Convert from governance tier string.
    pub fn from_governance_tier(tier: &str) -> Self {
        match tier.to_uppercase().as_str() {
            "LAW" => FrictionTier::Law,
            "POLICY" => FrictionTier::Policy,
            "GUIDANCE" => FrictionTier::Guidance,
            "OPERATIONAL" => FrictionTier::Operational,
            _ => FrictionTier::Law, // Default to maximum friction for unknown
        }
    }
}

impl std::fmt::Display for FrictionTier {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            FrictionTier::Law => write!(f, "LAW"),
            FrictionTier::Policy => write!(f, "POLICY"),
            FrictionTier::Guidance => write!(f, "GUIDANCE"),
            FrictionTier::Operational => write!(f, "OPERATIONAL"),
        }
    }
}

/// Errors that can occur during cognitive friction enforcement.
#[derive(Debug, Clone, PartialEq)]
pub enum CognitiveFrictionError {
    /// Operator approved too quickly (dwell time violation).
    /// This is interpreted as negligence.
    DwellTimeViolation {
        /// Required minimum dwell time
        required: Duration,
        /// Actual time spent reviewing
        actual: Duration,
        /// The tier that was violated
        tier: FrictionTier,
    },

    /// Challenge response was incorrect.
    ChallengeFailure {
        /// The challenge that was failed
        challenge_id: String,
        /// Number of attempts made
        attempts: u32,
        /// Maximum attempts allowed
        max_attempts: u32,
    },

    /// Attempted to use "Remember" shortcut on forbidden tier.
    RememberShortcutForbidden {
        /// The tier that forbids shortcuts
        tier: FrictionTier,
    },

    /// Decision velocity exceeded safe threshold.
    VelocityViolation {
        /// Decisions per minute observed
        decisions_per_minute: f64,
        /// Maximum safe velocity
        max_safe_velocity: f64,
    },

    /// Attempted to bypass friction timer via UI.
    BypassAttemptDetected {
        /// Method used to attempt bypass
        method: String,
        /// Timestamp of attempt
        timestamp: u64,
    },

    /// Timer was not started before approval.
    TimerNotStarted,

    /// Challenge was required but not completed.
    ChallengeRequired {
        /// The tier requiring challenge
        tier: FrictionTier,
    },

    /// Internal error in cognitive friction system.
    InternalError(String),
}

impl std::fmt::Display for CognitiveFrictionError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::DwellTimeViolation { required, actual, tier } => {
                write!(
                    f,
                    "DWELL_TIME_VIOLATION: {} tier requires {:?} review time, got {:?}. Speed interpreted as negligence.",
                    tier, required, actual
                )
            }
            Self::ChallengeFailure { challenge_id, attempts, max_attempts } => {
                write!(
                    f,
                    "CHALLENGE_FAILURE: Challenge {} failed after {}/{} attempts",
                    challenge_id, attempts, max_attempts
                )
            }
            Self::RememberShortcutForbidden { tier } => {
                write!(
                    f,
                    "REMEMBER_SHORTCUT_FORBIDDEN: {} tier does not allow 'Remember this choice'",
                    tier
                )
            }
            Self::VelocityViolation { decisions_per_minute, max_safe_velocity } => {
                write!(
                    f,
                    "VELOCITY_VIOLATION: {:.1} decisions/min exceeds safe threshold of {:.1}",
                    decisions_per_minute, max_safe_velocity
                )
            }
            Self::BypassAttemptDetected { method, timestamp } => {
                write!(
                    f,
                    "BYPASS_ATTEMPT_DETECTED: Method '{}' at timestamp {}",
                    method, timestamp
                )
            }
            Self::TimerNotStarted => {
                write!(f, "TIMER_NOT_STARTED: Approval attempted without starting review timer")
            }
            Self::ChallengeRequired { tier } => {
                write!(f, "CHALLENGE_REQUIRED: {} tier requires challenge completion", tier)
            }
            Self::InternalError(msg) => {
                write!(f, "INTERNAL_ERROR: {}", msg)
            }
        }
    }
}

impl std::error::Error for CognitiveFrictionError {}

/// Result type for cognitive friction operations.
pub type CognitiveFrictionResult<T> = Result<T, CognitiveFrictionError>;

/// The main Cognitive Gate that enforces all friction rules.
///
/// This is the "Mind" component of the Sovereign Gate, protecting
/// the operator from their own cognitive limitations under pressure.
#[derive(Debug)]
pub struct CognitiveGate {
    /// Friction timer for dwell time enforcement
    timer: FrictionTimer,

    /// Challenge verifier for semantic challenges
    verifier: ChallengeVerifier,

    /// Decision gate for approval flow
    decision_gate: DecisionGate,

    /// Maximum decisions per minute before velocity warning
    max_velocity: f64,

    /// Whether the gate is armed (enforcing friction)
    armed: bool,
}

impl CognitiveGate {
    /// Create a new cognitive gate with default settings.
    pub fn new() -> Self {
        Self {
            timer: FrictionTimer::new(),
            verifier: ChallengeVerifier::new(),
            decision_gate: DecisionGate::new(),
            max_velocity: 6.0, // Max 6 decisions per minute (10 second average)
            armed: true,
        }
    }

    /// Create a gate for a specific friction tier.
    pub fn for_tier(tier: FrictionTier) -> Self {
        let mut gate = Self::new();
        gate.decision_gate = DecisionGate::for_tier(tier);
        gate
    }

    /// Arm the gate (enable friction enforcement).
    pub fn arm(&mut self) {
        self.armed = true;
    }

    /// Disarm the gate (disable friction - ONLY for testing).
    ///
    /// # Warning
    /// Disarming in production violates Constitutional Invariant CF-004.
    #[cfg(any(test, feature = "test-mode"))]
    pub fn disarm(&mut self) {
        self.armed = false;
    }

    /// Check if the gate is armed.
    pub fn is_armed(&self) -> bool {
        self.armed
    }

    /// Start review timer for a decision.
    pub fn start_review(&mut self, decision_id: &str, tier: FrictionTier) {
        self.timer.start(decision_id, tier);
    }

    /// Generate a challenge for the current decision.
    pub fn generate_challenge(&mut self, tier: FrictionTier) -> Option<Challenge> {
        if tier.requires_challenge() || tier.challenge_recommended() {
            Some(self.verifier.generate(tier))
        } else {
            None
        }
    }

    /// Submit a decision for approval.
    ///
    /// This enforces all cognitive friction rules:
    /// 1. Dwell time must be satisfied
    /// 2. Challenge must be passed (if required)
    /// 3. Velocity must be within safe limits
    pub fn submit_decision(
        &mut self,
        request: DecisionRequest,
    ) -> CognitiveFrictionResult<DecisionOutcome> {
        if !self.armed {
            // Gate disarmed (test mode only)
            return Ok(DecisionOutcome::Approved {
                decision_id: request.decision_id,
                review_duration: Duration::ZERO,
                challenge_passed: false,
            });
        }

        // Check timer was started
        let timer_state = self.timer.check(&request.decision_id)?;

        // Enforce dwell time
        let dwell = request.tier.minimum_dwell();
        if timer_state.elapsed < dwell {
            return Err(CognitiveFrictionError::DwellTimeViolation {
                required: dwell,
                actual: timer_state.elapsed,
                tier: request.tier,
            });
        }

        // Check challenge if required
        if request.tier.requires_challenge() && request.challenge_response.is_none() {
            return Err(CognitiveFrictionError::ChallengeRequired { tier: request.tier });
        }

        // Verify challenge response if provided
        let challenge_passed = if let Some(response) = &request.challenge_response {
            self.verifier.verify(response)?
        } else {
            false
        };

        // Check for remember shortcut violation
        if request.remember_choice && !request.tier.allows_remember_shortcut() {
            return Err(CognitiveFrictionError::RememberShortcutForbidden { tier: request.tier });
        }

        // Record decision and check velocity
        self.decision_gate.record_decision(&request)?;

        // Clear timer
        self.timer.clear(&request.decision_id);

        Ok(DecisionOutcome::Approved {
            decision_id: request.decision_id,
            review_duration: timer_state.elapsed,
            challenge_passed,
        })
    }

    /// Get current decision velocity (decisions per minute).
    pub fn current_velocity(&self) -> f64 {
        self.decision_gate.current_velocity()
    }

    /// Check if velocity is within safe limits.
    pub fn velocity_safe(&self) -> bool {
        self.current_velocity() <= self.max_velocity
    }
}

impl Default for CognitiveGate {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_friction_tier_dwell_times() {
        assert_eq!(FrictionTier::Law.minimum_dwell(), Duration::from_secs(5));
        assert_eq!(FrictionTier::Policy.minimum_dwell(), Duration::from_secs(3));
        assert_eq!(FrictionTier::Guidance.minimum_dwell(), Duration::from_secs(2));
        assert_eq!(FrictionTier::Operational.minimum_dwell(), Duration::from_secs(1));
    }

    #[test]
    fn test_friction_tier_challenge_requirements() {
        assert!(FrictionTier::Law.requires_challenge());
        assert!(!FrictionTier::Policy.requires_challenge());
        assert!(!FrictionTier::Guidance.requires_challenge());
        assert!(!FrictionTier::Operational.requires_challenge());
    }

    #[test]
    fn test_friction_tier_remember_shortcuts() {
        // CF-003: LAW and POLICY must not allow remember shortcuts
        assert!(!FrictionTier::Law.allows_remember_shortcut());
        assert!(!FrictionTier::Policy.allows_remember_shortcut());
        assert!(FrictionTier::Guidance.allows_remember_shortcut());
        assert!(FrictionTier::Operational.allows_remember_shortcut());
    }

    #[test]
    fn test_friction_tier_from_string() {
        assert_eq!(FrictionTier::from_governance_tier("LAW"), FrictionTier::Law);
        assert_eq!(FrictionTier::from_governance_tier("policy"), FrictionTier::Policy);
        assert_eq!(FrictionTier::from_governance_tier("GUIDANCE"), FrictionTier::Guidance);
        assert_eq!(FrictionTier::from_governance_tier("operational"), FrictionTier::Operational);
        // Unknown defaults to LAW (maximum friction)
        assert_eq!(FrictionTier::from_governance_tier("unknown"), FrictionTier::Law);
    }

    #[test]
    fn test_cognitive_gate_creation() {
        let gate = CognitiveGate::new();
        assert!(gate.is_armed());
    }

    #[test]
    fn test_cognitive_gate_for_tier() {
        let gate = CognitiveGate::for_tier(FrictionTier::Law);
        assert!(gate.is_armed());
    }

    #[test]
    fn test_error_display() {
        let err = CognitiveFrictionError::DwellTimeViolation {
            required: Duration::from_secs(5),
            actual: Duration::from_secs(1),
            tier: FrictionTier::Law,
        };
        let msg = err.to_string();
        assert!(msg.contains("DWELL_TIME_VIOLATION"));
        assert!(msg.contains("LAW"));
        assert!(msg.contains("negligence"));
    }

    #[test]
    fn test_remember_shortcut_forbidden_error() {
        let err = CognitiveFrictionError::RememberShortcutForbidden {
            tier: FrictionTier::Law,
        };
        let msg = err.to_string();
        assert!(msg.contains("REMEMBER_SHORTCUT_FORBIDDEN"));
        assert!(msg.contains("LAW"));
    }
}
