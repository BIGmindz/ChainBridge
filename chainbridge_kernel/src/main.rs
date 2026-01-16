//! Titan Sentinel - Hardware-Bound Process Supervisor
//! 
//! PAC Reference: PAC-OCC-P16-HW-TITAN-SENTINEL
//! 
//! This binary is the Physical Root of Trust for ChainBridge.
//! It supervises the Python Sovereign Node and enforces hardware binding.
//! 
//! Invariants Enforced:
//!   INV-HW-001 (Binary Supremacy): Rust master, Python servant
//!   INV-HW-002 (Physical Binding): Continuous hardware signal required
//!   INV-SCRAM-003 (Hardware-bound SCRAM): Via scram_sentinel module
//! 
//! Behavior:
//!   1. Check hardware interface (GPIO/Serial/Mock)
//!   2. Spawn Python node as child process
//!   3. Poll hardware every 50ms
//!   4. If hardware signal lost -> SIGKILL child -> exit(1)
//!   5. If child dies unexpectedly -> exit(child_code)

// SCRAM Sentinel Module - Hardware-bound termination primitive
// PAC-JEFFREY-SCRAM-RUST-SENTINEL-REPLACEMENT-R2C-002
mod scram_sentinel;

use std::env;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant};

use anyhow::{bail, Context, Result};
use chrono::Utc;
use log::{debug, error, info, warn};
use nix::sys::signal::{self, Signal};
use nix::unistd::Pid;
use serde::{Deserialize, Serialize};

// ============================================================================
// Configuration
// ============================================================================

/// Sentinel configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SentinelConfig {
    /// Hardware interface type: "gpio", "serial", "mock"
    pub hardware_type: String,
    
    /// GPIO pin number (if using GPIO)
    pub gpio_pin: Option<u32>,
    
    /// Serial port path (if using serial)
    pub serial_port: Option<String>,
    
    /// Serial baud rate
    pub serial_baud: u32,
    
    /// Hardware poll interval in milliseconds
    pub poll_interval_ms: u64,
    
    /// Maximum consecutive hardware failures before kill
    pub max_failures: u32,
    
    /// Python command to spawn
    pub python_command: Vec<String>,
    
    /// Working directory for Python process
    pub work_dir: String,
    
    /// Log file path
    pub log_file: String,
    
    /// Fail-closed behavior (exit if hardware unavailable)
    pub fail_closed: bool,
}

impl Default for SentinelConfig {
    fn default() -> Self {
        Self {
            hardware_type: "mock".to_string(),
            gpio_pin: Some(17),
            serial_port: Some("/dev/ttyUSB0".to_string()),
            serial_baud: 9600,
            poll_interval_ms: 50,
            max_failures: 3,
            python_command: vec![
                "python3".to_string(),
                "-m".to_string(),
                "modules.core.node".to_string(),
            ],
            work_dir: "/app".to_string(),
            log_file: "/var/log/sentinel.json".to_string(),
            fail_closed: true,
        }
    }
}

// ============================================================================
// Hardware Interfaces
// ============================================================================

/// Hardware interface trait for physical binding
trait HardwareInterface: Send {
    /// Check if hardware signal is present (key inserted, voltage high, etc.)
    fn check_signal(&mut self) -> Result<bool>;
    
    /// Get interface name for logging
    fn name(&self) -> &str;
    
    /// Initialize the interface
    fn init(&mut self) -> Result<()>;
    
    /// Cleanup on shutdown
    fn cleanup(&mut self) -> Result<()>;
}

/// Mock hardware interface for testing
struct MockHardware {
    signal_file: String,
    initialized: bool,
}

impl MockHardware {
    fn new() -> Self {
        Self {
            signal_file: env::var("SENTINEL_SIGNAL_FILE")
                .unwrap_or_else(|_| "/tmp/sentinel_signal".to_string()),
            initialized: false,
        }
    }
}

impl HardwareInterface for MockHardware {
    fn check_signal(&mut self) -> Result<bool> {
        // Signal is present if file exists and contains "1"
        let path = Path::new(&self.signal_file);
        if path.exists() {
            let content = fs::read_to_string(path).unwrap_or_default();
            Ok(content.trim() == "1")
        } else {
            // No signal file = no signal (fail-closed)
            Ok(false)
        }
    }
    
    fn name(&self) -> &str {
        "mock"
    }
    
    fn init(&mut self) -> Result<()> {
        // Create signal file with "1" to indicate presence
        let path = Path::new(&self.signal_file);
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(&self.signal_file, "1")?;
        self.initialized = true;
        info!("Mock hardware initialized: {}", self.signal_file);
        Ok(())
    }
    
    fn cleanup(&mut self) -> Result<()> {
        if self.initialized {
            let _ = fs::remove_file(&self.signal_file);
        }
        Ok(())
    }
}

/// GPIO hardware interface (Linux sysfs)
struct GpioHardware {
    pin: u32,
    gpio_path: String,
    initialized: bool,
}

impl GpioHardware {
    fn new(pin: u32) -> Self {
        Self {
            pin,
            gpio_path: format!("/sys/class/gpio/gpio{}/value", pin),
            initialized: false,
        }
    }
}

impl HardwareInterface for GpioHardware {
    fn check_signal(&mut self) -> Result<bool> {
        let value = fs::read_to_string(&self.gpio_path)
            .context("Failed to read GPIO")?;
        Ok(value.trim() == "1")
    }
    
    fn name(&self) -> &str {
        "gpio"
    }
    
    fn init(&mut self) -> Result<()> {
        // Export GPIO pin
        let export_path = "/sys/class/gpio/export";
        if !Path::new(&self.gpio_path).exists() {
            fs::write(export_path, self.pin.to_string())
                .context("Failed to export GPIO")?;
        }
        
        // Set direction to input
        let direction_path = format!("/sys/class/gpio/gpio{}/direction", self.pin);
        fs::write(&direction_path, "in")
            .context("Failed to set GPIO direction")?;
        
        self.initialized = true;
        info!("GPIO {} initialized", self.pin);
        Ok(())
    }
    
    fn cleanup(&mut self) -> Result<()> {
        if self.initialized {
            let unexport_path = "/sys/class/gpio/unexport";
            let _ = fs::write(unexport_path, self.pin.to_string());
        }
        Ok(())
    }
}

/// Serial DTR hardware interface
struct SerialHardware {
    port_name: String,
    baud_rate: u32,
    port: Option<Box<dyn serialport::SerialPort>>,
}

impl SerialHardware {
    fn new(port_name: &str, baud_rate: u32) -> Self {
        Self {
            port_name: port_name.to_string(),
            baud_rate,
            port: None,
        }
    }
}

impl HardwareInterface for SerialHardware {
    fn check_signal(&mut self) -> Result<bool> {
        if let Some(ref mut port) = self.port {
            // Check DTR (Data Terminal Ready) or CTS (Clear To Send)
            let cts = port.read_clear_to_send()
                .context("Failed to read CTS")?;
            Ok(cts)
        } else {
            Ok(false)
        }
    }
    
    fn name(&self) -> &str {
        "serial"
    }
    
    fn init(&mut self) -> Result<()> {
        let port = serialport::new(&self.port_name, self.baud_rate)
            .timeout(Duration::from_millis(100))
            .open()
            .context("Failed to open serial port")?;
        
        self.port = Some(port);
        info!("Serial port {} initialized at {} baud", self.port_name, self.baud_rate);
        Ok(())
    }
    
    fn cleanup(&mut self) -> Result<()> {
        self.port = None;
        Ok(())
    }
}

// ============================================================================
// Process Supervision
// ============================================================================

/// Spawn the Python node as a child process
fn spawn_node(config: &SentinelConfig) -> Result<Child> {
    if config.python_command.is_empty() {
        bail!("Python command is empty");
    }
    
    let (program, args) = config.python_command.split_first().unwrap();
    
    info!("Spawning node: {} {:?}", program, args);
    
    let child = Command::new(program)
        .args(args)
        .current_dir(&config.work_dir)
        .stdin(Stdio::null())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .spawn()
        .context("Failed to spawn Python node")?;
    
    info!("Node spawned with PID {}", child.id());
    Ok(child)
}

/// Kill the child process with SIGKILL
fn kill_node(child: &mut Child) -> Result<()> {
    let pid = child.id();
    info!("Sending SIGKILL to PID {}", pid);
    
    // Use nix for proper signal handling
    let nix_pid = Pid::from_raw(pid as i32);
    
    match signal::kill(nix_pid, Signal::SIGKILL) {
        Ok(_) => {
            info!("SIGKILL sent to PID {}", pid);
            // Wait for process to die
            let _ = child.wait();
            Ok(())
        }
        Err(e) => {
            error!("Failed to kill PID {}: {}", pid, e);
            // Fallback to std::process kill
            let _ = child.kill();
            let _ = child.wait();
            Ok(())
        }
    }
}

// ============================================================================
// Logging
// ============================================================================

#[derive(Debug, Serialize)]
struct LogEntry {
    timestamp: String,
    level: String,
    event: String,
    details: serde_json::Value,
}

fn log_event(log_file: &str, event: &str, details: serde_json::Value) {
    let entry = LogEntry {
        timestamp: Utc::now().to_rfc3339(),
        level: "INFO".to_string(),
        event: event.to_string(),
        details,
    };
    
    if let Ok(json) = serde_json::to_string(&entry) {
        // Try to append to log file
        if let Ok(mut file) = OpenOptions::new()
            .create(true)
            .append(true)
            .open(log_file)
        {
            let _ = writeln!(file, "{}", json);
        }
    }
}

// ============================================================================
// Main Sentinel Loop
// ============================================================================

fn run_sentinel(config: SentinelConfig) -> Result<i32> {
    info!("╔═══════════════════════════════════════════════════════════╗");
    info!("║         TITAN SENTINEL - Physical Root of Trust          ║");
    info!("║         PAC-OCC-P16-HW-TITAN-SENTINEL                    ║");
    info!("╚═══════════════════════════════════════════════════════════╝");
    
    // Initialize hardware interface
    let mut hardware: Box<dyn HardwareInterface> = match config.hardware_type.as_str() {
        "gpio" => {
            let pin = config.gpio_pin.unwrap_or(17);
            Box::new(GpioHardware::new(pin))
        }
        "serial" => {
            let port = config.serial_port.clone().unwrap_or_else(|| "/dev/ttyUSB0".to_string());
            Box::new(SerialHardware::new(&port, config.serial_baud))
        }
        "mock" | _ => {
            Box::new(MockHardware::new())
        }
    };
    
    // Initialize hardware
    info!("Initializing hardware interface: {}", hardware.name());
    if let Err(e) = hardware.init() {
        error!("Hardware initialization failed: {}", e);
        if config.fail_closed {
            error!("FAIL-CLOSED: Exiting due to hardware unavailability");
            return Ok(1);
        }
        warn!("Continuing without hardware binding (UNSAFE)");
    }
    
    // Check initial hardware state
    let initial_signal = hardware.check_signal().unwrap_or(false);
    if !initial_signal && config.fail_closed {
        error!("FAIL-CLOSED: No hardware signal at startup");
        log_event(&config.log_file, "STARTUP_FAILED", serde_json::json!({
            "reason": "no_hardware_signal",
            "hardware_type": hardware.name(),
        }));
        return Ok(1);
    }
    
    info!("Hardware signal: {}", if initial_signal { "PRESENT" } else { "ABSENT" });
    
    log_event(&config.log_file, "SENTINEL_START", serde_json::json!({
        "hardware_type": hardware.name(),
        "poll_interval_ms": config.poll_interval_ms,
        "max_failures": config.max_failures,
        "fail_closed": config.fail_closed,
    }));
    
    // Spawn the Python node
    let mut child = spawn_node(&config)?;
    let child_pid = child.id();
    
    log_event(&config.log_file, "NODE_SPAWNED", serde_json::json!({
        "pid": child_pid,
        "command": config.python_command,
    }));
    
    // Setup signal handling for graceful shutdown
    let running = Arc::new(AtomicBool::new(true));
    let r = running.clone();
    
    ctrlc::set_handler(move || {
        warn!("Received shutdown signal");
        r.store(false, Ordering::SeqCst);
    }).ok();
    
    // Main supervision loop
    let poll_interval = Duration::from_millis(config.poll_interval_ms);
    let mut consecutive_failures = 0u32;
    let mut last_log_time = Instant::now();
    let log_interval = Duration::from_secs(60);
    
    info!("Entering supervision loop (poll every {}ms)", config.poll_interval_ms);
    
    while running.load(Ordering::SeqCst) {
        let loop_start = Instant::now();
        
        // Check child process status (non-blocking)
        match child.try_wait() {
            Ok(Some(status)) => {
                // Child has exited
                let exit_code = status.code().unwrap_or(-1);
                warn!("Node exited with code {}", exit_code);
                
                log_event(&config.log_file, "NODE_EXITED", serde_json::json!({
                    "pid": child_pid,
                    "exit_code": exit_code,
                }));
                
                hardware.cleanup()?;
                return Ok(exit_code);
            }
            Ok(None) => {
                // Child still running
            }
            Err(e) => {
                error!("Failed to check child status: {}", e);
            }
        }
        
        // Check hardware signal
        match hardware.check_signal() {
            Ok(true) => {
                // Signal present - all good
                consecutive_failures = 0;
                debug!("Hardware signal OK");
            }
            Ok(false) => {
                // Signal lost!
                consecutive_failures += 1;
                warn!("Hardware signal LOST (failure {}/{})", 
                      consecutive_failures, config.max_failures);
                
                if consecutive_failures >= config.max_failures {
                    // KILL THE NODE
                    error!("╔═══════════════════════════════════════════════════════════╗");
                    error!("║  HARDWARE SIGNAL LOST - INITIATING EMERGENCY SHUTDOWN    ║");
                    error!("╚═══════════════════════════════════════════════════════════╝");
                    
                    let kill_start = Instant::now();
                    kill_node(&mut child)?;
                    let kill_time = kill_start.elapsed();
                    
                    log_event(&config.log_file, "EMERGENCY_KILL", serde_json::json!({
                        "pid": child_pid,
                        "reason": "hardware_signal_lost",
                        "consecutive_failures": consecutive_failures,
                        "kill_time_us": kill_time.as_micros(),
                    }));
                    
                    info!("Node killed in {:?}", kill_time);
                    hardware.cleanup()?;
                    return Ok(1);
                }
            }
            Err(e) => {
                // Hardware check failed
                consecutive_failures += 1;
                error!("Hardware check failed: {} (failure {}/{})", 
                       e, consecutive_failures, config.max_failures);
                
                if consecutive_failures >= config.max_failures && config.fail_closed {
                    error!("FAIL-CLOSED: Killing node due to hardware interface failure");
                    kill_node(&mut child)?;
                    
                    log_event(&config.log_file, "FAIL_CLOSED_KILL", serde_json::json!({
                        "pid": child_pid,
                        "reason": "hardware_interface_failure",
                        "error": e.to_string(),
                    }));
                    
                    hardware.cleanup()?;
                    return Ok(1);
                }
            }
        }
        
        // Periodic status log
        if last_log_time.elapsed() >= log_interval {
            info!("Sentinel heartbeat: node PID {} running, hardware OK", child_pid);
            last_log_time = Instant::now();
        }
        
        // Sleep until next poll
        let elapsed = loop_start.elapsed();
        if elapsed < poll_interval {
            thread::sleep(poll_interval - elapsed);
        }
    }
    
    // Graceful shutdown
    info!("Graceful shutdown requested");
    info!("Sending SIGTERM to node...");
    
    let nix_pid = Pid::from_raw(child_pid as i32);
    let _ = signal::kill(nix_pid, Signal::SIGTERM);
    
    // Wait up to 5 seconds for graceful exit
    let shutdown_start = Instant::now();
    let shutdown_timeout = Duration::from_secs(5);
    
    loop {
        if let Ok(Some(status)) = child.try_wait() {
            info!("Node exited gracefully with code {}", status.code().unwrap_or(-1));
            break;
        }
        
        if shutdown_start.elapsed() >= shutdown_timeout {
            warn!("Graceful shutdown timeout - sending SIGKILL");
            kill_node(&mut child)?;
            break;
        }
        
        thread::sleep(Duration::from_millis(100));
    }
    
    log_event(&config.log_file, "SENTINEL_STOP", serde_json::json!({
        "reason": "graceful_shutdown",
    }));
    
    hardware.cleanup()?;
    Ok(0)
}

// ============================================================================
// Entry Point
// ============================================================================

fn main() {
    // Initialize logging
    env_logger::Builder::from_env(
        env_logger::Env::default().default_filter_or("info")
    ).init();
    
    info!("Titan Sentinel v{}", env!("CARGO_PKG_VERSION"));
    
    // Load configuration from environment or defaults
    let config = SentinelConfig {
        hardware_type: env::var("SENTINEL_HARDWARE")
            .unwrap_or_else(|_| "mock".to_string()),
        gpio_pin: env::var("SENTINEL_GPIO_PIN")
            .ok()
            .and_then(|s| s.parse().ok()),
        serial_port: env::var("SENTINEL_SERIAL_PORT").ok(),
        serial_baud: env::var("SENTINEL_SERIAL_BAUD")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(9600),
        poll_interval_ms: env::var("SENTINEL_POLL_MS")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(50),
        max_failures: env::var("SENTINEL_MAX_FAILURES")
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(3),
        python_command: env::var("SENTINEL_PYTHON_CMD")
            .map(|s| s.split_whitespace().map(String::from).collect())
            .unwrap_or_else(|_| vec![
                "python3".to_string(),
                "-m".to_string(),
                "modules.core.node".to_string(),
            ]),
        work_dir: env::var("SENTINEL_WORK_DIR")
            .unwrap_or_else(|_| "/app".to_string()),
        log_file: env::var("SENTINEL_LOG_FILE")
            .unwrap_or_else(|_| "/var/log/sentinel.json".to_string()),
        fail_closed: env::var("SENTINEL_FAIL_CLOSED")
            .map(|s| s != "0" && s.to_lowercase() != "false")
            .unwrap_or(true),
    };
    
    info!("Configuration: {:?}", config);
    
    // Run the sentinel
    match run_sentinel(config) {
        Ok(exit_code) => {
            info!("Sentinel exiting with code {}", exit_code);
            std::process::exit(exit_code);
        }
        Err(e) => {
            error!("Sentinel fatal error: {}", e);
            std::process::exit(1);
        }
    }
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;
    
    #[test]
    fn test_mock_hardware_signal_present() {
        let dir = tempdir().unwrap();
        let signal_file = dir.path().join("signal");
        fs::write(&signal_file, "1").unwrap();
        
        env::set_var("SENTINEL_SIGNAL_FILE", signal_file.to_str().unwrap());
        
        let mut hw = MockHardware::new();
        hw.signal_file = signal_file.to_str().unwrap().to_string();
        
        assert!(hw.check_signal().unwrap());
    }
    
    #[test]
    fn test_mock_hardware_signal_absent() {
        let dir = tempdir().unwrap();
        let signal_file = dir.path().join("signal");
        fs::write(&signal_file, "0").unwrap();
        
        let mut hw = MockHardware::new();
        hw.signal_file = signal_file.to_str().unwrap().to_string();
        
        assert!(!hw.check_signal().unwrap());
    }
    
    #[test]
    fn test_mock_hardware_signal_missing() {
        let mut hw = MockHardware::new();
        hw.signal_file = "/nonexistent/path/signal".to_string();
        
        // Missing file = no signal (fail-closed)
        assert!(!hw.check_signal().unwrap());
    }
    
    #[test]
    fn test_config_defaults() {
        let config = SentinelConfig::default();
        assert_eq!(config.hardware_type, "mock");
        assert_eq!(config.poll_interval_ms, 50);
        assert_eq!(config.max_failures, 3);
        assert!(config.fail_closed);
    }
}
