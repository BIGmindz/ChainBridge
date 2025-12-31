"""
PAC-015 Determinism Enforcement Tests
════════════════════════════════════════════════════════════════════════════════

Adversarial validation (ORDER 5 — Sam) and CI enforcement tests (ORDER 3 — Dan).

CRITICAL: These tests verify ABSOLUTE DETERMINISM:
- Same artifact × N runs = identical output
- No probabilistic behavior
- No discretionary paths

PAC Reference: PAC-JEFFREY-CHAINBRIDGE-DETERMINISM-ENFORCEMENT-EXEC-015
Effective Date: 2025-12-30

════════════════════════════════════════════════════════════════════════════════
"""

import pytest
import hashlib
from typing import List

from core.governance.determinism_enforcement import (
    ArtifactType,
    BER_GATES,
    BER_SECTIONS,
    PAC_SECTIONS,
    WRAP_SECTIONS,
    StructuralValidator,
    GatePipeline,
    SemanticValidator,
    BehavioralEnforcer,
    DeterminismEnforcer,
    validate_ber_or_fail,
    BERValidationFailure,
    verify_determinism,
    GateResult,
    SemanticValidity,
)


# =============================================================================
# TEST FIXTURES — SAMPLE ARTIFACTS
# =============================================================================

VALID_BER_SAMPLE = """
# ═══════════════════════════════════════════════════════════════════════════════
# BER-TEST-001
# ═══════════════════════════════════════════════════════════════════════════════

## RUNTIME ACTIVATION BLOCK

Runtime ID: RUNTIME-TEST
Execution Engine: Benson Execution (GID-00)
Mode: EXECUTION
Governance: FAIL-CLOSED

☑ Runtime initialized

---

## EXECUTION AUTHORITY & ORCHESTRATION DECLARATION

| Field | Value |
|-------|-------|
| **Issuer** | Jeffrey (CTO) |
| **Orchestrator** | Benson Execution (GID-00) |

---

## AGENT ACTIVATION & ROLE TABLE

| Order | Agent | GID | Mode |
|-------|-------|-----|------|
| 1 | Cody | GID-01 | EXECUTION |

---

## EXECUTION ORDER ACCOUNTING

### ORDER 1 — Cody (GID-01)
Test execution completed.

---

## INVARIANT VERIFICATION TABLE

| INV | Description | Status |
|-----|-------------|--------|
| INV-001 | Test invariant | ✅ VERIFIED |

---

## TEST EVIDENCE

| Test | Result |
|------|--------|
| test_sample | PASS |

---

## TRAINING LOOP

Training Signals Emitted:
- TS-TEST-001: Sample training signal

---

## POSITIVE CLOSURE

☑ All conditions met
☑ Session CLOSED

---

## FINAL_STATE DECLARATION

```yaml
FINAL_STATE:
  status: COMPLETE
  valid: true
```

---

## SIGNATURES & ATTESTATIONS

| Role | Agent | Status |
|------|-------|--------|
| Executor | Benson | ✅ SIGNED |
"""

INVALID_BER_MISSING_SECTIONS = """
# BER-INVALID-001

## RUNTIME ACTIVATION BLOCK
Runtime initialized

## Some Random Section
This is not a valid BER.
"""

INVALID_BER_PROHIBITED_LANGUAGE = """
# BER-INVALID-002

## RUNTIME ACTIVATION BLOCK
Runtime initialized

## EXECUTION AUTHORITY & ORCHESTRATION DECLARATION
Authority declared

## AGENT ACTIVATION & ROLE TABLE
| Agent | GID |
|-------|-----|
| Test | GID-01 |

## EXECUTION ORDER ACCOUNTING
Order 1 completed

## INVARIANT VERIFICATION TABLE
All invariants assumed complete (TBD)

## TEST EVIDENCE
See above for test results

## TRAINING LOOP
TS-001: Training signal

## POSITIVE CLOSURE
Covered elsewhere

## FINAL_STATE DECLARATION
FINAL_STATE: implicit pass

## SIGNATURES & ATTESTATIONS
Signed
"""


# =============================================================================
# ORDER 1 — STRUCTURAL DETERMINISM TESTS (CODY)
# =============================================================================

class TestStructuralDeterminism:
    """Tests for structural determinism (INV-DET-STR-*)."""
    
    def test_section_registry_immutable(self):
        """INV-DET-STR: Section registries are immutable tuples."""
        assert isinstance(BER_SECTIONS, tuple)
        assert isinstance(PAC_SECTIONS, tuple)
        assert isinstance(WRAP_SECTIONS, tuple)
        
        # Verify frozen
        with pytest.raises((TypeError, AttributeError)):
            BER_SECTIONS[0] = None  # type: ignore
    
    def test_ber_has_10_sections(self):
        """BER must have exactly 10 mandatory sections per LAW-001."""
        assert len(BER_SECTIONS) == 10
    
    def test_section_indices_sequential(self):
        """Section indices must be sequential (0-based)."""
        for i, section in enumerate(BER_SECTIONS):
            assert section.index == i, f"Section {section.name} index mismatch"
    
    def test_structural_validator_deterministic(self):
        """Same artifact produces identical structural result."""
        validator = StructuralValidator()
        
        # Run multiple times
        results = [
            validator.validate(VALID_BER_SAMPLE, ArtifactType.BER)
            for _ in range(5)
        ]
        
        # All results must be identical
        baseline = results[0]
        for result in results[1:]:
            assert result.valid == baseline.valid
            assert result.violations == baseline.violations
            assert result.sections_found == baseline.sections_found
    
    def test_inv_det_str_001_missing_section_invalid(self):
        """INV-DET-STR-001: Missing section = INVALID."""
        validator = StructuralValidator()
        result = validator.validate(INVALID_BER_MISSING_SECTIONS, ArtifactType.BER)
        
        assert not result.valid
        missing_violations = [v for v in result.violations if v.violation_type == "MISSING"]
        assert len(missing_violations) > 0
    
    def test_inv_det_str_003_empty_section_invalid(self):
        """INV-DET-STR-003: Empty section = INVALID."""
        validator = StructuralValidator()
        
        # BER with empty section
        empty_section_ber = """
## RUNTIME ACTIVATION BLOCK

## EXECUTION AUTHORITY & ORCHESTRATION DECLARATION
Content here
"""
        result = validator.validate(empty_section_ber, ArtifactType.BER)
        
        empty_violations = [v for v in result.violations if v.violation_type == "EMPTY"]
        # Runtime block is empty
        assert len(empty_violations) >= 1


# =============================================================================
# ORDER 2 — GATE DETERMINISM TESTS (CINDY)
# =============================================================================

class TestGateDeterminism:
    """Tests for gate determinism (INV-DET-GATE-*)."""
    
    def test_gates_immutable(self):
        """Gate definitions are immutable."""
        assert isinstance(BER_GATES, tuple)
        with pytest.raises((TypeError, AttributeError)):
            BER_GATES[0] = None  # type: ignore
    
    def test_gate_indices_sequential(self):
        """Gate indices must be sequential."""
        for i, gate in enumerate(BER_GATES):
            assert gate.index == i, f"Gate {gate.name} index mismatch"
    
    def test_inv_det_gate_001_fixed_order_evaluation(self):
        """INV-DET-GATE-001: Gates evaluated in fixed order."""
        pipeline = GatePipeline()
        validator = StructuralValidator()
        
        structural_result = validator.validate(VALID_BER_SAMPLE, ArtifactType.BER)
        result = pipeline.evaluate(VALID_BER_SAMPLE, structural_result)
        
        # Verify evaluations are in gate index order
        for i, evaluation in enumerate(result.evaluations):
            assert evaluation.gate_index == i
    
    def test_inv_det_gate_002_no_short_circuit(self):
        """INV-DET-GATE-002: All gates evaluated even after failure."""
        pipeline = GatePipeline()
        validator = StructuralValidator()
        
        # Use invalid BER
        structural_result = validator.validate(INVALID_BER_MISSING_SECTIONS, ArtifactType.BER)
        result = pipeline.evaluate(INVALID_BER_MISSING_SECTIONS, structural_result)
        
        # ALL gates must be evaluated
        assert len(result.evaluations) == len(BER_GATES)
    
    def test_inv_det_gate_003_no_warn_only(self):
        """INV-DET-GATE-003: No "warn-only" states - only PASS or FAIL."""
        pipeline = GatePipeline()
        validator = StructuralValidator()
        
        structural_result = validator.validate(VALID_BER_SAMPLE, ArtifactType.BER)
        result = pipeline.evaluate(VALID_BER_SAMPLE, structural_result)
        
        for evaluation in result.evaluations:
            assert evaluation.result in (GateResult.PASS, GateResult.FAIL)
    
    def test_gate_pipeline_deterministic(self):
        """Same artifact produces identical gate results."""
        pipeline = GatePipeline()
        validator = StructuralValidator()
        
        structural_result = validator.validate(VALID_BER_SAMPLE, ArtifactType.BER)
        
        results = [
            pipeline.evaluate(VALID_BER_SAMPLE, structural_result)
            for _ in range(5)
        ]
        
        baseline = results[0]
        for result in results[1:]:
            assert result.overall_result == baseline.overall_result
            assert result.failure_count == baseline.failure_count
            for i, eval in enumerate(result.evaluations):
                assert eval.result == baseline.evaluations[i].result


# =============================================================================
# ORDER 3 — CI/MECHANICAL DETERMINISM TESTS (DAN)
# =============================================================================

class TestCIMechanicalDeterminism:
    """Tests for CI and runtime mechanical enforcement (INV-DET-CI-*)."""
    
    def test_inv_det_ci_001_ci_runtime_parity(self):
        """INV-DET-CI-001: CI + runtime enforcement identical."""
        enforcer = DeterminismEnforcer()
        
        # Simulate CI run
        ci_result = enforcer.enforce(VALID_BER_SAMPLE, ArtifactType.BER)
        
        # Simulate runtime run (same function)
        runtime_result = enforcer.enforce(VALID_BER_SAMPLE, ArtifactType.BER)
        
        # Results must be identical
        assert ci_result.valid == runtime_result.valid
        assert ci_result.artifact_hash == runtime_result.artifact_hash
        assert len(ci_result.training_signals) == len(runtime_result.training_signals)
    
    def test_inv_det_ci_002_missing_enforcement_blocks(self):
        """INV-DET-CI-002: Missing enforcement blocks merge."""
        # validate_ber_or_fail must raise on invalid BER
        with pytest.raises(BERValidationFailure):
            validate_ber_or_fail(INVALID_BER_MISSING_SECTIONS)
    
    def test_validate_ber_or_fail_raises_on_invalid(self):
        """validate_ber_or_fail raises BERValidationFailure on invalid BER."""
        with pytest.raises(BERValidationFailure) as exc_info:
            validate_ber_or_fail(INVALID_BER_MISSING_SECTIONS)
        
        # Exception must contain result
        assert exc_info.value.result is not None
        assert not exc_info.value.result.valid
    
    def test_validate_ber_or_fail_returns_result_on_valid(self):
        """validate_ber_or_fail returns result on valid BER."""
        result = validate_ber_or_fail(VALID_BER_SAMPLE)
        
        assert result is not None
        assert result.valid


# =============================================================================
# ORDER 4 — SEMANTIC DETERMINISM TESTS (ALEX)
# =============================================================================

class TestSemanticDeterminism:
    """Tests for semantic determinism (INV-DET-SEM-*)."""
    
    def test_inv_det_sem_001_binary_validity(self):
        """INV-DET-SEM-001: No "mostly valid" — only VALID or INVALID."""
        validator = SemanticValidator()
        
        result = validator.validate(VALID_BER_SAMPLE)
        assert result.validity in (SemanticValidity.VALID, SemanticValidity.INVALID)
    
    def test_inv_det_sem_002_no_implied_closure(self):
        """INV-DET-SEM-002: No implied closure — prohibited phrases detected."""
        validator = SemanticValidator()
        
        result = validator.validate(INVALID_BER_PROHIBITED_LANGUAGE, strict=False)
        
        # Must detect prohibited phrases
        prohibited = [v for v in result.violations if v.violation_type == "PROHIBITED"]
        assert len(prohibited) > 0
    
    def test_inv_det_sem_003_deterministic_mapping(self):
        """INV-DET-SEM-003: Language maps to outcome deterministically."""
        validator = SemanticValidator()
        
        # Same input 5 times
        results = [
            validator.validate(INVALID_BER_PROHIBITED_LANGUAGE, strict=False)
            for _ in range(5)
        ]
        
        baseline = results[0]
        for result in results[1:]:
            assert result.validity == baseline.validity
            assert len(result.violations) == len(baseline.violations)
    
    def test_prohibited_phrases_detected(self):
        """All LAW-001 prohibited phrases must be detected."""
        validator = SemanticValidator()
        
        # Test each prohibited phrase
        prohibited = ["implicit pass", "covered elsewhere", "out of scope", 
                      "assumed complete", "see above", "tbd", "todo"]
        
        for phrase in prohibited:
            test_text = f"This is a test with {phrase} in it."
            result = validator.validate(test_text, strict=False)
            
            found = any(v.phrase == phrase for v in result.violations)
            assert found, f"Prohibited phrase '{phrase}' not detected"


# =============================================================================
# ORDER 5 — ADVERSARIAL REPEATABILITY TESTS (SAM)
# =============================================================================

class TestAdversarialDeterminism:
    """Adversarial tests for absolute repeatability."""
    
    def test_same_artifact_5_runs_identical(self):
        """Same artifact × 5 runs = identical output."""
        is_deterministic, discrepancies = verify_determinism(
            VALID_BER_SAMPLE,
            ArtifactType.BER,
            iterations=5
        )
        
        assert is_deterministic, f"Non-deterministic: {discrepancies}"
    
    def test_same_artifact_10_runs_identical(self):
        """Same artifact × 10 runs = identical output."""
        is_deterministic, discrepancies = verify_determinism(
            VALID_BER_SAMPLE,
            ArtifactType.BER,
            iterations=10
        )
        
        assert is_deterministic, f"Non-deterministic: {discrepancies}"
    
    def test_invalid_artifact_repeatability(self):
        """Invalid artifacts also produce deterministic results."""
        is_deterministic, discrepancies = verify_determinism(
            INVALID_BER_MISSING_SECTIONS,
            ArtifactType.BER,
            iterations=5
        )
        
        assert is_deterministic, f"Non-deterministic: {discrepancies}"
    
    def test_hash_consistency(self):
        """Artifact hash is consistent across runs."""
        enforcer = DeterminismEnforcer()
        
        hashes = [
            enforcer.enforce(VALID_BER_SAMPLE, ArtifactType.BER).artifact_hash
            for _ in range(5)
        ]
        
        assert len(set(hashes)) == 1, "Hash varies across runs"
    
    def test_signal_ids_consistent(self):
        """Training signal IDs are consistent across runs."""
        enforcer = DeterminismEnforcer()
        
        signal_sets = [
            frozenset(s.signal_id for s in enforcer.enforce(
                INVALID_BER_MISSING_SECTIONS, ArtifactType.BER
            ).training_signals)
            for _ in range(5)
        ]
        
        assert len(set(signal_sets)) == 1, "Signal IDs vary across runs"


# =============================================================================
# ORDER 6 — BEHAVIORAL DETERMINISM TESTS (MAGGIE)
# =============================================================================

class TestBehavioralDeterminism:
    """Tests for behavioral determinism (INV-DET-BEH-*)."""
    
    def test_inv_det_beh_001_same_violation_same_signal(self):
        """INV-DET-BEH-001: Same violation → same signal."""
        enforcer = BehavioralEnforcer()
        
        # Generate signal for same violation 5 times
        signals = [
            enforcer.generate_signal("MISSING", {"section": "TEST_SECTION"})
            for _ in range(5)
        ]
        
        baseline_id = signals[0].signal_id
        for signal in signals[1:]:
            assert signal.signal_id == baseline_id
    
    def test_inv_det_beh_002_same_signal_same_pac(self):
        """INV-DET-BEH-002: Same signal → same corrective PAC type."""
        enforcer = BehavioralEnforcer()
        
        # Same violation type should always produce same PAC type
        pac_types = [
            enforcer.get_corrective_pac_type("MISSING")
            for _ in range(5)
        ]
        
        assert len(set(pac_types)) == 1
    
    def test_training_signal_mapping_immutable(self):
        """Training signal mappings are immutable."""
        from core.governance.determinism_enforcement import TRAINING_SIGNAL_MAPPINGS
        
        assert isinstance(TRAINING_SIGNAL_MAPPINGS, tuple)
        for mapping in TRAINING_SIGNAL_MAPPINGS:
            # Frozen dataclass
            with pytest.raises(AttributeError):
                mapping.violation_type = "CHANGED"  # type: ignore


# =============================================================================
# INTEGRATION TESTS — FULL PIPELINE
# =============================================================================

class TestDeterminismIntegration:
    """Integration tests for full determinism pipeline."""
    
    def test_full_pipeline_deterministic(self):
        """Full enforcement pipeline is deterministic."""
        enforcer = DeterminismEnforcer()
        
        results = [
            enforcer.enforce(VALID_BER_SAMPLE, ArtifactType.BER)
            for _ in range(5)
        ]
        
        baseline = results[0]
        for result in results[1:]:
            assert result.valid == baseline.valid
            assert result.structural.valid == baseline.structural.valid
            assert result.semantic.valid == baseline.semantic.valid
            assert result.gate.all_passed == baseline.gate.all_passed
    
    def test_artifact_type_affects_validation(self):
        """Different artifact types use different section registries."""
        validator = StructuralValidator()
        
        ber_result = validator.validate(VALID_BER_SAMPLE, ArtifactType.BER)
        pac_result = validator.validate(VALID_BER_SAMPLE, ArtifactType.PAC)
        
        # Same text, different artifact type → different validation
        assert ber_result.sections_expected != pac_result.sections_expected
    
    def test_result_serializable(self):
        """Enforcement result is JSON-serializable."""
        enforcer = DeterminismEnforcer()
        result = enforcer.enforce(VALID_BER_SAMPLE, ArtifactType.BER)
        
        result_dict = result.to_dict()
        
        import json
        serialized = json.dumps(result_dict)
        assert len(serialized) > 0


# =============================================================================
# REGRESSION TESTS
# =============================================================================

class TestDeterminismRegression:
    """Regression tests to catch non-deterministic behavior."""
    
    def test_no_timestamp_in_violation_equality(self):
        """Timestamps should not affect violation equality."""
        enforcer = DeterminismEnforcer()
        
        # Run twice with time gap
        import time
        result1 = enforcer.enforce(INVALID_BER_MISSING_SECTIONS, ArtifactType.BER)
        time.sleep(0.01)
        result2 = enforcer.enforce(INVALID_BER_MISSING_SECTIONS, ArtifactType.BER)
        
        # Violations should match (ignoring timestamps)
        assert result1.structural.violations == result2.structural.violations
    
    def test_no_random_ordering(self):
        """No random ordering in any output."""
        enforcer = DeterminismEnforcer()
        
        for _ in range(10):
            result = enforcer.enforce(INVALID_BER_MISSING_SECTIONS, ArtifactType.BER)
            
            # Violations in index order
            prev_idx = -1
            for v in result.structural.violations:
                if v.violation_type == "MISSING":
                    # Same type violations should be in index order
                    if v.section_index < prev_idx:
                        pytest.fail("Violations not in deterministic order")
                    prev_idx = v.section_index


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
