WHAT YOU SHOULD KNOW DEEPLY
- FastAPI and Pydantic models
- SQLAlchemy, migrations, DB schema design
- Event-driven patterns: SSE, pub/sub, idempotency
- Canonical ID generation & deterministic schemas
- Error handling and structured logging
- Payment flows and milestone settlement logic
- ProofPack structure and verifiable compute basics

WHAT YOU SHOULD KNOW AT A HIGH LEVEL
- EDI → event mapping (handled by Tim later)
- IoT/ChainSense telemetry event semantics
- ChainIQ feature inputs, risk categories, anomaly signals
- Tokenization and on-chain settlement concepts

WHAT YOU SHOULD IGNORE
- UI layout details
- ML algorithm internals
- Smart contract code (future team)
- UX/design considerations

SERVICES YOU INTERACT WITH
- ChainBoard frontend (API contract consumer)
- ChainIQ scoring service
- ChainFreight tokenization module
- Seeburger BIS (via upstream event feeds)
- Future blockchain integration layer

ARCHITECTURAL AWARENESS REQUIRED
- Everything must be deterministic
- API responses must be stable across versions
- One-time event vs replays must produce identical state
- Canonical JSON must be pure and predictable
- Settlement state machines must never break or skip steps
