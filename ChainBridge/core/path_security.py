"""
Secure path handling utilities for ChainBridge.

SAM (GID-06) - Security & Threat Engineer
PAC-SAM-R2-001: Path Traversal Prevention

This module provides secure-by-default path handling to prevent:
- Directory traversal attacks (../)
- Absolute path injection (/etc/passwd)
- Symlink escape attacks
- Null byte injection
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional, Union

# Pattern to detect path traversal sequences
_TRAVERSAL_PATTERN = re.compile(r"(^|[\\/])\.\.($|[\\/])")
_NULL_BYTE_PATTERN = re.compile(r"\x00")


class PathTraversalError(ValueError):
    """Raised when a path traversal attempt is detected."""

    pass


def safe_join(base: Union[Path, str], user_path: Union[Path, str]) -> Path:
    """
    Securely join a base directory with a user-supplied path.

    This function ensures that the resulting path:
    1. Does not escape the base directory via .. traversal
    2. Does not use absolute paths to bypass the base
    3. Does not use symlinks to escape containment
    4. Does not contain null bytes

    Args:
        base: The trusted base directory (allowlisted)
        user_path: The untrusted user-supplied path component

    Returns:
        A resolved Path that is guaranteed to be under base

    Raises:
        PathTraversalError: If the path would escape the base directory

    Example:
        >>> safe_join("/data/uploads", "file.csv")
        PosixPath('/data/uploads/file.csv')

        >>> safe_join("/data/uploads", "../secrets/key.pem")
        PathTraversalError: Path traversal detected

        >>> safe_join("/data/uploads", "/etc/passwd")
        PathTraversalError: Absolute paths not allowed
    """
    base_path = Path(base).resolve()
    user_str = str(user_path)

    # Check for null bytes (CVE-style injection)
    if _NULL_BYTE_PATTERN.search(user_str):
        raise PathTraversalError("Null bytes not allowed in path")

    # Reject absolute paths
    if os.path.isabs(user_str):
        raise PathTraversalError(f"Absolute paths not allowed: {user_str}")

    # Check for explicit traversal sequences before joining
    if _TRAVERSAL_PATTERN.search(user_str):
        raise PathTraversalError(f"Path traversal detected: {user_str}")

    # Join and resolve
    joined = (base_path / user_str).resolve()

    # Final containment check: resolved path must be under base
    try:
        joined.relative_to(base_path)
    except ValueError:
        raise PathTraversalError(f"Path escapes base directory: {user_str} resolves to {joined}")

    return joined


def safe_filename(filename: str) -> str:
    """
    Sanitize a filename by stripping directory components and dangerous characters.

    This is a defense-in-depth measure on top of safe_join().

    Args:
        filename: The untrusted filename (may include path components)

    Returns:
        A safe filename with only the basename and no special characters

    Raises:
        PathTraversalError: If the filename is empty or contains only dots

    Example:
        >>> safe_filename("../../../etc/passwd")
        'passwd'

        >>> safe_filename("file.csv")
        'file.csv'
    """
    if not filename:
        raise PathTraversalError("Empty filename not allowed")

    # Check for null bytes
    if _NULL_BYTE_PATTERN.search(filename):
        raise PathTraversalError("Null bytes not allowed in filename")

    # Extract basename (handles both / and \ separators)
    basename = Path(filename).name

    # Reject empty or dot-only names
    if not basename or basename in (".", ".."):
        raise PathTraversalError(f"Invalid filename: {filename}")

    # Remove leading dots (hidden files) - optional policy
    # basename = basename.lstrip(".")

    return basename


def validate_path_within_base(
    path: Union[Path, str],
    base: Union[Path, str],
    *,
    resolve_symlinks: bool = True,
) -> Path:
    """
    Validate that a path is contained within a base directory.

    Use this to validate paths that have already been constructed
    (e.g., from database records or job queues).

    Args:
        path: The path to validate
        base: The allowed base directory
        resolve_symlinks: If True, resolve symlinks before checking

    Returns:
        The validated, resolved path

    Raises:
        PathTraversalError: If the path is not under base
    """
    base_path = Path(base).resolve()

    if resolve_symlinks:
        check_path = Path(path).resolve()
    else:
        # Use strict=False to avoid following symlinks
        check_path = Path(path).absolute()

    try:
        check_path.relative_to(base_path)
    except ValueError:
        raise PathTraversalError(f"Path {path} is not within allowed base {base}")

    return check_path


def get_allowed_data_dir(subdir: Optional[str] = None) -> Path:
    """
    Get the allowed data directory for shadow pilot uploads.

    This centralizes the base directory configuration to prevent
    scattered hardcoded paths.

    Args:
        subdir: Optional subdirectory within the data dir

    Returns:
        Resolved path to the data directory
    """
    data_dir = Path(os.getenv("SHADOW_PILOT_DATA_DIR", "data/shadow_pilot")).resolve()

    # Ensure the directory exists
    data_dir.mkdir(parents=True, exist_ok=True)

    if subdir:
        return safe_join(data_dir, subdir)

    return data_dir


__all__ = [
    "PathTraversalError",
    "safe_join",
    "safe_filename",
    "validate_path_within_base",
    "get_allowed_data_dir",
]
