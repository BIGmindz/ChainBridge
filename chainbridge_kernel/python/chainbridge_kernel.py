"""
PAC-OCC-P23-FFI-BRIDGE — Python FFI Wrapper
Lane 2 (DEVELOPER / GID-CODY) Implementation
Governance Tier: LAW
Invariant: CTYPES_STRICT | TYPE_SAFE | MEMORY_MANAGED

ChainBridge Constitutional Kernel FFI Wrapper
=============================================

This module provides Python bindings to the Rust Constitutional Kernel
via the Foreign Function Interface (FFI).

Usage:
    from chainbridge_kernel import KernelBridge

    bridge = KernelBridge()
    result = bridge.validate_pac(pac_json, "GID-00-EXEC")
    
    if result.approved:
        print("PAC Approved")
    else:
        print(f"PAC Rejected: {result.gates_passed}/{result.gates_total} gates passed")
"""

import ctypes
import json
import os
import platform
import time
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any, Dict, Optional, Union


# ═══════════════════════════════════════════════════════════════════════════════
# FFI ERROR CODES (must match ffi.rs)
# ═══════════════════════════════════════════════════════════════════════════════

class FfiErrorCode(IntEnum):
    """FFI error codes from the Rust kernel."""
    SUCCESS = 0
    PANIC = -1
    NULL_PTR = -2
    JSON_PARSE = -3
    VALIDATION_FAILED = -4
    UTF8 = -5


# ═══════════════════════════════════════════════════════════════════════════════
# FFI STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class FfiValidationResult(ctypes.Structure):
    """
    FFI-safe validation result structure.
    
    Must match the Rust `FfiValidationResult` struct exactly.
    
    Note: We use c_void_p for pdo_json to avoid ctypes auto-conversion
    issues. The pointer is manually cast when reading.
    """
    _fields_ = [
        ("error_code", ctypes.c_int),
        ("outcome", ctypes.c_int),
        ("gates_passed", ctypes.c_int),
        ("gates_total", ctypes.c_int),
        ("pdo_json", ctypes.c_void_p),  # Raw pointer - DO NOT use c_char_p
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# PYTHON RESULT CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ValidationResult:
    """Python-friendly validation result."""
    
    approved: bool
    """Whether the PAC was approved."""
    
    gates_passed: int
    """Number of gates that passed."""
    
    gates_total: int
    """Total number of gates."""
    
    pdo: Optional[Dict[str, Any]]
    """Full Policy Decision Object (parsed JSON)."""
    
    error_code: FfiErrorCode
    """FFI error code (SUCCESS if no error)."""
    
    error_message: Optional[str] = None
    """Human-readable error message if failed."""
    
    @property
    def rejected(self) -> bool:
        """Whether the PAC was rejected."""
        return not self.approved
    
    @property
    def all_gates_passed(self) -> bool:
        """Whether all gates passed."""
        return self.gates_passed == self.gates_total


@dataclass
class KernelInfo:
    """Information about the loaded kernel."""
    
    version: str
    """Kernel version string."""
    
    gate_count: int
    """Number of pre-flight gates."""
    
    library_path: str
    """Path to the loaded shared library."""


# ═══════════════════════════════════════════════════════════════════════════════
# KERNEL BRIDGE
# ═══════════════════════════════════════════════════════════════════════════════

class KernelBridge:
    """
    Python bridge to the ChainBridge Constitutional Kernel.
    
    This class loads the Rust shared library and provides a Pythonic
    interface to the kernel's validation functions.
    
    Example:
        >>> bridge = KernelBridge()
        >>> print(bridge.info)
        KernelInfo(version='2.1.3-sovereign', gate_count=9, ...)
        
        >>> result = bridge.validate_pac(pac_json, "GID-00-EXEC")
        >>> if result.approved:
        ...     print("Validation passed!")
    """
    
    def __init__(self, library_path: Optional[str] = None):
        """
        Initialize the kernel bridge.
        
        Args:
            library_path: Path to the shared library. If None, searches
                          in standard locations.
        
        Raises:
            FileNotFoundError: If the library cannot be found.
            OSError: If the library cannot be loaded.
        """
        self._lib_path = library_path or self._find_library()
        self._lib = ctypes.CDLL(self._lib_path)
        self._setup_functions()
        self._info: Optional[KernelInfo] = None
    
    def _find_library(self) -> str:
        """Find the shared library in standard locations."""
        # Determine library extension based on platform
        system = platform.system()
        if system == "Darwin":
            ext = ".dylib"
            lib_name = "libchainbridge_kernel"
        elif system == "Linux":
            ext = ".so"
            lib_name = "libchainbridge_kernel"
        elif system == "Windows":
            ext = ".dll"
            lib_name = "chainbridge_kernel"
        else:
            raise OSError(f"Unsupported platform: {system}")
        
        # Search paths
        search_paths = [
            # Development: relative to this file
            Path(__file__).parent.parent / "chainbridge_kernel" / "target" / "release" / f"{lib_name}{ext}",
            Path(__file__).parent.parent / "chainbridge_kernel" / "target" / "debug" / f"{lib_name}{ext}",
            # Installed: system paths
            Path(f"/usr/local/lib/{lib_name}{ext}"),
            Path(f"/usr/lib/{lib_name}{ext}"),
            # Current directory
            Path(f"./{lib_name}{ext}"),
        ]
        
        # Also check CHAINBRIDGE_KERNEL_LIB environment variable
        env_path = os.environ.get("CHAINBRIDGE_KERNEL_LIB")
        if env_path:
            search_paths.insert(0, Path(env_path))
        
        for path in search_paths:
            if path.exists():
                return str(path)
        
        raise FileNotFoundError(
            f"Could not find {lib_name}{ext}. "
            f"Set CHAINBRIDGE_KERNEL_LIB or build with 'cargo build --release'"
        )
    
    def _setup_functions(self) -> None:
        """Configure ctypes function signatures."""
        # ffi_validate_pac
        self._lib.ffi_validate_pac.argtypes = [
            ctypes.c_char_p,  # pac_json
            ctypes.c_char_p,  # executor_gid
            ctypes.c_int64,   # admission_epoch_secs
        ]
        self._lib.ffi_validate_pac.restype = FfiValidationResult
        
        # ffi_validate_pac_no_friction
        self._lib.ffi_validate_pac_no_friction.argtypes = [
            ctypes.c_char_p,  # pac_json
            ctypes.c_char_p,  # executor_gid
        ]
        self._lib.ffi_validate_pac_no_friction.restype = FfiValidationResult
        
        # ffi_free_string - takes raw void pointer
        self._lib.ffi_free_string.argtypes = [ctypes.c_void_p]
        self._lib.ffi_free_string.restype = None
        
        # ffi_kernel_version
        self._lib.ffi_kernel_version.argtypes = []
        self._lib.ffi_kernel_version.restype = ctypes.c_char_p
        
        # ffi_gate_count
        self._lib.ffi_gate_count.argtypes = []
        self._lib.ffi_gate_count.restype = ctypes.c_int
        
        # ffi_current_epoch_secs
        self._lib.ffi_current_epoch_secs.argtypes = []
        self._lib.ffi_current_epoch_secs.restype = ctypes.c_int64
    
    @property
    def info(self) -> KernelInfo:
        """Get information about the loaded kernel."""
        if self._info is None:
            version = self._lib.ffi_kernel_version().decode("utf-8")
            gate_count = self._lib.ffi_gate_count()
            self._info = KernelInfo(
                version=version,
                gate_count=gate_count,
                library_path=self._lib_path,
            )
        return self._info
    
    def current_epoch(self) -> int:
        """Get the current Unix timestamp from the kernel."""
        return self._lib.ffi_current_epoch_secs()
    
    def validate_pac(
        self,
        pac: Union[Dict[str, Any], str],
        executor_gid: str,
        admission_time: Optional[float] = None,
    ) -> ValidationResult:
        """
        Validate a PAC through the Constitutional Kernel.
        
        This method enforces cognitive friction (G9). If admission_time
        is not provided, it defaults to now, which will likely fail G9.
        
        Args:
            pac: PAC as a dict or JSON string.
            executor_gid: GID of the executing agent.
            admission_time: Unix timestamp when PAC was admitted for review.
                           If None, uses current time (will fail G9 friction).
        
        Returns:
            ValidationResult with approval status and PDO.
        """
        # Convert dict to JSON if needed
        if isinstance(pac, dict):
            pac_json = json.dumps(pac)
        else:
            pac_json = pac
        
        # Use current time if not provided
        if admission_time is None:
            admission_time = time.time()
        
        # Call FFI
        result = self._lib.ffi_validate_pac(
            pac_json.encode("utf-8"),
            executor_gid.encode("utf-8"),
            int(admission_time),
        )
        
        return self._process_result(result)
    
    def validate_pac_no_friction(
        self,
        pac: Union[Dict[str, Any], str],
        executor_gid: str,
    ) -> ValidationResult:
        """
        Validate a PAC without cognitive friction (TESTING ONLY).
        
        WARNING: This bypasses G9 friction enforcement. Only use for
        automated testing where dwell time simulation is not feasible.
        
        Args:
            pac: PAC as a dict or JSON string.
            executor_gid: GID of the executing agent.
        
        Returns:
            ValidationResult with approval status and PDO.
        """
        if isinstance(pac, dict):
            pac_json = json.dumps(pac)
        else:
            pac_json = pac
        
        result = self._lib.ffi_validate_pac_no_friction(
            pac_json.encode("utf-8"),
            executor_gid.encode("utf-8"),
        )
        
        return self._process_result(result)
    
    def _process_result(self, ffi_result: FfiValidationResult) -> ValidationResult:
        """Convert FFI result to Python result."""
        error_code = FfiErrorCode(ffi_result.error_code)
        
        # Parse PDO if available (pdo_json is c_void_p)
        pdo = None
        pdo_ptr = ffi_result.pdo_json
        if pdo_ptr:
            try:
                # Cast void pointer to char pointer and read bytes
                pdo_bytes = ctypes.cast(pdo_ptr, ctypes.c_char_p).value
                if pdo_bytes:
                    pdo = json.loads(pdo_bytes.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
            finally:
                # Free the Rust-allocated string
                self._lib.ffi_free_string(pdo_ptr)
        
        # Determine error message
        error_message = None
        if error_code != FfiErrorCode.SUCCESS:
            error_messages = {
                FfiErrorCode.PANIC: "Rust panic caught (fail-closed)",
                FfiErrorCode.NULL_PTR: "Null pointer passed to FFI",
                FfiErrorCode.JSON_PARSE: "JSON parsing failed",
                FfiErrorCode.VALIDATION_FAILED: "Validation error",
                FfiErrorCode.UTF8: "UTF-8 encoding error",
            }
            error_message = error_messages.get(error_code, f"Unknown error: {error_code}")
        
        return ValidationResult(
            approved=(ffi_result.outcome == 1),
            gates_passed=ffi_result.gates_passed,
            gates_total=ffi_result.gates_total,
            pdo=pdo,
            error_code=error_code,
            error_message=error_message,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_default_bridge: Optional[KernelBridge] = None


def get_bridge() -> KernelBridge:
    """Get the default kernel bridge (lazy initialization)."""
    global _default_bridge
    if _default_bridge is None:
        _default_bridge = KernelBridge()
    return _default_bridge


def validate_pac(
    pac: Union[Dict[str, Any], str],
    executor_gid: str,
    admission_time: Optional[float] = None,
) -> ValidationResult:
    """
    Validate a PAC using the default kernel bridge.
    
    See KernelBridge.validate_pac for full documentation.
    """
    return get_bridge().validate_pac(pac, executor_gid, admission_time)


def kernel_version() -> str:
    """Get the kernel version string."""
    return get_bridge().info.version


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "KernelBridge",
    "ValidationResult",
    "KernelInfo",
    "FfiErrorCode",
    "get_bridge",
    "validate_pac",
    "kernel_version",
]


if __name__ == "__main__":
    # Quick test
    try:
        bridge = KernelBridge()
        print(f"✓ Kernel loaded: {bridge.info.version}")
        print(f"✓ Gate count: {bridge.info.gate_count}")
        print(f"✓ Library: {bridge.info.library_path}")
    except FileNotFoundError as e:
        print(f"✗ Library not found: {e}")
        print("  Build with: cd chainbridge_kernel && cargo build --release")
