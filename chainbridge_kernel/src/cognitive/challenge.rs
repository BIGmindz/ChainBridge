//! # Challenge-Response Protocol (PAC-OCC-P21)
//!
//! Implements semantic challenges to verify operator attention and comprehension.
//! This prevents "rubber-stamping" by requiring active cognitive engagement.
//!
//! ## Challenge Types
//!
//! 1. **Semantic**: Requires understanding of the decision content
//! 2. **Confirmation**: Simple re-entry of key values
//! 3. **Digest**: Answer based on document summary
//! 4. **Consequence**: Acknowledge potential outcomes
//!
//! ## Constitutional Invariant CF-002
//!
//! Challenge failures MUST reject the decision. No partial credit.

use super::{CognitiveFrictionError, CognitiveFrictionResult, FrictionTier};
use std::collections::HashMap;
use std::time::{Duration, Instant};

/// Types of challenges that can be presented to operators.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ChallengeType {
    /// Semantic understanding challenge.
    /// Requires comprehension of the decision content.
    Semantic,

    /// Value confirmation challenge.
    /// Re-enter a specific value from the decision.
    Confirmation,

    /// Document digest challenge.
    /// Answer based on document summary.
    Digest,

    /// Consequence acknowledgment challenge.
    /// Acknowledge potential outcomes of the decision.
    Consequence,
}

impl ChallengeType {
    /// Get the difficulty level (1-5) for this challenge type.
    pub const fn difficulty(&self) -> u8 {
        match self {
            ChallengeType::Confirmation => 1,
            ChallengeType::Digest => 2,
            ChallengeType::Semantic => 3,
            ChallengeType::Consequence => 4,
        }
    }

    /// Get appropriate challenge type for a friction tier.
    pub fn for_tier(tier: FrictionTier) -> Self {
        match tier {
            FrictionTier::Law => ChallengeType::Consequence,
            FrictionTier::Policy => ChallengeType::Semantic,
            FrictionTier::Guidance => ChallengeType::Digest,
            FrictionTier::Operational => ChallengeType::Confirmation,
        }
    }
}

impl std::fmt::Display for ChallengeType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ChallengeType::Semantic => write!(f, "SEMANTIC"),
            ChallengeType::Confirmation => write!(f, "CONFIRMATION"),
            ChallengeType::Digest => write!(f, "DIGEST"),
            ChallengeType::Consequence => write!(f, "CONSEQUENCE"),
        }
    }
}

/// A challenge presented to the operator.
#[derive(Debug, Clone)]
pub struct Challenge {
    /// Unique identifier for this challenge
    pub id: String,

    /// Type of challenge
    pub challenge_type: ChallengeType,

    /// The question or prompt
    pub prompt: String,

    /// Expected answer (hashed for security)
    expected_hash: u64,

    /// Acceptable variations (for fuzzy matching)
    acceptable_variations: Vec<u64>,

    /// Maximum attempts allowed
    pub max_attempts: u32,

    /// Time limit for response
    pub time_limit: Duration,

    /// When the challenge was issued
    pub issued_at: Instant,

    /// Friction tier that generated this challenge
    pub tier: FrictionTier,
}

impl Challenge {
    /// Create a new challenge.
    pub fn new(
        id: String,
        challenge_type: ChallengeType,
        prompt: String,
        expected: &str,
        tier: FrictionTier,
    ) -> Self {
        Self {
            id,
            challenge_type,
            prompt,
            expected_hash: Self::hash_answer(expected),
            acceptable_variations: Vec::new(),
            max_attempts: Self::max_attempts_for_tier(tier),
            time_limit: Self::time_limit_for_tier(tier),
            issued_at: Instant::now(),
            tier,
        }
    }

    /// Add acceptable answer variations.
    pub fn with_variations(mut self, variations: &[&str]) -> Self {
        self.acceptable_variations = variations.iter().map(|v| Self::hash_answer(v)).collect();
        self
    }

    /// Check if an answer is correct.
    pub fn check_answer(&self, answer: &str) -> bool {
        let answer_hash = Self::hash_answer(answer);

        // Check exact match
        if answer_hash == self.expected_hash {
            return true;
        }

        // Check variations
        self.acceptable_variations.contains(&answer_hash)
    }

    /// Check if the challenge has expired.
    pub fn is_expired(&self) -> bool {
        self.issued_at.elapsed() > self.time_limit
    }

    /// Hash an answer for comparison.
    /// Uses a simple hash for in-memory comparison (not cryptographic).
    fn hash_answer(answer: &str) -> u64 {
        use std::hash::{Hash, Hasher};
        let normalized = answer.trim().to_lowercase();
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        normalized.hash(&mut hasher);
        hasher.finish()
    }

    /// Get max attempts for a tier.
    const fn max_attempts_for_tier(tier: FrictionTier) -> u32 {
        match tier {
            FrictionTier::Law => 2,        // Strict: only 2 tries
            FrictionTier::Policy => 3,     // Moderate: 3 tries
            FrictionTier::Guidance => 3,   // Moderate: 3 tries
            FrictionTier::Operational => 5, // Lenient: 5 tries
        }
    }

    /// Get time limit for a tier.
    const fn time_limit_for_tier(tier: FrictionTier) -> Duration {
        match tier {
            FrictionTier::Law => Duration::from_secs(120),       // 2 minutes
            FrictionTier::Policy => Duration::from_secs(90),     // 90 seconds
            FrictionTier::Guidance => Duration::from_secs(60),   // 1 minute
            FrictionTier::Operational => Duration::from_secs(30), // 30 seconds
        }
    }
}

/// Response to a challenge from the operator.
#[derive(Debug, Clone)]
pub struct ChallengeResponse {
    /// Challenge ID this responds to
    pub challenge_id: String,

    /// The operator's answer
    pub answer: String,

    /// Attempt number (1-indexed)
    pub attempt: u32,

    /// Time taken to respond
    pub response_time: Duration,
}

impl ChallengeResponse {
    /// Create a new challenge response.
    pub fn new(challenge_id: String, answer: String, attempt: u32, response_time: Duration) -> Self {
        Self {
            challenge_id,
            answer,
            attempt,
            response_time,
        }
    }
}

/// Verifies challenge responses and tracks challenge state.
#[derive(Debug)]
pub struct ChallengeVerifier {
    /// Active challenges by ID
    active_challenges: HashMap<String, Challenge>,

    /// Attempt counts by challenge ID
    attempt_counts: HashMap<String, u32>,

    /// Challenge counter for ID generation
    challenge_counter: u64,
}

impl ChallengeVerifier {
    /// Create a new challenge verifier.
    pub fn new() -> Self {
        Self {
            active_challenges: HashMap::new(),
            attempt_counts: HashMap::new(),
            challenge_counter: 0,
        }
    }

    /// Generate a new challenge for a tier.
    pub fn generate(&mut self, tier: FrictionTier) -> Challenge {
        self.challenge_counter += 1;
        let id = format!("CH-{:08X}", self.challenge_counter);
        let challenge_type = ChallengeType::for_tier(tier);

        let (prompt, expected) = self.generate_challenge_content(tier, challenge_type);

        let challenge = Challenge::new(id.clone(), challenge_type, prompt, &expected, tier);

        self.active_challenges.insert(id.clone(), challenge.clone());
        self.attempt_counts.insert(id, 0);

        challenge
    }

    /// Verify a challenge response.
    ///
    /// # Constitutional Invariant CF-002
    /// Challenge failures MUST reject the decision.
    pub fn verify(&mut self, response: &ChallengeResponse) -> CognitiveFrictionResult<bool> {
        let challenge = self
            .active_challenges
            .get(&response.challenge_id)
            .ok_or_else(|| {
                CognitiveFrictionError::InternalError(format!(
                    "Challenge {} not found",
                    response.challenge_id
                ))
            })?
            .clone();

        // Check expiration
        if challenge.is_expired() {
            self.active_challenges.remove(&response.challenge_id);
            return Err(CognitiveFrictionError::ChallengeFailure {
                challenge_id: response.challenge_id.clone(),
                attempts: response.attempt,
                max_attempts: challenge.max_attempts,
            });
        }

        // Update attempt count
        let attempts = self
            .attempt_counts
            .entry(response.challenge_id.clone())
            .or_insert(0);
        *attempts += 1;

        // Check max attempts
        if *attempts > challenge.max_attempts {
            self.active_challenges.remove(&response.challenge_id);
            return Err(CognitiveFrictionError::ChallengeFailure {
                challenge_id: response.challenge_id.clone(),
                attempts: *attempts,
                max_attempts: challenge.max_attempts,
            });
        }

        // Verify answer
        if challenge.check_answer(&response.answer) {
            // Success - remove challenge
            self.active_challenges.remove(&response.challenge_id);
            self.attempt_counts.remove(&response.challenge_id);
            Ok(true)
        } else if *attempts >= challenge.max_attempts {
            // Final attempt failed
            self.active_challenges.remove(&response.challenge_id);
            Err(CognitiveFrictionError::ChallengeFailure {
                challenge_id: response.challenge_id.clone(),
                attempts: *attempts,
                max_attempts: challenge.max_attempts,
            })
        } else {
            // More attempts available
            Ok(false)
        }
    }

    /// Check if a challenge is active.
    pub fn is_active(&self, challenge_id: &str) -> bool {
        self.active_challenges.contains_key(challenge_id)
    }

    /// Get remaining attempts for a challenge.
    pub fn remaining_attempts(&self, challenge_id: &str) -> Option<u32> {
        let challenge = self.active_challenges.get(challenge_id)?;
        let used = self.attempt_counts.get(challenge_id).copied().unwrap_or(0);
        Some(challenge.max_attempts.saturating_sub(used))
    }

    /// Clear expired challenges.
    pub fn clear_expired(&mut self) {
        let expired: Vec<String> = self
            .active_challenges
            .iter()
            .filter(|(_, c)| c.is_expired())
            .map(|(id, _)| id.clone())
            .collect();

        for id in expired {
            self.active_challenges.remove(&id);
            self.attempt_counts.remove(&id);
        }
    }

    /// Generate challenge content based on tier and type.
    fn generate_challenge_content(
        &self,
        tier: FrictionTier,
        challenge_type: ChallengeType,
    ) -> (String, String) {
        // In a real implementation, these would be dynamically generated
        // based on the actual decision content. For now, tier-appropriate templates.
        match (tier, challenge_type) {
            (FrictionTier::Law, ChallengeType::Consequence) => (
                "This is a LAW-tier decision. Type 'I ACKNOWLEDGE THE CONSEQUENCES' to proceed."
                    .to_string(),
                "I ACKNOWLEDGE THE CONSEQUENCES".to_string(),
            ),
            (FrictionTier::Policy, ChallengeType::Semantic) => (
                "This POLICY decision affects governance. Type 'POLICY UNDERSTOOD' to proceed."
                    .to_string(),
                "POLICY UNDERSTOOD".to_string(),
            ),
            (FrictionTier::Guidance, ChallengeType::Digest) => (
                "This is GUIDANCE-tier. Type 'GUIDANCE REVIEWED' to proceed.".to_string(),
                "GUIDANCE REVIEWED".to_string(),
            ),
            (FrictionTier::Operational, ChallengeType::Confirmation) => {
                ("Type 'CONFIRM' to proceed with this operational decision.".to_string(), "CONFIRM".to_string())
            }
            _ => (
                format!("Acknowledge this {} decision by typing 'PROCEED'", tier),
                "PROCEED".to_string(),
            ),
        }
    }
}

impl Default for ChallengeVerifier {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_challenge_type_difficulty() {
        assert_eq!(ChallengeType::Confirmation.difficulty(), 1);
        assert_eq!(ChallengeType::Digest.difficulty(), 2);
        assert_eq!(ChallengeType::Semantic.difficulty(), 3);
        assert_eq!(ChallengeType::Consequence.difficulty(), 4);
    }

    #[test]
    fn test_challenge_type_for_tier() {
        assert_eq!(
            ChallengeType::for_tier(FrictionTier::Law),
            ChallengeType::Consequence
        );
        assert_eq!(
            ChallengeType::for_tier(FrictionTier::Policy),
            ChallengeType::Semantic
        );
    }

    #[test]
    fn test_challenge_answer_checking() {
        let challenge = Challenge::new(
            "test-1".to_string(),
            ChallengeType::Confirmation,
            "Type CONFIRM".to_string(),
            "CONFIRM",
            FrictionTier::Operational,
        );

        assert!(challenge.check_answer("CONFIRM"));
        assert!(challenge.check_answer("confirm")); // Case insensitive
        assert!(challenge.check_answer("  CONFIRM  ")); // Whitespace tolerant
        assert!(!challenge.check_answer("DENY"));
    }

    #[test]
    fn test_challenge_with_variations() {
        let challenge = Challenge::new(
            "test-2".to_string(),
            ChallengeType::Confirmation,
            "Type YES".to_string(),
            "YES",
            FrictionTier::Operational,
        )
        .with_variations(&["Y", "YEAH", "YEP"]);

        assert!(challenge.check_answer("YES"));
        assert!(challenge.check_answer("Y"));
        assert!(challenge.check_answer("yeah"));
        assert!(!challenge.check_answer("NO"));
    }

    #[test]
    fn test_challenge_verifier_generate() {
        let mut verifier = ChallengeVerifier::new();
        let challenge = verifier.generate(FrictionTier::Law);

        assert!(challenge.id.starts_with("CH-"));
        assert_eq!(challenge.challenge_type, ChallengeType::Consequence);
        assert!(verifier.is_active(&challenge.id));
    }

    #[test]
    fn test_challenge_verifier_verify_success() {
        let mut verifier = ChallengeVerifier::new();
        let challenge = verifier.generate(FrictionTier::Law);

        let response = ChallengeResponse::new(
            challenge.id.clone(),
            "I ACKNOWLEDGE THE CONSEQUENCES".to_string(),
            1,
            Duration::from_secs(5),
        );

        let result = verifier.verify(&response);
        assert!(result.is_ok());
        assert!(result.unwrap()); // Answer correct
        assert!(!verifier.is_active(&challenge.id)); // Challenge cleared
    }

    #[test]
    fn test_challenge_verifier_verify_failure() {
        let mut verifier = ChallengeVerifier::new();
        let challenge = verifier.generate(FrictionTier::Law);
        let max_attempts = challenge.max_attempts;

        // Exhaust all attempts with wrong answers
        for attempt in 1..=max_attempts {
            let response = ChallengeResponse::new(
                challenge.id.clone(),
                "WRONG ANSWER".to_string(),
                attempt,
                Duration::from_secs(1),
            );

            let result = verifier.verify(&response);
            if attempt < max_attempts {
                // Not final attempt - returns false but no error
                assert!(result.is_ok());
                assert!(!result.unwrap());
            } else {
                // Final attempt - returns error
                assert!(matches!(
                    result,
                    Err(CognitiveFrictionError::ChallengeFailure { .. })
                ));
            }
        }
    }

    #[test]
    fn test_remaining_attempts() {
        let mut verifier = ChallengeVerifier::new();
        let challenge = verifier.generate(FrictionTier::Operational);
        let id = challenge.id.clone();

        assert_eq!(verifier.remaining_attempts(&id), Some(5));

        // Use one attempt
        let response = ChallengeResponse::new(
            id.clone(),
            "WRONG".to_string(),
            1,
            Duration::from_secs(1),
        );
        let _ = verifier.verify(&response);

        assert_eq!(verifier.remaining_attempts(&id), Some(4));
    }
}
