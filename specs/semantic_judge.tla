---------------- MODULE SemanticJudge ----------------
(*
TEST GOVERNANCE LAYER (TGL) - SEMANTIC JUDGE SPECIFICATION
TLA+ Formal Specification v1.0.0

AUTHORITY: JEFFREY (GID-CONST-01) Constitutional Architect
GOVERNANCE: LAW-tier (Fail-Closed)
IMPLEMENTER: FORGE (GID-04)

ABSTRACT:
This specification defines the Semantic Judge as a deterministic state machine
that adjudicates TestExecutionManifests. The Judge operates as a Constitutional
Court, not a CI pipeline. It does not "run tests"; it adjudicates proofs.

INVARIANTS:
1. A manifest can only transition from Pending to Approved or Rejected (never both)
2. Once Approved or Rejected, state is immutable (no re-adjudication)
3. Approval requires ALL conditions to hold (tests_failed=0 AND mcdc=100.0 AND ValidSignature)
4. Rejection occurs if ANY condition fails

TEMPORAL PROPERTIES:
- Liveness: Every manifest eventually reaches Approved or Rejected state
- Safety: No manifest can be Approved with failed tests or incomplete coverage

IMPLEMENTATION:
See: core/governance/test_governance_layer.py (Python/Pydantic implementation)
*)

EXTENDS Naturals, Sequences, TLC, FiniteSets

CONSTANTS 
    Manifests,          \* Set of all submitted manifests
    ValidSignatures,    \* Set of valid Ed25519 signatures
    MaxManifests        \* Maximum number of manifests to model-check

ASSUME 
    /\ MaxManifests \in Nat
    /\ MaxManifests > 0

VARIABLES 
    state,              \* Current state of each manifest: Pending | Approved | Rejected
    judgmentLog         \* Append-only log of all judgments (immutable audit trail)

\* Type definitions
States == {"Pending", "Approved", "Rejected"}

\* A manifest has the following structure (simplified for TLA+):
\* manifest.id: String (UUIDv4)
\* manifest.tests_failed: Nat (MUST be 0 for approval)
\* manifest.mcdc_percentage: Real (MUST be 100.0 for approval)
\* manifest.signature: String (MUST be in ValidSignatures)

\* Type invariant: state maps manifest IDs to States
TypeOK == 
    /\ state \in [Manifests -> States]
    /\ judgmentLog \in Seq([manifest: Manifests, judgment: States, timestamp: Nat])

\* Initialize all manifests to Pending state
Init == 
    /\ state = [m \in Manifests |-> "Pending"]
    /\ judgmentLog = <<>>

\* Helper: Verify Ed25519 signature (abstracted)
VerifySignature(signature) == 
    signature \in ValidSignatures

\* Helper: Check if manifest passes all approval conditions
MeetsApprovalCriteria(m) ==
    /\ m.tests_failed = 0
    /\ m.mcdc_percentage = 100.0
    /\ VerifySignature(m.signature)

\* Transition: Approve a manifest
\* Preconditions: 
\*   - Manifest is in Pending state
\*   - All approval criteria met
\* Postconditions:
\*   - State transitions to Approved
\*   - Judgment logged immutably
Approve(m) == 
    /\ state[m] = "Pending"
    /\ MeetsApprovalCriteria(m)
    /\ state' = [state EXCEPT ![m] = "Approved"]
    /\ judgmentLog' = Append(judgmentLog, [
           manifest |-> m, 
           judgment |-> "Approved", 
           timestamp |-> Len(judgmentLog) + 1
       ])

\* Transition: Reject a manifest
\* Preconditions:
\*   - Manifest is in Pending state
\*   - At least one approval criterion fails
\* Postconditions:
\*   - State transitions to Rejected
\*   - Judgment logged immutably
Reject(m) == 
    /\ state[m] = "Pending"
    /\ ~MeetsApprovalCriteria(m)  \* At least one criterion fails
    /\ state' = [state EXCEPT ![m] = "Rejected"]
    /\ judgmentLog' = Append(judgmentLog, [
           manifest |-> m, 
           judgment |-> "Rejected", 
           timestamp |-> Len(judgmentLog) + 1
       ])

\* Next-state relation: Judge can approve or reject any pending manifest
Next == 
    \E m \in Manifests : 
        \/ Approve(m)
        \/ Reject(m)

\* Specification: Initial state and next-state relation
Spec == Init /\ [][Next]_<<state, judgmentLog>>

\* ============================================================================
\* INVARIANTS (Safety Properties)
\* ============================================================================

\* INV-1: No manifest can be both Approved and have failed tests
NoApprovedFailures == 
    \A m \in Manifests : 
        state[m] = "Approved" => m.tests_failed = 0

\* INV-2: No manifest can be Approved without 100% MCDC coverage
NoApprovedIncompleteCoverage == 
    \A m \in Manifests : 
        state[m] = "Approved" => m.mcdc_percentage = 100.0

\* INV-3: No manifest can be Approved without valid signature
NoApprovedInvalidSignature == 
    \A m \in Manifests : 
        state[m] = "Approved" => VerifySignature(m.signature)

\* INV-4: Every judgment must be logged (audit trail completeness)
AllJudgmentsLogged == 
    \A m \in Manifests : 
        state[m] # "Pending" => 
            \E entry \in DOMAIN judgmentLog : 
                judgmentLog[entry].manifest = m

\* INV-5: State transitions are monotonic (no re-adjudication)
NoReAdjudication == 
    [](\A m \in Manifests : 
        (state[m] = "Approved" \/ state[m] = "Rejected") => 
            [](state[m] = "Approved" \/ state[m] = "Rejected"))

\* INV-6: Judgment log is append-only (immutability)
LogIsAppendOnly == 
    [][Len(judgmentLog') >= Len(judgmentLog)]_judgmentLog

\* Combined safety invariant
SafetyInvariant == 
    /\ TypeOK
    /\ NoApprovedFailures
    /\ NoApprovedIncompleteCoverage
    /\ NoApprovedInvalidSignature
    /\ AllJudgmentsLogged

\* ============================================================================
\* TEMPORAL PROPERTIES (Liveness)
\* ============================================================================

\* LIVENESS-1: Every manifest eventually reaches a terminal state
EventualJudgment == 
    \A m \in Manifests : 
        <>(state[m] = "Approved" \/ state[m] = "Rejected")

\* LIVENESS-2: Valid manifests are eventually approved
ValidManifestsEventuallyApproved == 
    \A m \in Manifests : 
        MeetsApprovalCriteria(m) ~> (state[m] = "Approved")

\* LIVENESS-3: Invalid manifests are eventually rejected
InvalidManifestsEventuallyRejected == 
    \A m \in Manifests : 
        ~MeetsApprovalCriteria(m) ~> (state[m] = "Rejected")

\* ============================================================================
\* THEOREM STATEMENTS (For TLAPS - TLA+ Proof System)
\* ============================================================================

\* THEOREM: Approval implies all criteria met
THEOREM ApprovalCorrectnessTheorem == 
    Spec => [](\A m \in Manifests : 
        state[m] = "Approved" => MeetsApprovalCriteria(m))

\* THEOREM: Rejection implies at least one criterion failed
THEOREM RejectionCorrectnessTheorem == 
    Spec => [](\A m \in Manifests : 
        state[m] = "Rejected" => ~MeetsApprovalCriteria(m))

\* THEOREM: Every manifest eventually reaches terminal state (termination)
THEOREM TerminationTheorem == 
    Spec => EventualJudgment

\* ============================================================================
\* MODEL CHECKING CONFIGURATION
\* ============================================================================

\* For TLC model checker, define a small concrete model:
\* 
\* CONSTANTS:
\*   Manifests = {m1, m2, m3}
\*   ValidSignatures = {sig1, sig2}
\*   MaxManifests = 3
\*
\* MANIFEST DEFINITIONS:
\*   m1 = [id |-> "uuid1", tests_failed |-> 0, mcdc_percentage |-> 100.0, signature |-> sig1]  (VALID)
\*   m2 = [id |-> "uuid2", tests_failed |-> 1, mcdc_percentage |-> 100.0, signature |-> sig1]  (INVALID: failed tests)
\*   m3 = [id |-> "uuid3", tests_failed |-> 0, mcdc_percentage |-> 95.0, signature |-> sig1]   (INVALID: incomplete MCDC)
\*
\* PROPERTIES TO CHECK:
\*   - SafetyInvariant (should always hold)
\*   - EventualJudgment (liveness - should eventually hold)
\*   - ApprovalCorrectnessTheorem (should hold)
\*   - RejectionCorrectnessTheorem (should hold)

\* ============================================================================
\* CONSTITUTIONAL ATTESTATION
\* ============================================================================

(*
ATTESTATION:
"This specification represents the Law of Verification. It is strict, typed, 
and fail-closed. No code may enter the system without presenting Evidence 
(TestExecutionManifest) to the Magistrate (SemanticJudge). 

If the Evidence is insufficient, the code is rejected with prejudice.

Approval requires unanimous satisfaction of all Invariants:
1. Zero failed tests (tests_failed = 0)
2. Complete decision coverage (mcdc_percentage = 100.0)
3. Valid cryptographic signature (VerifySignature = TRUE)

This is the Foundation of Trust."

— JEFFREY (GID-CONST-01), Constitutional Architect
— 2026-01-25
*)

======================================================
