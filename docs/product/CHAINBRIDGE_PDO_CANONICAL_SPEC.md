# PROOF DECISION OUTCOME (PDO) — CANONICAL SPEC v1

**AUTHORITY:** Benson — CTO / Canonical Authority
**STATUS:** LOCKED (v1)

---

## A. CANONICAL DEFINITION

A **Proof Decision Outcome (PDO)** is a **machine-verifiable, immutable record that binds a specific decision to its inputs, governing policy, execution action, and observed outcome**, such that the decision can be audited, validated, and defended independently of the system, agent, or organization that produced it.

A PDO is the **digital receipt for a decision**.

---

## B. REQUIRED FIELDS (CONCEPTUAL SCHEMA)

Every PDO **must** include the following fields:

1. **pdo_id**
   - Globally unique, canonical identifier

2. **decision_subject**
   - What the decision was about (shipment, payment, agent action, etc.)

3. **actor**
   - Human or agent identity responsible for the decision

4. **inputs**
   - References or hashes of all inputs used in the decision
   - Inputs must be reproducible or verifiable

5. **policy_reference**
   - Explicit reference to the governing policy, rule, or invariant applied

6. **decision**
   - The decision taken (approve, deny, route, execute, block, etc.)

7. **execution_action**
   - Action performed as a result of the decision (if any)

8. **outcome**
   - Observed result after execution (success, failure, partial, pending)

9. **timestamps**
   - Decision time
   - Execution time (if applicable)
   - Outcome observation time

10. **integrity_guarantee**
    - Mechanism asserting immutability and tamper resistance

No required field may be omitted.
Optional fields are not permitted unless explicitly versioned in a future spec.

---

## C. PDO LIFECYCLE STATES

A PDO progresses through the following lifecycle states:

1. **CREATED**
   - Decision has been evaluated and recorded

2. **EXECUTED**
   - Execution action (if any) has been performed

3. **SETTLED**
   - Outcome is final and no longer changing

4. **DISPUTED**
   - Outcome or decision is formally challenged

5. **SUPERSEDED**
   - A newer PDO replaces this one for the same subject

6. **ARCHIVED**
   - PDO retained for audit, no longer active

Each transition must be explicit and recorded.

---

## D. PDO INVARIANTS (HARD GUARANTEES)

The following statements **must always be true**:

1. **No execution without PDO creation**
2. **PDOs are immutable after execution**
3. **PDOs must outlive the system or agent that created them**
4. **PDOs must be independently auditable**
5. **PDOs must be human- and machine-interpretable**
6. **A missing PDO implies an unauthorized decision**

These invariants are non-negotiable.

---

## E. EXPLICIT NON-GOALS

A PDO is **not**:

- A log file
- A workflow definition
- A model output
- An explanation report
- An opinion or recommendation
- A monitoring trace

PDOs do not explain *how* a model works.
PDOs prove *that* a decision occurred, *why* it was allowed, and *what* happened.
