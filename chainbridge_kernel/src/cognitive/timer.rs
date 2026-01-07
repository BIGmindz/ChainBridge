//! # Friction Timer (PAC-OCC-P21)
//!
//! Implements dwell time enforcement to ensure operators spend adequate time
//! reviewing decisions before approval.
//!
//! ## Constitutional Invariant CF-001
//!
//! LAW-tier decisions require minimum 5 second dwell time.
//! Any approval attempt before dwell time expires is REJECTED.
//!
//! ## Constitutional Invariant CF-004
//!
//! UI cannot bypass Kernel friction timer. The timer runs in the Kernel,
//! not the UI. Frontend cannot fast-forward or skip.

use super::{CognitiveFrictionError, CognitiveFrictionResult, FrictionTier};
use std::collections::HashMap;
use std::time::{Duration, Instant};

/// State of the friction timer.
#[derive(Debug, Clone)]
pub struct TimerState {
    /// When the review started
    pub started_at: Instant,

    /// Time elapsed since start
    pub elapsed: Duration,

    /// Required minimum dwell time
    pub required_dwell: Duration,

    /// Whether dwell time has been satisfied
    pub dwell_satisfied: bool,

    /// The friction tier for this timer
    pub tier: FrictionTier,
}

impl TimerState {
    /// Time remaining until dwell is satisfied.
    pub fn time_remaining(&self) -> Duration {
        if self.dwell_satisfied {
            Duration::ZERO
        } else {
            self.required_dwell.saturating_sub(self.elapsed)
        }
    }

    /// Progress toward dwell satisfaction (0.0 to 1.0).
    pub fn progress(&self) -> f64 {
        let elapsed_secs = self.elapsed.as_secs_f64();
        let required_secs = self.required_dwell.as_secs_f64();
        (elapsed_secs / required_secs).min(1.0)
    }
}

/// Dwell time requirement for a decision.
#[derive(Debug, Clone)]
pub struct DwellRequirement {
    /// Minimum time required
    pub minimum: Duration,

    /// Recommended time (for UI hints)
    pub recommended: Duration,

    /// Maximum useful time (diminishing returns after this)
    pub maximum: Duration,

    /// Friction tier
    pub tier: FrictionTier,
}

impl DwellRequirement {
    /// Create dwell requirement for a tier.
    pub fn for_tier(tier: FrictionTier) -> Self {
        let (min, rec, max) = match tier {
            FrictionTier::Law => (
                Duration::from_secs(5),
                Duration::from_secs(30),
                Duration::from_secs(300),
            ),
            FrictionTier::Policy => (
                Duration::from_secs(3),
                Duration::from_secs(15),
                Duration::from_secs(180),
            ),
            FrictionTier::Guidance => (
                Duration::from_secs(2),
                Duration::from_secs(10),
                Duration::from_secs(120),
            ),
            FrictionTier::Operational => (
                Duration::from_secs(1),
                Duration::from_secs(5),
                Duration::from_secs(60),
            ),
        };

        Self {
            minimum: min,
            recommended: rec,
            maximum: max,
            tier,
        }
    }
}

/// Active timer entry.
#[derive(Debug, Clone)]
struct ActiveTimer {
    /// When the timer started
    started_at: Instant,

    /// Friction tier
    tier: FrictionTier,

    /// Dwell requirement
    requirement: DwellRequirement,

    /// Whether timer has been paused (e.g., window focus lost)
    paused: bool,

    /// Total paused duration
    paused_duration: Duration,
}

impl ActiveTimer {
    /// Get effective elapsed time (excluding paused time).
    fn effective_elapsed(&self) -> Duration {
        if self.paused {
            Duration::ZERO // Can't count paused time
        } else {
            self.started_at.elapsed().saturating_sub(self.paused_duration)
        }
    }

    /// Check if dwell is satisfied.
    fn is_satisfied(&self) -> bool {
        self.effective_elapsed() >= self.requirement.minimum
    }

    /// Convert to timer state.
    fn to_state(&self) -> TimerState {
        let elapsed = self.effective_elapsed();
        TimerState {
            started_at: self.started_at,
            elapsed,
            required_dwell: self.requirement.minimum,
            dwell_satisfied: elapsed >= self.requirement.minimum,
            tier: self.tier,
        }
    }
}

/// Friction timer that enforces dwell time requirements.
///
/// ## Design
///
/// The timer runs in the Kernel (Rust), not the UI. This prevents:
/// - JavaScript manipulation of timer values
/// - Frontend bypass attempts
/// - Clock manipulation attacks
///
/// ## Constitutional Invariant CF-004
///
/// UI cannot bypass Kernel friction timer.
#[derive(Debug)]
pub struct FrictionTimer {
    /// Active timers by decision ID
    active_timers: HashMap<String, ActiveTimer>,

    /// Historical timer data for analytics
    completed_timers: Vec<CompletedTimer>,

    /// Maximum concurrent timers (memory protection)
    max_concurrent: usize,
}

/// Completed timer record for analytics.
#[derive(Debug, Clone)]
pub struct CompletedTimer {
    /// Decision ID
    pub decision_id: String,

    /// Total review time
    pub review_duration: Duration,

    /// Friction tier
    pub tier: FrictionTier,

    /// Whether dwell was satisfied when completed
    pub dwell_satisfied: bool,

    /// When completed
    pub completed_at: Instant,
}

impl FrictionTimer {
    /// Create a new friction timer.
    pub fn new() -> Self {
        Self {
            active_timers: HashMap::new(),
            completed_timers: Vec::new(),
            max_concurrent: 100, // Prevent memory exhaustion
        }
    }

    /// Start a timer for a decision.
    pub fn start(&mut self, decision_id: &str, tier: FrictionTier) {
        // Enforce concurrent limit
        if self.active_timers.len() >= self.max_concurrent {
            // Remove oldest timer
            if let Some(oldest) = self.find_oldest_timer() {
                self.active_timers.remove(&oldest);
            }
        }

        let timer = ActiveTimer {
            started_at: Instant::now(),
            tier,
            requirement: DwellRequirement::for_tier(tier),
            paused: false,
            paused_duration: Duration::ZERO,
        };

        self.active_timers.insert(decision_id.to_string(), timer);
    }

    /// Check timer state for a decision.
    ///
    /// # Errors
    ///
    /// Returns `TimerNotStarted` if no timer exists for the decision.
    pub fn check(&self, decision_id: &str) -> CognitiveFrictionResult<TimerState> {
        let timer = self.active_timers.get(decision_id).ok_or_else(|| {
            CognitiveFrictionError::TimerNotStarted
        })?;

        Ok(timer.to_state())
    }

    /// Check if dwell time is satisfied.
    pub fn is_satisfied(&self, decision_id: &str) -> bool {
        self.active_timers
            .get(decision_id)
            .map(|t| t.is_satisfied())
            .unwrap_or(false)
    }

    /// Get time remaining until dwell is satisfied.
    pub fn time_remaining(&self, decision_id: &str) -> Option<Duration> {
        self.active_timers.get(decision_id).map(|t| {
            let elapsed = t.effective_elapsed();
            t.requirement.minimum.saturating_sub(elapsed)
        })
    }

    /// Pause a timer (e.g., window lost focus).
    ///
    /// Paused time does NOT count toward dwell time.
    pub fn pause(&mut self, decision_id: &str) {
        if let Some(timer) = self.active_timers.get_mut(decision_id) {
            timer.paused = true;
        }
    }

    /// Resume a paused timer.
    pub fn resume(&mut self, decision_id: &str) {
        if let Some(timer) = self.active_timers.get_mut(decision_id) {
            if timer.paused {
                // Track paused duration
                timer.paused_duration += timer.started_at.elapsed();
                timer.started_at = Instant::now();
                timer.paused = false;
            }
        }
    }

    /// Clear a timer (decision completed or cancelled).
    pub fn clear(&mut self, decision_id: &str) {
        if let Some(timer) = self.active_timers.remove(decision_id) {
            // Record completion
            self.completed_timers.push(CompletedTimer {
                decision_id: decision_id.to_string(),
                review_duration: timer.effective_elapsed(),
                tier: timer.tier,
                dwell_satisfied: timer.is_satisfied(),
                completed_at: Instant::now(),
            });

            // Trim history if too large
            if self.completed_timers.len() > 1000 {
                self.completed_timers.drain(0..500);
            }
        }
    }

    /// Get all active timer IDs.
    pub fn active_timer_ids(&self) -> Vec<String> {
        self.active_timers.keys().cloned().collect()
    }

    /// Get count of active timers.
    pub fn active_count(&self) -> usize {
        self.active_timers.len()
    }

    /// Get average review duration from history.
    pub fn average_review_duration(&self) -> Option<Duration> {
        if self.completed_timers.is_empty() {
            return None;
        }

        let total: Duration = self.completed_timers.iter().map(|t| t.review_duration).sum();
        Some(total / self.completed_timers.len() as u32)
    }

    /// Get dwell satisfaction rate from history.
    pub fn dwell_satisfaction_rate(&self) -> Option<f64> {
        if self.completed_timers.is_empty() {
            return None;
        }

        let satisfied = self
            .completed_timers
            .iter()
            .filter(|t| t.dwell_satisfied)
            .count();

        Some(satisfied as f64 / self.completed_timers.len() as f64)
    }

    /// Find the oldest active timer (for eviction).
    fn find_oldest_timer(&self) -> Option<String> {
        self.active_timers
            .iter()
            .min_by_key(|(_, t)| t.started_at)
            .map(|(id, _)| id.clone())
    }
}

impl Default for FrictionTimer {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;

    #[test]
    fn test_dwell_requirement_for_tier() {
        let law_req = DwellRequirement::for_tier(FrictionTier::Law);
        assert_eq!(law_req.minimum, Duration::from_secs(5));
        assert_eq!(law_req.tier, FrictionTier::Law);

        let op_req = DwellRequirement::for_tier(FrictionTier::Operational);
        assert_eq!(op_req.minimum, Duration::from_secs(1));
    }

    #[test]
    fn test_timer_start_and_check() {
        let mut timer = FrictionTimer::new();
        timer.start("decision-1", FrictionTier::Operational);

        let state = timer.check("decision-1").unwrap();
        assert_eq!(state.tier, FrictionTier::Operational);
        assert_eq!(state.required_dwell, Duration::from_secs(1));
    }

    #[test]
    fn test_timer_not_started_error() {
        let timer = FrictionTimer::new();
        let result = timer.check("nonexistent");
        assert!(matches!(result, Err(CognitiveFrictionError::TimerNotStarted)));
    }

    #[test]
    fn test_timer_satisfaction() {
        let mut timer = FrictionTimer::new();
        timer.start("decision-1", FrictionTier::Operational);

        // Initially not satisfied (need 1 second)
        assert!(!timer.is_satisfied("decision-1"));

        // Wait for dwell time
        thread::sleep(Duration::from_millis(1100));

        // Now satisfied
        assert!(timer.is_satisfied("decision-1"));
    }

    #[test]
    fn test_timer_clear_and_history() {
        let mut timer = FrictionTimer::new();
        timer.start("decision-1", FrictionTier::Operational);

        // Wait briefly
        thread::sleep(Duration::from_millis(50));

        // Clear
        timer.clear("decision-1");

        // Should be recorded in history
        assert_eq!(timer.completed_timers.len(), 1);
        assert_eq!(timer.completed_timers[0].decision_id, "decision-1");
    }

    #[test]
    fn test_timer_progress() {
        let state = TimerState {
            started_at: Instant::now(),
            elapsed: Duration::from_secs(3),
            required_dwell: Duration::from_secs(5),
            dwell_satisfied: false,
            tier: FrictionTier::Law,
        };

        assert!((state.progress() - 0.6).abs() < 0.01);
        assert_eq!(state.time_remaining(), Duration::from_secs(2));
    }

    #[test]
    fn test_timer_state_satisfied() {
        let state = TimerState {
            started_at: Instant::now(),
            elapsed: Duration::from_secs(6),
            required_dwell: Duration::from_secs(5),
            dwell_satisfied: true,
            tier: FrictionTier::Law,
        };

        assert!(state.dwell_satisfied);
        assert_eq!(state.time_remaining(), Duration::ZERO);
        assert!((state.progress() - 1.0).abs() < 0.01);
    }

    #[test]
    fn test_concurrent_timer_limit() {
        let mut timer = FrictionTimer::new();

        // Start many timers
        for i in 0..150 {
            timer.start(&format!("decision-{}", i), FrictionTier::Operational);
        }

        // Should be capped at max_concurrent (100)
        assert!(timer.active_count() <= 100);
    }

    #[test]
    fn test_active_timer_ids() {
        let mut timer = FrictionTimer::new();
        timer.start("d1", FrictionTier::Law);
        timer.start("d2", FrictionTier::Policy);

        let ids = timer.active_timer_ids();
        assert!(ids.contains(&"d1".to_string()));
        assert!(ids.contains(&"d2".to_string()));
    }
}
