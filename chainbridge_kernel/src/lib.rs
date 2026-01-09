// ============================================================================
// CHAINBRIDGE KERNEL - Core Library
// PAC-OCC-P61-XDIST: GaaS Parallelization Swarm
// PAC-STRAT-P48: The Invariant Engine (ERP Shield Integration)
// AUTH: BENSON (GID-00), CODY (GID-02)
// ============================================================================

/// GaaS Gateway - The Sovereign API Gasket
/// Stateless signal verification with <12ms latency guarantee
pub mod gaas_gateway;

/// ERP Shield - NetSuite Schema Validation
/// Structural and semantic validation for enterprise financial data
pub mod erp_shield;

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

// ============================================================================
// KERNEL ENTRY POINT
// ============================================================================

/// Initialize and run the ChainBridge kernel
/// 
/// This is the canonical entry point for the Rust-based invariant engine.
/// The gasket handles all external API traffic; the kernel handles verification.
/// P48: ERP Shield is now wired to the /validate_invoice endpoint.
#[tokio::main]
pub async fn run_kernel() {
    println!(">>> CHAINBRIDGE KERNEL INITIALIZING...");
    println!(">>> PAC-OCC-P61-XDIST: SPEED MOAT ACTIVE");
    println!(">>> PAC-STRAT-P48: INVARIANT ENGINE WIRED");
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
