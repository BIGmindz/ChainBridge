// ============================================================================
// CHAINBRIDGE KERNEL - Core Library
// PAC-OCC-P61-XDIST: GaaS Parallelization Swarm
// AUTH: BENSON (GID-00)
// ============================================================================

/// GaaS Gateway - The Sovereign API Gasket
/// Stateless signal verification with <12ms latency guarantee
pub mod gaas_gateway;

// Re-export primary types for ergonomic access
pub use gaas_gateway::{
    spawn_gateway,
    spawn_gateway_on_port,
    VerificationRequest,
    VerificationResponse,
};

// ============================================================================
// KERNEL ENTRY POINT
// ============================================================================

/// Initialize and run the ChainBridge kernel
/// 
/// This is the canonical entry point for the Rust-based invariant engine.
/// The gasket handles all external API traffic; the kernel handles verification.
#[tokio::main]
pub async fn run_kernel() {
    println!(">>> CHAINBRIDGE KERNEL INITIALIZING...");
    println!(">>> PAC-OCC-P61-XDIST: SPEED MOAT ACTIVE");
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
}
