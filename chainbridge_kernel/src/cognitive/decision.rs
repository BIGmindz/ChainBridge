//! # Decision Gate (PAC-OCC-P21)
//!
//! Implements the decision approval flow with velocity tracking and
//! rubber-stamping detection.
//!
//! ## Velocity Tracking
//!
//! Monitors decision rate to detect cognitive fatigue. If operators
//! make decisions too quickly, it indicates potential rubber-stamping.
//!
//! ## Constitutional Invariant CF-005
//!
//! Velocity violations trigger automatic rejection. The system protects
//! the operator from themselves.

use super::{ChallengeResponse, CognitiveFrictionError, CognitiveFrictionResult, FrictionTier};
use std::collections::VecDeque;
use std::time::{Duration, Instant};

/// State of the review process for a decision.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReviewState {
    /// Decision is pending review
    Pending,

    /// Review in progress (timer running)
    InProgress,

    /// Review complete, awaiting approval
    AwaitingApproval,

    /// Challenge required before approval
    ChallengeRequired,

    /// Decision approved
    Approved,

    /// Decision rejected
    Rejected,

    /// Decision expired (timeout)
    Expired,
}

impl std::fmt::Display for ReviewState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ReviewState::Pending => write!(f, "PENDING"),
            ReviewState::InProgress => write!(f, "IN_PROGRESS"),
            ReviewState::AwaitingApproval => write!(f, "AWAITING_APPROVAL"),
            ReviewState::ChallengeRequired => write!(f, "CHALLENGE_REQUIRED"),
            ReviewState::Approved => write!(f, "APPROVED"),
            ReviewState::Rejected => write!(f, "REJECTED"),
            ReviewState::Expired => write!(f, "EXPIRED"),
        }
    }
}

/// A request to make a decision.
#[derive(Debug, Clone)]
pub struct DecisionRequest {
    /// Unique identifier for the decision
    pub decision_id: String,

    /// Friction tier for this decision
    pub tier: FrictionTier,

    /// Whether operator wants to remember this choice
    pub remember_choice: bool,

    /// Challenge response if challenge was required
    pub challenge_response: Option<ChallengeResponse>,

    /// PAC ID this decision relates to (for audit)
    pub pac_id: Option<String>,

    /// Brief summary of what's being decided (for logging)
    pub summary: String,
}

impl DecisionRequest {
    /// Create a new decision request.
    pub fn new(decision_id: String, tier: FrictionTier, summary: String) -> Self {
        Self {
            decision_id,
            tier,
            remember_choice: false,
            challenge_response: None,
            pac_id: None,
            summary,
        }
    }

    /// Set challenge response.
    pub fn with_challenge_response(mut self, response: ChallengeResponse) -> Self {
        self.challenge_response = Some(response);
        self
    }

    /// Set remember choice flag.
    pub fn with_remember(mut self, remember: bool) -> Self {
        self.remember_choice = remember;
        self
    }

    /// Set PAC ID for audit trail.
    pub fn with_pac_id(mut self, pac_id: String) -> Self {
        self.pac_id = Some(pac_id);
        self
    }
}

/// Outcome of a decision submission.
#[derive(Debug, Clone)]
pub enum DecisionOutcome {
    /// Decision was approved
    Approved {
        /// Decision ID
        decision_id: String,
        /// Time spent reviewing
        review_duration: Duration,
        /// Whether challenge was passed
        challenge_passed: bool,
    },

    /// Decision was rejected
    Rejected {
        /// Decision ID
        decision_id: String,
        /// Reason for rejection
        reason: String,
    },

    /// Decision requires more review
    RequiresMoreReview {
        /// Decision ID
        decision_id: String,
        /// Time remaining
        time_remaining: Duration,
    },

    /// Challenge is required
    ChallengeRequired {
        /// Decision ID
        decision_id: String,
        /// Challenge ID
        challenge_id: String,
    },
}

/// Record of a completed decision.
#[derive(Debug, Clone)]
struct DecisionRecord {
    /// When the decision was made
    timestamp: Instant,

    /// Friction tier
    tier: FrictionTier,

    /// Review duration
    review_duration: Duration,
}

/// The decision gate that manages approval flow and velocity.
#[derive(Debug)]
pub struct DecisionGate {
    /// Default friction tier
    default_tier: FrictionTier,

    /// Recent decisions for velocity tracking
    recent_decisions: VecDeque<DecisionRecord>,

    /// Window for velocity calculation (default 1 minute)
    velocity_window: Duration,

    /// Maximum safe velocity (decisions per minute)
    max_velocity: f64,

    /// Velocity warning threshold (percentage of max)
    warning_threshold: f64,

    /// Whether velocity enforcement is enabled
    velocity_enforcement: bool,
}

impl DecisionGate {
    /// Create a new decision gate.
    pub fn new() -> Self {
        Self {
            default_tier: FrictionTier::Law, // Default to strictest
            recent_decisions: VecDeque::new(),
            velocity_window: Duration::from_secs(60),
            max_velocity: 6.0, // 6 decisions per minute max
            warning_threshold: 0.8, // Warn at 80% of max
            velocity_enforcement: true,
        }
    }

    /// Create a gate for a specific tier.
    pub fn for_tier(tier: FrictionTier) -> Self {
        let mut gate = Self::new();
        gate.default_tier = tier;

        // Adjust velocity based on tier
        gate.max_velocity = match tier {
            FrictionTier::Law => 3.0,        // Very slow for LAW
            FrictionTier::Policy => 6.0,     // Moderate for POLICY
            FrictionTier::Guidance => 10.0,  // Faster for GUIDANCE
            FrictionTier::Operational => 20.0, // Fast for OPERATIONAL
        };

        gate
    }

    /// Record a decision and check velocity.
    pub fn record_decision(&mut self, request: &DecisionRequest) -> CognitiveFrictionResult<()> {
        // Clean old decisions outside window
        self.clean_old_decisions();

        // Check velocity before recording
        if self.velocity_enforcement {
            let current_velocity = self.current_velocity();
            if current_velocity >= self.max_velocity {
                return Err(CognitiveFrictionError::VelocityViolation {
                    decisions_per_minute: current_velocity,
                    max_safe_velocity: self.max_velocity,
                });
            }
        }

        // Record the decision
        self.recent_decisions.push_back(DecisionRecord {
            timestamp: Instant::now(),
            tier: request.tier,
            review_duration: Duration::ZERO, // Will be updated by timer
        });

        Ok(())
    }

    /// Get current decision velocity (decisions per minute).
    pub fn current_velocity(&self) -> f64 {
        self.clean_old_decisions_readonly();

        let count = self.count_recent_decisions();
        let window_minutes = self.velocity_window.as_secs_f64() / 60.0;

        count as f64 / window_minutes
    }

    /// Check if velocity is in warning zone.
    pub fn velocity_warning(&self) -> bool {
        self.current_velocity() >= (self.max_velocity * self.warning_threshold)
    }

    /// Check if velocity enforcement would reject.
    pub fn would_reject(&self) -> bool {
        self.velocity_enforcement && self.current_velocity() >= self.max_velocity
    }

    /// Get time until next decision is allowed.
    pub fn time_until_allowed(&self) -> Duration {
        if !self.velocity_enforcement || self.current_velocity() < self.max_velocity {
            return Duration::ZERO;
        }

        // Find when oldest decision will expire from window
        if let Some(oldest) = self.recent_decisions.front() {
            let age = oldest.timestamp.elapsed();
            self.velocity_window.saturating_sub(age)
        } else {
            Duration::ZERO
        }
    }

    /// Set velocity enforcement.
    #[cfg(any(test, feature = "test-mode"))]
    pub fn set_velocity_enforcement(&mut self, enabled: bool) {
        self.velocity_enforcement = enabled;
    }

    /// Clean decisions outside the velocity window.
    fn clean_old_decisions(&mut self) {
        let cutoff = Instant::now() - self.velocity_window;
        while let Some(front) = self.recent_decisions.front() {
            if front.timestamp < cutoff {
                self.recent_decisions.pop_front();
            } else {
                break;
            }
        }
    }

    /// Count recent decisions (readonly version for velocity calc).
    fn clean_old_decisions_readonly(&self) -> usize {
        let cutoff = Instant::now() - self.velocity_window;
        self.recent_decisions
            .iter()
            .filter(|d| d.timestamp >= cutoff)
            .count()
    }

    /// Count recent decisions in window.
    fn count_recent_decisions(&self) -> usize {
        let cutoff = Instant::now() - self.velocity_window;
        self.recent_decisions
            .iter()
            .filter(|d| d.timestamp >= cutoff)
            .count()
    }

    /// Get statistics about recent decisions.
    pub fn stats(&self) -> DecisionStats {
        let count = self.count_recent_decisions();
        let velocity = self.current_velocity();

        let avg_review = if count > 0 {
            let total: Duration = self
                .recent_decisions
                .iter()
                .map(|d| d.review_duration)
                .sum();
            Some(total / count as u32)
        } else {
            None
        };

        DecisionStats {
            decisions_in_window: count,
            velocity,
            max_velocity: self.max_velocity,
            average_review_duration: avg_review,
            velocity_warning: self.velocity_warning(),
            would_reject: self.would_reject(),
        }
    }
}

impl Default for DecisionGate {
    fn default() -> Self {
        Self::new()
    }
}

/// Statistics about decision velocity.
#[derive(Debug, Clone)]
pub struct DecisionStats {
    /// Number of decisions in the velocity window
    pub decisions_in_window: usize,

    /// Current velocity (decisions per minute)
    pub velocity: f64,

    /// Maximum allowed velocity
    pub max_velocity: f64,

    /// Average review duration
    pub average_review_duration: Option<Duration>,

    /// Whether velocity is in warning zone
    pub velocity_warning: bool,

    /// Whether next decision would be rejected
    pub would_reject: bool,
}

impl DecisionStats {
    /// Percentage of max velocity used.
    pub fn velocity_percentage(&self) -> f64 {
        (self.velocity / self.max_velocity * 100.0).min(100.0)
    }

    /// Decisions remaining before rejection.
    pub fn decisions_remaining(&self) -> usize {
        let max_in_window = (self.max_velocity * 1.0).floor() as usize; // 1 minute window
        max_in_window.saturating_sub(self.decisions_in_window)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_review_state_display() {
        assert_eq!(ReviewState::Pending.to_string(), "PENDING");
        assert_eq!(ReviewState::Approved.to_string(), "APPROVED");
        assert_eq!(ReviewState::ChallengeRequired.to_string(), "CHALLENGE_REQUIRED");
    }

    #[test]
    fn test_decision_request_creation() {
        let request = DecisionRequest::new(
            "dec-1".to_string(),
            FrictionTier::Law,
            "Test decision".to_string(),
        );

        assert_eq!(request.decision_id, "dec-1");
        assert_eq!(request.tier, FrictionTier::Law);
        assert!(!request.remember_choice);
    }

    #[test]
    fn test_decision_request_builder() {
        let request = DecisionRequest::new(
            "dec-2".to_string(),
            FrictionTier::Policy,
            "Policy decision".to_string(),
        )
        .with_remember(true)
        .with_pac_id("PAC-001".to_string());

        assert!(request.remember_choice);
        assert_eq!(request.pac_id, Some("PAC-001".to_string()));
    }

    #[test]
    fn test_decision_gate_creation() {
        let gate = DecisionGate::new();
        assert_eq!(gate.default_tier, FrictionTier::Law);
        assert!((gate.max_velocity - 6.0).abs() < 0.01);
    }

    #[test]
    fn test_decision_gate_for_tier() {
        let law_gate = DecisionGate::for_tier(FrictionTier::Law);
        assert!((law_gate.max_velocity - 3.0).abs() < 0.01);

        let op_gate = DecisionGate::for_tier(FrictionTier::Operational);
        assert!((op_gate.max_velocity - 20.0).abs() < 0.01);
    }

    #[test]
    fn test_initial_velocity() {
        let gate = DecisionGate::new();
        assert!((gate.current_velocity() - 0.0).abs() < 0.01);
    }

    #[test]
    fn test_record_decision() {
        let mut gate = DecisionGate::new();
        let request = DecisionRequest::new(
            "dec-1".to_string(),
            FrictionTier::Operational,
            "Test".to_string(),
        );

        let result = gate.record_decision(&request);
        assert!(result.is_ok());

        // Velocity should now be > 0
        assert!(gate.current_velocity() > 0.0);
    }

    #[test]
    fn test_velocity_rejection() {
        let mut gate = DecisionGate::for_tier(FrictionTier::Law);
        // LAW tier has max_velocity of 3.0 per minute

        // Record 3 decisions (at limit)
        for i in 0..3 {
            let request = DecisionRequest::new(
                format!("dec-{}", i),
                FrictionTier::Law,
                "Test".to_string(),
            );
            let _ = gate.record_decision(&request);
        }

        // 4th should be rejected
        let request = DecisionRequest::new(
            "dec-4".to_string(),
            FrictionTier::Law,
            "Test".to_string(),
        );

        let result = gate.record_decision(&request);
        assert!(matches!(
            result,
            Err(CognitiveFrictionError::VelocityViolation { .. })
        ));
    }

    #[test]
    fn test_stats() {
        let mut gate = DecisionGate::new();

        let request = DecisionRequest::new(
            "dec-1".to_string(),
            FrictionTier::Operational,
            "Test".to_string(),
        );
        let _ = gate.record_decision(&request);

        let stats = gate.stats();
        assert_eq!(stats.decisions_in_window, 1);
        assert!(stats.velocity > 0.0);
        assert!(!stats.would_reject);
    }

    #[test]
    fn test_velocity_percentage() {
        let stats = DecisionStats {
            decisions_in_window: 3,
            velocity: 3.0,
            max_velocity: 6.0,
            average_review_duration: None,
            velocity_warning: false,
            would_reject: false,
        };

        assert!((stats.velocity_percentage() - 50.0).abs() < 0.01);
    }

    #[test]
    fn test_time_until_allowed() {
        let gate = DecisionGate::new();
        // No decisions, should be allowed immediately
        assert_eq!(gate.time_until_allowed(), Duration::ZERO);
    }
}
