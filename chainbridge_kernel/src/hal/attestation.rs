// ═══════════════════════════════════════════════════════════════════════════════
// PAC-OCC-P16-HW — Hardware Attestation Traits
// ChainBridge Constitutional Kernel - Sovereign Gate Specification
// Governance Tier: LAW
// Invariant: BOOT_VERIFY | CHAIN_OF_TRUST | FAIL_CLOSED
// ═══════════════════════════════════════════════════════════════════════════════
//!
//! # Hardware Attestation Module
//!
//! This module defines traits for hardware attestation and boot verification.
//! The Sovereign Gate MUST verify the integrity of its execution environment
//! before processing any PACs.
//!
//! ## Attestation Chain
//!
//! ```text
//! ┌─────────────────────────────────────────────────────────────────────┐
//! │                     CHAIN OF TRUST                                  │
//! │                                                                     │
//! │  ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────┐  │
//! │  │  Hardware  │───▶│   Boot     │───▶│   Kernel   │───▶│  PAC   │  │
//! │  │   Root     │    │  Loader    │    │   Binary   │    │ Engine │  │
//! │  │  of Trust  │    │            │    │            │    │        │  │
//! │  └────────────┘    └────────────┘    └────────────┘    └────────┘  │
//! │       ▲                  ▲                 ▲                ▲       │
//! │       │                  │                 │                │       │
//! │  [TPM Quote]        [Measured]        [Hash Check]     [Validated] │
//! │                                                                     │
//! └─────────────────────────────────────────────────────────────────────┘
//! ```
//!
//! ## Supported Attestation Methods
//!
//! - **TPM 2.0** — Trusted Platform Module attestation
//! - **Intel SGX** — Software Guard Extensions
//! - **AMD SEV** — Secure Encrypted Virtualization
//! - **ARM TrustZone** — Secure world isolation
//! - **Apple Secure Enclave** — macOS/iOS secure coprocessor

use core::fmt;

/// Result type for attestation operations.
pub type AttestationResult<T> = core::result::Result<T, AttestationError>;

/// Errors that can occur during attestation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AttestationError {
    /// Hardware attestation not available
    NotAvailable,
    /// TPM not detected
    TpmNotFound,
    /// TPM communication failed
    TpmCommunicationFailed(String),
    /// PCR (Platform Configuration Register) mismatch
    PcrMismatch { register: u8, expected: String, actual: String },
    /// Quote verification failed
    QuoteVerificationFailed(String),
    /// Certificate chain invalid
    CertificateChainInvalid(String),
    /// Nonce mismatch (replay attack detected)
    NonceMismatch,
    /// Attestation expired
    AttestationExpired,
    /// Unknown attestation algorithm
    UnknownAlgorithm(String),
    /// Boot measurements invalid
    BootMeasurementInvalid(String),
    /// Secure boot not enabled
    SecureBootNotEnabled,
    /// Kernel not signed
    KernelNotSigned,
    /// Attestation service unreachable
    ServiceUnreachable(String),
}

impl fmt::Display for AttestationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AttestationError::NotAvailable => write!(f, "Hardware attestation not available"),
            AttestationError::TpmNotFound => write!(f, "TPM not detected"),
            AttestationError::TpmCommunicationFailed(m) => {
                write!(f, "TPM communication failed: {}", m)
            }
            AttestationError::PcrMismatch { register, expected, actual } => {
                write!(
                    f,
                    "PCR{} mismatch: expected {}, got {}",
                    register, expected, actual
                )
            }
            AttestationError::QuoteVerificationFailed(m) => {
                write!(f, "Quote verification failed: {}", m)
            }
            AttestationError::CertificateChainInvalid(m) => {
                write!(f, "Certificate chain invalid: {}", m)
            }
            AttestationError::NonceMismatch => write!(f, "Nonce mismatch (possible replay attack)"),
            AttestationError::AttestationExpired => write!(f, "Attestation expired"),
            AttestationError::UnknownAlgorithm(a) => write!(f, "Unknown algorithm: {}", a),
            AttestationError::BootMeasurementInvalid(m) => {
                write!(f, "Boot measurement invalid: {}", m)
            }
            AttestationError::SecureBootNotEnabled => write!(f, "Secure boot not enabled"),
            AttestationError::KernelNotSigned => write!(f, "Kernel not signed"),
            AttestationError::ServiceUnreachable(s) => {
                write!(f, "Attestation service unreachable: {}", s)
            }
        }
    }
}

/// Evidence generated during attestation.
#[derive(Debug, Clone)]
pub struct AttestationEvidence {
    /// Type of attestation performed
    pub attestation_type: AttestationType,
    /// Timestamp when attestation was performed (Unix epoch seconds)
    pub timestamp: u64,
    /// Nonce used to prevent replay attacks
    pub nonce: [u8; 32],
    /// Quote/evidence data
    pub quote: Vec<u8>,
    /// Signature over the quote
    pub signature: Vec<u8>,
    /// Certificate chain for verification
    pub certificate_chain: Vec<Vec<u8>>,
    /// Platform Configuration Register values
    pub pcr_values: Vec<PcrValue>,
    /// Validity period in seconds
    pub validity_seconds: u64,
}

impl AttestationEvidence {
    /// Check if attestation evidence has expired.
    pub fn is_expired(&self, current_time: u64) -> bool {
        current_time > self.timestamp + self.validity_seconds
    }
}

/// A Platform Configuration Register value.
#[derive(Debug, Clone)]
pub struct PcrValue {
    /// PCR index (0-23 for TPM 2.0)
    pub index: u8,
    /// Hash algorithm used
    pub algorithm: HashAlgorithm,
    /// The PCR value
    pub value: Vec<u8>,
}

/// Hash algorithms supported for attestation.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum HashAlgorithm {
    /// SHA-256
    Sha256 = 1,
    /// SHA-384
    Sha384 = 2,
    /// SHA-512
    Sha512 = 3,
    /// SHA3-256
    Sha3_256 = 4,
}

/// Types of hardware attestation.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum AttestationType {
    /// TPM 2.0 attestation
    Tpm2 = 1,
    /// Intel SGX attestation
    IntelSgx = 2,
    /// AMD SEV attestation
    AmdSev = 3,
    /// ARM TrustZone
    ArmTrustZone = 4,
    /// Apple Secure Enclave
    AppleSecureEnclave = 5,
    /// Software-based (DEVELOPMENT ONLY)
    Software = 255,
}

/// Hardware attestation trait.
///
/// # Contract
///
/// Implementations MUST:
/// 1. Verify the hardware root of trust
/// 2. Use fresh nonces for each attestation
/// 3. Fail closed on any verification error
/// 4. Support certificate chain validation
pub trait HardwareAttestation: Send + Sync {
    /// Get the supported attestation type.
    fn attestation_type(&self) -> AttestationType;

    /// Check if hardware attestation is available.
    fn is_available(&self) -> bool;

    /// Generate fresh attestation evidence.
    ///
    /// # Arguments
    ///
    /// * `nonce` - Fresh nonce to prevent replay attacks
    /// * `pcr_selection` - Which PCRs to include in the quote
    ///
    /// # Returns
    ///
    /// Attestation evidence that can be verified by a relying party.
    fn generate_evidence(
        &self,
        nonce: &[u8; 32],
        pcr_selection: &[u8],
    ) -> AttestationResult<AttestationEvidence>;

    /// Verify attestation evidence.
    ///
    /// # Arguments
    ///
    /// * `evidence` - Evidence to verify
    /// * `expected_nonce` - The nonce that was used in generation
    /// * `expected_pcrs` - Expected PCR values
    ///
    /// # Returns
    ///
    /// `Ok(())` if verification succeeds.
    fn verify_evidence(
        &self,
        evidence: &AttestationEvidence,
        expected_nonce: &[u8; 32],
        expected_pcrs: &[PcrValue],
    ) -> AttestationResult<()>;

    /// Get current PCR values.
    fn read_pcrs(&self, pcr_selection: &[u8]) -> AttestationResult<Vec<PcrValue>>;

    /// Extend a PCR with new measurement.
    ///
    /// # Arguments
    ///
    /// * `pcr_index` - Which PCR to extend
    /// * `data` - Data to hash and extend into PCR
    fn extend_pcr(&self, pcr_index: u8, data: &[u8]) -> AttestationResult<()>;

    /// Get the endorsement key certificate.
    fn get_ek_certificate(&self) -> AttestationResult<Vec<u8>>;

    /// Check if secure boot is enabled.
    fn is_secure_boot_enabled(&self) -> bool;
}

/// Boot stage for measurements.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum BootStage {
    /// BIOS/UEFI firmware
    Firmware = 0,
    /// Boot loader (GRUB, systemd-boot, etc.)
    BootLoader = 1,
    /// Operating system kernel
    Kernel = 2,
    /// Kernel command line parameters
    KernelParams = 3,
    /// Init system (systemd, etc.)
    InitSystem = 4,
    /// Application (ChainBridge Kernel)
    Application = 5,
}

/// Boot measurement record.
#[derive(Debug, Clone)]
pub struct BootMeasurement {
    /// Which boot stage this measurement is for
    pub stage: BootStage,
    /// PCR index where this measurement is recorded
    pub pcr_index: u8,
    /// Hash of the measured component
    pub hash: Vec<u8>,
    /// Human-readable description
    pub description: String,
    /// Timestamp of measurement
    pub timestamp: u64,
}

/// Expected boot measurements for the Sovereign Gate.
///
/// These are the "known good" values that the system must match.
#[derive(Debug, Clone)]
pub struct ExpectedBootChain {
    /// Expected firmware measurement
    pub firmware: Option<Vec<u8>>,
    /// Expected boot loader measurement
    pub boot_loader: Option<Vec<u8>>,
    /// Expected kernel measurement
    pub kernel: Vec<u8>,
    /// Expected application measurement
    pub application: Vec<u8>,
}

/// Verify the boot chain against expected measurements.
///
/// # Arguments
///
/// * `attestation` - Hardware attestation provider
/// * `expected` - Expected boot chain measurements
///
/// # Returns
///
/// `Ok(())` if all measurements match.
pub fn verify_boot_chain<A: HardwareAttestation>(
    attestation: &A,
    expected: &ExpectedBootChain,
) -> AttestationResult<()> {
    // Read current PCR values
    let pcrs = attestation.read_pcrs(&[0, 1, 2, 3, 4, 5])?;

    // Verify each stage
    for pcr in pcrs {
        let expected_value = match pcr.index {
            0 => expected.firmware.as_ref(),
            2 => Some(&expected.kernel),
            5 => Some(&expected.application),
            _ => None,
        };

        if let Some(exp) = expected_value {
            if pcr.value != *exp {
                return Err(AttestationError::PcrMismatch {
                    register: pcr.index,
                    expected: hex_encode(exp),
                    actual: hex_encode(&pcr.value),
                });
            }
        }
    }

    Ok(())
}

/// Simple hex encoding for error messages.
fn hex_encode(data: &[u8]) -> String {
    data.iter().map(|b| format!("{:02x}", b)).collect()
}

/// Null attestation for development mode.
///
/// # Warning
///
/// This provides NO security. Use only for development.
#[cfg(any(test, feature = "dev-attestation"))]
pub struct NullAttestation;

#[cfg(any(test, feature = "dev-attestation"))]
impl HardwareAttestation for NullAttestation {
    fn attestation_type(&self) -> AttestationType {
        AttestationType::Software
    }

    fn is_available(&self) -> bool {
        true
    }

    fn generate_evidence(
        &self,
        nonce: &[u8; 32],
        _pcr_selection: &[u8],
    ) -> AttestationResult<AttestationEvidence> {
        Ok(AttestationEvidence {
            attestation_type: AttestationType::Software,
            timestamp: 0,
            nonce: *nonce,
            quote: vec![0u8; 32],
            signature: vec![0u8; 64],
            certificate_chain: vec![],
            pcr_values: vec![],
            validity_seconds: 3600,
        })
    }

    fn verify_evidence(
        &self,
        evidence: &AttestationEvidence,
        expected_nonce: &[u8; 32],
        _expected_pcrs: &[PcrValue],
    ) -> AttestationResult<()> {
        if evidence.nonce != *expected_nonce {
            return Err(AttestationError::NonceMismatch);
        }
        Ok(())
    }

    fn read_pcrs(&self, pcr_selection: &[u8]) -> AttestationResult<Vec<PcrValue>> {
        Ok(pcr_selection
            .iter()
            .map(|&i| PcrValue {
                index: i,
                algorithm: HashAlgorithm::Sha256,
                value: vec![0u8; 32],
            })
            .collect())
    }

    fn extend_pcr(&self, _pcr_index: u8, _data: &[u8]) -> AttestationResult<()> {
        Ok(())
    }

    fn get_ek_certificate(&self) -> AttestationResult<Vec<u8>> {
        Ok(vec![])
    }

    fn is_secure_boot_enabled(&self) -> bool {
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_attestation_error_display() {
        let err = AttestationError::TpmNotFound;
        assert_eq!(err.to_string(), "TPM not detected");
    }

    #[test]
    fn test_pcr_mismatch_error() {
        let err = AttestationError::PcrMismatch {
            register: 0,
            expected: "abc123".to_string(),
            actual: "def456".to_string(),
        };
        assert!(err.to_string().contains("PCR0"));
    }

    #[test]
    fn test_attestation_evidence_expiry() {
        let evidence = AttestationEvidence {
            attestation_type: AttestationType::Software,
            timestamp: 1000,
            nonce: [0u8; 32],
            quote: vec![],
            signature: vec![],
            certificate_chain: vec![],
            pcr_values: vec![],
            validity_seconds: 3600,
        };

        assert!(!evidence.is_expired(2000)); // Within validity
        assert!(evidence.is_expired(5000)); // Expired
    }

    #[test]
    fn test_null_attestation_basic() {
        let attestation = NullAttestation;
        assert!(attestation.is_available());
        assert_eq!(attestation.attestation_type(), AttestationType::Software);
    }

    #[test]
    fn test_null_attestation_evidence_generation() {
        let attestation = NullAttestation;
        let nonce = [0x42u8; 32];
        let evidence = attestation.generate_evidence(&nonce, &[0, 1, 2]).unwrap();
        assert_eq!(evidence.nonce, nonce);
    }

    #[test]
    fn test_null_attestation_verification() {
        let attestation = NullAttestation;
        let nonce = [0x42u8; 32];
        let evidence = attestation.generate_evidence(&nonce, &[]).unwrap();
        
        // Verify with correct nonce
        assert!(attestation.verify_evidence(&evidence, &nonce, &[]).is_ok());
        
        // Verify with wrong nonce
        let wrong_nonce = [0x00u8; 32];
        assert!(attestation.verify_evidence(&evidence, &wrong_nonce, &[]).is_err());
    }

    #[test]
    fn test_hex_encode() {
        assert_eq!(hex_encode(&[0xde, 0xad, 0xbe, 0xef]), "deadbeef");
    }
}
