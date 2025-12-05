"""
ALEX Governance & Alignment Engine (GID-08)
Implements multi-layer governance for ChainBridge settlement decisions.
"""
import uuid
from pathlib import Path
import yaml
from typing import Any, Dict

RULES_PATH = Path(__file__).with_name("rules.yaml")

class AlexGovernanceEngine:
    def __init__(self):
        self.rules = self.load_rules()

    def load_rules(self) -> Dict[str, Any]:
        with open(RULES_PATH, "r") as f:
            return yaml.safe_load(f)

    def _make_metadata(self, rationale, severity, rule_id, decision_path, trace_id=None):
        return {
            "rationale": rationale,
            "severity": severity,
            "rule_id": rule_id,
            "decision_path": decision_path,
            "trace_id": trace_id or str(uuid.uuid4()),
        }

    def apply_governance_rules(self, token_state, risk_state, ml_prediction):
        matched_rule = None
        decision_path = []
        # Risk rules
        for rule in self.rules.get("Risk Rules", []):
            if eval(rule["condition"], {}, {"event": risk_state, "FAIL_THRESHOLD": risk_state.get("fail_threshold", 80)}):
                matched_rule = rule
                decision_path.append(rule["id"])
                break
        # ML rules
        if not matched_rule:
            for rule in self.rules.get("ML Governance Rules", []):
                if eval(rule["condition"], {}, {"model": ml_prediction}):
                    matched_rule = rule
                    decision_path.append(rule["id"])
                    break
        # Economic rules
        if not matched_rule:
            for rule in self.rules.get("Economic Rules", []):
                if eval(rule["condition"], {}, {"event": token_state}):
                    matched_rule = rule
                    decision_path.append(rule["id"])
                    break
        # Time rules
        if not matched_rule:
            for rule in self.rules.get("Time Rules", []):
                if eval(rule["condition"], {}, {"event": token_state}):
                    matched_rule = rule
                    decision_path.append(rule["id"])
                    break
        # Proof rules (future)
        if not matched_rule:
            for rule in self.rules.get("Proof Rules", []):
                if eval(rule["condition"], {}, {"event": token_state}):
                    matched_rule = rule
                    decision_path.append(rule["id"])
                    break
        if matched_rule:
            return self.generate_governance_metadata(matched_rule, decision_path)
        # Default: approved
        return self._make_metadata("Approved by default", "LOW", "none", decision_path or ["default"])

    def evaluate_severity(self, rule):
        return rule.get("severity", "LOW")

    def generate_governance_metadata(self, rule, decision_path):
        return self._make_metadata(
            rationale=rule.get("rationale", ""),
            severity=rule.get("severity", "LOW"),
            rule_id=rule.get("id", "unknown"),
            decision_path=decision_path,
        )

    def decision_path(self, events):
        # Return ordered list of rule ids matched
        return [e.get("rule_id", "unknown") for e in events]

alex_engine = AlexGovernanceEngine()
