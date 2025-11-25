# ChainPay PaymentIntent Metrics – M03 Snapshot

## Implemented
- Auto-wired PaymentIntent creation on ChainIQ LOW/MEDIUM risk approvals with snapshot linkage (unique per shipment + snapshot id).
- ChainDocs-validated proof attachment with 404/503 handling and 409 conflict guard for reused proofs.
- Operator filters & KPIs: `has_proof`, `ready_for_payment`, risk-level propagation, summary counts (total/awaiting_proof/ready/blocked_by_risk).
- Structured logs on all PaymentIntent routes (`route`, `payment_intent_id`, `shipment_id`, `status`, `corridor_code`, `risk_score`, `has_proof`, `actor`).

## Known Gaps
- Amount/currency defaults: fall back to settlement plan total or `0.0`/`USD` when ChainIQ triggers auto-create without explicit pricing.
- Snapshot linkage relies on the latest stored snapshot; does not yet reconcile historical intent-to-snapshot drift.
- No external ChainDocs HTTP call yet—local DB lookup with mocks; true upstream client still to be swapped in.
- Settlement/authorization states remain stubbed (`PENDING`/`AUTHORIZED` only); no XRPL/HBAR payouts wired.

## V2 Ideas
- Multi-leg/partial PaymentIntents per shipment leg, keeping snapshot uniqueness per leg.
- Async ChainDocs fetch with retry/backoff and circuit breaker metrics.
- Enrich ready_for_payment with settlement milestones + carrier risk overrides.
- Emit domain events on intent creation/proof attach for Control Tower real-time UI.
- Add per-corridor/operator-level metrics (conversion to ready, proof SLA, risk downgrade/upgrade rates).
