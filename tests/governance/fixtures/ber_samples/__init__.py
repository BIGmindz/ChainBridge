"""
BER Sample Fixtures

Sample BER artifacts for testing the BER Review Engine.
Per PAC-BENSON-EXEC-GOVERNANCE-JEFFREY-REVIEW-LAW-022.

Contains:
- Valid BER samples
- Invalid BER samples (various failure modes)
- Edge case samples
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK BER ARTIFACT
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class MockBERArtifact:
    """
    Mock BER artifact for testing.
    
    Matches structure of real BERArtifact from ber_loop_enforcer.py.
    """
    
    pac_id: str
    decision: str  # APPROVE, CORRECTIVE, REJECT
    issuer: str  # Should be GID-00
    issued_at: str
    emitted_at: str
    wrap_status: str
    session_state: str  # BER_EMITTED or SESSION_INVALID
    ber_id: str = ""
    wrap_id: str = ""
    training_signal: Optional[Dict[str, Any]] = None
    ber_hash: str = ""
    
    def __post_init__(self) -> None:
        """Generate BER ID if not provided."""
        if not self.ber_id:
            object.__setattr__(self, 'ber_id', f"BER-{self.pac_id}")
    
    @property
    def is_approved(self) -> bool:
        """True if BER decision is APPROVE."""
        return self.decision == "APPROVE"
    
    @property
    def is_emitted(self) -> bool:
        """True if BER was emitted."""
        return self.session_state == "BER_EMITTED"


# ═══════════════════════════════════════════════════════════════════════════════
# VALID BER SAMPLES
# ═══════════════════════════════════════════════════════════════════════════════


def create_valid_approve_ber(pac_id: str = "PAC-VALID-001") -> MockBERArtifact:
    """Create a valid APPROVE BER."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id=pac_id,
        decision="APPROVE",
        issuer="GID-00",
        issued_at=now.isoformat(),
        emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
        wrap_status="COMPLETE",
        session_state="BER_EMITTED",
        wrap_id=f"WRAP-{pac_id}",
    )


def create_valid_corrective_ber(pac_id: str = "PAC-VALID-002") -> MockBERArtifact:
    """Create a valid CORRECTIVE BER with training signal."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id=pac_id,
        decision="CORRECTIVE",
        issuer="GID-00",
        issued_at=now.isoformat(),
        emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
        wrap_status="PARTIAL",
        session_state="BER_EMITTED",
        wrap_id=f"WRAP-{pac_id}",
        training_signal={
            "pac_id": pac_id,
            "failure_type": "INCOMPLETE_DELIVERABLES",
            "remediation": "Complete missing items",
        },
    )


def create_valid_reject_ber(pac_id: str = "PAC-VALID-003") -> MockBERArtifact:
    """Create a valid REJECT BER."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id=pac_id,
        decision="REJECT",
        issuer="GID-00",
        issued_at=now.isoformat(),
        emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
        wrap_status="FAILED",
        session_state="BER_EMITTED",
        wrap_id=f"WRAP-{pac_id}",
        training_signal={
            "pac_id": pac_id,
            "failure_type": "CONSTRAINT_VIOLATION",
            "remediation": "Review constraints and resubmit",
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INVALID BER SAMPLES - AUTHORITY FAILURES
# ═══════════════════════════════════════════════════════════════════════════════


def create_ber_missing_authority() -> MockBERArtifact:
    """Create BER with missing issuer field."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id="PAC-BAD-AUTH-001",
        decision="APPROVE",
        issuer="",  # MISSING
        issued_at=now.isoformat(),
        emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
        wrap_status="COMPLETE",
        session_state="BER_EMITTED",
    )


def create_ber_invalid_authority() -> MockBERArtifact:
    """Create BER with invalid issuer (not GID-00)."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id="PAC-BAD-AUTH-002",
        decision="APPROVE",
        issuer="GID-99",  # WRONG - only GID-00 can issue BERs
        issued_at=now.isoformat(),
        emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
        wrap_status="COMPLETE",
        session_state="BER_EMITTED",
    )


def create_ber_jeffrey_issuer() -> MockBERArtifact:
    """Create BER with Jeffrey as issuer (violation)."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id="PAC-BAD-AUTH-003",
        decision="APPROVE",
        issuer="JEFFREY",  # VIOLATION - Jeffrey cannot issue BERs
        issued_at=now.isoformat(),
        emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
        wrap_status="COMPLETE",
        session_state="BER_EMITTED",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INVALID BER SAMPLES - LOOP FAILURES
# ═══════════════════════════════════════════════════════════════════════════════


def create_ber_broken_loop() -> MockBERArtifact:
    """Create BER with missing PAC ID (broken loop)."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id="",  # MISSING - orphan BER
        decision="APPROVE",
        issuer="GID-00",
        issued_at=now.isoformat(),
        emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
        wrap_status="COMPLETE",
        session_state="BER_EMITTED",
    )


def create_ber_orphan() -> MockBERArtifact:
    """Create BER for a PAC that doesn't exist."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id="PAC-NONEXISTENT-999",  # PAC doesn't exist in pending set
        decision="APPROVE",
        issuer="GID-00",
        issued_at=now.isoformat(),
        emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
        wrap_status="COMPLETE",
        session_state="BER_EMITTED",
    )


def create_ber_missing_wrap() -> MockBERArtifact:
    """Create BER with missing WRAP reference."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id="PAC-BAD-LOOP-003",
        decision="APPROVE",
        issuer="GID-00",
        issued_at=now.isoformat(),
        emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
        wrap_status="",  # MISSING
        session_state="BER_EMITTED",
        wrap_id="",  # MISSING
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INVALID BER SAMPLES - EMISSION FAILURES
# ═══════════════════════════════════════════════════════════════════════════════


def create_ber_not_emitted() -> MockBERArtifact:
    """Create BER that was issued but not emitted."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id="PAC-BAD-EMIT-001",
        decision="APPROVE",
        issuer="GID-00",
        issued_at=now.isoformat(),
        emitted_at="",  # MISSING - not emitted
        wrap_status="COMPLETE",
        session_state="BER_ISSUED",  # NOT BER_EMITTED
    )


def create_ber_missing_emission_timestamp() -> MockBERArtifact:
    """Create BER with missing emission timestamp."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id="PAC-BAD-EMIT-002",
        decision="APPROVE",
        issuer="GID-00",
        issued_at=now.isoformat(),
        emitted_at="",  # MISSING
        wrap_status="COMPLETE",
        session_state="BER_EMITTED",  # Says emitted but no timestamp
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INVALID BER SAMPLES - DECISION FAILURES
# ═══════════════════════════════════════════════════════════════════════════════


def create_ber_invalid_decision() -> MockBERArtifact:
    """Create BER with invalid decision value."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id="PAC-BAD-DEC-001",
        decision="MAYBE",  # INVALID - not in {APPROVE, CORRECTIVE, REJECT}
        issuer="GID-00",
        issued_at=now.isoformat(),
        emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
        wrap_status="COMPLETE",
        session_state="BER_EMITTED",
    )


def create_ber_narrative_decision() -> MockBERArtifact:
    """Create BER with narrative decision (forbidden)."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id="PAC-BAD-DEC-002",
        decision="This looks good overall but...",  # FORBIDDEN narrative
        issuer="GID-00",
        issued_at=now.isoformat(),
        emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
        wrap_status="COMPLETE",
        session_state="BER_EMITTED",
    )


def create_ber_partial_decision() -> MockBERArtifact:
    """Create BER with partial acceptance (forbidden)."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id="PAC-BAD-DEC-003",
        decision="PARTIAL",  # FORBIDDEN - not a valid decision
        issuer="GID-00",
        issued_at=now.isoformat(),
        emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
        wrap_status="COMPLETE",
        session_state="BER_EMITTED",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INVALID BER SAMPLES - TRAINING SIGNAL FAILURES
# ═══════════════════════════════════════════════════════════════════════════════


def create_ber_missing_training_signal() -> MockBERArtifact:
    """Create CORRECTIVE BER without training signal."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id="PAC-BAD-SIG-001",
        decision="CORRECTIVE",
        issuer="GID-00",
        issued_at=now.isoformat(),
        emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
        wrap_status="PARTIAL",
        session_state="BER_EMITTED",
        training_signal=None,  # MISSING for CORRECTIVE
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INVALID BER SAMPLES - TEMPORAL FAILURES
# ═══════════════════════════════════════════════════════════════════════════════


def create_ber_temporal_paradox() -> MockBERArtifact:
    """Create BER with emission before issuance (temporal violation)."""
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id="PAC-BAD-TIME-001",
        decision="APPROVE",
        issuer="GID-00",
        issued_at=(now + timedelta(hours=1)).isoformat(),  # AFTER emission
        emitted_at=now.isoformat(),  # BEFORE issuance
        wrap_status="COMPLETE",
        session_state="BER_EMITTED",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INVALID BER SAMPLES - PERSONA BLEED
# ═══════════════════════════════════════════════════════════════════════════════


def create_ber_persona_bleed() -> MockBERArtifact:
    """
    Create BER showing persona bleed.
    
    This simulates an agent crossing identity boundaries.
    """
    now = datetime.now(timezone.utc)
    return MockBERArtifact(
        pac_id="PAC-BLEED-001",
        decision="APPROVE",
        issuer="GID-01",  # Wrong issuer - agent trying to issue BER
        issued_at=now.isoformat(),
        emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
        wrap_status="COMPLETE",
        session_state="BER_EMITTED",
        training_signal={
            "persona_origin": "GID-01",  # Evidence of persona bleed
            "claimed_identity": "GID-00",
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURE COLLECTION
# ═══════════════════════════════════════════════════════════════════════════════


# All valid BER samples
VALID_BER_SAMPLES = [
    ("valid_approve", create_valid_approve_ber),
    ("valid_corrective", create_valid_corrective_ber),
    ("valid_reject", create_valid_reject_ber),
]

# All invalid BER samples by failure mode
INVALID_BER_SAMPLES = {
    "authority": [
        ("missing_authority", create_ber_missing_authority),
        ("invalid_authority", create_ber_invalid_authority),
        ("jeffrey_issuer", create_ber_jeffrey_issuer),
    ],
    "loop": [
        ("broken_loop", create_ber_broken_loop),
        ("orphan", create_ber_orphan),
        ("missing_wrap", create_ber_missing_wrap),
    ],
    "emission": [
        ("not_emitted", create_ber_not_emitted),
        ("missing_emission_timestamp", create_ber_missing_emission_timestamp),
    ],
    "decision": [
        ("invalid_decision", create_ber_invalid_decision),
        ("narrative_decision", create_ber_narrative_decision),
        ("partial_decision", create_ber_partial_decision),
    ],
    "training_signal": [
        ("missing_training_signal", create_ber_missing_training_signal),
    ],
    "temporal": [
        ("temporal_paradox", create_ber_temporal_paradox),
    ],
    "persona_bleed": [
        ("persona_bleed", create_ber_persona_bleed),
    ],
}


def get_all_valid_bers() -> list:
    """Get all valid BER samples."""
    return [factory() for _, factory in VALID_BER_SAMPLES]


def get_all_invalid_bers() -> list:
    """Get all invalid BER samples."""
    result = []
    for category_samples in INVALID_BER_SAMPLES.values():
        for _, factory in category_samples:
            result.append(factory())
    return result


def get_invalid_bers_by_category(category: str) -> list:
    """Get invalid BER samples for a specific failure category."""
    if category not in INVALID_BER_SAMPLES:
        return []
    return [factory() for _, factory in INVALID_BER_SAMPLES[category]]


__all__ = [
    # Mock artifact
    "MockBERArtifact",
    # Valid samples
    "create_valid_approve_ber",
    "create_valid_corrective_ber",
    "create_valid_reject_ber",
    # Authority failures
    "create_ber_missing_authority",
    "create_ber_invalid_authority",
    "create_ber_jeffrey_issuer",
    # Loop failures
    "create_ber_broken_loop",
    "create_ber_orphan",
    "create_ber_missing_wrap",
    # Emission failures
    "create_ber_not_emitted",
    "create_ber_missing_emission_timestamp",
    # Decision failures
    "create_ber_invalid_decision",
    "create_ber_narrative_decision",
    "create_ber_partial_decision",
    # Training signal failures
    "create_ber_missing_training_signal",
    # Temporal failures
    "create_ber_temporal_paradox",
    # Persona bleed
    "create_ber_persona_bleed",
    # Collections
    "VALID_BER_SAMPLES",
    "INVALID_BER_SAMPLES",
    "get_all_valid_bers",
    "get_all_invalid_bers",
    "get_invalid_bers_by_category",
]
