// ============================================================================
// CHAINBRIDGE KERNEL - Core Library
// PAC-OCC-P61-XDIST: GaaS Parallelization Swarm
// PAC-STRAT-P48: The Invariant Engine (ERP Shield Integration)
// PAC-OCC-P58: ZK-Identity / Ed25519 Signature Enforcement
// PAC-STRAT-P65: Structured Audit Logging (Memory)
// AUTH: BENSON (GID-00), CODY (GID-02)
// ============================================================================

/// GaaS Gateway - The Sovereign API Gasket
/// Stateless signal verification with <12ms latency guarantee
pub mod gaas_gateway;

/// ERP Shield - NetSuite Schema Validation
/// Structural and semantic validation for enterprise financial data
pub mod erp_shield;

/// Identity Module - Ed25519 Cryptographic Signature Enforcement
/// We do not trust IP addresses; we trust Keys.
pub mod identity;

/// Observability Module - Structured Audit Logging
/// A Judge without a Court Reporter is just a tyrant.
pub mod observability;

// Re-export primary types for ergonomic access
pub use gaas_gateway::{
    spawn_gateway,
    spawn_gateway_on_port,
    VerificationRequest,
    VerificationResponse,
    InvoiceValidationResponse,
    validate_invoice,
};

pub use erp_shield::{
    NetSuiteInvoice,
    InvoiceLineItem,
    ValidationError,
};

pub use identity::{
    SignedRequest,
    IdentityError,
};

pub use observability::{
    init_tracing,
    init_tracing_default,
    AuditConfig,
    AuditEvent,
    error_codes,
};

// ============================================================================
// KERNEL ENTRY POINT
// ============================================================================

/// Initialize and run the ChainBridge kernel
/// 
/// This is the canonical entry point for the Rust-based invariant engine.
/// The gasket handles all external API traffic; the kernel handles verification.
/// P48: ERP Shield is now wired to the /validate_invoice endpoint.
/// P58: Ed25519 Identity Layer enforces cryptographic signatures.
/// P65: Structured audit logging captures every decision.
#[tokio::main]
pub async fn run_kernel() {
    // P65: Initialize structured audit logging FIRST
    // The guard MUST be held for the lifetime of the application
    let _guard = observability::init_tracing_default();
    
    tracing::info!(
        event = "kernel_ignite",
        version = env!("CARGO_PKG_VERSION"),
        ">>> CHAINBRIDGE KERNEL INITIALIZING"
    );
    tracing::info!(">>> PAC-OCC-P61-XDIST: SPEED MOAT ACTIVE");
    tracing::info!(">>> PAC-STRAT-P48: INVARIANT ENGINE WIRED");
    tracing::info!(">>> PAC-OCC-P58: ZK-IDENTITY LAYER ACTIVE");
    tracing::info!(">>> PAC-STRAT-P65: AUDIT LOGGING ACTIVE");
    
    gaas_gateway::spawn_gateway().await;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn kernel_exports_gateway() {
        // Verify types are exported
        let _req: Option<VerificationRequest> = None;
        let _resp: Option<VerificationResponse> = None;
    }
    
    #[test]
    fn kernel_exports_erp_shield() {
        // Verify ERP Shield types are exported
        let _invoice: Option<NetSuiteInvoice> = None;
        let _line: Option<InvoiceLineItem> = None;
    }
}
