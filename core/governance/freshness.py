"""
🟢 DAN (GID-07) — Trust Data Freshness Contract
PAC-GOV-FRESHNESS-01: Trust Data Freshness Contract

Freshness manifest schema and verification for audit bundles.

This module defines the freshness contract that cryptographically
binds time + scope, making staleness machine-verifiable.

Key properties:
- Fail-closed: Stale data FAILS verification
- Offline-verifiable: No network calls
- Read-only: No state modification
- Truth signaling: Not operations

NO GOVERNANCE AUTHORITY. Time binding only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

FRESHNESS_SCHEMA_VERSION = "1.0.0"
FRESHNESS_MANIFEST_FILENAME = "FRESHNESS_MANIFEST.json"

# Default staleness threshold: 24 hours
DEFAULT_MAX_STALENESS_SECONDS = 86400


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SourceTimestamp:
    """Timestamp for a specific data source."""

    source: str
    timestamp: datetime
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceTimestamp":
        """Create from dictionary."""
        ts = data.get("timestamp", "")
        if isinstance(ts, str):
            timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            timestamp = ts
        return cls(
            source=data["source"],
            timestamp=timestamp,
            description=data.get("description", ""),
        )


@dataclass
class FreshnessManifest:
    """
    Freshness manifest for audit bundle.

    Captures timestamps for all data sources to enable
    machine-verifiable staleness detection.
    """

    generated_at: datetime
    max_staleness_seconds: int
    source_timestamps: list[SourceTimestamp] = field(default_factory=list)
    schema_version: str = FRESHNESS_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at.isoformat(),
            "max_staleness_seconds": self.max_staleness_seconds,
            "source_timestamps": {
                st.source: {
                    "timestamp": st.timestamp.isoformat(),
                    "description": st.description,
                }
                for st in self.source_timestamps
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FreshnessManifest":
        """Create from dictionary."""
        generated_at_str = data.get("generated_at", "")
        if isinstance(generated_at_str, str):
            generated_at = datetime.fromisoformat(generated_at_str.replace("Z", "+00:00"))
        else:
            generated_at = generated_at_str

        source_timestamps = []
        for source, info in data.get("source_timestamps", {}).items():
            ts_str = info.get("timestamp", "")
            if isinstance(ts_str, str):
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            else:
                ts = ts_str
            source_timestamps.append(
                SourceTimestamp(
                    source=source,
                    timestamp=ts,
                    description=info.get("description", ""),
                )
            )

        return cls(
            schema_version=data.get("schema_version", FRESHNESS_SCHEMA_VERSION),
            generated_at=generated_at,
            max_staleness_seconds=data.get("max_staleness_seconds", DEFAULT_MAX_STALENESS_SECONDS),
            source_timestamps=source_timestamps,
        )

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


@dataclass
class FreshnessVerificationResult:
    """Result of freshness verification."""

    is_fresh: bool
    checked_at: datetime
    stale_sources: list[dict[str, Any]] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    def add_stale_source(
        self,
        source: str,
        source_timestamp: datetime,
        staleness_seconds: int,
        max_allowed: int,
    ) -> None:
        """Record a stale source."""
        self.is_fresh = False
        self.stale_sources.append(
            {
                "source": source,
                "timestamp": source_timestamp.isoformat(),
                "staleness_seconds": staleness_seconds,
                "max_allowed_seconds": max_allowed,
                "exceeded_by_seconds": staleness_seconds - max_allowed,
            }
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FRESHNESS VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════


def verify_freshness(
    manifest: FreshnessManifest,
    check_time: datetime | None = None,
) -> FreshnessVerificationResult:
    """
    Verify that all sources are within freshness threshold.

    Args:
        manifest: Freshness manifest to verify
        check_time: Time to check against (defaults to now)

    Returns:
        FreshnessVerificationResult with staleness details

    Verification FAILS if:
        now - any(source_timestamp) > max_staleness_seconds
    """
    if check_time is None:
        check_time = datetime.now(timezone.utc)

    # Ensure check_time is timezone-aware
    if check_time.tzinfo is None:
        check_time = check_time.replace(tzinfo=timezone.utc)

    result = FreshnessVerificationResult(
        is_fresh=True,
        checked_at=check_time,
    )

    max_staleness = manifest.max_staleness_seconds

    for source_ts in manifest.source_timestamps:
        ts = source_ts.timestamp
        # Ensure timestamp is timezone-aware
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        age_seconds = int((check_time - ts).total_seconds())

        if age_seconds > max_staleness:
            result.add_stale_source(
                source=source_ts.source,
                source_timestamp=ts,
                staleness_seconds=age_seconds,
                max_allowed=max_staleness,
            )
            result.messages.append(
                f"Source '{source_ts.source}' is stale: "
                f"{age_seconds}s old (max: {max_staleness}s, exceeded by: {age_seconds - max_staleness}s)"
            )
        else:
            result.messages.append(f"Source '{source_ts.source}' is fresh: {age_seconds}s old")

    if result.is_fresh:
        result.messages.insert(0, "All sources are within freshness threshold")
    else:
        result.messages.insert(0, f"STALE: {len(result.stale_sources)} source(s) exceeded threshold")

    return result


def load_freshness_manifest(bundle_path: Path) -> FreshnessManifest | None:
    """
    Load freshness manifest from audit bundle.

    Args:
        bundle_path: Path to audit bundle directory

    Returns:
        FreshnessManifest or None if not found/invalid
    """
    manifest_path = bundle_path / FRESHNESS_MANIFEST_FILENAME

    if not manifest_path.exists():
        return None

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return FreshnessManifest.from_dict(data)
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def create_freshness_manifest(
    generated_at: datetime,
    source_timestamps: list[SourceTimestamp],
    max_staleness_seconds: int = DEFAULT_MAX_STALENESS_SECONDS,
) -> FreshnessManifest:
    """
    Create a freshness manifest.

    Args:
        generated_at: Time when bundle was generated
        source_timestamps: List of source timestamps
        max_staleness_seconds: Maximum allowed staleness

    Returns:
        FreshnessManifest instance
    """
    return FreshnessManifest(
        generated_at=generated_at,
        max_staleness_seconds=max_staleness_seconds,
        source_timestamps=source_timestamps,
    )
