// ═══════════════════════════════════════════════════════════════════════════════
// PAC-OCC-P23-FFI-BRIDGE — Foreign Function Interface
// Lane 2 (DEVELOPER / GID-CODY) Implementation
// Governance Tier: LAW
// Invariant: CATCH_UNWIND | FAIL_CLOSED | C_ABI_STABLE
// ═══════════════════════════════════════════════════════════════════════════════
//!
//! # FFI Bridge Module
//!
//! This module provides C-ABI compatible functions for Python integration via ctypes.
//!
//! ## Safety Contract
//!
//! All FFI functions use `catch_unwind` to prevent Rust panics from unwinding
//! across the FFI boundary. A panic returns an error code, never crashes Python.
//!
//! ## Error Codes
//!
//! | Code | Meaning |
//! |------|---------|
//! | 0 | Success |
//! | -1 | Panic caught (fail-closed) |
//! | -2 | Invalid input (null pointer) |
//! | -3 | JSON parse error |
//! | -4 | Validation failed |
//! | -5 | UTF-8 decode error |

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int};
use std::panic::catch_unwind;
use std::ptr;

use crate::models::{GovernanceTier, Pac, PacMetadata, Pdo, PdoOutcome};
use crate::validator::ConstitutionalValidator;
use crate::friction::AdmissionTimestamp;

// ═══════════════════════════════════════════════════════════════════════════════
// FFI ERROR CODES
// ═══════════════════════════════════════════════════════════════════════════════

/// Success return code.
pub const FFI_SUCCESS: c_int = 0;

/// Panic was caught - fail-closed engaged.
pub const FFI_ERR_PANIC: c_int = -1;

/// Null pointer passed to function.
pub const FFI_ERR_NULL_PTR: c_int = -2;

/// JSON parsing failed.
pub const FFI_ERR_JSON_PARSE: c_int = -3;

/// Validation rejected the PAC.
pub const FFI_ERR_VALIDATION_FAILED: c_int = -4;

/// UTF-8 decode error.
pub const FFI_ERR_UTF8: c_int = -5;

// ═══════════════════════════════════════════════════════════════════════════════
// FFI RESULT STRUCTURES
// ═══════════════════════════════════════════════════════════════════════════════

/// FFI-safe validation result.
/// 
/// Memory: The `pdo_json` pointer is heap-allocated and must be freed
/// by calling `ffi_free_string`.
#[repr(C)]
pub struct FfiValidationResult {
    /// Error code (0 = success).
    pub error_code: c_int,
    /// PDO outcome: 1 = Approved, 0 = Rejected, -1 = Error.
    pub outcome: c_int,
    /// Number of gates that passed.
    pub gates_passed: c_int,
    /// Total number of gates.
    pub gates_total: c_int,
    /// JSON string of the full PDO (caller must free with ffi_free_string).
    pub pdo_json: *mut c_char,
}

impl Default for FfiValidationResult {
    fn default() -> Self {
        Self {
            error_code: FFI_ERR_PANIC,
            outcome: -1,
            gates_passed: 0,
            gates_total: 0,
            pdo_json: ptr::null_mut(),
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// FFI FUNCTIONS - VALIDATION
// ═══════════════════════════════════════════════════════════════════════════════

/// Validates a PAC and returns the result.
///
/// # Safety
///
/// - `pac_json` must be a valid null-terminated UTF-8 string.
/// - `executor_gid` must be a valid null-terminated UTF-8 string.
/// - The returned `pdo_json` must be freed by calling `ffi_free_string`.
///
/// # Arguments
///
/// * `pac_json` - JSON string of the PAC to validate.
/// * `executor_gid` - GID of the executing agent.
/// * `admission_epoch_secs` - Unix timestamp when PAC was admitted for review.
///
/// # Returns
///
/// `FfiValidationResult` with error_code = 0 on success.
#[no_mangle]
pub extern "C" fn ffi_validate_pac(
    pac_json: *const c_char,
    executor_gid: *const c_char,
    admission_epoch_secs: i64,
) -> FfiValidationResult {
    let result = catch_unwind(|| {
        // Validate inputs
        if pac_json.is_null() || executor_gid.is_null() {
            return FfiValidationResult {
                error_code: FFI_ERR_NULL_PTR,
                ..Default::default()
            };
        }

        // Parse C strings
        let pac_str = unsafe {
            match CStr::from_ptr(pac_json).to_str() {
                Ok(s) => s,
                Err(_) => {
                    return FfiValidationResult {
                        error_code: FFI_ERR_UTF8,
                        ..Default::default()
                    };
                }
            }
        };

        let gid_str = unsafe {
            match CStr::from_ptr(executor_gid).to_str() {
                Ok(s) => s,
                Err(_) => {
                    return FfiValidationResult {
                        error_code: FFI_ERR_UTF8,
                        ..Default::default()
                    };
                }
            }
        };

        // Parse PAC from JSON
        let pac: Pac = match serde_json::from_str(pac_str) {
            Ok(p) => p,
            Err(_) => {
                return FfiValidationResult {
                    error_code: FFI_ERR_JSON_PARSE,
                    ..Default::default()
                };
            }
        };

        // Create admission timestamp from epoch
        let admission_ts = AdmissionTimestamp::from_epoch_secs(admission_epoch_secs);

        // Validate
        let validator = ConstitutionalValidator::new(gid_str);
        let pdo = match validator.validate_preflight_with_friction(&pac, &admission_ts) {
            Ok(p) => p,
            Err(_) => {
                return FfiValidationResult {
                    error_code: FFI_ERR_VALIDATION_FAILED,
                    ..Default::default()
                };
            }
        };

        // Serialize PDO to JSON
        let pdo_json_string = match serde_json::to_string(&pdo) {
            Ok(s) => s,
            Err(_) => {
                return FfiValidationResult {
                    error_code: FFI_ERR_JSON_PARSE,
                    ..Default::default()
                };
            }
        };

        // Convert to C string
        let pdo_cstring = match CString::new(pdo_json_string) {
            Ok(cs) => cs,
            Err(_) => {
                return FfiValidationResult {
                    error_code: FFI_ERR_UTF8,
                    ..Default::default()
                };
            }
        };

        // Calculate outcome
        let outcome = match pdo.outcome {
            PdoOutcome::Approved => 1,
            PdoOutcome::Rejected => 0,
            _ => -1,
        };

        let gates_passed = pdo.gate_results.iter().filter(|g| g.passed).count() as c_int;
        let gates_total = pdo.gate_results.len() as c_int;

        FfiValidationResult {
            error_code: FFI_SUCCESS,
            outcome,
            gates_passed,
            gates_total,
            pdo_json: pdo_cstring.into_raw(),
        }
    });

    result.unwrap_or_default()
}

/// Validates a PAC without friction (for testing only).
///
/// # Safety
///
/// Same as `ffi_validate_pac`.
#[no_mangle]
pub extern "C" fn ffi_validate_pac_no_friction(
    pac_json: *const c_char,
    executor_gid: *const c_char,
) -> FfiValidationResult {
    let result = catch_unwind(|| {
        if pac_json.is_null() || executor_gid.is_null() {
            return FfiValidationResult {
                error_code: FFI_ERR_NULL_PTR,
                ..Default::default()
            };
        }

        let pac_str = unsafe {
            match CStr::from_ptr(pac_json).to_str() {
                Ok(s) => s,
                Err(_) => {
                    return FfiValidationResult {
                        error_code: FFI_ERR_UTF8,
                        ..Default::default()
                    };
                }
            }
        };

        let gid_str = unsafe {
            match CStr::from_ptr(executor_gid).to_str() {
                Ok(s) => s,
                Err(_) => {
                    return FfiValidationResult {
                        error_code: FFI_ERR_UTF8,
                        ..Default::default()
                    };
                }
            }
        };

        let pac: Pac = match serde_json::from_str(pac_str) {
            Ok(p) => p,
            Err(_) => {
                return FfiValidationResult {
                    error_code: FFI_ERR_JSON_PARSE,
                    ..Default::default()
                };
            }
        };

        // Use old timestamp (10 minutes ago) to bypass friction for testing
        let admission_ts = AdmissionTimestamp::from_epoch_secs(
            chrono::Utc::now().timestamp() - 600,
        );

        let validator = ConstitutionalValidator::new(gid_str);
        let pdo = match validator.validate_preflight_with_friction(&pac, &admission_ts) {
            Ok(p) => p,
            Err(_) => {
                return FfiValidationResult {
                    error_code: FFI_ERR_VALIDATION_FAILED,
                    ..Default::default()
                };
            }
        };

        let pdo_json_string = match serde_json::to_string(&pdo) {
            Ok(s) => s,
            Err(_) => {
                return FfiValidationResult {
                    error_code: FFI_ERR_JSON_PARSE,
                    ..Default::default()
                };
            }
        };

        let pdo_cstring = match CString::new(pdo_json_string) {
            Ok(cs) => cs,
            Err(_) => {
                return FfiValidationResult {
                    error_code: FFI_ERR_UTF8,
                    ..Default::default()
                };
            }
        };

        let outcome = match pdo.outcome {
            PdoOutcome::Approved => 1,
            PdoOutcome::Rejected => 0,
            _ => -1,
        };

        let gates_passed = pdo.gate_results.iter().filter(|g| g.passed).count() as c_int;
        let gates_total = pdo.gate_results.len() as c_int;

        FfiValidationResult {
            error_code: FFI_SUCCESS,
            outcome,
            gates_passed,
            gates_total,
            pdo_json: pdo_cstring.into_raw(),
        }
    });

    result.unwrap_or_default()
}

// ═══════════════════════════════════════════════════════════════════════════════
// FFI FUNCTIONS - MEMORY MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════

/// Frees a string allocated by the FFI layer.
///
/// # Safety
///
/// - `ptr` must have been returned by an FFI function (e.g., `pdo_json`).
/// - `ptr` must not be used after this call.
/// - Calling with null is safe (no-op).
#[no_mangle]
pub extern "C" fn ffi_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        let _ = catch_unwind(|| {
            unsafe {
                drop(CString::from_raw(ptr));
            }
        });
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// FFI FUNCTIONS - VERSION & INFO
// ═══════════════════════════════════════════════════════════════════════════════

/// Returns the kernel version as a static string.
///
/// # Safety
///
/// The returned pointer is valid for the lifetime of the library.
/// Do NOT free this pointer.
#[no_mangle]
pub extern "C" fn ffi_kernel_version() -> *const c_char {
    // Static string - no allocation, no free needed
    static VERSION: &[u8] = b"2.1.3-sovereign\0";
    VERSION.as_ptr() as *const c_char
}

/// Returns the number of pre-flight gates.
#[no_mangle]
pub extern "C" fn ffi_gate_count() -> c_int {
    crate::PREFLIGHT_GATE_COUNT as c_int
}

/// Returns the current Unix timestamp (for admission time tracking).
#[no_mangle]
pub extern "C" fn ffi_current_epoch_secs() -> i64 {
    chrono::Utc::now().timestamp()
}

// ═══════════════════════════════════════════════════════════════════════════════
// TESTS
// ═══════════════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::CString;

    fn create_test_pac_json() -> CString {
        let pac_json = r#"{
            "metadata": {
                "pac_id": "PAC-TEST-FFI",
                "pac_version": "v1.0.0",
                "classification": "TEST",
                "governance_tier": "Law",
                "issuer_gid": "GID-00",
                "issuer_role": "Test",
                "issued_at": "2026-01-07T00:00:00Z",
                "scope": "FFI Test",
                "supersedes": null,
                "drift_tolerance": "ZERO",
                "fail_closed": true,
                "schema_version": "CHAINBRIDGE_PAC_SCHEMA_v1.1.0"
            },
            "blocks": [
                {"index": 0, "block_type": "Metadata", "content": "Test", "hash": null},
                {"index": 1, "block_type": "PacAdmission", "content": "Test", "hash": null},
                {"index": 2, "block_type": "RuntimeActivation", "content": "Test", "hash": null},
                {"index": 3, "block_type": "RuntimeAcknowledgment", "content": "Test", "hash": null},
                {"index": 4, "block_type": "RuntimeCollection", "content": "Test", "hash": null},
                {"index": 5, "block_type": "GovernanceModeActivation", "content": "Test", "hash": null},
                {"index": 6, "block_type": "GovernanceModeAcknowledgment", "content": "Test", "hash": null},
                {"index": 7, "block_type": "GovernanceModeCollection", "content": "Test", "hash": null},
                {"index": 8, "block_type": "AgentActivation", "content": "Test", "hash": null},
                {"index": 9, "block_type": "AgentAcknowledgment", "content": "Test", "hash": null},
                {"index": 10, "block_type": "AgentCollection", "content": "Test", "hash": null},
                {"index": 11, "block_type": "DecisionAuthorityExecutionLane", "content": "Test", "hash": null},
                {"index": 12, "block_type": "Context", "content": "Test", "hash": null},
                {"index": 13, "block_type": "GoalState", "content": "Test", "hash": null},
                {"index": 14, "block_type": "ConstraintsAndGuardrails", "content": "Test", "hash": null},
                {"index": 15, "block_type": "InvariantsEnforced", "content": "Test", "hash": null},
                {"index": 16, "block_type": "TasksAndPlan", "content": "Test", "hash": null},
                {"index": 17, "block_type": "FileAndCodeInterfacesAndContracts", "content": "Test", "hash": null},
                {"index": 18, "block_type": "SecurityThreatTestingFailure", "content": "Test", "hash": null},
                {"index": 19, "block_type": "FinalState", "content": "execution_blocking: TRUE", "hash": null}
            ],
            "content_hash": null
        }"#;
        CString::new(pac_json).unwrap()
    }

    #[test]
    fn test_ffi_kernel_version() {
        let version = ffi_kernel_version();
        assert!(!version.is_null());
        let version_str = unsafe { CStr::from_ptr(version).to_str().unwrap() };
        assert!(version_str.starts_with("2.1"));
    }

    #[test]
    fn test_ffi_gate_count() {
        let count = ffi_gate_count();
        assert_eq!(count, 9);
    }

    #[test]
    fn test_ffi_current_epoch() {
        let epoch = ffi_current_epoch_secs();
        assert!(epoch > 1700000000); // After 2023
    }

    #[test]
    fn test_ffi_validate_pac_null_input() {
        let result = ffi_validate_pac(ptr::null(), ptr::null(), 0);
        assert_eq!(result.error_code, FFI_ERR_NULL_PTR);
    }

    #[test]
    fn test_ffi_validate_pac_no_friction() {
        let pac_json = create_test_pac_json();
        let gid = CString::new("GID-00-EXEC").unwrap();

        let result = ffi_validate_pac_no_friction(pac_json.as_ptr(), gid.as_ptr());

        assert_eq!(result.error_code, FFI_SUCCESS);
        assert_eq!(result.outcome, 1); // Approved
        assert_eq!(result.gates_total, 9);
        assert!(result.gates_passed > 0);
        assert!(!result.pdo_json.is_null());

        // Free the allocated string
        ffi_free_string(result.pdo_json);
    }

    #[test]
    fn test_ffi_validate_pac_with_friction_fails_immediately() {
        let pac_json = create_test_pac_json();
        let gid = CString::new("GID-00-EXEC").unwrap();
        let now = chrono::Utc::now().timestamp();

        // No dwell time - should fail G9
        let result = ffi_validate_pac(pac_json.as_ptr(), gid.as_ptr(), now);

        assert_eq!(result.error_code, FFI_SUCCESS);
        assert_eq!(result.outcome, 0); // Rejected (G9 friction failure)
        assert!(!result.pdo_json.is_null());

        ffi_free_string(result.pdo_json);
    }

    #[test]
    fn test_ffi_validate_pac_with_adequate_dwell() {
        let pac_json = create_test_pac_json();
        let gid = CString::new("GID-00-EXEC").unwrap();
        let past = chrono::Utc::now().timestamp() - 10; // 10 seconds ago

        let result = ffi_validate_pac(pac_json.as_ptr(), gid.as_ptr(), past);

        assert_eq!(result.error_code, FFI_SUCCESS);
        assert_eq!(result.outcome, 1); // Approved (dwell satisfied)
        assert_eq!(result.gates_passed, 9);

        ffi_free_string(result.pdo_json);
    }

    #[test]
    fn test_ffi_free_string_null_safe() {
        // Should not crash
        ffi_free_string(ptr::null_mut());
    }
}
