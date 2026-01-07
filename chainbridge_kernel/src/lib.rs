// ═══════════════════════════════════════════════════════════════════════════════
// PAC-OCC-P20-BOOTSTRAP + PAC-OCC-P16-HW + PAC-OCC-P21-FRICTION — lib.rs
// ChainBridge Constitutional Kernel + Sovereign Gate HAL + Cognitive Friction
// Governance Tier: LAW
// Invariant: BINARY_PDO_PARITY | ZERO_UNSAFE_RUST | FAIL_CLOSED | DWELL_TIME
// ═══════════════════════════════════════════════════════════════════════════════
//!
//! # ChainBridge Constitutional Kernel
//!
//! The Constitutional Kernel (CK) is the binary gatekeeper for PAC validation.
//! It enforces the G1-G8 pre-flight gates with ZERO drift tolerance.
//!
//! ## Architecture
//!
//! ```text
//! ┌─────────────────────────────────────────────────────────────────────┐
//! │                   CONSTITUTIONAL KERNEL                             │
//! │  ┌───────────────────────────────────────────────────────────────┐  │
//! │  │                     PAC VALIDATION                            │  │
//! │  │  • G1-G8 Pre-flight Gates                                     │  │
//! │  │  • PDO Generation                                             │  │
//! │  │  • Governance Tier Enforcement                                │  │
//! │  └───────────────────────────────────────────────────────────────┘  │
//! │                              │                                      │
//! │                              ▼                                      │
//! │  ┌───────────────────────────────────────────────────────────────┐  │
//! │  │              HARDWARE ABSTRACTION LAYER (HAL)                 │  │
//! │  │  • HSM Integration (Key Operations)                           │  │
//! │  │  • Hardware Attestation (TPM, SGX, SEV)                       │  │
//! │  │  • Secure Memory (Zeroize, Constant-Time)                     │  │
//! │  │  • Execution Mode Enforcement                                 │  │
//! │  └───────────────────────────────────────────────────────────────┘  │
//! │                              │                                      │
//! │                              ▼                                      │
//! │  ┌───────────────────────────────────────────────────────────────┐  │
//! │  │              COGNITIVE FRICTION (P21)                         │  │
//! │  │  • Dwell Time Enforcement (min 5s for LAW)                    │  │
//! │  │  • Challenge-Response Protocol                                │  │
//! │  │  • Velocity Tracking (anti-rubber-stamping)                   │  │
//! │  │  • No "Remember" shortcuts for LAW/POLICY                     │  │
//! │  └───────────────────────────────────────────────────────────────┘  │
//! └─────────────────────────────────────────────────────────────────────┘
//! ```
//!
//! ## Core Principles
//!
//! 1. **Binary Law**: Validation is deterministic. Same input → Same output.
//! 2. **Zero Drift**: LAW tier PACs must have ZERO drift tolerance.
//! 3. **Fail Closed**: Any validation failure results in rejection.
//! 4. **PDO Parity**: Every validation produces a Policy Decision Object.
//! 5. **Sovereign Gate**: Hardware security is non-negotiable in Production.
//! 6. **Cognitive Friction**: Speed is negligence. Operators must dwell.
//!
//! ## Pre-flight Gates
//!
//! | Gate | Name | Description |
//! |------|------|-------------|
//! | G1 | Structural Lint | PAC has exactly 20 blocks |
//! | G2 | Governance Tier | Valid governance tier |
//! | G3 | Constitutional Continuity | Schema version compatible |
//! | G4 | Block Index Integrity | Block indices match types |
//! | G5 | Content Hash | Hash verification (optional) |
//! | G6 | Issuer Authorization | Valid GID format |
//! | G7 | Drift Tolerance | LAW tier requires ZERO |
//! | G8 | Final State | Contains execution_blocking |
//!
//! ## Usage
//!
//! ```rust,no_run
//! use chainbridge_kernel::{ConstitutionalValidator, Pac, PdoOutcome};
//! use chainbridge_kernel::hal::{ExecutionMode, SovereignGateConfig};
//! use chainbridge_kernel::cognitive::{CognitiveGate, FrictionTier};
//!
//! // Configure Sovereign Gate
//! let config = SovereignGateConfig::production();
//!
//! // Create validator
//! let validator = ConstitutionalValidator::new("GID-00-EXEC");
//!
//! // Create cognitive gate for LAW-tier decisions
//! let mut gate = CognitiveGate::for_tier(FrictionTier::Law);
//! gate.start_review("decision-1", FrictionTier::Law);
//! // ... operator reviews for minimum 5 seconds ...
//! ```
//!

// NOTE: unsafe_code is denied by default but allowed in hal::secure_memory
// for volatile writes needed for secure zeroization
#![deny(unsafe_code)]
#![warn(missing_docs)]
#![warn(clippy::all)]

/// Cognitive Friction module for operator safety (PAC-OCC-P21).
///
/// Prevents "rubber-stamping" by enforcing dwell time, challenge-response,
/// and velocity limits on human decision-making.
pub mod cognitive;
pub mod error;
/// Friction gate for G9 cognitive friction validation.
pub mod friction;
/// Hardware Abstraction Layer for Sovereign Gate security.
///
/// Note: The `hal::secure_memory` submodule uses controlled unsafe code
/// for volatile writes to ensure memory zeroization is not optimized away.
pub mod hal;
pub mod models;
pub mod validator;

// Re-exports for convenience
pub use error::{KernelError, KernelResult};
pub use friction::AdmissionTimestamp;
pub use models::{
    Block, BlockType, GateResult, GovernanceTier, Pac, PacMetadata, Pdo, PdoOutcome,
    PreflightGate,
};
pub use validator::ConstitutionalValidator;

/// Kernel version constant.
pub const KERNEL_VERSION: &str = "0.1.0";

/// Schema version this kernel validates against.
pub const SUPPORTED_SCHEMA_PREFIX: &str = "CHAINBRIDGE_PAC_SCHEMA_v1.";

/// Number of blocks in a valid PAC.
pub const PAC_BLOCK_COUNT: usize = 20;

/// Number of pre-flight gates (G1-G9).
pub const PREFLIGHT_GATE_COUNT: usize = 9;

// ═══════════════════════════════════════════════════════════════════════════════
// COMPILE-TIME INVARIANT ASSERTIONS
// ═══════════════════════════════════════════════════════════════════════════════

const _: () = {
    // Ensure PAC block count matches BlockType variant count
    assert!(PAC_BLOCK_COUNT == 20);
    
    // Ensure pre-flight gate count matches PreflightGate variant count (G1-G9)
    assert!(PREFLIGHT_GATE_COUNT == 9);
};

/// Quick validation entry point - validates a PAC and returns the outcome.
///
/// This is a convenience function for simple validation without needing
/// to construct a validator instance.
///
/// # Arguments
///
/// * `pac` - The PAC to validate
/// * `executor_gid` - The GID of the executing agent
///
/// # Returns
///
/// A `KernelResult<Pdo>` containing the validation outcome.
pub fn validate(pac: &Pac, executor_gid: &str) -> KernelResult<Pdo> {
    let validator = ConstitutionalValidator::new(executor_gid);
    validator.validate_preflight(pac)
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;

    #[test]
    fn test_kernel_constants() {
        assert_eq!(KERNEL_VERSION, "0.1.0");
        assert_eq!(PAC_BLOCK_COUNT, 20);
        assert_eq!(PREFLIGHT_GATE_COUNT, 9);
    }

    #[test]
    fn test_block_type_completeness() {
        let all_blocks = BlockType::all();
        assert_eq!(all_blocks.len(), PAC_BLOCK_COUNT);
    }

    #[test]
    fn test_preflight_gate_completeness() {
        let all_gates = PreflightGate::all();
        assert_eq!(all_gates.len(), PREFLIGHT_GATE_COUNT);
    }

    #[test]
    fn test_validate_function_with_friction() {
        use chrono::Duration;
        
        let metadata = PacMetadata {
            pac_id: "PAC-TEST".to_string(),
            pac_version: "v1.1.0".to_string(),
            classification: "TEST".to_string(),
            governance_tier: GovernanceTier::Law,
            issuer_gid: "GID-00".to_string(),
            issuer_role: "Test".to_string(),
            issued_at: Utc::now(),
            scope: "test".to_string(),
            supersedes: None,
            drift_tolerance: "ZERO".to_string(),
            fail_closed: true,
            schema_version: "CHAINBRIDGE_PAC_SCHEMA_v1.1.0".to_string(),
        };

        let mut pac = Pac::new(metadata);
        let block_types = BlockType::all();
        
        for (i, bt) in block_types.iter().enumerate() {
            let content = if *bt == BlockType::FinalState {
                "execution_blocking: TRUE".to_string()
            } else {
                format!("Block {} content", i)
            };
            pac.blocks.push(Block::new(i as u8, *bt, content));
        }

        // Create admission timestamp 10 seconds ago (satisfies LAW tier 5s requirement)
        let admission_ts = AdmissionTimestamp::from_datetime(Utc::now() - Duration::seconds(10));
        
        let validator = ConstitutionalValidator::new("GID-00-EXEC");
        let pdo = validator.validate_preflight_with_friction(&pac, &admission_ts).unwrap();
        assert_eq!(pdo.outcome, PdoOutcome::Approved);
    }
}
