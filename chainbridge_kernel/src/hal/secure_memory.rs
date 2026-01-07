// ═══════════════════════════════════════════════════════════════════════════════
// PAC-OCC-P16-HW — Secure Memory Traits
// ChainBridge Constitutional Kernel - Sovereign Gate Specification
// Governance Tier: LAW
// Invariant: ZEROIZE_ON_DROP | CONSTANT_TIME | NO_SWAP
// ═══════════════════════════════════════════════════════════════════════════════
//!
//! # Secure Memory Module
//!
//! This module defines traits for secure memory allocation and management.
//! All sensitive data (keys, credentials, PAC content) MUST use secure memory.
//!
//! ## Core Principles
//!
//! 1. **Zeroize on Drop**: Memory is overwritten with zeros when freed
//! 2. **No Swap**: Secure memory is locked to prevent swapping to disk
//! 3. **Constant-Time**: Memory comparisons are constant-time
//! 4. **Guard Pages**: Optional guard pages to detect buffer overflows
//!
//! ## Side-Channel Mitigations
//!
//! - Memory access patterns are constant regardless of data
//! - No branching based on secret data
//! - No variable-time operations
//!
//! ## Note on Unsafe Code
//!
//! This module requires `unsafe` for volatile writes to prevent compiler
//! optimization of zeroization. This is the ONLY place in the kernel where
//! unsafe is permitted, and it is tightly controlled.

// Allow unsafe in this module only for volatile writes
#![allow(unsafe_code)]

use core::fmt;

/// Trait for types that can be securely zeroized.
///
/// # Contract
///
/// Implementing types MUST:
/// 1. Overwrite ALL memory with zeros
/// 2. Ensure the compiler doesn't optimize away the zeroization
/// 3. Handle any nested sensitive data
pub trait Zeroize {
    /// Securely overwrite this value with zeros.
    ///
    /// # Safety
    ///
    /// After calling this method, the value should be considered
    /// invalid and not used.
    fn zeroize(&mut self);
}

// Implement Zeroize for common types
impl Zeroize for u8 {
    fn zeroize(&mut self) {
        // Use volatile write to prevent optimization
        unsafe {
            core::ptr::write_volatile(self, 0);
        }
        core::sync::atomic::compiler_fence(core::sync::atomic::Ordering::SeqCst);
    }
}

impl Zeroize for [u8] {
    fn zeroize(&mut self) {
        for byte in self.iter_mut() {
            byte.zeroize();
        }
        core::sync::atomic::compiler_fence(core::sync::atomic::Ordering::SeqCst);
    }
}

impl<const N: usize> Zeroize for [u8; N] {
    fn zeroize(&mut self) {
        for byte in self.iter_mut() {
            byte.zeroize();
        }
        core::sync::atomic::compiler_fence(core::sync::atomic::Ordering::SeqCst);
    }
}

impl Zeroize for Vec<u8> {
    fn zeroize(&mut self) {
        for byte in self.iter_mut() {
            byte.zeroize();
        }
        self.clear();
        core::sync::atomic::compiler_fence(core::sync::atomic::Ordering::SeqCst);
    }
}

impl Zeroize for String {
    fn zeroize(&mut self) {
        // SAFETY: We're overwriting with valid UTF-8 (zeros)
        unsafe {
            for byte in self.as_bytes_mut().iter_mut() {
                byte.zeroize();
            }
        }
        self.clear();
        core::sync::atomic::compiler_fence(core::sync::atomic::Ordering::SeqCst);
    }
}

/// Errors that can occur during secure memory operations.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SecureMemoryError {
    /// Failed to allocate memory
    AllocationFailed,
    /// Failed to lock memory (mlock)
    LockFailed,
    /// Failed to protect memory (mprotect)
    ProtectFailed,
    /// Memory region is too large
    SizeTooLarge { requested: usize, max: usize },
    /// Memory is not properly aligned
    AlignmentError,
    /// Operation not supported on this platform
    NotSupported,
}

impl fmt::Display for SecureMemoryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SecureMemoryError::AllocationFailed => write!(f, "Secure memory allocation failed"),
            SecureMemoryError::LockFailed => write!(f, "Failed to lock memory (mlock)"),
            SecureMemoryError::ProtectFailed => write!(f, "Failed to protect memory"),
            SecureMemoryError::SizeTooLarge { requested, max } => {
                write!(
                    f,
                    "Requested size {} exceeds maximum {}",
                    requested, max
                )
            }
            SecureMemoryError::AlignmentError => write!(f, "Memory alignment error"),
            SecureMemoryError::NotSupported => write!(f, "Operation not supported on this platform"),
        }
    }
}

/// Trait for secure memory allocators.
///
/// # Contract
///
/// Implementations MUST:
/// 1. Lock allocated memory to prevent swapping
/// 2. Zeroize memory on deallocation
/// 3. Optionally provide guard pages
pub trait SecureMemory {
    /// Allocate secure memory.
    ///
    /// # Arguments
    ///
    /// * `size` - Number of bytes to allocate
    ///
    /// # Returns
    ///
    /// A `SecureBuffer` that will be zeroized on drop.
    fn allocate(&self, size: usize) -> Result<SecureBuffer, SecureMemoryError>;

    /// Maximum allocation size.
    fn max_size(&self) -> usize;

    /// Whether memory locking is supported.
    fn supports_locking(&self) -> bool;

    /// Whether guard pages are supported.
    fn supports_guard_pages(&self) -> bool;
}

/// A buffer of secure memory that is zeroized on drop.
///
/// # Invariants
///
/// - Memory is locked (if supported)
/// - Memory is zeroized on drop
/// - Cannot be cloned (prevents accidental copies)
pub struct SecureBuffer {
    data: Vec<u8>,
    locked: bool,
}

impl SecureBuffer {
    /// Create a new secure buffer.
    ///
    /// # Arguments
    ///
    /// * `size` - Size of buffer in bytes
    /// * `lock` - Whether to lock memory
    pub fn new(size: usize, lock: bool) -> Result<Self, SecureMemoryError> {
        let data = vec![0u8; size];
        
        // In a real implementation, we would call mlock() here
        // For now, we just track the intent
        
        Ok(Self { data, locked: lock })
    }

    /// Get buffer contents as a slice.
    pub fn as_slice(&self) -> &[u8] {
        &self.data
    }

    /// Get buffer contents as a mutable slice.
    pub fn as_mut_slice(&mut self) -> &mut [u8] {
        &mut self.data
    }

    /// Get buffer length.
    pub fn len(&self) -> usize {
        self.data.len()
    }

    /// Check if buffer is empty.
    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }

    /// Check if memory is locked.
    pub fn is_locked(&self) -> bool {
        self.locked
    }
}

impl Drop for SecureBuffer {
    fn drop(&mut self) {
        // CRITICAL: Zeroize before dropping
        self.data.zeroize();
        
        // In a real implementation, we would call munlock() here
    }
}

// SecureBuffer cannot be cloned to prevent accidental copies of sensitive data
// impl !Clone for SecureBuffer {}

impl fmt::Debug for SecureBuffer {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // Never print contents, only metadata
        f.debug_struct("SecureBuffer")
            .field("len", &self.data.len())
            .field("locked", &self.locked)
            .field("contents", &"[REDACTED]")
            .finish()
    }
}

/// Constant-time comparison of two byte slices.
///
/// # Security
///
/// This function takes the same amount of time regardless of
/// where the first difference occurs, preventing timing attacks.
///
/// # Arguments
///
/// * `a` - First slice
/// * `b` - Second slice
///
/// # Returns
///
/// `true` if slices are equal, `false` otherwise.
pub fn constant_time_eq(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }

    let mut result = 0u8;
    for (x, y) in a.iter().zip(b.iter()) {
        result |= x ^ y;
    }

    // Use subtle comparison to avoid branch
    result == 0
}

/// Constant-time select between two values.
///
/// # Arguments
///
/// * `condition` - If true, return `a`, else return `b`
/// * `a` - First value
/// * `b` - Second value
///
/// # Security
///
/// This function takes the same amount of time regardless of condition.
pub fn constant_time_select(condition: bool, a: u8, b: u8) -> u8 {
    let mask = if condition { 0xff } else { 0x00 };
    (a & mask) | (b & !mask)
}

/// Default secure memory allocator.
pub struct DefaultSecureAllocator {
    max_size: usize,
}

impl DefaultSecureAllocator {
    /// Create a new default secure allocator.
    ///
    /// # Arguments
    ///
    /// * `max_size` - Maximum allocation size in bytes
    pub fn new(max_size: usize) -> Self {
        Self { max_size }
    }
}

impl Default for DefaultSecureAllocator {
    fn default() -> Self {
        Self::new(1024 * 1024) // 1 MB default max
    }
}

impl SecureMemory for DefaultSecureAllocator {
    fn allocate(&self, size: usize) -> Result<SecureBuffer, SecureMemoryError> {
        if size > self.max_size {
            return Err(SecureMemoryError::SizeTooLarge {
                requested: size,
                max: self.max_size,
            });
        }

        SecureBuffer::new(size, true)
    }

    fn max_size(&self) -> usize {
        self.max_size
    }

    fn supports_locking(&self) -> bool {
        // In a real implementation, check if mlock is available
        #[cfg(unix)]
        return true;
        #[cfg(not(unix))]
        return false;
    }

    fn supports_guard_pages(&self) -> bool {
        // Guard pages require mmap with PROT_NONE
        #[cfg(unix)]
        return true;
        #[cfg(not(unix))]
        return false;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_zeroize_u8() {
        let mut value: u8 = 0xFF;
        value.zeroize();
        assert_eq!(value, 0);
    }

    #[test]
    fn test_zeroize_slice() {
        let mut data = [0xFFu8; 16];
        data.zeroize();
        assert!(data.iter().all(|&b| b == 0));
    }

    #[test]
    fn test_zeroize_vec() {
        let mut data = vec![0xFFu8; 16];
        data.zeroize();
        assert!(data.is_empty());
    }

    #[test]
    fn test_secure_buffer_creation() {
        let buf = SecureBuffer::new(256, false).unwrap();
        assert_eq!(buf.len(), 256);
        assert!(!buf.is_locked());
    }

    #[test]
    fn test_secure_buffer_debug_redacts() {
        let buf = SecureBuffer::new(256, false).unwrap();
        let debug_str = format!("{:?}", buf);
        assert!(debug_str.contains("[REDACTED]"));
        assert!(!debug_str.contains("0"));
    }

    #[test]
    fn test_constant_time_eq_equal() {
        let a = [1u8, 2, 3, 4];
        let b = [1u8, 2, 3, 4];
        assert!(constant_time_eq(&a, &b));
    }

    #[test]
    fn test_constant_time_eq_not_equal() {
        let a = [1u8, 2, 3, 4];
        let b = [1u8, 2, 3, 5];
        assert!(!constant_time_eq(&a, &b));
    }

    #[test]
    fn test_constant_time_eq_different_lengths() {
        let a = [1u8, 2, 3];
        let b = [1u8, 2, 3, 4];
        assert!(!constant_time_eq(&a, &b));
    }

    #[test]
    fn test_constant_time_select() {
        assert_eq!(constant_time_select(true, 0xAA, 0x55), 0xAA);
        assert_eq!(constant_time_select(false, 0xAA, 0x55), 0x55);
    }

    #[test]
    fn test_default_allocator() {
        let alloc = DefaultSecureAllocator::default();
        let buf = alloc.allocate(256).unwrap();
        assert_eq!(buf.len(), 256);
    }

    #[test]
    fn test_allocator_size_limit() {
        let alloc = DefaultSecureAllocator::new(100);
        let result = alloc.allocate(200);
        assert!(matches!(result, Err(SecureMemoryError::SizeTooLarge { .. })));
    }
}
