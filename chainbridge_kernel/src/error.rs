// ═══════════════════════════════════════════════════════════════════════════════
// PAC-OCC-P20-BOOTSTRAP — error.rs
// Constitutional Kernel: Error Types
// Governance Tier: LAW
// Invariant: BINARY_PDO_PARITY | ZERO_UNSAFE_RUST
// ═══════════════════════════════════════════════════════════════════════════════

use thiserror::Error;

/// Kernel error types for the Constitutional Kernel.
#[derive(Error, Debug)]
pub enum KernelError {
    #[error("Structural validation failed: {0}")]
    StructuralError(String),

    #[error("Governance tier violation: {0}")]
    GovernanceError(String),

    #[error("Block index mismatch at position {index}: expected {expected}, got {actual}")]
    BlockIndexError {
        index: u8,
        expected: String,
        actual: String,
    },

    #[error("Content hash verification failed: expected {expected}, got {actual}")]
    HashVerificationError { expected: String, actual: String },

    #[error("Issuer authorization failed: {0}")]
    AuthorizationError(String),

    #[error("Drift tolerance violation: {0}")]
    DriftError(String),

    #[error("Final state assertion failed: {0}")]
    FinalStateError(String),

    #[error("Cognitive friction violation: {0}")]
    CognitiveFrictionError(String),

    #[error("System time error (Fail-Closed): {message}")]
    SystemTimeError {
        message: String,
    },

    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),

    #[error("Internal kernel error: {0}")]
    InternalError(String),
}

/// Result type alias for kernel operations.
pub type KernelResult<T> = Result<T, KernelError>;

// ═══════════════════════════════════════════════════════════════════════════════
// ERROR CODES (for binary protocol compatibility)
// ═══════════════════════════════════════════════════════════════════════════════

impl KernelError {
    /// Returns a numeric error code for the error type.
    pub const fn error_code(&self) -> u32 {
        match self {
            KernelError::StructuralError(_) => 1001,
            KernelError::GovernanceError(_) => 1002,
            KernelError::BlockIndexError { .. } => 1003,
            KernelError::HashVerificationError { .. } => 1004,
            KernelError::AuthorizationError(_) => 1005,
            KernelError::DriftError(_) => 1006,
            KernelError::FinalStateError(_) => 1007,
            KernelError::CognitiveFrictionError(_) => 1008,
            KernelError::SystemTimeError { .. } => 1009,
            KernelError::SerializationError(_) => 2001,
            KernelError::InternalError(_) => 9999,
        }
    }

    /// Returns the gate associated with this error, if applicable.
    pub const fn associated_gate(&self) -> Option<&'static str> {
        match self {
            KernelError::StructuralError(_) => Some("G1_STRUCTURAL_LINT"),
            KernelError::GovernanceError(_) => Some("G2_GOVERNANCE_TIER_VALIDATION"),
            KernelError::BlockIndexError { .. } => Some("G4_BLOCK_INDEX_INTEGRITY"),
            KernelError::HashVerificationError { .. } => Some("G5_CONTENT_HASH_VERIFICATION"),
            KernelError::AuthorizationError(_) => Some("G6_ISSUER_AUTHORIZATION_CHECK"),
            KernelError::DriftError(_) => Some("G7_DRIFT_TOLERANCE_ENFORCEMENT"),
            KernelError::FinalStateError(_) => Some("G8_FINAL_STATE_ASSERTION"),
            KernelError::CognitiveFrictionError(_) => Some("G9_COGNITIVE_FRICTION"),
            KernelError::SystemTimeError { .. } => Some("G9_COGNITIVE_FRICTION"),
            _ => None,
        }
    }
}
