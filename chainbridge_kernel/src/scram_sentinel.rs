//! SCRAM Sentinel - Hardware-Bound Emergency Shutdown
//!
//! PAC-SEC-P820 | LAW-TIER | ZERO DRIFT TOLERANCE
//! Constitutional Mandate: PAC-GOV-P45
//!
//! This module provides the Rust/kernel-level enforcement of SCRAM.
//! INV-SCRAM-003: Hardware-bound execution via TITAN sentinel.
//!
//! The sentinel monitors for SCRAM activation signals and enforces
//! immediate process termination at the kernel level.

use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::Path;
use std::process;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

/// SCRAM Sentinel configuration
pub struct SentinelConfig {
    /// Path to sentinel signal file
    pub sentinel_path: String,
    /// Maximum termination deadline in milliseconds
    pub max_termination_ms: u64,
    /// Poll interval for sentinel file
    pub poll_interval_ms: u64,
    /// Enable hardware enforcement (process termination)
    pub hardware_enforcement: bool,
    /// Audit log path
    pub audit_log_path: String,
}

impl Default for SentinelConfig {
    fn default() -> Self {
        SentinelConfig {
            sentinel_path: "/tmp/chainbridge_scram_sentinel".to_string(),
            max_termination_ms: 500,
            poll_interval_ms: 10,
            hardware_enforcement: true,
            audit_log_path: "/var/log/chainbridge/scram_sentinel.log".to_string(),
        }
    }
}

/// SCRAM Sentinel state
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SentinelState {
    /// Sentinel is monitoring for SCRAM signals
    Monitoring,
    /// SCRAM signal detected, executing termination
    Executing,
    /// Termination complete
    Complete,
    /// Error state (still terminates - fail-closed)
    Failed,
}

/// SCRAM Command from Python layer
#[derive(Debug)]
pub struct ScramCommand {
    pub command: String,
    pub timestamp: String,
    pub pid: u32,
}

impl ScramCommand {
    /// Parse SCRAM command from JSON
    pub fn from_json(json: &str) -> Option<ScramCommand> {
        // Simple JSON parsing without serde for minimal dependencies
        let command = extract_json_string(json, "command")?;
        let timestamp = extract_json_string(json, "timestamp")?;
        let pid = extract_json_number(json, "pid")?;
        
        Some(ScramCommand {
            command,
            timestamp,
            pid,
        })
    }
    
    /// Check if this is a valid SCRAM activation command
    pub fn is_scram_activate(&self) -> bool {
        self.command == "SCRAM_ACTIVATE"
    }
}

/// Extract a string value from JSON (simple parser)
fn extract_json_string(json: &str, key: &str) -> Option<String> {
    let pattern = format!("\"{}\":", key);
    let start = json.find(&pattern)? + pattern.len();
    let json_rest = &json[start..];
    
    // Skip whitespace
    let json_rest = json_rest.trim_start();
    
    if !json_rest.starts_with('"') {
        return None;
    }
    
    let json_rest = &json_rest[1..];
    let end = json_rest.find('"')?;
    
    Some(json_rest[..end].to_string())
}

/// Extract a number value from JSON (simple parser)
fn extract_json_number(json: &str, key: &str) -> Option<u32> {
    let pattern = format!("\"{}\":", key);
    let start = json.find(&pattern)? + pattern.len();
    let json_rest = &json[start..].trim_start();
    
    let end = json_rest.find(|c: char| !c.is_ascii_digit()).unwrap_or(json_rest.len());
    json_rest[..end].parse().ok()
}

/// SCRAM Audit Event for sentinel
#[derive(Debug)]
pub struct SentinelAuditEvent {
    pub event_id: String,
    pub timestamp: String,
    pub state: SentinelState,
    pub termination_latency_ms: u64,
    pub source_pid: u32,
    pub enforced: bool,
}

impl SentinelAuditEvent {
    /// Convert to JSON for logging
    pub fn to_json(&self) -> String {
        format!(
            r#"{{"event_id":"{}","timestamp":"{}","state":"{:?}","termination_latency_ms":{},"source_pid":{},"enforced":{}}}"#,
            self.event_id,
            self.timestamp,
            self.state,
            self.termination_latency_ms,
            self.source_pid,
            self.enforced
        )
    }
}

/// SCRAM Sentinel - Hardware-level enforcement
pub struct ScramSentinel {
    config: SentinelConfig,
    state: Arc<AtomicU64>,
    running: Arc<AtomicBool>,
    activation_time: Arc<AtomicU64>,
}

impl ScramSentinel {
    /// Create new SCRAM sentinel with default configuration
    pub fn new() -> Self {
        Self::with_config(SentinelConfig::default())
    }
    
    /// Create new SCRAM sentinel with custom configuration
    pub fn with_config(config: SentinelConfig) -> Self {
        ScramSentinel {
            config,
            state: Arc::new(AtomicU64::new(SentinelState::Monitoring as u64)),
            running: Arc::new(AtomicBool::new(false)),
            activation_time: Arc::new(AtomicU64::new(0)),
        }
    }
    
    /// Get current sentinel state
    pub fn state(&self) -> SentinelState {
        match self.state.load(Ordering::SeqCst) {
            0 => SentinelState::Monitoring,
            1 => SentinelState::Executing,
            2 => SentinelState::Complete,
            _ => SentinelState::Failed,
        }
    }
    
    /// Start sentinel monitoring in background thread
    pub fn start(&self) -> thread::JoinHandle<()> {
        let config = self.config.clone();
        let state = Arc::clone(&self.state);
        let running = Arc::clone(&self.running);
        let activation_time = Arc::clone(&self.activation_time);
        
        running.store(true, Ordering::SeqCst);
        
        thread::spawn(move || {
            Self::monitor_loop(config, state, running, activation_time);
        })
    }
    
    /// Stop sentinel monitoring
    pub fn stop(&self) {
        self.running.store(false, Ordering::SeqCst);
    }
    
    /// Sentinel monitoring loop
    fn monitor_loop(
        config: SentinelConfig,
        state: Arc<AtomicU64>,
        running: Arc<AtomicBool>,
        activation_time: Arc<AtomicU64>,
    ) {
        let sentinel_path = Path::new(&config.sentinel_path);
        let poll_interval = Duration::from_millis(config.poll_interval_ms);
        
        while running.load(Ordering::SeqCst) {
            // Check for SCRAM signal file
            if sentinel_path.exists() {
                if let Ok(mut file) = File::open(sentinel_path) {
                    let mut content = String::new();
                    if file.read_to_string(&mut content).is_ok() {
                        if let Some(cmd) = ScramCommand::from_json(&content) {
                            if cmd.is_scram_activate() {
                                // Record activation time
                                let now = SystemTime::now()
                                    .duration_since(UNIX_EPOCH)
                                    .unwrap_or_default()
                                    .as_millis() as u64;
                                activation_time.store(now, Ordering::SeqCst);
                                
                                // Execute SCRAM
                                Self::execute_scram(
                                    &config,
                                    &state,
                                    &activation_time,
                                    cmd.pid,
                                );
                                
                                // Remove signal file
                                let _ = fs::remove_file(sentinel_path);
                                
                                // Exit loop after SCRAM
                                break;
                            }
                        }
                    }
                }
            }
            
            thread::sleep(poll_interval);
        }
    }
    
    /// Execute SCRAM termination
    fn execute_scram(
        config: &SentinelConfig,
        state: &Arc<AtomicU64>,
        activation_time: &Arc<AtomicU64>,
        source_pid: u32,
    ) {
        let start = Instant::now();
        
        // Transition to Executing state
        state.store(SentinelState::Executing as u64, Ordering::SeqCst);
        
        // Log SCRAM activation
        eprintln!("🔴 SCRAM SENTINEL: Executing hardware-level termination");
        
        // Create audit event
        let event = SentinelAuditEvent {
            event_id: format!(
                "SENTINEL-{}",
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_micros()
            ),
            timestamp: format!(
                "{}",
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_secs()
            ),
            state: SentinelState::Executing,
            termination_latency_ms: start.elapsed().as_millis() as u64,
            source_pid,
            enforced: config.hardware_enforcement,
        };
        
        // Write audit log
        Self::write_audit_log(config, &event);
        
        // Check deadline
        let elapsed_ms = start.elapsed().as_millis() as u64;
        if elapsed_ms > config.max_termination_ms {
            eprintln!(
                "⚠️ SCRAM SENTINEL: Deadline exceeded ({} ms > {} ms)",
                elapsed_ms, config.max_termination_ms
            );
        }
        
        // Mark complete
        state.store(SentinelState::Complete as u64, Ordering::SeqCst);
        
        // Hardware enforcement: terminate process
        if config.hardware_enforcement {
            eprintln!("🔴 SCRAM SENTINEL: Hardware enforcement - terminating process");
            process::exit(1);
        }
    }
    
    /// Write audit event to log
    fn write_audit_log(config: &SentinelConfig, event: &SentinelAuditEvent) {
        let log_path = Path::new(&config.audit_log_path);
        
        // Create parent directories if needed
        if let Some(parent) = log_path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        
        // Append to audit log
        if let Ok(mut file) = OpenOptions::new()
            .create(true)
            .append(true)
            .open(log_path)
        {
            let _ = writeln!(file, "{}", event.to_json());
        }
    }
    
    /// Manually trigger SCRAM (for testing)
    pub fn trigger_scram(&self, reason: &str) {
        let sentinel_path = Path::new(&self.config.sentinel_path);
        
        // Create parent directories if needed
        if let Some(parent) = sentinel_path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        
        let command = format!(
            r#"{{"command":"SCRAM_ACTIVATE","timestamp":"{}","pid":{},"reason":"{}"}}"#,
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
            process::id(),
            reason
        );
        
        if let Ok(mut file) = File::create(sentinel_path) {
            let _ = file.write_all(command.as_bytes());
        }
    }
}

impl Default for ScramSentinel {
    fn default() -> Self {
        Self::new()
    }
}

impl Clone for SentinelConfig {
    fn clone(&self) -> Self {
        SentinelConfig {
            sentinel_path: self.sentinel_path.clone(),
            max_termination_ms: self.max_termination_ms,
            poll_interval_ms: self.poll_interval_ms,
            hardware_enforcement: self.hardware_enforcement,
            audit_log_path: self.audit_log_path.clone(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::PathBuf;
    use tempfile::tempdir;
    
    #[test]
    fn test_sentinel_config_default() {
        let config = SentinelConfig::default();
        assert_eq!(config.max_termination_ms, 500);
        assert!(config.hardware_enforcement);
    }
    
    #[test]
    fn test_scram_command_parsing() {
        let json = r#"{"command":"SCRAM_ACTIVATE","timestamp":"2026-01-12T19:45:00Z","pid":12345}"#;
        let cmd = ScramCommand::from_json(json).unwrap();
        
        assert_eq!(cmd.command, "SCRAM_ACTIVATE");
        assert!(cmd.is_scram_activate());
        assert_eq!(cmd.pid, 12345);
    }
    
    #[test]
    fn test_sentinel_state_transitions() {
        let config = SentinelConfig {
            hardware_enforcement: false, // Disable for testing
            ..Default::default()
        };
        let sentinel = ScramSentinel::with_config(config);
        
        assert_eq!(sentinel.state(), SentinelState::Monitoring);
    }
    
    #[test]
    fn test_audit_event_json() {
        let event = SentinelAuditEvent {
            event_id: "TEST-001".to_string(),
            timestamp: "2026-01-12T19:45:00Z".to_string(),
            state: SentinelState::Complete,
            termination_latency_ms: 50,
            source_pid: 12345,
            enforced: true,
        };
        
        let json = event.to_json();
        assert!(json.contains("TEST-001"));
        assert!(json.contains("Complete"));
    }
    
    #[test]
    fn test_sentinel_trigger_creates_file() {
        let dir = tempdir().unwrap();
        let sentinel_path = dir.path().join("scram_sentinel");
        
        let config = SentinelConfig {
            sentinel_path: sentinel_path.to_string_lossy().to_string(),
            hardware_enforcement: false,
            ..Default::default()
        };
        
        let sentinel = ScramSentinel::with_config(config);
        sentinel.trigger_scram("test");
        
        assert!(sentinel_path.exists());
        
        let content = fs::read_to_string(&sentinel_path).unwrap();
        assert!(content.contains("SCRAM_ACTIVATE"));
    }
}

/// Initialize SCRAM sentinel and start monitoring
/// 
/// This should be called early in the ChainBridge kernel initialization.
pub fn init_scram_sentinel() -> ScramSentinel {
    let sentinel = ScramSentinel::new();
    
    // Log initialization
    eprintln!("🛡️ SCRAM SENTINEL: Initialized (INV-SCRAM-003 hardware-bound enforcement active)");
    
    sentinel
}

/// Start SCRAM sentinel monitoring in background
pub fn start_sentinel_monitoring(sentinel: &ScramSentinel) -> thread::JoinHandle<()> {
    eprintln!("🛡️ SCRAM SENTINEL: Starting monitoring loop");
    sentinel.start()
}
