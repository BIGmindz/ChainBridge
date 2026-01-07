// ═══════════════════════════════════════════════════════════════════════════════
// PAC-OCC-P25-LEDGER-SYNC — Atomic Ledger Operations
// Lane 2 (DEVELOPER / GID-CODY) Implementation
// Governance Tier: LAW
// Invariant: ATOMIC_WRITE | MUTEX_LOCK | FAIL_CLOSED
// ═══════════════════════════════════════════════════════════════════════════════
//!
//! # Atomic Ledger Module
//!
//! This module provides thread-safe, atomic operations for the GOVERNANCE_LEDGER.
//! All writes are protected by file-level locks and use write-ahead logging.
//!
//! ## Safety Contract
//!
//! 1. **Lock Acquisition**: Must acquire exclusive lock before any write
//! 2. **Atomic Write**: Write to temp file → fsync → rename
//! 3. **Sequence Monotonicity**: Sequence numbers strictly increasing
//! 4. **Fail-Closed**: Lock timeout or any error → reject operation
//!
//! ## Lock Protocol (WRAP-P25-L7-MUTEX-DESIGN)
//!
//! ```text
//! ┌─────────────────────────────────────────────────────────────┐
//! │  1. ACQUIRE exclusive lock (5s timeout)                    │
//! │  2. READ current ledger state                              │
//! │  3. VALIDATE sequence number (must be next in sequence)    │
//! │  4. WRITE to temporary file (.ledger.tmp)                  │
//! │  5. FSYNC to ensure durability                             │
//! │  6. RENAME temp → ledger (atomic on POSIX)                 │
//! │  7. RELEASE lock                                           │
//! └─────────────────────────────────────────────────────────────┘
//! ```

use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::time::Duration;

use fs2::FileExt;
use serde::{Deserialize, Serialize};

use crate::models::PdoOutcome;

// ═══════════════════════════════════════════════════════════════════════════════
// ERROR CODES
// ═══════════════════════════════════════════════════════════════════════════════

/// Ledger operation error codes (FFI-compatible).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(i32)]
pub enum LedgerError {
    /// Success
    Success = 0,
    /// Failed to acquire lock (timeout or contention)
    LockFailed = -10,
    /// Lock timeout exceeded
    LockTimeout = -11,
    /// Failed to read ledger file
    ReadFailed = -12,
    /// Failed to parse ledger JSON
    ParseFailed = -13,
    /// Sequence number mismatch (not next in sequence)
    SequenceMismatch = -14,
    /// Failed to write temporary file
    WriteFailed = -15,
    /// Failed to sync to disk
    SyncFailed = -16,
    /// Failed to rename (atomic commit)
    RenameFailed = -17,
    /// Invalid entry data
    InvalidEntry = -18,
    /// Ledger file not found (will create new)
    NotFound = -19,
}

impl From<LedgerError> for i32 {
    fn from(e: LedgerError) -> i32 {
        e as i32
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// LEDGER STRUCTURES
// ═══════════════════════════════════════════════════════════════════════════════

/// A single entry in the governance ledger.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LedgerEntry {
    /// Monotonically increasing sequence number
    pub sequence: u64,
    /// Timestamp of the entry (ISO 8601)
    pub timestamp: String,
    /// Type of entry (WRAP, BER, PAC, etc.)
    pub entry_type: String,
    /// Unique identifier for the entry
    pub entry_id: String,
    /// GID of the issuing agent
    pub issuer_gid: String,
    /// Lane number (1-8)
    pub lane: Option<u8>,
    /// Reference to parent PAC
    pub pac_ref: Option<String>,
    /// Outcome if this is a BER
    pub outcome: Option<String>,
    /// Summary/description
    pub summary: String,
    /// SHA-256 hash of entry content
    pub content_hash: String,
    /// Git commit hash (if committed)
    pub commit_hash: Option<String>,
}

/// The complete governance ledger.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GovernanceLedger {
    /// Ledger version
    pub version: String,
    /// Last updated timestamp
    pub last_updated: String,
    /// Current sequence number (next entry gets this + 1)
    pub current_sequence: u64,
    /// All ledger entries
    pub entries: Vec<LedgerEntry>,
}

impl Default for GovernanceLedger {
    fn default() -> Self {
        Self {
            version: "1.0.0".to_string(),
            last_updated: chrono::Utc::now().to_rfc3339(),
            current_sequence: 0,
            entries: Vec::new(),
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// ATOMIC LEDGER WRITER
// ═══════════════════════════════════════════════════════════════════════════════

/// Configuration for ledger operations.
#[derive(Debug, Clone)]
pub struct LedgerConfig {
    /// Path to the ledger file
    pub ledger_path: PathBuf,
    /// Lock timeout duration
    pub lock_timeout: Duration,
    /// Whether to create ledger if not exists
    pub create_if_missing: bool,
}

impl Default for LedgerConfig {
    fn default() -> Self {
        Self {
            ledger_path: PathBuf::from("GOVERNANCE_LEDGER.json"),
            lock_timeout: Duration::from_secs(5),
            create_if_missing: true,
        }
    }
}

/// Atomic ledger writer with file-level locking.
pub struct AtomicLedgerWriter {
    config: LedgerConfig,
}

impl AtomicLedgerWriter {
    /// Create a new atomic ledger writer.
    pub fn new(config: LedgerConfig) -> Self {
        Self { config }
    }

    /// Create with default configuration and custom path.
    pub fn with_path<P: AsRef<Path>>(path: P) -> Self {
        Self::new(LedgerConfig {
            ledger_path: path.as_ref().to_path_buf(),
            ..Default::default()
        })
    }

    /// Get the temporary file path for write-ahead.
    fn temp_path(&self) -> PathBuf {
        let mut temp = self.config.ledger_path.clone();
        temp.set_extension("ledger.tmp");
        temp
    }

    /// Get the lock file path.
    fn lock_path(&self) -> PathBuf {
        let mut lock = self.config.ledger_path.clone();
        lock.set_extension("ledger.lock");
        lock
    }

    /// Acquire an exclusive lock on the ledger.
    fn acquire_lock(&self) -> Result<File, LedgerError> {
        // Create lock file if it doesn't exist
        let lock_file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(self.lock_path())
            .map_err(|_| LedgerError::LockFailed)?;

        // Try to acquire exclusive lock with timeout
        // fs2 doesn't have timeout, so we use try_lock in a loop
        let start = std::time::Instant::now();
        loop {
            match lock_file.try_lock_exclusive() {
                Ok(()) => return Ok(lock_file),
                Err(_) => {
                    if start.elapsed() >= self.config.lock_timeout {
                        return Err(LedgerError::LockTimeout);
                    }
                    std::thread::sleep(Duration::from_millis(10));
                }
            }
        }
    }

    /// Read the current ledger state.
    fn read_ledger(&self) -> Result<GovernanceLedger, LedgerError> {
        if !self.config.ledger_path.exists() {
            if self.config.create_if_missing {
                return Ok(GovernanceLedger::default());
            } else {
                return Err(LedgerError::NotFound);
            }
        }

        let mut file = File::open(&self.config.ledger_path)
            .map_err(|_| LedgerError::ReadFailed)?;
        
        let mut content = String::new();
        file.read_to_string(&mut content)
            .map_err(|_| LedgerError::ReadFailed)?;

        serde_json::from_str(&content)
            .map_err(|_| LedgerError::ParseFailed)
    }

    /// Write ledger atomically using write-ahead pattern.
    fn write_ledger_atomic(&self, ledger: &GovernanceLedger) -> Result<(), LedgerError> {
        let temp_path = self.temp_path();

        // Step 1: Write to temporary file
        let mut temp_file = File::create(&temp_path)
            .map_err(|_| LedgerError::WriteFailed)?;
        
        let json = serde_json::to_string_pretty(ledger)
            .map_err(|_| LedgerError::WriteFailed)?;
        
        temp_file.write_all(json.as_bytes())
            .map_err(|_| LedgerError::WriteFailed)?;

        // Step 2: Fsync to ensure durability
        temp_file.sync_all()
            .map_err(|_| LedgerError::SyncFailed)?;

        // Step 3: Atomic rename (POSIX guarantees atomicity)
        fs::rename(&temp_path, &self.config.ledger_path)
            .map_err(|_| LedgerError::RenameFailed)?;

        Ok(())
    }

    /// Append an entry to the ledger atomically.
    ///
    /// This is the main public API for adding entries.
    /// It handles lock acquisition, sequence validation, and atomic write.
    pub fn append_entry(&self, mut entry: LedgerEntry) -> Result<u64, LedgerError> {
        // Step 1: Acquire exclusive lock
        let lock_file = self.acquire_lock()?;

        // Step 2: Read current state
        let mut ledger = self.read_ledger()?;

        // Step 3: Assign next sequence number
        let next_seq = ledger.current_sequence + 1;
        entry.sequence = next_seq;

        // Step 4: Validate entry
        if entry.entry_id.is_empty() || entry.entry_type.is_empty() {
            // Release lock by dropping
            drop(lock_file);
            return Err(LedgerError::InvalidEntry);
        }

        // Step 5: Update ledger
        ledger.current_sequence = next_seq;
        ledger.last_updated = chrono::Utc::now().to_rfc3339();
        ledger.entries.push(entry);

        // Step 6: Atomic write
        self.write_ledger_atomic(&ledger)?;

        // Step 7: Release lock (automatic on drop)
        drop(lock_file);

        Ok(next_seq)
    }

    /// Get the current sequence number without modifying the ledger.
    pub fn current_sequence(&self) -> Result<u64, LedgerError> {
        let _lock = self.acquire_lock()?;
        let ledger = self.read_ledger()?;
        Ok(ledger.current_sequence)
    }

    /// Read all entries (read-only, still acquires lock for consistency).
    pub fn read_entries(&self) -> Result<Vec<LedgerEntry>, LedgerError> {
        let _lock = self.acquire_lock()?;
        let ledger = self.read_ledger()?;
        Ok(ledger.entries)
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

/// Compute SHA-256 hash of content.
pub fn compute_content_hash(content: &str) -> String {
    use sha2::{Sha256, Digest};
    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    hex::encode(hasher.finalize())
}

/// Create a WRAP entry.
pub fn create_wrap_entry(
    wrap_id: &str,
    issuer_gid: &str,
    lane: u8,
    pac_ref: &str,
    summary: &str,
) -> LedgerEntry {
    let content = format!("{}:{}:{}:{}", wrap_id, issuer_gid, pac_ref, summary);
    LedgerEntry {
        sequence: 0, // Will be assigned by append_entry
        timestamp: chrono::Utc::now().to_rfc3339(),
        entry_type: "WRAP".to_string(),
        entry_id: wrap_id.to_string(),
        issuer_gid: issuer_gid.to_string(),
        lane: Some(lane),
        pac_ref: Some(pac_ref.to_string()),
        outcome: None,
        summary: summary.to_string(),
        content_hash: compute_content_hash(&content),
        commit_hash: None,
    }
}

/// Create a BER entry.
pub fn create_ber_entry(
    ber_id: &str,
    issuer_gid: &str,
    pac_ref: &str,
    outcome: PdoOutcome,
    summary: &str,
) -> LedgerEntry {
    let outcome_str = match outcome {
        PdoOutcome::Approved => "APPROVED",
        PdoOutcome::Rejected => "REJECTED",
        PdoOutcome::RequiresReview => "REQUIRES_REVIEW",
        PdoOutcome::Error => "ERROR",
    };
    let content = format!("{}:{}:{}:{}:{}", ber_id, issuer_gid, pac_ref, outcome_str, summary);
    LedgerEntry {
        sequence: 0,
        timestamp: chrono::Utc::now().to_rfc3339(),
        entry_type: "BER".to_string(),
        entry_id: ber_id.to_string(),
        issuer_gid: issuer_gid.to_string(),
        lane: None,
        pac_ref: Some(pac_ref.to_string()),
        outcome: Some(outcome_str.to_string()),
        summary: summary.to_string(),
        content_hash: compute_content_hash(&content),
        commit_hash: None,
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// TESTS
// ═══════════════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::thread;

    #[test]
    fn test_ledger_default() {
        let ledger = GovernanceLedger::default();
        assert_eq!(ledger.version, "1.0.0");
        assert_eq!(ledger.current_sequence, 0);
        assert!(ledger.entries.is_empty());
    }

    #[test]
    fn test_content_hash() {
        let hash = compute_content_hash("test content");
        assert_eq!(hash.len(), 64); // SHA-256 = 32 bytes = 64 hex chars
    }

    #[test]
    fn test_create_wrap_entry() {
        let entry = create_wrap_entry(
            "WRAP-TEST-001",
            "GID-01",
            2,
            "PAC-TEST",
            "Test wrap entry",
        );
        assert_eq!(entry.entry_type, "WRAP");
        assert_eq!(entry.lane, Some(2));
        assert!(!entry.content_hash.is_empty());
    }

    #[test]
    fn test_create_ber_entry() {
        let entry = create_ber_entry(
            "BER-TEST-001",
            "GID-00",
            "PAC-TEST",
            PdoOutcome::Approved,
            "Test BER entry",
        );
        assert_eq!(entry.entry_type, "BER");
        assert_eq!(entry.outcome, Some("APPROVED".to_string()));
    }

    #[test]
    fn test_atomic_write_single_thread() {
        let temp_dir = std::env::temp_dir().join("ledger_test_single");
        let _ = fs::remove_dir_all(&temp_dir);
        fs::create_dir_all(&temp_dir).unwrap();
        
        let ledger_path = temp_dir.join("test_ledger.json");
        let writer = AtomicLedgerWriter::with_path(&ledger_path);

        // Append first entry
        let entry1 = create_wrap_entry("WRAP-001", "GID-01", 2, "PAC-001", "First entry");
        let seq1 = writer.append_entry(entry1).unwrap();
        assert_eq!(seq1, 1);

        // Append second entry
        let entry2 = create_wrap_entry("WRAP-002", "GID-02", 3, "PAC-001", "Second entry");
        let seq2 = writer.append_entry(entry2).unwrap();
        assert_eq!(seq2, 2);

        // Verify
        let entries = writer.read_entries().unwrap();
        assert_eq!(entries.len(), 2);
        assert_eq!(entries[0].sequence, 1);
        assert_eq!(entries[1].sequence, 2);

        // Cleanup
        let _ = fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_atomic_write_concurrent() {
        let temp_dir = std::env::temp_dir().join("ledger_test_concurrent");
        let _ = fs::remove_dir_all(&temp_dir);
        fs::create_dir_all(&temp_dir).unwrap();
        
        let ledger_path = temp_dir.join("test_ledger.json");
        let ledger_path = Arc::new(ledger_path);
        
        let num_threads = 8;
        let entries_per_thread = 10;
        let mut handles = vec![];

        for thread_id in 0..num_threads {
            let path = Arc::clone(&ledger_path);
            let handle = thread::spawn(move || {
                let writer = AtomicLedgerWriter::with_path(path.as_ref());
                let mut sequences = vec![];
                
                for i in 0..entries_per_thread {
                    let entry = create_wrap_entry(
                        &format!("WRAP-T{}-{}", thread_id, i),
                        &format!("GID-{:02}", thread_id),
                        (thread_id % 8 + 1) as u8,
                        "PAC-CONCURRENT",
                        &format!("Thread {} entry {}", thread_id, i),
                    );
                    match writer.append_entry(entry) {
                        Ok(seq) => sequences.push(seq),
                        Err(e) => panic!("Thread {} failed: {:?}", thread_id, e),
                    }
                }
                sequences
            });
            handles.push(handle);
        }

        // Collect all sequences
        let mut all_sequences: Vec<u64> = vec![];
        for handle in handles {
            let sequences = handle.join().unwrap();
            all_sequences.extend(sequences);
        }

        // Verify all sequences are unique and contiguous
        all_sequences.sort();
        let expected_total = num_threads * entries_per_thread;
        assert_eq!(all_sequences.len(), expected_total);
        
        // Check sequence numbers are 1..=total
        for (i, seq) in all_sequences.iter().enumerate() {
            assert_eq!(*seq, (i + 1) as u64, "Sequence mismatch at index {}", i);
        }

        // Verify ledger file
        let writer = AtomicLedgerWriter::with_path(ledger_path.as_ref());
        let entries = writer.read_entries().unwrap();
        assert_eq!(entries.len(), expected_total);

        // Cleanup
        let _ = fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_lock_timeout() {
        let temp_dir = std::env::temp_dir().join("ledger_test_timeout");
        let _ = fs::remove_dir_all(&temp_dir);
        fs::create_dir_all(&temp_dir).unwrap();
        
        let ledger_path = temp_dir.join("test_ledger.json");
        
        // Create writer with very short timeout
        let config = LedgerConfig {
            ledger_path: ledger_path.clone(),
            lock_timeout: Duration::from_millis(100),
            create_if_missing: true,
        };
        let writer1 = AtomicLedgerWriter::new(config.clone());
        
        // Acquire lock from first writer
        let lock_file = writer1.acquire_lock().unwrap();
        
        // Try to acquire from second writer (should timeout)
        let writer2 = AtomicLedgerWriter::new(config);
        let result = writer2.acquire_lock();
        
        assert!(matches!(result, Err(LedgerError::LockTimeout)));
        
        // Release first lock
        drop(lock_file);
        
        // Now second writer should succeed
        let lock_file2 = writer2.acquire_lock();
        assert!(lock_file2.is_ok());

        // Cleanup
        let _ = fs::remove_dir_all(&temp_dir);
    }
}
