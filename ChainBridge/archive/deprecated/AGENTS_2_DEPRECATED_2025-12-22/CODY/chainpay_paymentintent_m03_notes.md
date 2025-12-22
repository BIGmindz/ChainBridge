# ChainPay PaymentIntent – M03 Notes

## Current Behavior
- Ready rule (server-side): proof attached AND status in {PENDING, AUTHORIZED} AND risk_level in {LOW, MEDIUM}.
- awaiting_proof: status ok + risk ok but no proof attached.
- blocked_by_risk: risk_level HIGH or CRITICAL.
- List endpoint filters: status, corridor_code, mode, has_proof, ready_for_payment; includes shipment summary + created/updated timestamps.
- Summary endpoint: total, ready_for_payment, awaiting_proof, blocked_by_risk via single aggregated query.
- Proof attach validates proof_id format, verifies against ChainDocs, captures `proof_hash`, and enforces uniqueness across intents with structured 409/404/503 errors.
- Settlement timeline (demo): HAPPY path CREATED → AUTHORIZED → CAPTURED unless risk_level in {HIGH, CRITICAL}, then AUTHORIZED → FAILED/FAILED. RECONCILED and STAKE_COMPLETED events are appended when audit/stake flows run.
- ChainAudit v1: `/audit/payment_intents/{id}/reconcile` writes payout_confidence/auto_adjusted_amount/reconciliation_explanation, appends RECONCILED settlement events, and publishes `payment_intent.reconciled`.
- ChainStake v1: stake_jobs table + `/stake/shipments/{id}` (auto-completes stub) with stake.created/stake.completed events and optional settlement linkage to intents.
- ChainDocs Hashing v1: documents carry sha256_hex/storage_backend/storage_ref; PaymentIntents carry proof_hash; `/chaindocs/documents/{id}/verify` re-hashes stored files and emits `document.verified`.

## Known Gaps
- ChainDocs call is local DB-bound; no outbound HTTP/circuit breaker yet.
- Monetary rails not wired (status is PENDING/AUTHORIZED only; no settlement).
- Amount/currency defaults to settlement plan total or 0.0/USD when ChainIQ auto-creates.
- Snapshot-id linkage assumed latest; no reconciliation for revised risk snapshots.
- Settlement events are demo-only (CREATED/AUTHORIZED/CAPTURED vs FAILED) with scripted timelines; no gateway integration beyond audit/stake appends.
- Alembic baseline exists; future schema changes must go through Alembic migrations.
- Event bus is still in-process; external MQ integration still pending.
- Webhook orchestrator hardened with optional signature + rate guards but still demo providers.

## Ideas for V2
- Partial/multi-leg PaymentIntents with per-leg readiness and proofs.
- Asynchronous ChainDocs lookup with retry/backoff and circuit breaker metrics.
- Risk-based authorization windows (e.g., auto-void after N days).
- Event emissions for Control Tower real-time updates + audit trail.
- Reconciliation job to re-evaluate readiness when risk downgrades/upgrades or proofs arrive.
- Operator Console endpoints added (/operator queue, risk_snapshot, settlement events, IoT health summary, event stream) for OC wiring.
- Added OC-facing endpoints (/operator) for queue, risk snapshot, settlement events, IoT health summary, and operator event stream; tests cover pagination and since filtering.
