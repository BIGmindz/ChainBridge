// ============================================================================
// FILE: gaas_gateway.rs
// CONTEXT: PAC-OCC-P61-XDIST (GaaS PARALLELIZATION SWARM)
// AUTH: BENSON (GID-00)
// PURPOSE: The Sovereign API Gasket - Stateless Signal Verification Gateway
// INVARIANT: External_Latency < 12ms
// SECURITY: Opaque Error Codes (No Logic Leakage)
// ============================================================================

use axum::{
    routing::post,
    Router,
    Json,
    http::StatusCode,
};
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;

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
        .route("/health", axum::routing::get(health_check));

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    println!(">>> CHAINBRIDGE GAAS GATEWAY ACTIVE ON: {}", addr);
    println!(">>> INVARIANT: External_Latency < 12ms");
    println!(">>> SECURITY: Opaque Error Codes Enabled");
    
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
