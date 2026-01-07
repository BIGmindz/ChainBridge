// ═══════════════════════════════════════════════════════════════════════════════
// PAC-OCC-P20-BOOTSTRAP + PAC-OCC-P20-G1-SYNC — models.rs
// Constitutional Kernel: PAC Schema and Block Type Definitions (v2.1.4)
// Governance Tier: LAW
// Invariant: BINARY_PDO_PARITY | ZERO_UNSAFE_RUST
// ═══════════════════════════════════════════════════════════════════════════════

use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

/// The 23 canonical block types in a v2.1.4 PAC.
/// Order is immutable. Index must match block position.
/// v2.1.4 adds: BensonAnchor (00), TestTermination (20), AgentWrapBerHandshake (21)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[repr(u8)]
pub enum BlockType {
    /// Block 00: BENSON_EXECUTION_ACTIVATION_ACKNOWLEDGMENT_COLLECTION (Anchor)
    BensonAnchor = 0,
    Metadata = 1,
    PacAdmission = 2,
    RuntimeActivation = 3,
    RuntimeAcknowledgment = 4,
    RuntimeCollection = 5,
    GovernanceModeActivation = 6,
    GovernanceModeAcknowledgment = 7,
    GovernanceModeCollection = 8,
    AgentActivation = 9,
    AgentAcknowledgment = 10,
    AgentCollection = 11,
    DecisionAuthorityExecutionLane = 12,
    Context = 13,
    GoalState = 14,
    ConstraintsAndGuardrails = 15,
    InvariantsEnforced = 16,
    TasksAndPlan = 17,
    TrainingSignal = 18,
    PositiveClosureAndFinalState = 19,
    LedgerCommitAndAttestation = 20,
    TestTerminationEnforcement = 21,
    /// Block 22: AGENT_WRAP_BER_HANDSHAKE (Terminal)
    AgentWrapBerHandshake = 22,
}

impl BlockType {
    /// Returns the canonical block name as a string slice.
    pub const fn as_str(&self) -> &'static str {
        match self {
            BlockType::BensonAnchor => "BENSON_EXECUTION_ACTIVATION_ACKNOWLEDGMENT_COLLECTION",
            BlockType::Metadata => "METADATA",
            BlockType::PacAdmission => "PAC_ADMISSION",
            BlockType::RuntimeActivation => "RUNTIME_ACTIVATION",
            BlockType::RuntimeAcknowledgment => "RUNTIME_ACKNOWLEDGMENT",
            BlockType::RuntimeCollection => "RUNTIME_COLLECTION",
            BlockType::GovernanceModeActivation => "GOVERNANCE_MODE_ACTIVATION",
            BlockType::GovernanceModeAcknowledgment => "GOVERNANCE_MODE_ACKNOWLEDGMENT",
            BlockType::GovernanceModeCollection => "GOVERNANCE_MODE_COLLECTION",
            BlockType::AgentActivation => "AGENT_ACTIVATION",
            BlockType::AgentAcknowledgment => "AGENT_ACKNOWLEDGMENT",
            BlockType::AgentCollection => "AGENT_COLLECTION",
            BlockType::DecisionAuthorityExecutionLane => "DECISION_AUTHORITY_EXECUTION_LANE",
            BlockType::Context => "CONTEXT",
            BlockType::GoalState => "GOAL_STATE",
            BlockType::ConstraintsAndGuardrails => "CONSTRAINTS_AND_GUARDRAILS",
            BlockType::InvariantsEnforced => "INVARIANTS_ENFORCED",
            BlockType::TasksAndPlan => "TASKS_AND_PLAN",
            BlockType::TrainingSignal => "TRAINING_SIGNAL",
            BlockType::PositiveClosureAndFinalState => "POSITIVE_CLOSURE_AND_FINAL_STATE",
            BlockType::LedgerCommitAndAttestation => "LEDGER_COMMIT_AND_ATTESTATION",
            BlockType::TestTerminationEnforcement => "TEST_TERMINATION_ENFORCEMENT",
            BlockType::AgentWrapBerHandshake => "AGENT_WRAP_BER_HANDSHAKE",
        }
    }

    /// Returns all block types in canonical order (v2.1.4: 23 blocks).
    pub const fn all() -> [BlockType; 23] {
        [
            BlockType::BensonAnchor,
            BlockType::Metadata,
            BlockType::PacAdmission,
            BlockType::RuntimeActivation,
            BlockType::RuntimeAcknowledgment,
            BlockType::RuntimeCollection,
            BlockType::GovernanceModeActivation,
            BlockType::GovernanceModeAcknowledgment,
            BlockType::GovernanceModeCollection,
            BlockType::AgentActivation,
            BlockType::AgentAcknowledgment,
            BlockType::AgentCollection,
            BlockType::DecisionAuthorityExecutionLane,
            BlockType::Context,
            BlockType::GoalState,
            BlockType::ConstraintsAndGuardrails,
            BlockType::InvariantsEnforced,
            BlockType::TasksAndPlan,
            BlockType::TrainingSignal,
            BlockType::PositiveClosureAndFinalState,
            BlockType::LedgerCommitAndAttestation,
            BlockType::TestTerminationEnforcement,
            BlockType::AgentWrapBerHandshake,
        ]
    }
}

/// Governance tier classification.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum GovernanceTier {
    Law,
    Policy,
    Guidance,
    Operational,
}

impl GovernanceTier {
    pub const fn as_str(&self) -> &'static str {
        match self {
            GovernanceTier::Law => "LAW",
            GovernanceTier::Policy => "POLICY",
            GovernanceTier::Guidance => "GUIDANCE",
            GovernanceTier::Operational => "OPERATIONAL",
        }
    }
}

/// A single block within a PAC.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Block {
    pub index: u8,
    pub block_type: BlockType,
    pub content: String,
    pub hash: Option<String>,
}

impl Block {
    pub fn new(index: u8, block_type: BlockType, content: String) -> Self {
        Self {
            index,
            block_type,
            content,
            hash: None,
        }
    }

    /// Validates that the block index matches the expected block type.
    pub fn is_index_valid(&self) -> bool {
        self.index == self.block_type as u8
    }
}

/// PAC Metadata (Block 0).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PacMetadata {
    pub pac_id: String,
    pub pac_version: String,
    pub classification: String,
    pub governance_tier: GovernanceTier,
    pub issuer_gid: String,
    pub issuer_role: String,
    pub issued_at: DateTime<Utc>,
    pub scope: String,
    pub supersedes: Option<String>,
    pub drift_tolerance: String,
    pub fail_closed: bool,
    pub schema_version: String,
}

/// The complete 23-block PAC structure (v2.1.4 schema).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Pac {
    pub metadata: PacMetadata,
    pub blocks: Vec<Block>,
    pub content_hash: Option<String>,
}

impl Pac {
    /// Creates a new PAC with the given metadata.
    pub fn new(metadata: PacMetadata) -> Self {
        Self {
            metadata,
            blocks: Vec::with_capacity(23),
            content_hash: None,
        }
    }

    /// Returns true if the PAC has exactly 23 blocks (v2.1.4 schema).
    pub fn has_complete_blocks(&self) -> bool {
        self.blocks.len() == 23
    }

    /// Returns true if all block indices are valid.
    pub fn all_indices_valid(&self) -> bool {
        self.blocks.iter().all(|b| b.is_index_valid())
    }
}

/// PDO Outcome - The result of a validation decision.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PdoOutcome {
    Approved,
    Rejected,
    RequiresReview,
    Error,
}

impl PdoOutcome {
    pub const fn as_str(&self) -> &'static str {
        match self {
            PdoOutcome::Approved => "APPROVED",
            PdoOutcome::Rejected => "REJECTED",
            PdoOutcome::RequiresReview => "REQUIRES_REVIEW",
            PdoOutcome::Error => "ERROR",
        }
    }
}

/// Pre-flight gate identifiers (G1-G9).
/// G9 (Cognitive Friction) added in PAC-OCC-P21.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[repr(u8)]
pub enum PreflightGate {
    G1StructuralLint = 1,
    G2GovernanceTierValidation = 2,
    G3ConstitutionalContinuityCheck = 3,
    G4BlockIndexIntegrity = 4,
    G5ContentHashVerification = 5,
    G6IssuerAuthorizationCheck = 6,
    G7DriftToleranceEnforcement = 7,
    G8FinalStateAssertion = 8,
    G9CognitiveFriction = 9,
}

impl PreflightGate {
    pub const fn as_str(&self) -> &'static str {
        match self {
            PreflightGate::G1StructuralLint => "G1_STRUCTURAL_LINT",
            PreflightGate::G2GovernanceTierValidation => "G2_GOVERNANCE_TIER_VALIDATION",
            PreflightGate::G3ConstitutionalContinuityCheck => "G3_CONSTITUTIONAL_CONTINUITY_CHECK",
            PreflightGate::G4BlockIndexIntegrity => "G4_BLOCK_INDEX_INTEGRITY",
            PreflightGate::G5ContentHashVerification => "G5_CONTENT_HASH_VERIFICATION",
            PreflightGate::G6IssuerAuthorizationCheck => "G6_ISSUER_AUTHORIZATION_CHECK",
            PreflightGate::G7DriftToleranceEnforcement => "G7_DRIFT_TOLERANCE_ENFORCEMENT",
            PreflightGate::G8FinalStateAssertion => "G8_FINAL_STATE_ASSERTION",
            PreflightGate::G9CognitiveFriction => "G9_COGNITIVE_FRICTION",
        }
    }

    /// Returns all gates in order (G1-G9).
    pub const fn all() -> [PreflightGate; 9] {
        [
            PreflightGate::G1StructuralLint,
            PreflightGate::G2GovernanceTierValidation,
            PreflightGate::G3ConstitutionalContinuityCheck,
            PreflightGate::G4BlockIndexIntegrity,
            PreflightGate::G5ContentHashVerification,
            PreflightGate::G6IssuerAuthorizationCheck,
            PreflightGate::G7DriftToleranceEnforcement,
            PreflightGate::G8FinalStateAssertion,
            PreflightGate::G9CognitiveFriction,
        ]
    }
}

/// A single gate result within a PDO.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GateResult {
    pub gate: PreflightGate,
    pub passed: bool,
    pub message: String,
    pub timestamp: DateTime<Utc>,
}

/// The Policy Decision Object (PDO) - The atomic unit of governance output.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Pdo {
    pub pac_id: String,
    pub outcome: PdoOutcome,
    pub gate_results: Vec<GateResult>,
    pub decision_timestamp: DateTime<Utc>,
    pub decision_hash: String,
    pub executor_gid: String,
}

impl Pdo {
    /// Returns true if all gates passed.
    pub fn all_gates_passed(&self) -> bool {
        self.gate_results.iter().all(|gr| gr.passed)
    }

    /// Returns the first failed gate, if any.
    pub fn first_failure(&self) -> Option<&GateResult> {
        self.gate_results.iter().find(|gr| !gr.passed)
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPILE-TIME ASSERTIONS
// ═══════════════════════════════════════════════════════════════════════════════

const _: () = {
    // Ensure BlockType has exactly 23 variants matching indices 0-22 (v2.1.4)
    assert!(BlockType::BensonAnchor as u8 == 0);
    assert!(BlockType::AgentWrapBerHandshake as u8 == 22);
    
    // Ensure PreflightGate has exactly 9 variants matching indices 1-9
    assert!(PreflightGate::G1StructuralLint as u8 == 1);
    assert!(PreflightGate::G9CognitiveFriction as u8 == 9);
};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_block_type_indices() {
        let all_blocks = BlockType::all();
        for (i, block_type) in all_blocks.iter().enumerate() {
            assert_eq!(*block_type as u8, i as u8);
        }
    }

    #[test]
    fn test_block_type_count() {
        assert_eq!(BlockType::all().len(), 23); // v2.1.4: Blocks 00-22
    }

    #[test]
    fn test_preflight_gate_count() {
        assert_eq!(PreflightGate::all().len(), 9);
    }

    #[test]
    fn test_block_index_validation() {
        // BensonAnchor is at index 0 in v2.1.4 schema
        let valid_block = Block::new(0, BlockType::BensonAnchor, "BENSON ACK".to_string());
        assert!(valid_block.is_index_valid());

        // Metadata is now at index 1
        let valid_metadata = Block::new(1, BlockType::Metadata, "test".to_string());
        assert!(valid_metadata.is_index_valid());

        let invalid_block = Block {
            index: 5,
            block_type: BlockType::Metadata, // Metadata is index 1, not 5
            content: "test".to_string(),
            hash: None,
        };
        assert!(!invalid_block.is_index_valid());
    }
}
