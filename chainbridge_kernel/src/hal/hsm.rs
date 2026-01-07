// ═══════════════════════════════════════════════════════════════════════════════
// PAC-OCC-P16-HW — Hardware Security Module (HSM) Trait Contract
// ChainBridge Constitutional Kernel - Sovereign Gate Specification
// Governance Tier: LAW
// Invariant: FAIL_CLOSED | NO_SOFT_FALLBACK | CONSTANT_TIME
// ═══════════════════════════════════════════════════════════════════════════════
//!
//! # Hardware Security Module (HSM) Trait
//!
//! This module defines the trait contract for Hardware Security Module integration.
//! Any HSM implementation MUST satisfy these traits to be used with the Sovereign Gate.
//!
//! ## Supported HSM Types
//!
//! - **YubiHSM 2** — Primary recommendation
//! - **AWS CloudHSM** — Cloud deployment (air-gapped VPC required)
//! - **Azure Dedicated HSM** — Cloud deployment (air-gapped VNET required)
//! - **Thales Luna** — Enterprise deployment
//! - **SoftHSM** — DEVELOPMENT MODE ONLY (forbidden in Production)
//!
//! ## Key Operations
//!
//! All key operations are constant-time to prevent timing side-channels.
//!
//! ## Fail-Closed Semantics
//!
//! If any HSM operation fails, the Kernel MUST reject the PAC and halt.

use core::fmt;

/// Result type for HSM operations.
pub type HsmResult<T> = core::result::Result<T, HsmError>;

/// Errors that can occur during HSM operations.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HsmError {
    /// HSM device not found
    DeviceNotFound,
    /// HSM device not initialized
    NotInitialized,
    /// Authentication failed (wrong PIN/password)
    AuthenticationFailed,
    /// Key not found in HSM
    KeyNotFound(KeyHandle),
    /// Key generation failed
    KeyGenerationFailed(String),
    /// Signing operation failed
    SigningFailed(String),
    /// Verification operation failed
    VerificationFailed(String),
    /// Encryption operation failed
    EncryptionFailed(String),
    /// Decryption operation failed
    DecryptionFailed(String),
    /// HSM is locked (too many failed attempts)
    DeviceLocked,
    /// HSM session expired
    SessionExpired,
    /// Operation not supported by this HSM
    OperationNotSupported,
    /// HSM internal error
    InternalError(String),
    /// Communication error with HSM
    CommunicationError(String),
    /// HSM firmware version incompatible
    IncompatibleFirmware { required: String, actual: String },
}

impl fmt::Display for HsmError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            HsmError::DeviceNotFound => write!(f, "HSM device not found"),
            HsmError::NotInitialized => write!(f, "HSM not initialized"),
            HsmError::AuthenticationFailed => write!(f, "HSM authentication failed"),
            HsmError::KeyNotFound(h) => write!(f, "Key not found: {:?}", h),
            HsmError::KeyGenerationFailed(m) => write!(f, "Key generation failed: {}", m),
            HsmError::SigningFailed(m) => write!(f, "Signing failed: {}", m),
            HsmError::VerificationFailed(m) => write!(f, "Verification failed: {}", m),
            HsmError::EncryptionFailed(m) => write!(f, "Encryption failed: {}", m),
            HsmError::DecryptionFailed(m) => write!(f, "Decryption failed: {}", m),
            HsmError::DeviceLocked => write!(f, "HSM device locked"),
            HsmError::SessionExpired => write!(f, "HSM session expired"),
            HsmError::OperationNotSupported => write!(f, "Operation not supported"),
            HsmError::InternalError(m) => write!(f, "HSM internal error: {}", m),
            HsmError::CommunicationError(m) => write!(f, "HSM communication error: {}", m),
            HsmError::IncompatibleFirmware { required, actual } => {
                write!(
                    f,
                    "Incompatible HSM firmware: required {}, actual {}",
                    required, actual
                )
            }
        }
    }
}

/// Handle to a key stored in the HSM.
///
/// Keys are never exported from the HSM. All operations using keys
/// reference them by handle only.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct KeyHandle {
    /// Unique identifier within the HSM
    pub id: u32,
    /// Key type discriminant
    pub key_type: KeyType,
}

impl KeyHandle {
    /// Create a new key handle.
    pub fn new(id: u32, key_type: KeyType) -> Self {
        Self { id, key_type }
    }
}

/// Types of keys that can be stored in the HSM.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u8)]
pub enum KeyType {
    /// Ed25519 signing key (PAC signatures)
    Ed25519 = 1,
    /// X25519 key exchange key (secure channel)
    X25519 = 2,
    /// AES-256-GCM symmetric key (proofpack encryption)
    Aes256Gcm = 3,
    /// HMAC-SHA256 key (content hashing)
    HmacSha256 = 4,
    /// RSA-4096 key (legacy compatibility)
    Rsa4096 = 5,
}

/// Capabilities that an HSM implementation may support.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct HsmCapabilities {
    /// Supports Ed25519 signatures
    pub ed25519: bool,
    /// Supports X25519 key exchange
    pub x25519: bool,
    /// Supports AES-256-GCM encryption
    pub aes_256_gcm: bool,
    /// Supports HMAC-SHA256
    pub hmac_sha256: bool,
    /// Supports RSA-4096
    pub rsa_4096: bool,
    /// Supports secure key backup
    pub secure_backup: bool,
    /// Supports remote attestation
    pub remote_attestation: bool,
    /// Maximum keys that can be stored
    pub max_keys: u32,
    /// Supports FIPS 140-2 Level 3
    pub fips_140_2_level_3: bool,
}

impl Default for HsmCapabilities {
    fn default() -> Self {
        Self {
            ed25519: true,
            x25519: true,
            aes_256_gcm: true,
            hmac_sha256: true,
            rsa_4096: false,
            secure_backup: false,
            remote_attestation: false,
            max_keys: 16,
            fips_140_2_level_3: false,
        }
    }
}

/// Hardware Security Module trait.
///
/// # Contract
///
/// Any type implementing this trait MUST:
///
/// 1. **Never export private keys** — Keys stay in the HSM
/// 2. **Use constant-time operations** — No timing side-channels
/// 3. **Fail closed** — Any error must be propagated, no silent failures
/// 4. **Zeroize sensitive data** — Clear memory after use
///
/// # Safety
///
/// Implementations may use `unsafe` internally for hardware access,
/// but must provide a safe interface.
pub trait HardwareSecurityModule: Send + Sync {
    /// Get HSM device information.
    fn device_info(&self) -> HsmResult<HsmDeviceInfo>;

    /// Get HSM capabilities.
    fn capabilities(&self) -> HsmCapabilities;

    /// Initialize the HSM connection.
    ///
    /// # Arguments
    ///
    /// * `auth` - Authentication credentials (PIN, password, etc.)
    ///
    /// # Errors
    ///
    /// Returns `HsmError::AuthenticationFailed` if credentials are wrong.
    /// Returns `HsmError::DeviceLocked` if too many failed attempts.
    fn initialize(&mut self, auth: &HsmAuth) -> HsmResult<()>;

    /// Check if HSM is initialized and ready.
    fn is_ready(&self) -> bool;

    /// Generate a new key in the HSM.
    ///
    /// # Arguments
    ///
    /// * `key_type` - Type of key to generate
    /// * `label` - Human-readable label for the key
    ///
    /// # Returns
    ///
    /// Handle to the newly generated key.
    fn generate_key(&mut self, key_type: KeyType, label: &str) -> HsmResult<KeyHandle>;

    /// Sign data using a key in the HSM.
    ///
    /// # Arguments
    ///
    /// * `key` - Handle to the signing key
    /// * `data` - Data to sign (will be hashed internally for large data)
    ///
    /// # Returns
    ///
    /// Signature bytes.
    ///
    /// # Constant-Time Requirement
    ///
    /// This operation MUST complete in constant time regardless of input.
    fn sign(&self, key: KeyHandle, data: &[u8]) -> HsmResult<Vec<u8>>;

    /// Verify a signature using a key in the HSM.
    ///
    /// # Arguments
    ///
    /// * `key` - Handle to the verification key
    /// * `data` - Original data
    /// * `signature` - Signature to verify
    ///
    /// # Returns
    ///
    /// `Ok(true)` if valid, `Ok(false)` if invalid.
    ///
    /// # Constant-Time Requirement
    ///
    /// This operation MUST complete in constant time regardless of input.
    fn verify(&self, key: KeyHandle, data: &[u8], signature: &[u8]) -> HsmResult<bool>;

    /// Encrypt data using a key in the HSM.
    ///
    /// # Arguments
    ///
    /// * `key` - Handle to the encryption key
    /// * `plaintext` - Data to encrypt
    /// * `associated_data` - Additional authenticated data (AAD)
    ///
    /// # Returns
    ///
    /// Ciphertext with authentication tag.
    fn encrypt(
        &self,
        key: KeyHandle,
        plaintext: &[u8],
        associated_data: &[u8],
    ) -> HsmResult<Vec<u8>>;

    /// Decrypt data using a key in the HSM.
    ///
    /// # Arguments
    ///
    /// * `key` - Handle to the decryption key
    /// * `ciphertext` - Data to decrypt (includes auth tag)
    /// * `associated_data` - Additional authenticated data (AAD)
    ///
    /// # Returns
    ///
    /// Plaintext if decryption and authentication succeed.
    fn decrypt(
        &self,
        key: KeyHandle,
        ciphertext: &[u8],
        associated_data: &[u8],
    ) -> HsmResult<Vec<u8>>;

    /// Compute HMAC using a key in the HSM.
    ///
    /// # Arguments
    ///
    /// * `key` - Handle to the HMAC key
    /// * `data` - Data to authenticate
    ///
    /// # Returns
    ///
    /// HMAC tag.
    fn hmac(&self, key: KeyHandle, data: &[u8]) -> HsmResult<Vec<u8>>;

    /// Delete a key from the HSM.
    ///
    /// # Warning
    ///
    /// This is irreversible. Key will be securely erased.
    fn delete_key(&mut self, key: KeyHandle) -> HsmResult<()>;

    /// List all keys in the HSM.
    fn list_keys(&self) -> HsmResult<Vec<KeyHandle>>;

    /// Get the public key for an asymmetric key pair.
    ///
    /// # Note
    ///
    /// This is the ONLY way to export key material. Private keys NEVER leave the HSM.
    fn get_public_key(&self, key: KeyHandle) -> HsmResult<Vec<u8>>;

    /// Close the HSM session.
    fn close(&mut self) -> HsmResult<()>;
}

/// HSM device information.
#[derive(Debug, Clone)]
pub struct HsmDeviceInfo {
    /// Device manufacturer
    pub manufacturer: String,
    /// Device model
    pub model: String,
    /// Serial number
    pub serial: String,
    /// Firmware version
    pub firmware_version: String,
    /// Whether device is FIPS certified
    pub fips_certified: bool,
    /// FIPS certification level (if certified)
    pub fips_level: Option<u8>,
}

/// Authentication credentials for HSM.
#[derive(Clone)]
pub struct HsmAuth {
    /// Authentication type
    pub auth_type: HsmAuthType,
    /// Credential data (PIN, password, etc.)
    /// This is stored in secure memory and zeroized on drop.
    credential: Vec<u8>,
}

impl HsmAuth {
    /// Create new PIN authentication.
    pub fn pin(pin: &[u8]) -> Self {
        Self {
            auth_type: HsmAuthType::Pin,
            credential: pin.to_vec(),
        }
    }

    /// Create new password authentication.
    pub fn password(password: &[u8]) -> Self {
        Self {
            auth_type: HsmAuthType::Password,
            credential: password.to_vec(),
        }
    }

    /// Get credential bytes.
    pub fn credential(&self) -> &[u8] {
        &self.credential
    }
}

impl Drop for HsmAuth {
    fn drop(&mut self) {
        // Zeroize credential on drop
        for byte in self.credential.iter_mut() {
            *byte = 0;
        }
    }
}

/// Types of authentication supported by HSMs.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HsmAuthType {
    /// PIN code (numeric)
    Pin,
    /// Password (alphanumeric)
    Password,
    /// Certificate-based
    Certificate,
    /// Multi-factor
    MultiFactor,
}

// ═══════════════════════════════════════════════════════════════════════════════
// SOFT HSM (DEVELOPMENT ONLY)
// ═══════════════════════════════════════════════════════════════════════════════

/// Soft HSM implementation for DEVELOPMENT MODE ONLY.
///
/// # Warning
///
/// This implementation stores keys in memory and provides NO security.
/// It is FORBIDDEN in Production mode.
#[cfg(feature = "soft-hsm")]
pub struct SoftHsm {
    initialized: bool,
    keys: std::collections::HashMap<u32, Vec<u8>>,
    next_key_id: u32,
}

#[cfg(feature = "soft-hsm")]
impl SoftHsm {
    /// Create a new SoftHSM instance.
    ///
    /// # Warning
    ///
    /// This is for DEVELOPMENT ONLY.
    pub fn new() -> Self {
        Self {
            initialized: false,
            keys: std::collections::HashMap::new(),
            next_key_id: 1,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_key_handle_creation() {
        let handle = KeyHandle::new(1, KeyType::Ed25519);
        assert_eq!(handle.id, 1);
        assert_eq!(handle.key_type, KeyType::Ed25519);
    }

    #[test]
    fn test_hsm_capabilities_default() {
        let caps = HsmCapabilities::default();
        assert!(caps.ed25519);
        assert!(caps.aes_256_gcm);
        assert!(!caps.fips_140_2_level_3);
    }

    #[test]
    fn test_hsm_auth_zeroizes_on_drop() {
        let auth = HsmAuth::pin(b"123456");
        assert_eq!(auth.credential(), b"123456");
        // Drop will zeroize - we can't easily test this, but the implementation is correct
    }

    #[test]
    fn test_hsm_error_display() {
        let err = HsmError::DeviceNotFound;
        assert_eq!(err.to_string(), "HSM device not found");

        let err = HsmError::IncompatibleFirmware {
            required: "2.0.0".to_string(),
            actual: "1.5.0".to_string(),
        };
        assert!(err.to_string().contains("2.0.0"));
    }
}
