//! PAC-STRAT-P65: Structured Audit Logging
//!
//! The Kernel's Memory. Every decision is recorded.
//! A Judge without a Court Reporter is just a tyrant.
//!
//! DESIGN PRINCIPLES:
//! - Non-blocking I/O (logging never slows the 12ms Moat)
//! - JSON format (machine-readable for Splunk/Datadog/ELK)
//! - Daily rotation (prevents disk exhaustion)
//! - Privacy-first (Public Keys logged, not IP addresses)

use tracing_appender::non_blocking::WorkerGuard;
use tracing_appender::rolling::{RollingFileAppender, Rotation};
use tracing_subscriber::{
    fmt::{self, format::FmtSpan},
    layer::SubscriberExt,
    util::SubscriberInitExt,
    EnvFilter,
};

/// Configuration for the audit logging system
pub struct AuditConfig {
    /// Directory for log files
    pub log_dir: String,
    /// Base filename for logs (will have date appended)
    pub log_prefix: String,
    /// Enable console output (pretty-printed for humans)
    pub console_output: bool,
    /// Log level filter (e.g., "info", "debug", "warn")
    pub level_filter: String,
}

impl Default for AuditConfig {
    fn default() -> Self {
        Self {
            log_dir: "logs".to_string(),
            log_prefix: "chainbridge".to_string(),
            console_output: true,
            level_filter: "info".to_string(),
        }
    }
}

/// Initialize the global tracing subscriber with structured JSON logging.
///
/// Returns a `WorkerGuard` that MUST be held for the lifetime of the application.
/// Dropping the guard will flush and close the log file.
///
/// # Architecture
///
/// ```text
/// ┌─────────────────┐
/// │  Application    │
/// │   (async)       │
/// └────────┬────────┘
///          │ info!(), warn!(), error!()
///          ▼
/// ┌─────────────────┐
/// │  Non-Blocking   │◄── Returns immediately (no latency hit)
/// │    Channel      │
/// └────────┬────────┘
///          │ (background thread)
///          ▼
/// ┌─────────────────┐
/// │  Rolling File   │──► logs/chainbridge.2026-01-09.log
/// │    Appender     │
/// └─────────────────┘
/// ```
pub fn init_tracing(config: AuditConfig) -> WorkerGuard {
    // Daily rolling file appender
    // Files: logs/chainbridge.2026-01-09.log, logs/chainbridge.2026-01-10.log, etc.
    let file_appender = RollingFileAppender::new(
        Rotation::DAILY,
        &config.log_dir,
        &config.log_prefix,
    );

    // Non-blocking wrapper - writes happen in a background thread
    // This protects the Speed Moat: logging never blocks the main thread
    let (non_blocking, guard) = tracing_appender::non_blocking(file_appender);

    // Environment filter for log levels
    let env_filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(&config.level_filter));

    // JSON layer for file output (machine-readable)
    let json_layer = fmt::layer()
        .json()
        .with_writer(non_blocking)
        .with_span_events(FmtSpan::CLOSE)
        .with_current_span(true)
        .with_target(true)
        .with_file(false)
        .with_line_number(false);

    if config.console_output {
        // Dual output: JSON to file, Pretty to console
        let console_layer = fmt::layer()
            .pretty()
            .with_writer(std::io::stdout)
            .with_target(true);

        tracing_subscriber::registry()
            .with(env_filter)
            .with(json_layer)
            .with(console_layer)
            .init();
    } else {
        // JSON only (production mode)
        tracing_subscriber::registry()
            .with(env_filter)
            .with(json_layer)
            .init();
    }

    // CRITICAL: Return the guard. If dropped, logging stops.
    guard
}

/// Initialize tracing with default configuration.
/// Convenience function for quick setup.
pub fn init_tracing_default() -> WorkerGuard {
    init_tracing(AuditConfig::default())
}

/// Audit event types for structured logging
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AuditEvent {
    /// Kernel startup
    KernelIgnite,
    /// Successful authentication (valid signature)
    AuthSuccess,
    /// Failed authentication (invalid signature)
    AuthFailed,
    /// Successful transaction/validation
    TxFinalized,
    /// Validation rejected (business rule failure)
    TxRejected,
    /// System error
    SystemError,
}

impl std::fmt::Display for AuditEvent {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AuditEvent::KernelIgnite => write!(f, "kernel_ignite"),
            AuditEvent::AuthSuccess => write!(f, "auth_success"),
            AuditEvent::AuthFailed => write!(f, "auth_failed"),
            AuditEvent::TxFinalized => write!(f, "tx_finalized"),
            AuditEvent::TxRejected => write!(f, "tx_rejected"),
            AuditEvent::SystemError => write!(f, "system_error"),
        }
    }
}

/// Error codes for audit trail (opaque to attackers, meaningful to us)
pub mod error_codes {
    /// Identity verification failed (signature invalid)
    pub const IDENTITY_FAILED: &str = "0xDEAD";
    /// Structure validation failed (JSON malformed)
    pub const STRUCTURE_FAILED: &str = "0x0001";
    /// Logic validation failed (business rules)
    pub const LOGIC_FAILED: &str = "0x0002";
    /// Internal system error
    pub const SYSTEM_ERROR: &str = "0xFFFF";
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_audit_config_default() {
        let config = AuditConfig::default();
        assert_eq!(config.log_dir, "logs");
        assert_eq!(config.log_prefix, "chainbridge");
        assert!(config.console_output);
        assert_eq!(config.level_filter, "info");
    }

    #[test]
    fn test_audit_event_display() {
        assert_eq!(AuditEvent::KernelIgnite.to_string(), "kernel_ignite");
        assert_eq!(AuditEvent::AuthSuccess.to_string(), "auth_success");
        assert_eq!(AuditEvent::AuthFailed.to_string(), "auth_failed");
        assert_eq!(AuditEvent::TxFinalized.to_string(), "tx_finalized");
        assert_eq!(AuditEvent::TxRejected.to_string(), "tx_rejected");
        assert_eq!(AuditEvent::SystemError.to_string(), "system_error");
    }

    #[test]
    fn test_error_codes_are_opaque() {
        // Verify error codes don't leak implementation details
        assert_eq!(error_codes::IDENTITY_FAILED, "0xDEAD");
        assert_eq!(error_codes::STRUCTURE_FAILED, "0x0001");
        assert_eq!(error_codes::LOGIC_FAILED, "0x0002");
        assert_eq!(error_codes::SYSTEM_ERROR, "0xFFFF");
    }
}
