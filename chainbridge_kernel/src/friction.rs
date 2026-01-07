//! # Friction Gate (PAC-OCC-P21-CODE)
//!
//! Integrates Cognitive Friction into the Constitutional Validator.
//! This module provides the G9 gate that enforces dwell time before approval.
//!
//! ## Constitutional Invariant
//!
//! Speed is negligence. The operator MUST spend adequate time reviewing
//! before any PAC can be approved.
//!
//! ## Design: State Comparison, Not Sleep
//!
//! The friction check is a **timestamp comparison**, not a blocking sleep.
//! This allows the Kernel to remain responsive while still enforcing
//! cognitive friction.
//!
//! ```text
//! if now < admission_ts + min_dwell:
//!     return REJECTED  // Too fast, negligence detected
//! else:
//!     return PASSED    // Adequate deliberation time
//! ```

use chrono::{DateTime, Duration, Utc};
use crate::error::{KernelError, KernelResult};
use crate::models::{GateResult, GovernanceTier, PreflightGate};

/// Minimum dwell times by governance tier.
///
/// ## Constitutional Invariant CF-001
/// LAW-tier decisions require minimum 5 second dwell time.
pub mod dwell_times {
    use chrono::Duration;

    /// LAW tier: 5 seconds minimum (STRICT)
    pub fn law() -> Duration {
        Duration::seconds(5)
    }

    /// POLICY tier: 3 seconds minimum
    pub fn policy() -> Duration {
        Duration::seconds(3)
    }

    /// GUIDANCE tier: 2 seconds minimum
    pub fn guidance() -> Duration {
        Duration::seconds(2)
    }

    /// OPERATIONAL tier: 1 second minimum
    pub fn operational() -> Duration {
        Duration::seconds(1)
    }

    /// Get dwell time for a governance tier.
    pub fn for_tier(tier: &super::GovernanceTier) -> Duration {
        match tier {
            super::GovernanceTier::Law => law(),
            super::GovernanceTier::Policy => policy(),
            super::GovernanceTier::Guidance => guidance(),
            super::GovernanceTier::Operational => operational(),
        }
    }
}

/// Admission timestamp for a PAC review session.
///
/// This captures when the operator first viewed the PAC for review.
/// The dwell time is calculated from this timestamp.
#[derive(Debug, Clone, Copy)]
pub struct AdmissionTimestamp {
    /// When the PAC was admitted for review
    timestamp: DateTime<Utc>,
}

impl AdmissionTimestamp {
    /// Create a new admission timestamp (now).
    pub fn now() -> Self {
        Self {
            timestamp: Utc::now(),
        }
    }

    /// Create an admission timestamp from an existing datetime.
    pub fn from_datetime(timestamp: DateTime<Utc>) -> Self {
        Self { timestamp }
    }

    /// Get the underlying timestamp.
    pub fn timestamp(&self) -> DateTime<Utc> {
        self.timestamp
    }

    /// Calculate elapsed time since admission.
    pub fn elapsed(&self) -> Duration {
        Utc::now().signed_duration_since(self.timestamp)
    }

    /// Check if minimum dwell time has been satisfied for a tier.
    pub fn dwell_satisfied(&self, tier: &GovernanceTier) -> bool {
        let min_dwell = dwell_times::for_tier(tier);
        self.elapsed() >= min_dwell
    }

    /// Get remaining time until dwell is satisfied.
    pub fn time_remaining(&self, tier: &GovernanceTier) -> Duration {
        let min_dwell = dwell_times::for_tier(tier);
        let elapsed = self.elapsed();
        if elapsed >= min_dwell {
            Duration::zero()
        } else {
            min_dwell - elapsed
        }
    }
}

impl Default for AdmissionTimestamp {
    fn default() -> Self {
        Self::now()
    }
}

/// Result of a dwell time verification.
#[derive(Debug, Clone)]
pub struct DwellVerification {
    /// Whether the dwell time was satisfied
    pub satisfied: bool,

    /// Required minimum dwell time
    pub required: Duration,

    /// Actual elapsed time
    pub elapsed: Duration,

    /// Time remaining (zero if satisfied)
    pub remaining: Duration,

    /// The tier that was checked
    pub tier: GovernanceTier,
}

impl DwellVerification {
    /// Create a new dwell verification result.
    pub fn new(
        satisfied: bool,
        required: Duration,
        elapsed: Duration,
        tier: GovernanceTier,
    ) -> Self {
        let remaining = if satisfied {
            Duration::zero()
        } else {
            required - elapsed
        };

        Self {
            satisfied,
            required,
            elapsed,
            remaining,
            tier,
        }
    }

    /// Format the verification result as a human-readable message.
    pub fn message(&self) -> String {
        if self.satisfied {
            format!(
                "Dwell time satisfied: {:.1}s elapsed >= {:.1}s required for {} tier",
                self.elapsed.num_milliseconds() as f64 / 1000.0,
                self.required.num_milliseconds() as f64 / 1000.0,
                self.tier.as_str()
            )
        } else {
            format!(
                "DWELL_TIME_VIOLATION: {:.1}s elapsed < {:.1}s required for {} tier. {:.1}s remaining. Speed interpreted as negligence.",
                self.elapsed.num_milliseconds() as f64 / 1000.0,
                self.required.num_milliseconds() as f64 / 1000.0,
                self.tier.as_str(),
                self.remaining.num_milliseconds() as f64 / 1000.0
            )
        }
    }
}

/// The Friction Gate trait for G9 enforcement.
///
/// This trait allows the validator to check cognitive friction
/// requirements before approving a PAC.
pub trait FrictionGate {
    /// Verify that dwell time has been satisfied.
    ///
    /// ## Arguments
    /// * `admission_ts` - When the PAC was admitted for review
    /// * `tier` - The governance tier of the PAC
    ///
    /// ## Returns
    /// * `Ok(DwellVerification)` - Verification result (may be satisfied or not)
    /// * `Err(KernelError)` - System error (clock failure = Fail-Closed)
    fn verify_dwell_time(
        &self,
        admission_ts: &AdmissionTimestamp,
        tier: &GovernanceTier,
    ) -> KernelResult<DwellVerification>;

    /// Execute G9 gate check.
    ///
    /// This creates a GateResult for the G9 Cognitive Friction gate.
    fn gate_g9_cognitive_friction(
        &self,
        admission_ts: &AdmissionTimestamp,
        tier: &GovernanceTier,
    ) -> KernelResult<GateResult>;
}

/// Default implementation of the Friction Gate.
#[derive(Debug, Default)]
pub struct DefaultFrictionGate;

impl DefaultFrictionGate {
    /// Create a new default friction gate.
    pub fn new() -> Self {
        Self
    }
}

impl FrictionGate for DefaultFrictionGate {
    fn verify_dwell_time(
        &self,
        admission_ts: &AdmissionTimestamp,
        tier: &GovernanceTier,
    ) -> KernelResult<DwellVerification> {
        // Get current time - Fail-Closed on clock error
        let now = Utc::now();

        // Calculate elapsed time
        let elapsed = now.signed_duration_since(admission_ts.timestamp());

        // Handle negative duration (clock skew) - Fail-Closed
        if elapsed < Duration::zero() {
            return Err(KernelError::SystemTimeError {
                message: "Clock skew detected: admission timestamp is in the future".to_string(),
            });
        }

        // Get required dwell time for tier
        let required = dwell_times::for_tier(tier);

        // Check if satisfied
        let satisfied = elapsed >= required;

        Ok(DwellVerification::new(satisfied, required, elapsed, *tier))
    }

    fn gate_g9_cognitive_friction(
        &self,
        admission_ts: &AdmissionTimestamp,
        tier: &GovernanceTier,
    ) -> KernelResult<GateResult> {
        let verification = self.verify_dwell_time(admission_ts, tier)?;

        Ok(GateResult {
            gate: PreflightGate::G9CognitiveFriction,
            passed: verification.satisfied,
            message: verification.message(),
            timestamp: Utc::now(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;
    use std::time::Duration as StdDuration;

    #[test]
    fn test_dwell_times_law_is_5_seconds() {
        assert_eq!(dwell_times::law(), Duration::seconds(5));
    }

    #[test]
    fn test_dwell_times_policy_is_3_seconds() {
        assert_eq!(dwell_times::policy(), Duration::seconds(3));
    }

    #[test]
    fn test_dwell_times_guidance_is_2_seconds() {
        assert_eq!(dwell_times::guidance(), Duration::seconds(2));
    }

    #[test]
    fn test_dwell_times_operational_is_1_second() {
        assert_eq!(dwell_times::operational(), Duration::seconds(1));
    }

    #[test]
    fn test_dwell_times_for_tier() {
        assert_eq!(dwell_times::for_tier(&GovernanceTier::Law), Duration::seconds(5));
        assert_eq!(dwell_times::for_tier(&GovernanceTier::Policy), Duration::seconds(3));
        assert_eq!(dwell_times::for_tier(&GovernanceTier::Guidance), Duration::seconds(2));
        assert_eq!(dwell_times::for_tier(&GovernanceTier::Operational), Duration::seconds(1));
    }

    #[test]
    fn test_admission_timestamp_now() {
        let ts = AdmissionTimestamp::now();
        let elapsed = ts.elapsed();
        // Should be very close to zero
        assert!(elapsed.num_milliseconds() < 100);
    }

    #[test]
    fn test_admission_timestamp_elapsed() {
        let ts = AdmissionTimestamp::now();
        thread::sleep(StdDuration::from_millis(100));
        let elapsed = ts.elapsed();
        assert!(elapsed.num_milliseconds() >= 100);
    }

    #[test]
    fn test_dwell_not_satisfied_immediately() {
        let ts = AdmissionTimestamp::now();
        assert!(!ts.dwell_satisfied(&GovernanceTier::Operational));
    }

    #[test]
    fn test_dwell_satisfied_after_wait() {
        let past = Utc::now() - Duration::seconds(10);
        let ts = AdmissionTimestamp::from_datetime(past);
        assert!(ts.dwell_satisfied(&GovernanceTier::Law));
    }

    #[test]
    fn test_time_remaining() {
        let ts = AdmissionTimestamp::now();
        let remaining = ts.time_remaining(&GovernanceTier::Law);
        // Should be close to 5 seconds
        assert!(remaining.num_seconds() >= 4);
    }

    #[test]
    fn test_time_remaining_zero_when_satisfied() {
        let past = Utc::now() - Duration::seconds(10);
        let ts = AdmissionTimestamp::from_datetime(past);
        let remaining = ts.time_remaining(&GovernanceTier::Law);
        assert_eq!(remaining, Duration::zero());
    }

    #[test]
    fn test_default_friction_gate_rejects_fast_click() {
        let gate = DefaultFrictionGate::new();
        let ts = AdmissionTimestamp::now();

        let result = gate.verify_dwell_time(&ts, &GovernanceTier::Law).unwrap();
        assert!(!result.satisfied);
        assert!(result.message().contains("DWELL_TIME_VIOLATION"));
    }

    #[test]
    fn test_default_friction_gate_accepts_slow_click() {
        let gate = DefaultFrictionGate::new();
        let past = Utc::now() - Duration::seconds(10);
        let ts = AdmissionTimestamp::from_datetime(past);

        let result = gate.verify_dwell_time(&ts, &GovernanceTier::Law).unwrap();
        assert!(result.satisfied);
        assert!(result.message().contains("satisfied"));
    }

    #[test]
    fn test_g9_gate_result_format() {
        let gate = DefaultFrictionGate::new();
        let past = Utc::now() - Duration::seconds(10);
        let ts = AdmissionTimestamp::from_datetime(past);

        let result = gate.gate_g9_cognitive_friction(&ts, &GovernanceTier::Law).unwrap();
        assert_eq!(result.gate, PreflightGate::G9CognitiveFriction);
        assert!(result.passed);
    }

    #[test]
    fn test_dwell_verification_message_satisfied() {
        let verification = DwellVerification::new(
            true,
            Duration::seconds(5),
            Duration::seconds(6),
            GovernanceTier::Law,
        );
        let msg = verification.message();
        assert!(msg.contains("satisfied"));
        assert!(msg.contains("LAW"));
    }

    #[test]
    fn test_dwell_verification_message_violation() {
        let verification = DwellVerification::new(
            false,
            Duration::seconds(5),
            Duration::seconds(2),
            GovernanceTier::Law,
        );
        let msg = verification.message();
        assert!(msg.contains("DWELL_TIME_VIOLATION"));
        assert!(msg.contains("negligence"));
    }
}
