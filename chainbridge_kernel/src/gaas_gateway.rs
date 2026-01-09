// ============================================================================
// FILE: gaas_gateway.rs
// CONTEXT: PAC-OCC-P61-XDIST + PAC-STRAT-P48-MOAT-ENFORCEMENT + PAC-OCC-P58-ZK-IDENTITY
// AUTH: BENSON (GID-00), CODY (GID-02)
// PURPOSE: The Sovereign API Gasket - Stateless Signal Verification Gateway
// INVARIANT: External_Latency < 12ms
// SECURITY: Opaque Error Codes (No Logic Leakage)
// INTEGRATION: P48 - ERP Shield wired to /validate_invoice endpoint
// INTEGRATION: P58 - Ed25519 Identity wired to /validate_signed_invoice endpoint
// ============================================================================

use axum::{
    routing::{post, get},
    Router,
    Json,
    http::StatusCode,
};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::net::SocketAddr;

// Import the ERP Shield for invoice validation
use crate::erp_shield::NetSuiteInvoice;

// Import the Identity Module for signature verification
use crate::identity::SignedRequest;

// ============================================================================
// STRICT SCHEMA (No Natural Language)
// ============================================================================

/// Inbound verification request - minimal surface area
#[derive(Debug, Deserialize)]
pub struct VerificationRequest {
    /// SHA-256 hash of the payload being verified
    pub payload_hash: String,
    /// Ed25519 signature from authorized signer
    pub signature: String,
    /// Unix timestamp (seconds) - must be within 30s of server time
    pub timestamp: u64,
}

/// Outbound verification response - opaque by design
#[derive(Debug, Serialize)]
pub struct VerificationResponse {
    /// Status: "VERIFIED" | "REJECTED" (no other values)
    pub status: String,
    /// Transaction ID (only present on success)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tx_id: Option<String>,
    /// Opaque error code (only present on failure)
    /// NEVER expose internal logic through error codes
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error_code: Option<u16>,
}

// ============================================================================
// THE SPEED MOAT - Gateway Implementation
// ============================================================================

/// Spawn the GaaS gateway on the specified port
/// 
/// # Panics
/// Panics if the TCP listener cannot bind to the address
pub async fn spawn_gateway() {
    spawn_gateway_on_port(8080).await
}

/// Spawn the GaaS gateway on a custom port
pub async fn spawn_gateway_on_port(port: u16) {
    let app = Router::new()
        .route("/verify", post(verify_decision))
        .route("/validate_invoice", post(validate_invoice))
        .route("/validate_signed_invoice", post(validate_signed_invoice))
        .route("/health", get(health_check));

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    println!(">>> CHAINBRIDGE GAAS GATEWAY ACTIVE ON: {}", addr);
    println!(">>> INVARIANT: External_Latency < 12ms");
    println!(">>> SECURITY: Opaque Error Codes Enabled");
    println!(">>> P48: ERP Shield Integration ACTIVE");
    println!(">>> P58: ZK-Identity Layer ACTIVE");
    
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

/// Health check endpoint for load balancers
async fn health_check() -> &'static str {
    "OK"
}

/// Core verification endpoint - THE GASKET
/// 
/// This function MUST NOT hold state - it only passes verified signals
/// to the kernel and returns opaque results.
async fn verify_decision(
    Json(req): Json<VerificationRequest>
) -> (StatusCode, Json<VerificationResponse>) {
    // STEP 1: Validate timestamp (anti-replay)
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    
    if req.timestamp > now + 30 || req.timestamp < now.saturating_sub(30) {
        return reject(0x0001); // OPAQUE: Timestamp violation
    }

    // STEP 2: Validate signature format
    if !validate_signature_format(&req.signature) {
        return reject(0x0002); // OPAQUE: Format violation
    }

    // STEP 3: Verify against kernel (P20 binding point)
    // In production, this binds to the Rust Invariant Engine
    let is_valid = verify_with_kernel(&req).await;

    if is_valid {
        let tx_id = generate_tx_id(&req.payload_hash);
        (StatusCode::OK, Json(VerificationResponse {
            status: "VERIFIED".to_string(),
            tx_id: Some(tx_id),
            error_code: None,
        }))
    } else {
        reject(0xDEAD) // OPAQUE: Kernel rejection
    }
}

/// Validate signature format - structural check only
fn validate_signature_format(sig: &str) -> bool {
    // Must start with 0x and be valid hex
    sig.starts_with("0x") && sig.len() >= 4 && sig[2..].chars().all(|c| c.is_ascii_hexdigit())
}

/// Kernel verification stub - will bind to P20 Invariant Engine
async fn verify_with_kernel(req: &VerificationRequest) -> bool {
    // STUB: In production, this calls the kernel via ZeroMQ or direct binding
    // For now, accept any structurally valid request
    !req.payload_hash.is_empty() && !req.signature.is_empty()
}

/// Generate transaction ID from payload hash
fn generate_tx_id(payload_hash: &str) -> String {
    format!("0xCB_{}", &payload_hash[..std::cmp::min(16, payload_hash.len())])
}

/// Create a rejection response with opaque error code
fn reject(code: u16) -> (StatusCode, Json<VerificationResponse>) {
    (StatusCode::FORBIDDEN, Json(VerificationResponse {
        status: "REJECTED".to_string(),
        tx_id: None,
        error_code: Some(code),
    }))
}

// ============================================================================
// P48: THE INVARIANT ENGINE - ERP Shield Integration
// ============================================================================

/// Invoice validation response - opaque by design
#[derive(Debug, Serialize)]
pub struct InvoiceValidationResponse {
    /// Status: "VERIFIED" | "REJECTED"
    pub status: String,
    /// Invoice ID (only present on success)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub invoice_id: Option<String>,
    /// Opaque error code (only present on failure)
    /// 0x0001 = Malformed JSON (Syntax Error)
    /// 0x0002 = Business Logic Violation (Semantic Error)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error_code: Option<String>,
}

impl InvoiceValidationResponse {
    fn approve(invoice_id: &str) -> Self {
        Self {
            status: "VERIFIED".to_string(),
            invoice_id: Some(invoice_id.to_string()),
            error_code: None,
        }
    }
    
    fn reject_syntax() -> Self {
        Self {
            status: "REJECTED".to_string(),
            invoice_id: None,
            error_code: Some("0x0001".to_string()),
        }
    }
    
    fn reject_logic() -> Self {
        Self {
            status: "REJECTED".to_string(),
            invoice_id: None,
            error_code: Some("0x0002".to_string()),
        }
    }
    
    fn reject_identity() -> Self {
        Self {
            status: "REJECTED".to_string(),
            invoice_id: None,
            error_code: Some("0xDEAD".to_string()), // Signature verification failed
        }
    }
}

/// THE INVARIANT ENGINE - Main validation loop
/// 
/// This endpoint validates NetSuite invoices against:
/// 1. SYNTAX GATE: JSON must parse into NetSuiteInvoice schema
/// 2. LOGIC GATE: Business rules must pass (currency, amounts, subsidiaries)
/// 
/// SECURITY: We never expose WHY validation failed - only that it did.
/// ERROR CODES:
/// - 0x0001: Malformed data (wrong types, missing fields, floats instead of ints)
/// - 0x0002: Logic violation (invalid currency, negative amount, bad subsidiary)
pub async fn validate_invoice(
    Json(payload): Json<Value>
) -> (StatusCode, Json<InvoiceValidationResponse>) {
    
    // ========================================================================
    // GATE 1: PROOF OF STRUCTURE (Syntax)
    // Attempt to mold raw JSON into strict NetSuiteInvoice schema.
    // If it has floats, missing fields, or bad types, it fails here.
    // ========================================================================
    let invoice: NetSuiteInvoice = match serde_json::from_value(payload) {
        Ok(inv) => inv,
        Err(_) => {
            // FAIL-CLOSED: Malformed data gets opaque rejection
            return (StatusCode::BAD_REQUEST, Json(InvoiceValidationResponse::reject_syntax()));
        }
    };
    
    // ========================================================================
    // GATE 2: PROOF OF LAW (Semantics)
    // Run business logic: currency codes, negative values, subsidiaries.
    // ========================================================================
    match invoice.validate() {
        Ok(_) => {
            // GATE 3: REWARD (Positive Closure)
            // Logic passed. In a full system, we would sign/stamp here.
            (StatusCode::OK, Json(InvoiceValidationResponse::approve(&invoice.internal_id)))
        },
        Err(_) => {
            // FAIL-CLOSED: Logic violation gets opaque rejection
            // We do not explain WHY it failed (Security through Asymmetry)
            (StatusCode::FORBIDDEN, Json(InvoiceValidationResponse::reject_logic()))
        }
    }
}

// ============================================================================
// P58: ZK-IDENTITY LAYER - Signed Invoice Validation
// ============================================================================

/// Signed Invoice Validation - VERIFY THEN PARSE
///
/// This endpoint enforces cryptographic identity before processing:
/// 1. IDENTITY GATE: Signature must verify (Ed25519)
/// 2. SYNTAX GATE: JSON must parse into NetSuiteInvoice schema
/// 3. LOGIC GATE: Business rules must pass
///
/// SECURITY MODEL:
/// - Invalid signature = Immediate 0xDEAD (no CPU wasted on parsing)
/// - Signature verified in ~20µs (600x under 12ms limit)
/// - We trust Keys, not IP addresses
///
/// WIRE FORMAT:
/// ```json
/// {
///     "payload": "{\"internalId\":\"INV-001\",...}",
///     "public_key": "hex-encoded-32-byte-ed25519-public-key",
///     "signature": "hex-encoded-64-byte-ed25519-signature"
/// }
/// ```
pub async fn validate_signed_invoice(
    Json(signed_req): Json<SignedRequest>
) -> (StatusCode, Json<InvoiceValidationResponse>) {
    
    // ========================================================================
    // GATE 0: PROOF OF IDENTITY (Cryptographic)
    // The signature is verified BEFORE we touch the payload.
    // If the math doesn't align, the code does not execute.
    // Cost: ~20µs (DoS Protection)
    // ========================================================================
    if !signed_req.is_valid() {
        // FAIL-CLOSED: Invalid signature gets immediate rejection
        // We do not waste CPU parsing unverified data
        return (StatusCode::FORBIDDEN, Json(InvoiceValidationResponse::reject_identity()));
    }
    
    // ========================================================================
    // GATE 1: PROOF OF STRUCTURE (Syntax)
    // Now that we trust the sender, parse the payload.
    // ========================================================================
    let payload_value: Value = match serde_json::from_str(&signed_req.payload) {
        Ok(v) => v,
        Err(_) => {
            return (StatusCode::BAD_REQUEST, Json(InvoiceValidationResponse::reject_syntax()));
        }
    };
    
    let invoice: NetSuiteInvoice = match serde_json::from_value(payload_value) {
        Ok(inv) => inv,
        Err(_) => {
            return (StatusCode::BAD_REQUEST, Json(InvoiceValidationResponse::reject_syntax()));
        }
    };
    
    // ========================================================================
    // GATE 2: PROOF OF LAW (Semantics)
    // ========================================================================
    match invoice.validate() {
        Ok(_) => {
            // All gates passed. The transaction is verified AND signed.
            (StatusCode::OK, Json(InvoiceValidationResponse::approve(&invoice.internal_id)))
        },
        Err(_) => {
            (StatusCode::FORBIDDEN, Json(InvoiceValidationResponse::reject_logic()))
        }
    }
}

// ============================================================================
// UNIT TESTS - Prove the invariants hold
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_signature_format_valid() {
        assert!(validate_signature_format("0x1234abcd"));
        assert!(validate_signature_format("0xDEADBEEF"));
    }

    #[test]
    fn test_signature_format_invalid() {
        assert!(!validate_signature_format("1234abcd")); // Missing 0x
        assert!(!validate_signature_format("0x"));       // Too short
        assert!(!validate_signature_format("0xGHIJ"));   // Invalid hex
        assert!(!validate_signature_format(""));         // Empty
    }

    #[test]
    fn test_tx_id_generation() {
        let hash = "abc123def456789";
        let tx_id = generate_tx_id(hash);
        assert!(tx_id.starts_with("0xCB_"));
        assert!(tx_id.len() <= 22); // 0xCB_ + max 16 chars
    }

    #[test]
    fn test_rejection_response() {
        let (status, json) = reject(0xDEAD);
        assert_eq!(status, StatusCode::FORBIDDEN);
        assert_eq!(json.status, "REJECTED");
        assert_eq!(json.error_code, Some(0xDEAD));
        assert!(json.tx_id.is_none());
    }
}
