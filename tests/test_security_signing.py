"""
Tests for src/security/signing.py
"""
import datetime
import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException

# Set dev environment before importing signing module
os.environ["APP_ENV"] = "dev"

from src.security.signing import (
    canonical_json_bytes,
    compute_sig,
    now_utc_iso,
    parse_timestamp,
    verify_headers,
    verify_request,
)


class TestCanonicalJson:
    """Tests for canonical JSON serialization."""

    def test_canonical_json_deterministic(self):
        """Test that canonical JSON is deterministic."""
        obj = {"z": 3, "a": 1, "m": 2}
        result1 = canonical_json_bytes(obj)
        result2 = canonical_json_bytes(obj)
        assert result1 == result2

    def test_canonical_json_sorted_keys(self):
        """Test that keys are sorted."""
        obj = {"z": 3, "a": 1, "m": 2}
        result = canonical_json_bytes(obj)
        # Should be {"a":1,"m":2,"z":3}
        assert result == b'{"a":1,"m":2,"z":3}'

    def test_canonical_json_no_spaces(self):
        """Test that output has no spaces."""
        obj = {"key": "value", "num": 123}
        result = canonical_json_bytes(obj)
        assert b' ' not in result


class TestTimestamp:
    """Tests for timestamp handling."""

    def test_now_utc_iso_format(self):
        """Test that now_utc_iso returns valid ISO format."""
        result = now_utc_iso()
        # Should be able to parse it back
        dt = datetime.datetime.fromisoformat(result)
        assert dt.tzinfo is not None

    def test_parse_timestamp_with_z_suffix(self):
        """Test parsing timestamp with Z suffix."""
        ts = "2025-01-15T12:00:00Z"
        result = parse_timestamp(ts)
        assert result.tzinfo is not None
        assert result.hour == 12

    def test_parse_timestamp_with_offset(self):
        """Test parsing timestamp with offset."""
        ts = "2025-01-15T12:00:00+00:00"
        result = parse_timestamp(ts)
        assert result.tzinfo is not None

    def test_parse_timestamp_naive_becomes_utc(self):
        """Test that naive timestamps are treated as UTC."""
        ts = "2025-01-15T12:00:00"
        result = parse_timestamp(ts)
        assert result.tzinfo == datetime.timezone.utc

    def test_parse_timestamp_invalid_format(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid timestamp format"):
            parse_timestamp("not-a-timestamp")


class TestSignature:
    """Tests for signature computation."""

    def test_compute_sig_deterministic(self):
        """Test that signature computation is deterministic."""
        ts = "2025-01-15T12:00:00Z"
        body = b"test body"
        sig1 = compute_sig(ts, body)
        sig2 = compute_sig(ts, body)
        assert sig1 == sig2

    def test_compute_sig_different_timestamp(self):
        """Test that different timestamps produce different signatures."""
        body = b"test body"
        sig1 = compute_sig("2025-01-15T12:00:00Z", body)
        sig2 = compute_sig("2025-01-15T12:00:01Z", body)
        assert sig1 != sig2

    def test_compute_sig_different_body(self):
        """Test that different bodies produce different signatures."""
        ts = "2025-01-15T12:00:00Z"
        sig1 = compute_sig(ts, b"body1")
        sig2 = compute_sig(ts, b"body2")
        assert sig1 != sig2


class TestVerifyHeaders:
    """Tests for header verification."""

    def test_verify_headers_missing_signature(self):
        """Test that missing signature raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            verify_headers(x_signature=None, x_signature_timestamp="2025-01-15T12:00:00Z")
        assert exc_info.value.status_code == 401

    def test_verify_headers_missing_timestamp(self):
        """Test that missing timestamp raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            verify_headers(x_signature="fake-sig", x_signature_timestamp=None)
        assert exc_info.value.status_code == 401

    def test_verify_headers_invalid_timestamp_format(self):
        """Test that invalid timestamp format raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            verify_headers(x_signature="fake-sig", x_signature_timestamp="invalid")
        assert exc_info.value.status_code == 400

    def test_verify_headers_expired_timestamp(self):
        """Test that expired timestamp raises HTTPException."""
        # Timestamp from 10 minutes ago
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=10)
        with pytest.raises(HTTPException) as exc_info:
            verify_headers(x_signature="fake-sig", x_signature_timestamp=past.isoformat())
        assert exc_info.value.status_code == 401

    def test_verify_headers_future_timestamp(self):
        """Test that future timestamp raises HTTPException."""
        # Timestamp from 10 minutes in the future
        future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
        with pytest.raises(HTTPException) as exc_info:
            verify_headers(x_signature="fake-sig", x_signature_timestamp=future.isoformat())
        assert exc_info.value.status_code == 401

    def test_verify_headers_valid_recent_timestamp(self):
        """Test that recent valid timestamp passes."""
        now = datetime.datetime.now(datetime.timezone.utc)
        sig, ts = verify_headers(x_signature="fake-sig", x_signature_timestamp=now.isoformat())
        assert sig == "fake-sig"
        assert ts == now.isoformat()


class TestVerifyRequest:
    """Tests for request body verification."""

    def test_verify_request_valid_signature(self):
        """Test that valid signature passes verification."""
        ts = "2025-01-15T12:00:00Z"
        body = b"test body"
        sig = compute_sig(ts, body)
        # Should not raise
        verify_request(body, sig, ts)

    def test_verify_request_invalid_signature(self):
        """Test that invalid signature fails verification."""
        ts = "2025-01-15T12:00:00Z"
        body = b"test body"
        sig = "invalid-signature"
        with pytest.raises(HTTPException) as exc_info:
            verify_request(body, sig, ts)
        assert exc_info.value.status_code == 401

    def test_verify_request_tampered_body(self):
        """Test that tampered body fails verification."""
        ts = "2025-01-15T12:00:00Z"
        original_body = b"original body"
        sig = compute_sig(ts, original_body)

        # Try to verify with different body
        with pytest.raises(HTTPException) as exc_info:
            verify_request(b"tampered body", sig, ts)
        assert exc_info.value.status_code == 401


class TestSecretConfiguration:
    """Tests for signing secret configuration."""

    def test_dev_mode_allows_default_secret(self):
        """Test that dev mode allows default secret."""
        with patch.dict(os.environ, {"APP_ENV": "dev", "SIGNING_SECRET": ""}):
            # Re-import to trigger configuration
            import importlib
            import src.security.signing
            importlib.reload(src.security.signing)
            # Should not raise

    def test_production_requires_secret(self):
        """Test that production mode requires SIGNING_SECRET."""
        with patch.dict(os.environ, {"APP_ENV": "production", "SIGNING_SECRET": ""}, clear=True):
            # Re-import should raise RuntimeError
            with pytest.raises(RuntimeError, match="SIGNING_SECRET"):
                import importlib
                import src.security.signing
                importlib.reload(src.security.signing)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
