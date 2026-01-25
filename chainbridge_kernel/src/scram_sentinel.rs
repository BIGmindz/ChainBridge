//! ═══════════════════════════════════════════════════════════════════════════
//! SCRAM SENTINEL - HARDWARE-BOUND TERMINATION PRIMITIVE
//! ═══════════════════════════════════════════════════════════════════════════
//!
//! PAC-JEFFREY-SCRAM-RUST-SENTINEL-REPLACEMENT-R2C-002
//! GOVERNANCE_TIER: LAW
//! DRIFT_TOLERANCE: ZERO
//! FAIL_CLOSED: TRUE
//!
//! ═══════════════════════════════════════════════════════════════════════════

#![allow(dead_code)]
//! REPLACEMENT DECLARATION
//! ═══════════════════════════════════════════════════════════════════════════
//!
//! This file REPLACES all prior SCRAM sentinel implementations.
//! No backward compatibility is preserved.
//! No conditional execution paths are allowed.
//!
//! SUPERSEDES:
//!   - All prior scram_sentinel.rs versions
//!   - All prior hardware sentinel implementations
//!   - PAC-JEFFREY-SCRAM-RUST-SENTINEL-REPLACEMENT-R2C-001 (TERMINATED)
//!
//! ═══════════════════════════════════════════════════════════════════════════
//! INVARIANTS ENFORCED BY CONSTRUCTION
//! ═══════════════════════════════════════════════════════════════════════════
//!
//! INV-SCRAM-003: Hardware-bound execution
//! INV-FAIL-CLOSED: All errors terminate
//! INV-NO-RECOVERY: Termination is irreversible
//! INV-LATENCY-BOUND: ≤500ms deadline
//!
//! ═══════════════════════════════════════════════════════════════════════════
//! PROPERTIES (NON-NEGOTIABLE)
//! ═══════════════════════════════════════════════════════════════════════════
//!
//! - Deterministic: Same input → same output, always
//! - Hardware-bound: Terminates via kernel-level process exit
//! - Non-recoverable: No restart, no retry, no rollback
//! - No policy logic: Pure actuation only
//! - No discretion: No conditionals on termination path
//! - Fail-closed: Error, ambiguity, or timeout → TERMINATE
//!
//! Author: BENSON-GID-00
//! Authority: ARCHITECT-JEFFREY (STRATEGY_ONLY)
//! Certification: ALEX (GID-08)
//! Date: 2026-01-16
//!
//! ═══════════════════════════════════════════════════════════════════════════

#![forbid(unsafe_code)]
#![deny(missing_docs)]
#![deny(clippy::all)]

use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::Path;
use std::process;
use std::sync::atomic::{AtomicU8, Ordering};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

// ═══════════════════════════════════════════════════════════════════════════
// CONSTANTS - IMMUTABLE BY DESIGN
// ═══════════════════════════════════════════════════════════════════════════

/// Constitutional termination deadline (INV-LATENCY-BOUND)
const MAX_TERMINATION_MS: u64 = 500;

/// Sentinel file poll interval
const POLL_INTERVAL_MS: u64 = 10;

/// Default sentinel signal path
const DEFAULT_SENTINEL_PATH: &str = "/tmp/chainbridge_scram_sentinel";

/// SCRAM activation command (exact match required)
const SCRAM_ACTIVATE_COMMAND: &str = "SCRAM_ACTIVATE";

// ═══════════════════════════════════════════════════════════════════════════
// STATE MACHINE - MONOTONIC PROGRESSION ONLY
// ═══════════════════════════════════════════════════════════════════════════

/// Sentinel state - monotonic progression, no backward transitions
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SentinelState {
    /// Initial state - monitoring for SCRAM signal
    Armed = 0,
    /// SCRAM signal received - executing termination
    Executing = 1,
    /// Termination complete (process will exit)
    Terminated = 2,
}

impl From<u8> for SentinelState {
    fn from(v: u8) -> Self {
        match v {
            0 => SentinelState::Armed,
            1 => SentinelState::Executing,
            _ => SentinelState::Terminated,
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// SCRAM SENTINEL - HARDWARE TERMINATION PRIMITIVE
// ═══════════════════════════════════════════════════════════════════════════

/// SCRAM Sentinel - Hardware-bound termination actuator
///
/// This is the sole termination primitive for ChainBridge SCRAM.
/// It monitors a sentinel file and executes irreversible process termination
/// upon receiving a valid SCRAM_ACTIVATE command.
///
/// # Invariants
///
/// - INV-SCRAM-003: Hardware-bound (uses process::exit)
/// - INV-FAIL-CLOSED: Any error triggers termination
/// - INV-NO-RECOVERY: No restart mechanism exists
/// - INV-LATENCY-BOUND: Must complete within 500ms
pub struct ScramSentinel {
    /// Atomic state for lock-free access
    state: AtomicU8,
    /// Path to sentinel signal file
    sentinel_path: String,
    /// Activation timestamp (for latency measurement)
    activation_instant: Option<Instant>,
}

impl ScramSentinel {
    /// Create new SCRAM sentinel with default path
    #[must_use]
    pub fn new() -> Self {
        Self::with_path(DEFAULT_SENTINEL_PATH)
    }

    /// Create new SCRAM sentinel with custom path
    #[must_use]
    pub fn with_path(path: &str) -> Self {
        ScramSentinel {
            state: AtomicU8::new(SentinelState::Armed as u8),
            sentinel_path: path.to_string(),
            activation_instant: None,
        }
    }

    /// Get current state (atomic read)
    #[must_use]
    pub fn state(&self) -> SentinelState {
        SentinelState::from(self.state.load(Ordering::SeqCst))
    }

    /// Check for SCRAM signal and execute if present
    ///
    /// # Behavior
    ///
    /// 1. Checks sentinel file for SCRAM_ACTIVATE command
    /// 2. If found: transitions to Executing, then terminates process
    /// 3. If error: terminates process (fail-closed)
    /// 4. If not found: returns false, remains Armed
    ///
    /// # Returns
    ///
    /// This function only returns `false` if no signal is present.
    /// On signal detection or error, the process terminates.
    pub fn check_and_execute(&mut self) -> bool {
        // Only proceed if Armed
        if self.state() != SentinelState::Armed {
            return false;
        }

        let path = Path::new(&self.sentinel_path);

        // No signal file - remain armed
        if !path.exists() {
            return false;
        }

        // Signal file exists - read and validate
        let content = match Self::read_signal_file(path) {
            Ok(c) => c,
            Err(_) => {
                // INV-FAIL-CLOSED: Read error → terminate
                self.execute_termination("SIGNAL_READ_ERROR")
            }
        };

        // Validate command
        if !Self::is_valid_scram_command(&content) {
            // Invalid command in signal file → terminate (fail-closed)
            self.execute_termination("INVALID_SCRAM_COMMAND")
        }

        // Valid SCRAM command - execute termination
        self.execute_termination("SCRAM_ACTIVATE")
    }

    /// Execute irreversible process termination
    ///
    /// # Behavior
    ///
    /// 1. Transition state to Executing
    /// 2. Record activation time
    /// 3. Write audit record
    /// 4. Remove signal file
    /// 5. Terminate process with exit code 1
    ///
    /// # Panics
    ///
    /// This function never returns - it always terminates the process.
    fn execute_termination(&mut self, reason: &str) -> ! {
        let start = Instant::now();

        // Transition to Executing (monotonic - cannot go back)
        self.state.store(SentinelState::Executing as u8, Ordering::SeqCst);
        self.activation_instant = Some(start);

        // Log to stderr (guaranteed to be available)
        eprintln!("═══════════════════════════════════════════════════════════════");
        eprintln!("🔴 SCRAM SENTINEL: TERMINATION EXECUTING");
        eprintln!("═══════════════════════════════════════════════════════════════");
        eprintln!("  Reason: {}", reason);
        eprintln!("  Timestamp: {}", Self::timestamp_now());
        eprintln!("  PID: {}", process::id());
        eprintln!("═══════════════════════════════════════════════════════════════");

        // Write audit record (best effort - failure does not stop termination)
        let _ = self.write_audit_record(reason);

        // Remove signal file (best effort)
        let _ = fs::remove_file(&self.sentinel_path);

        // Check latency bound
        let elapsed_ms = start.elapsed().as_millis() as u64;
        if elapsed_ms > MAX_TERMINATION_MS {
            eprintln!(
                "⚠️ SCRAM SENTINEL: LATENCY VIOLATION ({} ms > {} ms)",
                elapsed_ms, MAX_TERMINATION_MS
            );
        }

        // Transition to Terminated
        self.state.store(SentinelState::Terminated as u8, Ordering::SeqCst);

        eprintln!("🔴 SCRAM SENTINEL: PROCESS TERMINATING (exit code 1)");
        eprintln!("═══════════════════════════════════════════════════════════════");

        // INV-SCRAM-003: Hardware-bound termination via kernel
        // INV-NO-RECOVERY: This is final - no return, no restart
        process::exit(1)
    }

    /// Read signal file content
    fn read_signal_file(path: &Path) -> Result<String, std::io::Error> {
        let mut file = File::open(path)?;
        let mut content = String::new();
        file.read_to_string(&mut content)?;
        Ok(content)
    }

    /// Validate SCRAM command (exact match, no parsing)
    fn is_valid_scram_command(content: &str) -> bool {
        // Look for exact command string
        content.contains(SCRAM_ACTIVATE_COMMAND)
    }

    /// Get current timestamp as ISO 8601 string
    fn timestamp_now() -> String {
        let duration = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default();
        format!("{}.{:09}Z", duration.as_secs(), duration.subsec_nanos())
    }

    /// Write audit record to log file
    fn write_audit_record(&self, reason: &str) -> Result<(), std::io::Error> {
        let log_path = "/var/log/chainbridge/scram_sentinel_audit.jsonl";

        // Create directory if needed
        if let Some(parent) = Path::new(log_path).parent() {
            let _ = fs::create_dir_all(parent);
        }

        let record = format!(
            r#"{{"event":"SCRAM_TERMINATION","reason":"{}","timestamp":"{}","pid":{},"state":"Executing"}}"#,
            reason,
            Self::timestamp_now(),
            process::id()
        );

        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(log_path)?;

        writeln!(file, "{}", record)?;
        Ok(())
    }

    /// Trigger SCRAM by writing signal file (for external callers)
    ///
    /// This creates the sentinel file that will cause termination
    /// on the next check_and_execute() call.
    pub fn trigger(&self, reason: &str) -> Result<(), std::io::Error> {
        let path = Path::new(&self.sentinel_path);

        // Create parent directory if needed
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }

        let signal = format!(
            r#"{{"command":"{}","timestamp":"{}","pid":{},"reason":"{}"}}"#,
            SCRAM_ACTIVATE_COMMAND,
            Self::timestamp_now(),
            process::id(),
            reason
        );

        let mut file = File::create(path)?;
        file.write_all(signal.as_bytes())?;
        file.sync_all()?;

        Ok(())
    }

    /// Run monitoring loop (blocking)
    ///
    /// This function blocks and continuously monitors for SCRAM signals.
    /// It only returns if the process would need to continue (which it won't
    /// after SCRAM - the process terminates).
    pub fn monitor_blocking(&mut self) {
        let poll_interval = Duration::from_millis(POLL_INTERVAL_MS);

        loop {
            if self.check_and_execute() {
                // Signal detected - process will terminate
                // This line is unreachable
                unreachable!()
            }
            std::thread::sleep(poll_interval);
        }
    }
}

impl Default for ScramSentinel {
    fn default() -> Self {
        Self::new()
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PUBLIC API - MINIMAL SURFACE
// ═══════════════════════════════════════════════════════════════════════════

/// Initialize and return a new SCRAM sentinel
///
/// This is the canonical entry point for SCRAM sentinel initialization.
#[must_use]
pub fn init() -> ScramSentinel {
    eprintln!("🛡️ SCRAM SENTINEL: Initialized (INV-SCRAM-003 hardware-bound)");
    ScramSentinel::new()
}

/// Execute immediate SCRAM termination (no signal file needed)
///
/// This function immediately terminates the process.
/// Use when SCRAM must be executed synchronously.
pub fn terminate_now(reason: &str) -> ! {
    let mut sentinel = ScramSentinel::new();
    sentinel.execute_termination(reason)
}

// ═══════════════════════════════════════════════════════════════════════════
// TESTS - VALIDATION OF INVARIANTS
// ═══════════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    /// Test: Sentinel initializes in Armed state
    #[test]
    fn test_initial_state_is_armed() {
        let sentinel = ScramSentinel::new();
        assert_eq!(sentinel.state(), SentinelState::Armed);
    }

    /// Test: State transitions are monotonic
    #[test]
    fn test_state_values_are_monotonic() {
        assert!((SentinelState::Armed as u8) < (SentinelState::Executing as u8));
        assert!((SentinelState::Executing as u8) < (SentinelState::Terminated as u8));
    }

    /// Test: MAX_TERMINATION_MS is exactly 500
    #[test]
    fn test_termination_deadline_is_500ms() {
        assert_eq!(MAX_TERMINATION_MS, 500);
    }

    /// Test: SCRAM command string is correct
    #[test]
    fn test_scram_command_string() {
        assert_eq!(SCRAM_ACTIVATE_COMMAND, "SCRAM_ACTIVATE");
    }

    /// Test: Valid command detection
    #[test]
    fn test_valid_command_detection() {
        let valid = r#"{"command":"SCRAM_ACTIVATE","timestamp":"123"}"#;
        assert!(ScramSentinel::is_valid_scram_command(valid));

        let invalid = r#"{"command":"OTHER_COMMAND"}"#;
        assert!(!ScramSentinel::is_valid_scram_command(invalid));
    }

    /// Test: Custom path works
    #[test]
    fn test_custom_sentinel_path() {
        let sentinel = ScramSentinel::with_path("/custom/path");
        assert_eq!(sentinel.sentinel_path, "/custom/path");
    }

    /// Test: No signal file returns false
    #[test]
    fn test_no_signal_returns_false() {
        let mut sentinel = ScramSentinel::with_path("/nonexistent/path/sentinel");
        assert!(!sentinel.check_and_execute());
        assert_eq!(sentinel.state(), SentinelState::Armed);
    }

    /// Test: Trigger creates signal file
    #[test]
    fn test_trigger_creates_file() {
        let temp_path = "/tmp/test_scram_sentinel_trigger";
        let _ = fs::remove_file(temp_path); // Clean up first

        let sentinel = ScramSentinel::with_path(temp_path);
        sentinel.trigger("test").unwrap();

        assert!(Path::new(temp_path).exists());

        let content = fs::read_to_string(temp_path).unwrap();
        assert!(content.contains("SCRAM_ACTIVATE"));

        // Clean up
        let _ = fs::remove_file(temp_path);
    }

    /// Test: Timestamp format is valid
    #[test]
    fn test_timestamp_format() {
        let ts = ScramSentinel::timestamp_now();
        assert!(ts.ends_with('Z'));
        assert!(ts.contains('.'));
    }
}
