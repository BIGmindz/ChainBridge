# Decision Logic Specification

**PAC ID**: PAC-MAGGIE-DECISION-LOGIC-01
**Author**: MAGGIE (GID-10) — ML & Applied AI Lead
**Version**: 1.0.0
**Status**: LOCKED

---

## 1. Philosophy

All decision logic in ChainBridge follows these principles:

| Principle | Description |
|-----------|-------------|
| **Glass-Box** | Every rule is inspectable; no hidden state |
| **Deterministic** | Same inputs → same outputs → same explanation |
| **Monotonic** | More severe inputs → more severe outputs |
| **Conservative** | Bias toward false negatives (reject/escalate) over false positives |
| **Auditable** | Every decision includes a human-readable explanation |

**What is NOT permitted:**
- Probabilities or confidence scores
- Learned weights or model outputs
- Hidden state between decisions
- Non-deterministic logic (randomness, timing)
- Implicit type coercion

---

## 2. Decision Inputs (Canonical Feature Set)

### 2.1 Payment Request Decision

| Field | Type | Required | Validation | Domain |
|-------|------|----------|------------|--------|
| `amount` | float | ✅ | Must be > 0 | Payment value in specified currency |
| `currency` | string | ❌ | ISO 4217 code | Default: "USD" |
| `vendor_id` | string | ✅ | Non-empty | Vendor identifier |
| `requestor_id` | string | ✅ | Non-empty | Person/system requesting payment |

**Input Constraints:**
- `amount` MUST be a positive finite number (not NaN, not Inf)
- `vendor_id` MUST NOT be empty string or whitespace-only
- `requestor_id` MUST NOT be empty string or whitespace-only
- `currency` MUST be 3-character uppercase string if provided

### 2.2 Input Audit Notes

| Risk | Status | Mitigation |
|------|--------|------------|
| Type leakage (string "1000" vs int 1000) | MITIGATED | Explicit float conversion with validation |
| Missing fields | MITIGATED | Explicit None checks before processing |
| Negative amounts | MITIGATED | Explicit > 0 validation |
| Empty identifiers | MITIGATED | Non-empty string validation |
| Currency ambiguity | MITIGATED | Uppercase normalization, default USD |

---

## 3. Decision Rules (V1)

### 3.1 Rule: Payment Threshold (RULE-PAYMENT-THRESHOLD-V1)

**Version**: 1.0.0
**Threshold**: $10,000.00 USD

```
IF amount <= THRESHOLD:
    RETURN APPROVED
ELSE:
    RETURN REQUIRES_REVIEW
```

**Rule Properties:**
- **Monotonic**: Higher amounts → more restrictive outcome (APPROVED → REQUIRES_REVIEW)
- **Deterministic**: No randomness, no external state
- **Conservative**: Above threshold triggers human review, never auto-approved

### 3.2 Rule: Input Validation (RULE-INPUT-VALIDATION-V1)

**Version**: 1.0.0

```
IF amount IS NULL:
    RETURN ERROR("Missing required field: amount")

IF amount IS NOT NUMERIC:
    RETURN ERROR("Invalid amount type")

IF amount <= 0:
    RETURN ERROR("Amount must be positive")

IF vendor_id IS NULL OR EMPTY:
    RETURN ERROR("Missing required field: vendor_id")

IF requestor_id IS NULL OR EMPTY:
    RETURN ERROR("Missing required field: requestor_id")
```

### 3.3 Rule: Event Type Validation (RULE-EVENT-TYPE-V1)

**Version**: 1.0.0

```
IF event_type NOT IN SUPPORTED_TYPES:
    RETURN ERROR("Unsupported event type")
```

**Supported Types (V1)**:
- `payment_request`

---

## 4. Decision Outputs

### 4.1 Outcome Enumeration

| Outcome | Code | Description | Next Action |
|---------|------|-------------|-------------|
| `APPROVED` | 100 | Decision passes threshold | Execute action |
| `REJECTED` | 200 | Decision explicitly denied | Log and halt |
| `REQUIRES_REVIEW` | 300 | Human review required | Queue for manual review |
| `ERROR` | 400 | Invalid input or system error | Log error, halt execution |

### 4.2 Output Schema

```python
@dataclass(frozen=True)
class DecisionOutput:
    outcome: DecisionOutcome        # One of: APPROVED, REJECTED, REQUIRES_REVIEW, ERROR
    rule_id: str                    # e.g., "RULE-PAYMENT-THRESHOLD-V1"
    rule_version: str               # e.g., "1.0.0"
    inputs_snapshot: dict           # All inputs used in decision
    explanation: str                # Human-readable explanation
    timestamp: str                  # ISO 8601 timestamp
```

---

## 5. Explanation Schema

### 5.1 Template Structure

Every decision explanation follows this template:

```
[OUTCOME] — [RULE_ID] v[VERSION]
Reason: [PLAIN_LANGUAGE_REASON]
Inputs: [RELEVANT_INPUT_VALUES]
Threshold: [THRESHOLD_VALUE] (if applicable)
```

### 5.2 Examples

**Approved Payment:**
```
APPROVED — RULE-PAYMENT-THRESHOLD-V1 v1.0.0
Reason: Payment amount is within auto-approval threshold.
Inputs: amount=$5,000.00, currency=USD, vendor=ACME-001
Threshold: $10,000.00
```

**Requires Review:**
```
REQUIRES_REVIEW — RULE-PAYMENT-THRESHOLD-V1 v1.0.0
Reason: Payment amount exceeds auto-approval threshold and requires human review.
Inputs: amount=$15,000.00, currency=USD, vendor=ACME-001
Threshold: $10,000.00
```

**Error (Missing Input):**
```
ERROR — RULE-INPUT-VALIDATION-V1 v1.0.0
Reason: Required field 'amount' is missing from payment request.
Inputs: vendor_id=ACME-001, requestor_id=user-123
```

---

## 6. Edge Cases (Explicit Handling)

| Edge Case | Expected Behavior | Rule Applied |
|-----------|-------------------|--------------|
| `amount = 0` | ERROR | RULE-INPUT-VALIDATION-V1 |
| `amount = -100` | ERROR | RULE-INPUT-VALIDATION-V1 |
| `amount = 10000.00` (exact threshold) | APPROVED | RULE-PAYMENT-THRESHOLD-V1 |
| `amount = 10000.01` | REQUIRES_REVIEW | RULE-PAYMENT-THRESHOLD-V1 |
| `amount = "ten thousand"` (string) | ERROR | RULE-INPUT-VALIDATION-V1 |
| `amount = NaN` | ERROR | RULE-INPUT-VALIDATION-V1 |
| `amount = Infinity` | ERROR | RULE-INPUT-VALIDATION-V1 |
| `vendor_id = ""` | ERROR | RULE-INPUT-VALIDATION-V1 |
| `vendor_id = "   "` (whitespace) | ERROR | RULE-INPUT-VALIDATION-V1 |
| `event_type = "unknown"` | ERROR | RULE-EVENT-TYPE-V1 |

---

## 7. Failure Modes

### 7.1 Recoverable Failures

| Failure | Symptom | Recovery |
|---------|---------|----------|
| Invalid input type | ERROR outcome | Caller corrects input and resubmits |
| Missing required field | ERROR outcome | Caller provides missing field |
| Unsupported event type | ERROR outcome | Use supported event type |

### 7.2 Non-Recoverable Failures (System)

| Failure | Symptom | Response |
|---------|---------|----------|
| Decision engine unavailable | Exception raised | Fail closed, no action taken |
| Proof store unavailable | Exception raised | Fail closed, decision not persisted |

### 7.3 Failure Philosophy

**ALWAYS FAIL CLOSED:**
- If in doubt, do NOT approve
- If decision cannot be computed, HALT (do not default to any outcome)
- If explanation cannot be generated, include error details, never empty string

---

## 8. Invariants (Must Hold)

These invariants MUST be true for every decision:

1. **Determinism**: `decide(event) == decide(event)` for identical events
2. **Explanation Coverage**: Every outcome has a non-empty explanation
3. **Input Traceability**: Every decision includes snapshot of inputs used
4. **Monotonicity**: For payment threshold, `amount_a > amount_b` implies `outcome_a >= outcome_b`
5. **No Side Effects**: Decision computation never mutates external state
6. **Audit Trail**: Every decision can be reconstructed from logged data

---

## 9. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-19 | MAGGIE (GID-10) | Initial specification |

---

## 10. Appendix: Decision Flow Diagram

```
┌─────────────────┐
│  Input Event    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Event Type      │────▶│ ERROR           │
│ Validation      │ NO  │ Unsupported     │
└────────┬────────┘     └─────────────────┘
         │ YES
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Input           │────▶│ ERROR           │
│ Validation      │ NO  │ Invalid Input   │
└────────┬────────┘     └─────────────────┘
         │ YES
         ▼
┌─────────────────┐     ┌─────────────────┐
│ amount <=       │────▶│ REQUIRES_REVIEW │
│ threshold?      │ NO  │                 │
└────────┬────────┘     └─────────────────┘
         │ YES
         ▼
┌─────────────────┐
│ APPROVED        │
└─────────────────┘
```

---

**END OF SPECIFICATION**
