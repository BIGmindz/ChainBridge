#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
🟦🟩 UNIT TESTS: EXECUTION ACCURACY HARDENING
PAC Reference: PAC-BENSON-P56-CORRECTIVE-EXECUTION-ACCURACY-HARDENING-01
═══════════════════════════════════════════════════════════════════════════════

Tests for execution accuracy and self-evaluation constraints.

Invariants Tested:
    - GS_170: Self-referential accuracy scoring blocked
    - GS_171: Missing ground-truth source warning
    - GS_172: Prescriptive language in self-eval warning
    - GS_173: Self-approval HARD_BLOCK
    - GS_174: Corrective action recommendation warning
"""

import unittest
from datetime import datetime, timezone

# Import from benson_execution
from benson_execution import (
    validate_ground_truth_sources,
    validate_self_eval_constraints,
    VALID_GROUND_TRUTH_SOURCES,
    INVALID_TRUTH_SOURCES,
    FORBIDDEN_SELF_EVAL_FIELDS,
    PRESCRIPTIVE_PATTERNS,
    BlockReason,
)


class TestGroundTruthSources(unittest.TestCase):
    """Test suite for ground-truth source validation (GS_170/GS_171)."""
    
    def test_valid_ground_truth_sources_pass(self):
        """Test that valid ground-truth sources are accepted."""
        result = validate_ground_truth_sources(["human_review_outcome"])
        self.assertTrue(result["valid"])
        self.assertIsNone(result["error_code"])
    
    def test_multiple_valid_sources_pass(self):
        """Test multiple valid ground-truth sources."""
        result = validate_ground_truth_sources([
            "human_review_outcome",
            "override_decisions",
            "post_execution_failure_analysis"
        ])
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["warnings"]), 0)
    
    def test_missing_ground_truth_gs171(self):
        """Test GS_171: Missing ground-truth sources."""
        result = validate_ground_truth_sources([])
        self.assertFalse(result["valid"])
        self.assertEqual(result["error_code"], "GS_171")
        self.assertIn("Missing ground-truth", result["message"])
    
    def test_none_ground_truth_gs171(self):
        """Test GS_171: None ground-truth sources."""
        result = validate_ground_truth_sources(None)
        self.assertFalse(result["valid"])
        self.assertEqual(result["error_code"], "GS_171")
    
    def test_self_referential_accuracy_gs170(self):
        """Test GS_170: Self-referential accuracy source blocked."""
        result = validate_ground_truth_sources(["self_assessment"])
        self.assertFalse(result["valid"])
        self.assertEqual(result["error_code"], "GS_170")
        self.assertIn("Self-referential", result["message"])
    
    def test_model_confidence_blocked_gs170(self):
        """Test GS_170: Model confidence as truth source blocked."""
        result = validate_ground_truth_sources(["model_confidence"])
        self.assertFalse(result["valid"])
        self.assertEqual(result["error_code"], "GS_170")
    
    def test_internal_scoring_blocked_gs170(self):
        """Test GS_170: Internal scoring blocked."""
        result = validate_ground_truth_sources(["internal_scoring"])
        self.assertFalse(result["valid"])
        self.assertEqual(result["error_code"], "GS_170")
    
    def test_auto_generated_blocked_gs170(self):
        """Test GS_170: Auto-generated truth signal blocked."""
        result = validate_ground_truth_sources(["auto_generated"])
        self.assertFalse(result["valid"])
        self.assertEqual(result["error_code"], "GS_170")
    
    def test_mixed_valid_invalid_fails(self):
        """Test that mixing valid with invalid source fails."""
        result = validate_ground_truth_sources([
            "human_review_outcome",
            "self_assessment"  # Invalid
        ])
        self.assertFalse(result["valid"])
        self.assertEqual(result["error_code"], "GS_170")
    
    def test_unrecognized_source_warns(self):
        """Test that unrecognized sources generate warnings."""
        result = validate_ground_truth_sources([
            "human_review_outcome",
            "unknown_source"
        ])
        self.assertTrue(result["valid"])  # Still valid
        self.assertGreater(len(result["warnings"]), 0)
        self.assertEqual(result["warnings"][0]["warning_code"], "GS_171")


class TestSelfEvalConstraints(unittest.TestCase):
    """Test suite for self-evaluation constraints (GS_172/GS_173/GS_174)."""
    
    def test_valid_descriptive_self_eval_passes(self):
        """Test that descriptive-only self-eval passes."""
        self_eval = {
            "confidence_level": 0.85,
            "uncertainty_factors": ["data variance", "sample size"],
            "deviation_from_baseline": {
                "metric_name": "quality_score",
                "expected_value": 0.9,
                "observed_value": 0.87,
                "deviation_percent": -3.3
            }
        }
        result = validate_self_eval_constraints(self_eval)
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["warnings"]), 0)
    
    def test_self_approval_blocked_gs173(self):
        """Test GS_173: Self-approval is HARD_BLOCK."""
        self_eval = {
            "confidence_level": 0.9,
            "self_approved": True  # Forbidden - GS_173
        }
        result = validate_self_eval_constraints(self_eval)
        self.assertFalse(result["valid"])
        self.assertEqual(result["error_code"], "GS_173")
    
    def test_improvement_plan_blocked_gs173(self):
        """Test GS_173: Improvement plan is HARD_BLOCK."""
        self_eval = {
            "confidence_level": 0.8,
            "improvement_plan": "Increase training data"  # Forbidden - GS_173
        }
        result = validate_self_eval_constraints(self_eval)
        self.assertFalse(result["valid"])
        self.assertEqual(result["error_code"], "GS_173")
    
    def test_recommended_action_warns_gs174(self):
        """Test GS_174: Recommended action generates warning."""
        self_eval = {
            "confidence_level": 0.85,
            "recommended_action": "Retrain model"  # Forbidden - GS_174
        }
        result = validate_self_eval_constraints(self_eval)
        self.assertTrue(result["valid"])  # Warning, not block
        warnings = [w for w in result["warnings"] if w["warning_code"] == "GS_174"]
        self.assertGreater(len(warnings), 0)
    
    def test_corrective_steps_warns_gs174(self):
        """Test GS_174: Corrective steps generates warning."""
        self_eval = {
            "corrective_steps": ["Step 1", "Step 2"]  # Forbidden - GS_174
        }
        result = validate_self_eval_constraints(self_eval)
        self.assertTrue(result["valid"])  # Warning, not block
        warnings = [w for w in result["warnings"] if w["warning_code"] == "GS_174"]
        self.assertGreater(len(warnings), 0)
    
    def test_suggested_fix_warns_gs174(self):
        """Test GS_174: Suggested fix generates warning."""
        self_eval = {
            "suggested_fix": "Update configuration"  # Forbidden - GS_174
        }
        result = validate_self_eval_constraints(self_eval)
        warnings = [w for w in result["warnings"] if w["warning_code"] == "GS_174"]
        self.assertGreater(len(warnings), 0)
    
    def test_prescriptive_should_warns_gs172(self):
        """Test GS_172: 'should' language generates warning."""
        self_eval = {
            "observation": "Quality score should be higher"
        }
        result = validate_self_eval_constraints(self_eval)
        warnings = [w for w in result["warnings"] if w["warning_code"] == "GS_172"]
        self.assertGreater(len(warnings), 0)
    
    def test_prescriptive_must_warns_gs172(self):
        """Test GS_172: 'must' language generates warning."""
        self_eval = {
            "notes": ["The system must be reconfigured"]
        }
        result = validate_self_eval_constraints(self_eval)
        warnings = [w for w in result["warnings"] if w["warning_code"] == "GS_172"]
        self.assertGreater(len(warnings), 0)
    
    def test_prescriptive_needs_to_warns_gs172(self):
        """Test GS_172: 'needs to' language generates warning."""
        self_eval = {
            "observation": "The model needs to be updated"
        }
        result = validate_self_eval_constraints(self_eval)
        warnings = [w for w in result["warnings"] if w["warning_code"] == "GS_172"]
        self.assertGreater(len(warnings), 0)
    
    def test_prescriptive_recommend_warns_gs172(self):
        """Test GS_172: 'recommend' language generates warning."""
        self_eval = {
            "assessment": "I recommend increasing batch size"
        }
        result = validate_self_eval_constraints(self_eval)
        warnings = [w for w in result["warnings"] if w["warning_code"] == "GS_172"]
        self.assertGreater(len(warnings), 0)
    
    def test_prescriptive_suggest_warns_gs172(self):
        """Test GS_172: 'suggest' language generates warning."""
        self_eval = {
            "notes": ["Suggest reviewing the logs"]
        }
        result = validate_self_eval_constraints(self_eval)
        warnings = [w for w in result["warnings"] if w["warning_code"] == "GS_172"]
        self.assertGreater(len(warnings), 0)
    
    def test_empty_self_eval_passes(self):
        """Test that empty self-eval passes validation."""
        result = validate_self_eval_constraints({})
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["warnings"]), 0)
    
    def test_numeric_only_self_eval_passes(self):
        """Test that numeric-only self-eval has no prescriptive warnings."""
        self_eval = {
            "confidence_level": 0.75,
            "deviation_percent": -5.2,
            "sample_count": 100
        }
        result = validate_self_eval_constraints(self_eval)
        self.assertTrue(result["valid"])
        warnings = [w for w in result["warnings"] if w["warning_code"] == "GS_172"]
        self.assertEqual(len(warnings), 0)


class TestBlockReasonEnum(unittest.TestCase):
    """Test that BlockReason includes P56 additions."""
    
    def test_self_approval_blocked_in_enum(self):
        """Test SELF_APPROVAL_BLOCKED is in BlockReason."""
        self.assertEqual(
            BlockReason.SELF_APPROVAL_BLOCKED.value,
            "SELF_APPROVAL_BLOCKED"
        )


class TestGroundTruthConstants(unittest.TestCase):
    """Test ground-truth source constants are properly defined."""
    
    def test_valid_sources_defined(self):
        """Test VALID_GROUND_TRUTH_SOURCES contains required entries."""
        required = [
            "human_review_outcome",
            "override_decisions",
            "post_execution_failure_analysis",
        ]
        for source in required:
            self.assertIn(source, VALID_GROUND_TRUTH_SOURCES)
    
    def test_invalid_sources_defined(self):
        """Test INVALID_TRUTH_SOURCES contains required entries."""
        required = [
            "self_assessment",
            "model_confidence",
            "internal_scoring",
            "auto_generated",
        ]
        for source in required:
            self.assertIn(source, INVALID_TRUTH_SOURCES)
    
    def test_no_overlap_valid_invalid(self):
        """Test no overlap between valid and invalid sources."""
        overlap = set(VALID_GROUND_TRUTH_SOURCES) & set(INVALID_TRUTH_SOURCES)
        self.assertEqual(len(overlap), 0)


class TestForbiddenSelfEvalFields(unittest.TestCase):
    """Test forbidden self-eval fields are properly defined."""
    
    def test_gs173_fields_defined(self):
        """Test GS_173 (HARD_BLOCK) fields are defined."""
        gs173_fields = [k for k, v in FORBIDDEN_SELF_EVAL_FIELDS.items() if v == "GS_173"]
        self.assertIn("self_approved", gs173_fields)
        self.assertIn("improvement_plan", gs173_fields)
    
    def test_gs174_fields_defined(self):
        """Test GS_174 (WARNING) fields are defined."""
        gs174_fields = [k for k, v in FORBIDDEN_SELF_EVAL_FIELDS.items() if v == "GS_174"]
        self.assertIn("recommended_action", gs174_fields)
        self.assertIn("corrective_steps", gs174_fields)


class TestPrescriptivePatterns(unittest.TestCase):
    """Test prescriptive language patterns are properly defined."""
    
    def test_patterns_are_regex(self):
        """Test patterns can be compiled as regex."""
        import re
        for pattern in PRESCRIPTIVE_PATTERNS:
            try:
                re.compile(pattern)
            except re.error:
                self.fail(f"Invalid regex pattern: {pattern}")
    
    def test_should_pattern_matches(self):
        """Test 'should' pattern matches correctly."""
        import re
        pattern = next(p for p in PRESCRIPTIVE_PATTERNS if "should" in p)
        self.assertTrue(re.search(pattern, "you should update", re.IGNORECASE))
        self.assertFalse(re.search(pattern, "shoulder pain", re.IGNORECASE))
    
    def test_must_pattern_matches(self):
        """Test 'must' pattern matches correctly."""
        import re
        pattern = next(p for p in PRESCRIPTIVE_PATTERNS if "must" in p)
        self.assertTrue(re.search(pattern, "this must change", re.IGNORECASE))


class TestWarningVsFailureBehavior(unittest.TestCase):
    """Test correct warning vs failure behavior per severity."""
    
    def test_gs170_is_warning_not_block(self):
        """Test GS_170 returns valid=False (blocks self-ref)."""
        result = validate_ground_truth_sources(["self_assessment"])
        self.assertFalse(result["valid"])
    
    def test_gs171_is_warning_not_block(self):
        """Test GS_171 returns valid=False (no sources)."""
        result = validate_ground_truth_sources([])
        self.assertFalse(result["valid"])
    
    def test_gs172_is_warning_continues(self):
        """Test GS_172 allows continuation with warning."""
        self_eval = {"note": "should be updated"}
        result = validate_self_eval_constraints(self_eval)
        self.assertTrue(result["valid"])  # Continues with warning
        self.assertGreater(len(result["warnings"]), 0)
    
    def test_gs173_is_hard_block(self):
        """Test GS_173 is HARD_BLOCK (self-approval)."""
        self_eval = {"self_approved": True}
        result = validate_self_eval_constraints(self_eval)
        self.assertFalse(result["valid"])  # Hard block
        self.assertEqual(result["error_code"], "GS_173")
    
    def test_gs174_is_warning_continues(self):
        """Test GS_174 allows continuation with warning."""
        self_eval = {"recommended_action": "do something"}
        result = validate_self_eval_constraints(self_eval)
        self.assertTrue(result["valid"])  # Continues with warning
        warnings = [w for w in result["warnings"] if w["warning_code"] == "GS_174"]
        self.assertGreater(len(warnings), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
