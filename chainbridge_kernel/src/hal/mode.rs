// ═══════════════════════════════════════════════════════════════════════════════
// PAC-OCC-P16-HW — Execution Mode Configuration
// ChainBridge Constitutional Kernel - Sovereign Gate Specification
// Governance Tier: LAW
// Invariant: MODE_ENFORCEMENT | NO_PRODUCTION_BYPASS
// ═══════════════════════════════════════════════════════════════════════════════
//!
//! # Execution Mode Module
//!
//! This module defines execution modes and configuration for the Sovereign Gate.
//! Different modes have different security requirements.
//!
//! ## Mode Hierarchy
//!
//! ```text
//! ┌─────────────────────────────────────────────────────────────────────────┐
//! │                        EXECUTION MODES                                  │
//! │                                                                         │
//! │  ┌─────────────────────────────────────────────────────────────────┐   │
//! │  │                     PRODUCTION                                   │   │
//! │  │  • HSM REQUIRED (no fallback)                                   │   │
//! │  │  • Attestation REQUIRED                                         │   │
//! │  │  • Secure Memory REQUIRED                                       │   │
//! │  │  • Air-Gap REQUIRED                                             │   │
//! │  │  • FAIL-CLOSED on any error                                     │   │
//! │  └─────────────────────────────────────────────────────────────────┘   │
//! │                              ▲                                          │
//! │                              │ (upgrade path)                           │
//! │                              │                                          │
//! │  ┌─────────────────────────────────────────────────────────────────┐   │
//! │  │                     SIMULATION                                   │   │
//! │  │  • HSM may be simulated                                         │   │
//! │  │  • Attestation REQUIRED (may be software)                       │   │
//! │  │  • Secure Memory REQUIRED                                       │   │
//! │  │  • Air-Gap OPTIONAL                                             │   │
//! │  │  • FAIL-CLOSED on security errors                               │   │
//! │  └─────────────────────────────────────────────────────────────────┘   │
//! │                              ▲                                          │
//! │                              │ (upgrade path)                           │
//! │                              │                                          │
//! │  ┌─────────────────────────────────────────────────────────────────┐   │
//! │  │                     DEVELOPMENT                                  │   │
//! │  │  • HSM OPTIONAL (soft fallback allowed)                         │   │
//! │  │  • Attestation OPTIONAL                                         │   │
//! │  │  • Secure Memory OPTIONAL                                       │   │
//! │  │  • Network ALLOWED                                              │   │
//! │  │  • FAIL-OPEN for testing                                        │   │
//! │  └─────────────────────────────────────────────────────────────────┘   │
//! │                                                                         │
//! └─────────────────────────────────────────────────────────────────────────┘
//! ```

use core::fmt;

/// Execution mode for the Sovereign Gate.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u8)]
pub enum ExecutionMode {
    /// Development mode - all security features optional.
    ///
    /// Use this mode for:
    /// - Local development
    /// - Unit testing
    /// - CI/CD pipelines
    ///
    /// **WARNING**: Never use in production!
    Development = 0,

    /// Simulation mode - simulated security features.
    ///
    /// Use this mode for:
    /// - Integration testing
    /// - Security audits
    /// - Staging environments
    ///
    /// Requires software implementations of HSM and attestation.
    Simulation = 1,

    /// Production mode - full security enforcement.
    ///
    /// Requirements:
    /// - Real HSM device connected
    /// - Hardware attestation passing
    /// - Secure memory locked
    /// - Air-gapped network
    ///
    /// **FAIL-CLOSED**: Any security violation causes immediate halt.
    Production = 2,
}

impl ExecutionMode {
    /// Check if this is a secure mode (Simulation or Production).
    pub fn is_secure(&self) -> bool {
        matches!(self, ExecutionMode::Simulation | ExecutionMode::Production)
    }

    /// Check if HSM fallback is allowed.
    pub fn allows_hsm_fallback(&self) -> bool {
        matches!(self, ExecutionMode::Development)
    }

    /// Check if network access is allowed.
    pub fn allows_network(&self) -> bool {
        matches!(self, ExecutionMode::Development)
    }

    /// Get the mode from environment variable.
    ///
    /// # Environment Variable
    ///
    /// `CHAINBRIDGE_MODE` can be set to:
    /// - `development` or `dev`
    /// - `simulation` or `sim`
    /// - `production` or `prod`
    ///
    /// Defaults to `Development` if not set.
    #[cfg(feature = "std")]
    pub fn from_env() -> Self {
        match std::env::var("CHAINBRIDGE_MODE")
            .unwrap_or_default()
            .to_lowercase()
            .as_str()
        {
            "production" | "prod" => ExecutionMode::Production,
            "simulation" | "sim" => ExecutionMode::Simulation,
            _ => ExecutionMode::Development,
        }
    }
}

impl fmt::Display for ExecutionMode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ExecutionMode::Development => write!(f, "DEVELOPMENT"),
            ExecutionMode::Simulation => write!(f, "SIMULATION"),
            ExecutionMode::Production => write!(f, "PRODUCTION"),
        }
    }
}

impl Default for ExecutionMode {
    fn default() -> Self {
        ExecutionMode::Development
    }
}

/// Configuration for the Sovereign Gate.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SovereignGateConfig {
    /// Execution mode
    pub mode: ExecutionMode,
    /// Whether HSM is required
    pub hsm_required: bool,
    /// Whether attestation is required
    pub attestation_required: bool,
    /// Whether secure memory is required
    pub secure_memory_required: bool,
}

impl SovereignGateConfig {
    /// Create a new configuration for the given mode.
    ///
    /// This automatically sets the appropriate security requirements
    /// based on the mode.
    pub fn new(mode: ExecutionMode) -> Self {
        match mode {
            ExecutionMode::Development => Self {
                mode,
                hsm_required: false,
                attestation_required: false,
                secure_memory_required: false,
            },
            ExecutionMode::Simulation => Self {
                mode,
                hsm_required: true, // Simulated HSM required
                attestation_required: true, // Software attestation
                secure_memory_required: true,
            },
            ExecutionMode::Production => Self {
                mode,
                hsm_required: true, // Real HSM required
                attestation_required: true, // Hardware attestation
                secure_memory_required: true,
            },
        }
    }

    /// Create a development configuration.
    pub fn development() -> Self {
        Self::new(ExecutionMode::Development)
    }

    /// Create a simulation configuration.
    pub fn simulation() -> Self {
        Self::new(ExecutionMode::Simulation)
    }

    /// Create a production configuration.
    pub fn production() -> Self {
        Self::new(ExecutionMode::Production)
    }

    /// Validate the configuration.
    ///
    /// # Errors
    ///
    /// Returns an error if:
    /// - Production mode without HSM requirement
    /// - Simulation mode without attestation requirement
    pub fn validate(&self) -> Result<(), ConfigValidationError> {
        if self.mode == ExecutionMode::Production && !self.hsm_required {
            return Err(ConfigValidationError::ProductionRequiresHsm);
        }

        if self.mode == ExecutionMode::Production && !self.attestation_required {
            return Err(ConfigValidationError::ProductionRequiresAttestation);
        }

        if self.mode == ExecutionMode::Production && !self.secure_memory_required {
            return Err(ConfigValidationError::ProductionRequiresSecureMemory);
        }

        Ok(())
    }
}

impl Default for SovereignGateConfig {
    fn default() -> Self {
        Self::development()
    }
}

/// Configuration validation errors.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ConfigValidationError {
    /// Production mode requires HSM
    ProductionRequiresHsm,
    /// Production mode requires attestation
    ProductionRequiresAttestation,
    /// Production mode requires secure memory
    ProductionRequiresSecureMemory,
    /// Invalid mode transition
    InvalidModeTransition { from: ExecutionMode, to: ExecutionMode },
}

impl fmt::Display for ConfigValidationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ConfigValidationError::ProductionRequiresHsm => {
                write!(f, "Production mode requires HSM to be enabled")
            }
            ConfigValidationError::ProductionRequiresAttestation => {
                write!(f, "Production mode requires attestation to be enabled")
            }
            ConfigValidationError::ProductionRequiresSecureMemory => {
                write!(f, "Production mode requires secure memory to be enabled")
            }
            ConfigValidationError::InvalidModeTransition { from, to } => {
                write!(f, "Invalid mode transition from {} to {}", from, to)
            }
        }
    }
}

/// Mode enforcer that ensures mode constraints are respected.
pub struct ModeEnforcer {
    config: SovereignGateConfig,
}

impl ModeEnforcer {
    /// Create a new mode enforcer.
    pub fn new(config: SovereignGateConfig) -> Result<Self, ConfigValidationError> {
        config.validate()?;
        Ok(Self { config })
    }

    /// Get the current execution mode.
    pub fn mode(&self) -> ExecutionMode {
        self.config.mode
    }

    /// Check if an action is allowed.
    pub fn is_allowed(&self, action: &SecurityAction) -> bool {
        match action {
            SecurityAction::HsmFallback => self.config.mode.allows_hsm_fallback(),
            SecurityAction::NetworkAccess => self.config.mode.allows_network(),
            SecurityAction::SkipAttestation => !self.config.attestation_required,
            SecurityAction::UseInsecureMemory => !self.config.secure_memory_required,
        }
    }

    /// Enforce that an action is allowed, or panic.
    ///
    /// # Panics
    ///
    /// Panics if the action is not allowed in the current mode.
    pub fn enforce(&self, action: &SecurityAction) {
        if !self.is_allowed(action) {
            panic!(
                "SOVEREIGN GATE VIOLATION: {:?} not allowed in {} mode",
                action, self.config.mode
            );
        }
    }

    /// Get the configuration.
    pub fn config(&self) -> &SovereignGateConfig {
        &self.config
    }
}

/// Actions that may be restricted based on mode.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SecurityAction {
    /// Use software HSM fallback
    HsmFallback,
    /// Access network
    NetworkAccess,
    /// Skip attestation
    SkipAttestation,
    /// Use non-secure memory
    UseInsecureMemory,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_development_mode_allows_fallback() {
        assert!(ExecutionMode::Development.allows_hsm_fallback());
        assert!(!ExecutionMode::Production.allows_hsm_fallback());
    }

    #[test]
    fn test_production_mode_is_secure() {
        assert!(!ExecutionMode::Development.is_secure());
        assert!(ExecutionMode::Simulation.is_secure());
        assert!(ExecutionMode::Production.is_secure());
    }

    #[test]
    fn test_config_validation_production() {
        let config = SovereignGateConfig::production();
        assert!(config.validate().is_ok());

        // Production without HSM should fail
        let invalid = SovereignGateConfig {
            mode: ExecutionMode::Production,
            hsm_required: false,
            attestation_required: true,
            secure_memory_required: true,
        };
        assert!(matches!(
            invalid.validate(),
            Err(ConfigValidationError::ProductionRequiresHsm)
        ));
    }

    #[test]
    fn test_mode_enforcer() {
        let config = SovereignGateConfig::production();
        let enforcer = ModeEnforcer::new(config).unwrap();

        assert!(!enforcer.is_allowed(&SecurityAction::HsmFallback));
        assert!(!enforcer.is_allowed(&SecurityAction::NetworkAccess));
    }

    #[test]
    fn test_development_config() {
        let config = SovereignGateConfig::development();
        assert_eq!(config.mode, ExecutionMode::Development);
        assert!(!config.hsm_required);
    }

    #[test]
    fn test_mode_display() {
        assert_eq!(format!("{}", ExecutionMode::Production), "PRODUCTION");
        assert_eq!(format!("{}", ExecutionMode::Development), "DEVELOPMENT");
    }
}
