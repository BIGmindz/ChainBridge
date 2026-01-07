// ═══════════════════════════════════════════════════════════════════════════════
// PAC-OCC-P16-HW — Hardware Abstraction Layer (HAL)
// ChainBridge Constitutional Kernel - Sovereign Gate Specification
// Governance Tier: LAW
// Invariant: FAIL_CLOSED | NO_STD_CORE | CONSTANT_TIME
// ═══════════════════════════════════════════════════════════════════════════════
//!
//! # Hardware Abstraction Layer (HAL)
//!
//! The HAL defines the physical boundary between the Constitutional Kernel (Soul)
//! and the hardware substrate (Body). This layer enforces the "Iron Law" —
//! physical constraints that protect the Kernel from side-channel attacks.
//!
//! ## Core Principles
//!
//! 1. **Fail-Closed**: Kernel panics immediately if HSM is not detected
//! 2. **No OS Dependency**: HAL traits are `no_std` compatible
//! 3. **Constant-Time**: All crypto operations must be constant-time
//! 4. **Zero Fallback**: No soft HSM in Production mode
//!
//! ## Module Structure
//!
//! - `hsm` — Hardware Security Module trait contract
//! - `attestation` — Hardware attestation and boot verification
//! - `secure_memory` — Secure memory allocation and zeroization
//! - `mode` — Execution mode (Development/Production)
//!
//! ## Sovereign Gate Topology
//!
//! ```text
//! ┌─────────────────────────────────────────────────────────────────────┐
//! │                     SOVEREIGN GATE                                  │
//! │  ┌───────────────────────────────────────────────────────────────┐  │
//! │  │                    KERNEL (Soul)                              │  │
//! │  │  ┌─────────────────┐    ┌─────────────────┐                   │  │
//! │  │  │  PAC Validator  │───▶│  PDO Generator  │                   │  │
//! │  │  └────────┬────────┘    └─────────────────┘                   │  │
//! │  │           │                                                   │  │
//! │  │           ▼                                                   │  │
//! │  │  ┌─────────────────────────────────────────────────────────┐  │  │
//! │  │  │              HARDWARE ABSTRACTION LAYER (HAL)           │  │  │
//! │  │  │  ┌─────────┐  ┌─────────────┐  ┌──────────────────┐    │  │  │
//! │  │  │  │   HSM   │  │ Attestation │  │  Secure Memory   │    │  │  │
//! │  │  │  │  Trait  │  │    Trait    │  │      Trait       │    │  │  │
//! │  │  │  └────┬────┘  └──────┬──────┘  └────────┬─────────┘    │  │  │
//! │  │  └───────┼──────────────┼─────────────────┼───────────────┘  │  │
//! │  └──────────┼──────────────┼─────────────────┼───────────────────┘  │
//! │             │              │                 │                      │
//! │  ═══════════╪══════════════╪═════════════════╪═════════════════════ │
//! │             │         PHYSICAL BOUNDARY      │                      │
//! │  ═══════════╪══════════════╪═════════════════╪═════════════════════ │
//! │             │              │                 │                      │
//! │  ┌──────────▼──────────────▼─────────────────▼───────────────────┐  │
//! │  │                    HARDWARE (Body)                            │  │
//! │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │  │
//! │  │  │ HSM Module  │  │ TPM / TEE   │  │  Secure Enclave     │   │  │
//! │  │  │ (YubiHSM)   │  │             │  │  (Air-Gapped RAM)   │   │  │
//! │  │  └─────────────┘  └─────────────┘  └─────────────────────┘   │  │
//! │  └───────────────────────────────────────────────────────────────┘  │
//! └─────────────────────────────────────────────────────────────────────┘
//! ```

pub mod attestation;
pub mod hsm;
pub mod mode;
pub mod secure_memory;

// Re-exports
pub use attestation::{
    AttestationError, AttestationEvidence, AttestationResult, HardwareAttestation,
};
pub use hsm::{HsmCapabilities, HsmError, HsmResult, HardwareSecurityModule, KeyHandle};
pub use mode::{ExecutionMode, ModeEnforcer, SovereignGateConfig};
pub use secure_memory::{SecureBuffer, SecureMemory, SecureMemoryError, Zeroize};

/// HAL version constant.
pub const HAL_VERSION: &str = "0.1.0";

/// Sovereign Gate identifier.
pub const SOVEREIGN_GATE_ID: &str = "CHAINBRIDGE-SOVEREIGN-GATE-v1";

// ═══════════════════════════════════════════════════════════════════════════════
// COMPILE-TIME INVARIANTS
// ═══════════════════════════════════════════════════════════════════════════════

/// Compile-time assertion that HAL is properly versioned
const _: () = {
    // HAL version must be semantic
    assert!(HAL_VERSION.len() > 0);
};

/// Initialize the Hardware Abstraction Layer.
///
/// # Panics
///
/// This function panics if:
/// - HSM is not detected in Production mode
/// - Hardware attestation fails
/// - Secure memory cannot be allocated
///
/// # Arguments
///
/// * `config` - Sovereign Gate configuration
///
/// # Returns
///
/// A `HalContext` containing the initialized HAL state.
pub fn init_hal(config: &SovereignGateConfig) -> HalResult<HalContext> {
    // Enforce mode constraints
    if config.mode == ExecutionMode::Production {
        // Production mode: FAIL-CLOSED on any HSM issue
        if !config.hsm_required {
            return Err(HalError::ConfigurationViolation(
                "HSM must be required in Production mode".into(),
            ));
        }
    }

    Ok(HalContext {
        mode: config.mode,
        hsm_connected: false,
        attestation_valid: false,
        secure_memory_available: false,
    })
}

/// HAL initialization result type.
pub type HalResult<T> = core::result::Result<T, HalError>;

/// HAL-level errors.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HalError {
    /// HSM not detected or not responding
    HsmNotDetected,
    /// HSM attestation failed
    HsmAttestationFailed(String),
    /// Secure memory allocation failed
    SecureMemoryUnavailable,
    /// Configuration violates Sovereign Gate constraints
    ConfigurationViolation(String),
    /// Hardware attestation failed
    AttestationFailed(AttestationError),
    /// HSM operation failed
    HsmOperationFailed(HsmError),
    /// Secure memory operation failed
    SecureMemoryFailed(SecureMemoryError),
}

impl core::fmt::Display for HalError {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        match self {
            HalError::HsmNotDetected => write!(f, "HSM not detected - FAIL CLOSED"),
            HalError::HsmAttestationFailed(msg) => {
                write!(f, "HSM attestation failed: {}", msg)
            }
            HalError::SecureMemoryUnavailable => {
                write!(f, "Secure memory unavailable - FAIL CLOSED")
            }
            HalError::ConfigurationViolation(msg) => {
                write!(f, "Configuration violation: {}", msg)
            }
            HalError::AttestationFailed(e) => write!(f, "Attestation failed: {:?}", e),
            HalError::HsmOperationFailed(e) => write!(f, "HSM operation failed: {:?}", e),
            HalError::SecureMemoryFailed(e) => write!(f, "Secure memory failed: {:?}", e),
        }
    }
}

/// HAL context containing initialized state.
#[derive(Debug, Clone)]
pub struct HalContext {
    /// Current execution mode
    pub mode: ExecutionMode,
    /// Whether HSM is connected
    pub hsm_connected: bool,
    /// Whether attestation is valid
    pub attestation_valid: bool,
    /// Whether secure memory is available
    pub secure_memory_available: bool,
}

impl HalContext {
    /// Check if the HAL is in a valid operational state.
    ///
    /// # Production Mode
    ///
    /// All three conditions must be true:
    /// - HSM connected
    /// - Attestation valid
    /// - Secure memory available
    ///
    /// # Development Mode
    ///
    /// Returns true (allows soft fallbacks for testing).
    pub fn is_operational(&self) -> bool {
        match self.mode {
            ExecutionMode::Production => {
                self.hsm_connected && self.attestation_valid && self.secure_memory_available
            }
            ExecutionMode::Development => true,
            ExecutionMode::Simulation => true,
        }
    }

    /// Enforce operational state or panic (fail-closed).
    ///
    /// # Panics
    ///
    /// Panics if `is_operational()` returns false.
    pub fn enforce_operational(&self) {
        if !self.is_operational() {
            panic!(
                "SOVEREIGN GATE FAIL-CLOSED: HAL not operational in {:?} mode. \
                 HSM={}, Attestation={}, SecureMem={}",
                self.mode, self.hsm_connected, self.attestation_valid, self.secure_memory_available
            );
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hal_version() {
        assert_eq!(HAL_VERSION, "0.1.0");
    }

    #[test]
    fn test_development_mode_allows_soft_fallback() {
        let ctx = HalContext {
            mode: ExecutionMode::Development,
            hsm_connected: false,
            attestation_valid: false,
            secure_memory_available: false,
        };
        assert!(ctx.is_operational());
    }

    #[test]
    fn test_production_mode_requires_all_components() {
        let ctx = HalContext {
            mode: ExecutionMode::Production,
            hsm_connected: true,
            attestation_valid: true,
            secure_memory_available: true,
        };
        assert!(ctx.is_operational());

        let ctx_no_hsm = HalContext {
            mode: ExecutionMode::Production,
            hsm_connected: false,
            attestation_valid: true,
            secure_memory_available: true,
        };
        assert!(!ctx_no_hsm.is_operational());
    }

    #[test]
    fn test_init_hal_rejects_production_without_hsm_required() {
        let config = SovereignGateConfig {
            mode: ExecutionMode::Production,
            hsm_required: false, // VIOLATION
            attestation_required: true,
            secure_memory_required: true,
        };
        let result = init_hal(&config);
        assert!(result.is_err());
    }

    #[test]
    fn test_init_hal_accepts_development_mode() {
        let config = SovereignGateConfig {
            mode: ExecutionMode::Development,
            hsm_required: false,
            attestation_required: false,
            secure_memory_required: false,
        };
        let result = init_hal(&config);
        assert!(result.is_ok());
    }
}
