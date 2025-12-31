"""
Base Rule Module
================

Base utilities for creating Lex rules.
"""

from typing import Any, Callable

from ..schema import LexRule, RuleCategory, RuleSeverity


# Type alias for predicate function
RulePredicate = Callable[[dict[str, Any], dict[str, Any]], bool]


def create_rule(
    rule_id: str,
    category: RuleCategory,
    severity: RuleSeverity,
    name: str,
    description: str,
    predicate_fn: str,
    error_template: str,
    override_allowed: bool = True,
    requires_senior_override: bool = False,
) -> LexRule:
    """
    Factory function to create a LexRule.
    
    Args:
        rule_id: Unique identifier (e.g., "LEX-INT-001")
        category: Rule category (INTEGRITY, AUTHORIZATION, etc.)
        severity: Violation severity (CRITICAL, HIGH, MEDIUM, LOW, INFO)
        name: Human-readable rule name
        description: Full description of what the rule enforces
        predicate_fn: Name of the predicate function
        error_template: Template for error messages (supports {rule_id}, {rule_name}, etc.)
        override_allowed: Whether this rule can be overridden
        requires_senior_override: Whether override requires senior authority
        
    Returns:
        LexRule instance (immutable)
    """
    return LexRule(
        rule_id=rule_id,
        category=category,
        severity=severity,
        name=name,
        description=description,
        predicate_fn=predicate_fn,
        error_template=error_template,
        override_allowed=override_allowed,
        requires_senior_override=requires_senior_override,
    )


class RuleBuilder:
    """
    Builder pattern for creating Lex rules.
    
    Usage:
        rule = (RuleBuilder()
            .with_id("LEX-INT-001")
            .with_category(RuleCategory.INTEGRITY)
            .with_severity(RuleSeverity.CRITICAL)
            .with_name("Signature Verification")
            .build())
    """
    
    def __init__(self):
        self._rule_id: str = ""
        self._category: RuleCategory = RuleCategory.GOVERNANCE
        self._severity: RuleSeverity = RuleSeverity.MEDIUM
        self._name: str = ""
        self._description: str = ""
        self._predicate_fn: str = ""
        self._error_template: str = "Rule {rule_id} failed"
        self._override_allowed: bool = True
        self._requires_senior_override: bool = False
    
    def with_id(self, rule_id: str) -> "RuleBuilder":
        self._rule_id = rule_id
        return self
    
    def with_category(self, category: RuleCategory) -> "RuleBuilder":
        self._category = category
        return self
    
    def with_severity(self, severity: RuleSeverity) -> "RuleBuilder":
        self._severity = severity
        return self
    
    def with_name(self, name: str) -> "RuleBuilder":
        self._name = name
        return self
    
    def with_description(self, description: str) -> "RuleBuilder":
        self._description = description
        return self
    
    def with_predicate(self, predicate_fn: str) -> "RuleBuilder":
        self._predicate_fn = predicate_fn
        return self
    
    def with_error_template(self, template: str) -> "RuleBuilder":
        self._error_template = template
        return self
    
    def allow_override(self, allowed: bool = True) -> "RuleBuilder":
        self._override_allowed = allowed
        return self
    
    def require_senior_override(self, required: bool = True) -> "RuleBuilder":
        self._requires_senior_override = required
        return self
    
    def no_override(self) -> "RuleBuilder":
        self._override_allowed = False
        return self
    
    def build(self) -> LexRule:
        """Build the LexRule instance."""
        if not self._rule_id:
            raise ValueError("Rule ID is required")
        if not self._name:
            raise ValueError("Rule name is required")
        
        return LexRule(
            rule_id=self._rule_id,
            category=self._category,
            severity=self._severity,
            name=self._name,
            description=self._description,
            predicate_fn=self._predicate_fn,
            error_template=self._error_template,
            override_allowed=self._override_allowed,
            requires_senior_override=self._requires_senior_override,
        )
