// ═══════════════════════════════════════════════════════════════════════════════
// PAC-OCC-P20-BOOTSTRAP + PAC-OCC-P21-CODE — validator.rs
// Constitutional Kernel: G1-G9 Pre-flight Validation Logic
// Governance Tier: LAW
// Invariant: BINARY_PDO_PARITY | ZERO_UNSAFE_RUST | DWELL_TIME
// ═══════════════════════════════════════════════════════════════════════════════
//!
//! # Constitutional Validator (P21 Enhanced)
//!
//! This module implements the G1-G9 pre-flight gates with cognitive friction.
//!
//! ## Gate Summary
//!
//! | Gate | Name | Description |
//! |------|------|-------------|
//! | G1 | Structural Lint | PAC has exactly 23 blocks (v2.1.4) |
//! | G2 | Governance Tier | Valid governance tier |
//! | G3 | Constitutional Continuity | Schema version compatible |
//! | G4 | Block Index Integrity | Block indices match types |
//! | G5 | Content Hash | Hash verification (optional) |
//! | G6 | Issuer Authorization | Valid GID format |
//! | G7 | Drift Tolerance | LAW tier requires ZERO |
//! | G8 | Final State | Contains execution_blocking |
//! | G9 | Cognitive Friction | Dwell time satisfied (P21) |

use chrono::Utc;
use sha2::{Digest, Sha256};

use crate::error::KernelResult;
use crate::friction::{AdmissionTimestamp, DefaultFrictionGate, FrictionGate};
use crate::models::{BlockType, GateResult, GovernanceTier, Pac, Pdo, PdoOutcome, PreflightGate};

/// The Constitutional Validator - Binary Gatekeeper for PAC admission.
///
/// This validator enforces the G1-G9 pre-flight gates with ZERO drift tolerance.
/// All decisions are deterministic and produce a PDO (Policy Decision Object).
///
/// ## P21 Enhancement: Cognitive Friction
///
/// The validator now includes G9 (Cognitive Friction) which enforces minimum
/// dwell time before a PAC can be approved. This prevents "rubber-stamping"
/// by operators who approve too quickly.
#[derive(Debug)]
pub struct ConstitutionalValidator {
    /// Executor GID for PDO attribution
    executor_gid: String,

    /// Friction gate for G9 enforcement
    friction_gate: DefaultFrictionGate,
}

impl Default for ConstitutionalValidator {
    fn default() -> Self {
        Self {
            executor_gid: String::new(),
            friction_gate: DefaultFrictionGate::new(),
        }
    }
}

impl ConstitutionalValidator {
    /// Creates a new validator with the given executor GID.
    pub fn new(executor_gid: impl Into<String>) -> Self {
        Self {
            executor_gid: executor_gid.into(),
            friction_gate: DefaultFrictionGate::new(),
        }
    }

    /// Validates a PAC through all G1-G9 pre-flight gates.
    ///
    /// This is the primary entry point for the Constitutional Kernel.
    /// Returns a PDO with the validation outcome.
    ///
    /// ## Arguments
    /// * `pac` - The PAC to validate
    /// * `admission_ts` - When the PAC was admitted for review (for G9)
    ///
    /// ## Note on G9
    /// G9 requires an admission timestamp to calculate dwell time.
    /// Use `validate_preflight_with_friction` for full G1-G9 validation.
    /// This method auto-generates a timestamp but will likely fail G9
    /// since no dwell time has elapsed.
    pub fn validate_preflight(&self, pac: &Pac) -> KernelResult<Pdo> {
        // Auto-generate admission timestamp (will likely fail G9)
        let admission_ts = AdmissionTimestamp::now();
        self.validate_preflight_with_friction(pac, &admission_ts)
    }

    /// Validates a PAC through all G1-G9 pre-flight gates with friction.
    ///
    /// This is the full validation entry point including G9 cognitive friction.
    ///
    /// ## Arguments
    /// * `pac` - The PAC to validate
    /// * `admission_ts` - When the PAC was admitted for review
    ///
    /// ## G9: Cognitive Friction
    ///
    /// The operator must have spent adequate time reviewing the PAC before
    /// this validation can pass. The required dwell time depends on the
    /// governance tier (LAW = 5s, POLICY = 3s, GUIDANCE = 2s, OPERATIONAL = 1s).
    pub fn validate_preflight_with_friction(
        &self,
        pac: &Pac,
        admission_ts: &AdmissionTimestamp,
    ) -> KernelResult<Pdo> {
        let mut gate_results = Vec::with_capacity(9);
        let mut all_passed = true;

        // G1: Structural Lint
        let g1 = self.gate_g1_structural_lint(pac);
        all_passed &= g1.passed;
        gate_results.push(g1);

        // G2: Governance Tier Validation
        let g2 = self.gate_g2_governance_tier(pac);
        all_passed &= g2.passed;
        gate_results.push(g2);

        // G3: Constitutional Continuity Check
        let g3 = self.gate_g3_constitutional_continuity(pac);
        all_passed &= g3.passed;
        gate_results.push(g3);

        // G4: Block Index Integrity
        let g4 = self.gate_g4_block_index_integrity(pac);
        all_passed &= g4.passed;
        gate_results.push(g4);

        // G5: Content Hash Verification
        let g5 = self.gate_g5_content_hash(pac);
        all_passed &= g5.passed;
        gate_results.push(g5);

        // G6: Issuer Authorization Check
        let g6 = self.gate_g6_issuer_authorization(pac);
        all_passed &= g6.passed;
        gate_results.push(g6);

        // G7: Drift Tolerance Enforcement
        let g7 = self.gate_g7_drift_tolerance(pac);
        all_passed &= g7.passed;
        gate_results.push(g7);

        // G8: Final State Assertion
        let g8 = self.gate_g8_final_state(pac);
        all_passed &= g8.passed;
        gate_results.push(g8);

        // G9: Cognitive Friction (P21)
        let g9 = self.gate_g9_cognitive_friction(pac, admission_ts)?;
        all_passed &= g9.passed;
        gate_results.push(g9);

        // Determine outcome
        let outcome = if all_passed {
            PdoOutcome::Approved
        } else {
            PdoOutcome::Rejected
        };

        // Compute decision hash
        let decision_hash = self.compute_decision_hash(pac, &gate_results);

        Ok(Pdo {
            pac_id: pac.metadata.pac_id.clone(),
            outcome,
            gate_results,
            decision_timestamp: Utc::now(),
            decision_hash,
            executor_gid: self.executor_gid.clone(),
        })
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // GATE IMPLEMENTATIONS (G1-G8: Structural/Governance)
    // ═══════════════════════════════════════════════════════════════════════════

    /// G1: Structural Lint - Validates PAC has exactly 23 blocks (v2.1.4).
    fn gate_g1_structural_lint(&self, pac: &Pac) -> GateResult {
        let passed = pac.has_complete_blocks();
        let message = if passed {
            "PAC has exactly 23 blocks (v2.1.4 schema)".to_string()
        } else {
            format!("PAC has {} blocks, expected 23 (v2.1.4)", pac.blocks.len())
        };

        GateResult {
            gate: PreflightGate::G1StructuralLint,
            passed,
            message,
            timestamp: Utc::now(),
        }
    }

    /// G2: Governance Tier Validation - Validates governance tier is recognized.
    fn gate_g2_governance_tier(&self, pac: &Pac) -> GateResult {
        let tier = &pac.metadata.governance_tier;
        let passed = matches!(
            tier,
            GovernanceTier::Law
                | GovernanceTier::Policy
                | GovernanceTier::Guidance
                | GovernanceTier::Operational
        );
        let message = format!("Governance tier '{}' validated", tier.as_str());

        GateResult {
            gate: PreflightGate::G2GovernanceTierValidation,
            passed,
            message,
            timestamp: Utc::now(),
        }
    }

    /// G3: Constitutional Continuity Check - Validates schema version.
    fn gate_g3_constitutional_continuity(&self, pac: &Pac) -> GateResult {
        let schema = &pac.metadata.schema_version;
        // Accept both v1.x and v2.x schemas for backward compatibility
        let passed = schema.starts_with("CHAINBRIDGE_PAC_SCHEMA_v1.")
            || schema.starts_with("CHAINBRIDGE_PAC_SCHEMA_v2.");
        let message = if passed {
            format!("Schema version '{}' is compatible", schema)
        } else {
            format!("Schema version '{}' is not compatible with v1.x or v2.x", schema)
        };

        GateResult {
            gate: PreflightGate::G3ConstitutionalContinuityCheck,
            passed,
            message,
            timestamp: Utc::now(),
        }
    }

    /// G4: Block Index Integrity - Validates all block indices match their types.
    fn gate_g4_block_index_integrity(&self, pac: &Pac) -> GateResult {
        let passed = pac.all_indices_valid();
        let message = if passed {
            "All block indices match their block types".to_string()
        } else {
            let mismatched: Vec<_> = pac
                .blocks
                .iter()
                .filter(|b| !b.is_index_valid())
                .map(|b| format!("Block {} has type {:?}", b.index, b.block_type))
                .collect();
            format!("Block index mismatch: {}", mismatched.join(", "))
        };

        GateResult {
            gate: PreflightGate::G4BlockIndexIntegrity,
            passed,
            message,
            timestamp: Utc::now(),
        }
    }

    /// G5: Content Hash Verification - Validates content hash if present.
    fn gate_g5_content_hash(&self, pac: &Pac) -> GateResult {
        let (passed, message) = match &pac.content_hash {
            Some(expected_hash) => {
                let computed = self.compute_content_hash(pac);
                if computed == *expected_hash {
                    (true, "Content hash verified".to_string())
                } else {
                    (
                        false,
                        format!(
                            "Content hash mismatch: expected {}, got {}",
                            expected_hash, computed
                        ),
                    )
                }
            }
            None => {
                // No hash provided - pass with warning
                (true, "No content hash provided (optional)".to_string())
            }
        };

        GateResult {
            gate: PreflightGate::G5ContentHashVerification,
            passed,
            message,
            timestamp: Utc::now(),
        }
    }

    /// G6: Issuer Authorization Check - Validates issuer GID format.
    fn gate_g6_issuer_authorization(&self, pac: &Pac) -> GateResult {
        let gid = &pac.metadata.issuer_gid;
        let passed = gid.starts_with("GID-");
        let message = if passed {
            format!("Issuer GID '{}' has valid format", gid)
        } else {
            format!("Issuer GID '{}' does not match GID-XX pattern", gid)
        };

        GateResult {
            gate: PreflightGate::G6IssuerAuthorizationCheck,
            passed,
            message,
            timestamp: Utc::now(),
        }
    }

    /// G7: Drift Tolerance Enforcement - Validates drift tolerance setting.
    fn gate_g7_drift_tolerance(&self, pac: &Pac) -> GateResult {
        let drift = &pac.metadata.drift_tolerance;
        let tier = &pac.metadata.governance_tier;

        // LAW tier must have ZERO drift tolerance
        let passed = match tier {
            GovernanceTier::Law => drift == "ZERO",
            _ => true, // Other tiers can have any drift tolerance
        };

        let message = if passed {
            format!(
                "Drift tolerance '{}' is valid for tier '{}'",
                drift,
                tier.as_str()
            )
        } else {
            format!("LAW tier requires ZERO drift tolerance, got '{}'", drift)
        };

        GateResult {
            gate: PreflightGate::G7DriftToleranceEnforcement,
            passed,
            message,
            timestamp: Utc::now(),
        }
    }

    /// G8: Final State Assertion - Validates POSITIVE_CLOSURE_AND_FINAL_STATE block content.
    fn gate_g8_final_state(&self, pac: &Pac) -> GateResult {
        // In v2.1.4, FinalState is now PositiveClosureAndFinalState at index 19
        let final_block = pac
            .blocks
            .iter()
            .find(|b| b.block_type == BlockType::PositiveClosureAndFinalState);

        let (passed, message) = match final_block {
            Some(block) => {
                // Final state must contain "execution_blocking" assertion
                let has_blocking = block.content.contains("execution_blocking");
                if has_blocking {
                    (
                        true,
                        "FINAL_STATE contains execution_blocking assertion".to_string(),
                    )
                } else {
                    (
                        false,
                        "FINAL_STATE missing execution_blocking assertion".to_string(),
                    )
                }
            }
            None => (false, "FINAL_STATE block not found".to_string()),
        };

        GateResult {
            gate: PreflightGate::G8FinalStateAssertion,
            passed,
            message,
            timestamp: Utc::now(),
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // G9: COGNITIVE FRICTION (PAC-OCC-P21)
    // ═══════════════════════════════════════════════════════════════════════════

    /// G9: Cognitive Friction - Validates dwell time for operator review.
    ///
    /// ## Constitutional Mandate
    ///
    /// Speed is negligence. The operator MUST spend adequate time reviewing
    /// before any PAC can be approved. This gate enforces:
    ///
    /// - LAW tier: 5 seconds minimum
    /// - POLICY tier: 3 seconds minimum
    /// - GUIDANCE tier: 2 seconds minimum
    /// - OPERATIONAL tier: 1 second minimum
    ///
    /// ## Fail-Closed
    ///
    /// If system time is unavailable or clock skew is detected, the kernel
    /// returns an error, effectively blocking the action.
    fn gate_g9_cognitive_friction(
        &self,
        pac: &Pac,
        admission_ts: &AdmissionTimestamp,
    ) -> KernelResult<GateResult> {
        self.friction_gate
            .gate_g9_cognitive_friction(admission_ts, &pac.metadata.governance_tier)
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // HELPER FUNCTIONS
    // ═══════════════════════════════════════════════════════════════════════════

    /// Computes SHA-256 hash of PAC content.
    fn compute_content_hash(&self, pac: &Pac) -> String {
        let mut hasher = Sha256::new();
        hasher.update(pac.metadata.pac_id.as_bytes());
        for block in &pac.blocks {
            hasher.update(block.content.as_bytes());
        }
        hex::encode(hasher.finalize())
    }

    /// Computes SHA-256 hash of the decision (for PDO integrity).
    fn compute_decision_hash(&self, pac: &Pac, gate_results: &[GateResult]) -> String {
        let mut hasher = Sha256::new();
        hasher.update(pac.metadata.pac_id.as_bytes());
        for gr in gate_results {
            hasher.update(&[gr.passed as u8]);
            hasher.update(gr.message.as_bytes());
        }
        hex::encode(hasher.finalize())
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// TESTS
// ═══════════════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{Block, PacMetadata};
    use chrono::Duration;

    /// Create a v2.1.4 compliant test PAC with 23 blocks.
    fn create_test_pac(num_blocks: usize) -> Pac {
        let metadata = PacMetadata {
            pac_id: "PAC-TEST-001".to_string(),
            pac_version: "v2.1.4".to_string(),
            classification: "TEST".to_string(),
            governance_tier: GovernanceTier::Law,
            issuer_gid: "GID-00".to_string(),
            issuer_role: "Test".to_string(),
            issued_at: Utc::now(),
            scope: "test".to_string(),
            supersedes: None,
            drift_tolerance: "ZERO".to_string(),
            fail_closed: true,
            schema_version: "CHAINBRIDGE_PAC_SCHEMA_v2.1.4".to_string(),
        };

        let mut pac = Pac::new(metadata);
        let block_types = BlockType::all();

        for i in 0..num_blocks.min(23) {
            let content = if block_types[i] == BlockType::PositiveClosureAndFinalState {
                "execution_blocking: TRUE".to_string()
            } else if block_types[i] == BlockType::BensonAnchor {
                "BENSON ACK: I am GID-00-EXEC".to_string()
            } else if block_types[i] == BlockType::AgentWrapBerHandshake {
                "WRAP/BER HANDSHAKE: EXECUTE".to_string()
            } else {
                format!("Block {} content", i)
            };
            pac.blocks.push(Block::new(i as u8, block_types[i], content));
        }

        pac
    }

    /// Create an admission timestamp from the past (simulating adequate dwell time).
    fn create_past_admission(seconds_ago: i64) -> AdmissionTimestamp {
        let past = Utc::now() - Duration::seconds(seconds_ago);
        AdmissionTimestamp::from_datetime(past)
    }

    #[test]
    fn test_valid_pac_passes_all_gates_with_dwell() {
        let validator = ConstitutionalValidator::new("GID-00-EXEC");
        let pac = create_test_pac(23); // v2.1.4: 23 blocks

        // Simulate 10 seconds of review time (exceeds LAW tier 5s requirement)
        let admission_ts = create_past_admission(10);

        let pdo = validator
            .validate_preflight_with_friction(&pac, &admission_ts)
            .unwrap();

        assert_eq!(pdo.outcome, PdoOutcome::Approved);
        assert!(pdo.all_gates_passed());

        // Verify G9 passed
        let g9 = pdo
            .gate_results
            .iter()
            .find(|gr| gr.gate == PreflightGate::G9CognitiveFriction)
            .unwrap();
        assert!(g9.passed);
    }

    #[test]
    fn test_valid_pac_fails_g9_without_dwell() {
        let validator = ConstitutionalValidator::new("GID-00-EXEC");
        let pac = create_test_pac(23); // v2.1.4: 23 blocks

        // No dwell time - admission just now
        let admission_ts = AdmissionTimestamp::now();

        let pdo = validator
            .validate_preflight_with_friction(&pac, &admission_ts)
            .unwrap();

        // Should be rejected due to G9 failure
        assert_eq!(pdo.outcome, PdoOutcome::Rejected);

        // Verify G9 failed
        let g9 = pdo
            .gate_results
            .iter()
            .find(|gr| gr.gate == PreflightGate::G9CognitiveFriction)
            .unwrap();
        assert!(!g9.passed);
        assert!(g9.message.contains("DWELL_TIME_VIOLATION"));
    }

    #[test]
    fn test_incomplete_pac_fails_g1() {
        let validator = ConstitutionalValidator::new("GID-00-EXEC");
        let pac = create_test_pac(15); // Only 15 blocks (needs 23)

        // Even with adequate dwell time, G1 should fail
        let admission_ts = create_past_admission(10);

        let pdo = validator
            .validate_preflight_with_friction(&pac, &admission_ts)
            .unwrap();

        assert_eq!(pdo.outcome, PdoOutcome::Rejected);
        let g1 = pdo
            .gate_results
            .iter()
            .find(|gr| gr.gate == PreflightGate::G1StructuralLint)
            .unwrap();
        assert!(!g1.passed);
    }

    #[test]
    fn test_law_tier_requires_zero_drift() {
        let validator = ConstitutionalValidator::new("GID-00-EXEC");
        let mut pac = create_test_pac(23); // v2.1.4: 23 blocks
        pac.metadata.drift_tolerance = "LOW".to_string(); // Invalid for LAW tier

        let admission_ts = create_past_admission(10);

        let pdo = validator
            .validate_preflight_with_friction(&pac, &admission_ts)
            .unwrap();

        assert_eq!(pdo.outcome, PdoOutcome::Rejected);
        let g7 = pdo
            .gate_results
            .iter()
            .find(|gr| gr.gate == PreflightGate::G7DriftToleranceEnforcement)
            .unwrap();
        assert!(!g7.passed);
    }

    #[test]
    fn test_operational_tier_requires_less_dwell() {
        let validator = ConstitutionalValidator::new("GID-00-EXEC");
        let mut pac = create_test_pac(23); // v2.1.4: 23 blocks
        pac.metadata.governance_tier = GovernanceTier::Operational;
        pac.metadata.drift_tolerance = "HIGH".to_string(); // OK for operational

        // Only 2 seconds - enough for OPERATIONAL (1s) but not LAW (5s)
        let admission_ts = create_past_admission(2);

        let pdo = validator
            .validate_preflight_with_friction(&pac, &admission_ts)
            .unwrap();

        // Should pass G9 since OPERATIONAL only needs 1 second
        let g9 = pdo
            .gate_results
            .iter()
            .find(|gr| gr.gate == PreflightGate::G9CognitiveFriction)
            .unwrap();
        assert!(g9.passed);
    }

    #[test]
    fn test_pdo_contains_9_gate_results() {
        let validator = ConstitutionalValidator::new("GID-00-EXEC");
        let pac = create_test_pac(23); // v2.1.4: 23 blocks
        let admission_ts = create_past_admission(10);

        let pdo = validator
            .validate_preflight_with_friction(&pac, &admission_ts)
            .unwrap();

        // Should have exactly 9 gate results (G1-G9)
        assert_eq!(pdo.gate_results.len(), 9);
    }
}
