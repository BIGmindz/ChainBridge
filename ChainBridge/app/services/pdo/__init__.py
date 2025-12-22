"""PDO (Proof Decision Outcome) enforcement services.

This package implements server-side PDO validation and enforcement
per the PDO Enforcement Model v1 (LOCKED doctrine).

INVARIANTS (non-negotiable):
1. No execution without PDO validation
2. PDOs must be validated BEFORE any side effects
3. Fail closed - no soft bypasses
4. No environment-based skips
"""
