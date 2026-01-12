"""
Trusted Timestamp Authority Module
==================================

PAC-SEC-P822-A: IMMUTABLE AUDIT STORAGE CORE
Component: Monotonic Timestamp Generation
Agent: CHRONOS (GID-TIME-01)

PURPOSE:
  Provides trusted, monotonically increasing timestamps for audit events.
  Ensures temporal ordering cannot be manipulated - time never goes backward.
  UTC-based timestamps with nanosecond precision where available.

INVARIANTS:
  INV-AUDIT-003: Timestamps MUST increase monotonically
  INV-TIME-001: Timestamps MUST be UTC-based
  INV-TIME-002: Timestamp sequence MUST be validatable
  INV-TIME-003: Clock skew MUST be detected and handled

TEMPORAL GUARANTEES:
  - Monotonic: Each timestamp > all previous timestamps
  - UTC: All timestamps in Coordinated Universal Time
  - Precision: Microsecond precision minimum
  - Unique: No duplicate timestamps issued
"""

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from enum import Enum
import threading


class TimestampFormat(Enum):
    """Supported timestamp formats."""
    ISO8601 = "iso8601"
    UNIX_SECONDS = "unix_seconds"
    UNIX_MILLIS = "unix_millis"
    UNIX_MICROS = "unix_micros"


@dataclass
class TimestampRecord:
    """
    Record of an issued timestamp.
    
    Contains:
    - sequence_number: Monotonic sequence counter
    - timestamp: UTC timestamp when issued
    - unix_time: Unix timestamp with microsecond precision
    - hash: SHA-256 hash of timestamp data for verification
    """
    sequence_number: int
    timestamp: str  # ISO8601 format
    unix_time: float  # Unix timestamp with fractions
    previous_hash: str
    hash: str = ""
    
    def __post_init__(self):
        """Compute hash if not provided."""
        if not self.hash:
            content = f"{self.sequence_number}:{self.unix_time}:{self.previous_hash}"
            self.hash = hashlib.sha256(content.encode()).hexdigest()
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp,
            "unix_time": self.unix_time,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TimestampRecord":
        """Deserialize from dictionary."""
        return cls(
            sequence_number=data["sequence_number"],
            timestamp=data["timestamp"],
            unix_time=data["unix_time"],
            previous_hash=data["previous_hash"],
            hash=data.get("hash", ""),
        )


class TimestampAuthority:
    """
    Trusted timestamp authority for audit events.
    
    Guarantees:
    - Monotonic timestamps (always increasing)
    - UTC-based time
    - Sequence numbers for ordering
    - Hash chain for verification
    
    Thread-safe for concurrent timestamp requests.
    """
    
    GENESIS_HASH = "0" * 64
    
    def __init__(self, 
                 min_interval_micros: int = 1,
                 format: TimestampFormat = TimestampFormat.ISO8601):
        """
        Initialize timestamp authority.
        
        Args:
            min_interval_micros: Minimum microseconds between timestamps
            format: Default timestamp format
        """
        self._min_interval = min_interval_micros / 1_000_000  # Convert to seconds
        self._format = format
        self._sequence = 0
        self._last_time = 0.0
        self._last_hash = self.GENESIS_HASH
        self._lock = threading.Lock()
        self._history: List[TimestampRecord] = []
        self._max_history = 10000  # Keep last N timestamps
    
    @property
    def sequence_number(self) -> int:
        """Current sequence number."""
        return self._sequence
    
    @property
    def last_timestamp(self) -> Optional[str]:
        """Most recent timestamp issued."""
        if self._history:
            return self._history[-1].timestamp
        return None
    
    def _get_monotonic_time(self) -> float:
        """
        Get current time, ensuring monotonic increase.
        
        If system clock has moved backward, waits until
        time exceeds last issued timestamp.
        """
        current = time.time()
        
        # Ensure monotonic increase
        if current <= self._last_time:
            # Clock skew detected - advance minimally
            current = self._last_time + self._min_interval
        
        # Ensure minimum interval
        if current - self._last_time < self._min_interval:
            current = self._last_time + self._min_interval
        
        return current
    
    def get_timestamp(self) -> TimestampRecord:
        """
        Issue a new trusted timestamp.
        
        Returns:
            TimestampRecord with monotonically increasing values
            
        Guarantees:
            - sequence_number > all previous sequence_numbers
            - unix_time > all previous unix_times
            - hash chains to previous timestamp
        """
        with self._lock:
            # Get monotonic time
            current_time = self._get_monotonic_time()
            
            # Create timestamp record
            self._sequence += 1
            
            record = TimestampRecord(
                sequence_number=self._sequence,
                timestamp=datetime.fromtimestamp(current_time, tz=timezone.utc).isoformat(),
                unix_time=current_time,
                previous_hash=self._last_hash,
            )
            
            # Update state
            self._last_time = current_time
            self._last_hash = record.hash
            
            # Add to history (with bounded size)
            self._history.append(record)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
            
            return record
    
    def validate_sequence(self, records: List[TimestampRecord]) -> Tuple[bool, Optional[int]]:
        """
        Validate a sequence of timestamp records.
        
        Checks:
        - Sequence numbers are strictly increasing
        - Unix times are strictly increasing
        - Hash chain is intact
        
        Args:
            records: List of TimestampRecord to validate
            
        Returns:
            Tuple of (is_valid, first_invalid_index)
        """
        if not records:
            return True, None
        
        for i, record in enumerate(records):
            # Verify hash
            expected_hash = hashlib.sha256(
                f"{record.sequence_number}:{record.unix_time}:{record.previous_hash}".encode()
            ).hexdigest()
            
            if record.hash != expected_hash:
                return False, i
            
            # Check ordering against previous
            if i > 0:
                prev = records[i - 1]
                
                # Sequence must increase
                if record.sequence_number <= prev.sequence_number:
                    return False, i
                
                # Time must increase
                if record.unix_time <= prev.unix_time:
                    return False, i
                
                # Hash chain must link
                if record.previous_hash != prev.hash:
                    return False, i
        
        return True, None
    
    def validate_single(self, record: TimestampRecord, expected_previous_hash: str) -> bool:
        """
        Validate a single timestamp record.
        
        Args:
            record: Record to validate
            expected_previous_hash: Expected previous hash value
            
        Returns:
            True if record is valid
        """
        # Verify hash computation
        expected_hash = hashlib.sha256(
            f"{record.sequence_number}:{record.unix_time}:{record.previous_hash}".encode()
        ).hexdigest()
        
        if record.hash != expected_hash:
            return False
        
        # Verify chain linkage
        if record.previous_hash != expected_previous_hash:
            return False
        
        return True
    
    def format_timestamp(self, record: TimestampRecord, fmt: TimestampFormat = None) -> str:
        """
        Format timestamp record in specified format.
        
        Args:
            record: TimestampRecord to format
            fmt: Format to use (default: authority's default)
            
        Returns:
            Formatted timestamp string
        """
        fmt = fmt or self._format
        
        if fmt == TimestampFormat.ISO8601:
            return record.timestamp
        elif fmt == TimestampFormat.UNIX_SECONDS:
            return str(int(record.unix_time))
        elif fmt == TimestampFormat.UNIX_MILLIS:
            return str(int(record.unix_time * 1000))
        elif fmt == TimestampFormat.UNIX_MICROS:
            return str(int(record.unix_time * 1_000_000))
        else:
            return record.timestamp
    
    def get_current_utc(self) -> datetime:
        """Get current UTC time without issuing timestamp."""
        return datetime.now(timezone.utc)
    
    def is_timestamp_valid(self, timestamp_str: str) -> bool:
        """
        Check if a timestamp string is valid ISO8601 format.
        
        Args:
            timestamp_str: Timestamp string to validate
            
        Returns:
            True if valid ISO8601 format
        """
        try:
            datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return True
        except (ValueError, AttributeError):
            return False
    
    def compare_timestamps(self, ts1: str, ts2: str) -> int:
        """
        Compare two ISO8601 timestamps.
        
        Args:
            ts1: First timestamp
            ts2: Second timestamp
            
        Returns:
            -1 if ts1 < ts2, 0 if equal, 1 if ts1 > ts2
        """
        dt1 = datetime.fromisoformat(ts1.replace('Z', '+00:00'))
        dt2 = datetime.fromisoformat(ts2.replace('Z', '+00:00'))
        
        if dt1 < dt2:
            return -1
        elif dt1 > dt2:
            return 1
        return 0
    
    def get_history(self, count: int = 100) -> List[TimestampRecord]:
        """
        Get recent timestamp history.
        
        Args:
            count: Number of recent timestamps to return
            
        Returns:
            List of recent TimestampRecord
        """
        return self._history[-count:]
    
    def reset(self):
        """
        Reset timestamp authority state.
        
        WARNING: Only use for testing. In production, this would
        break the timestamp chain.
        """
        with self._lock:
            self._sequence = 0
            self._last_time = 0.0
            self._last_hash = self.GENESIS_HASH
            self._history.clear()


# Module-level singleton
_authority: Optional[TimestampAuthority] = None
_authority_lock = threading.Lock()


def get_timestamp_authority() -> TimestampAuthority:
    """Get or create the global timestamp authority."""
    global _authority
    
    if _authority is None:
        with _authority_lock:
            if _authority is None:
                _authority = TimestampAuthority()
    
    return _authority


def get_trusted_timestamp() -> TimestampRecord:
    """Convenience function to get a trusted timestamp."""
    return get_timestamp_authority().get_timestamp()
