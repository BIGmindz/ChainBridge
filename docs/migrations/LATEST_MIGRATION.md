# Latest Migration Notes

**PR:** #18 — OCC/ChainBoard: mount routers + add gatekeeper + OC auth stubs
**Branch:** `fix/cody-occ-foundation-clean`
**Date:** 2025-12-16
**Author:** ATLAS (GID-11) under BENSON CTO (GID-00) direction

---

## Summary

This PR introduces foundational OCC (Operator Control Center) and ChainBoard infrastructure along with supporting database migrations and model definitions. All migrations are **additive** — no breaking schema changes or data loss.

---

## Alembic Migrations Included

| Migration | Description | Type |
|-----------|-------------|------|
| `0001_baseline.py` | Initial schema baseline | CREATE |
| `0002_settlement_indexes_paymentintent_constraints.py` | Settlement indexes, PaymentIntent constraints | ALTER/INDEX |
| `0003_payment_intent_pricing_fields.py` | Pricing fields for PaymentIntent | ALTER |
| `0004_payment_intent_recon_fields.py` | Reconciliation fields | ALTER |
| `0005_ricardian_instruments.py` | Ricardian contract instruments table | CREATE |
| `0006_inventory_stakes.py` | Inventory staking tables | CREATE |
| `0007_ricardian_supremacy_fields.py` | Supremacy clause fields | ALTER |
| `0008_inventory_stakes_extension.py` | Extended stake metadata | ALTER |
| `0009_settlement_event_audit.py` | Settlement audit event logging | CREATE |
| `0010_payment_intent_audit_fields.py` | Audit trail fields for payments | ALTER |
| `0011_stake_jobs.py` | Background stake job tracking | CREATE |
| `0012_chaindocs_hashing_and_proof.py` | Document hashing and proof tables | CREATE |
| `0013_payment_intent_final_payout_fields.py` | Final payout tracking | ALTER |
| `0014_stake_positions.py` | Stake position ledger | CREATE |
| `0015_add_financial_primitives.py` | Core financial primitive tables | CREATE |
| `0016_add_chainsalvage_tables.py` | ChainSalvage recovery tables | CREATE |
| `0017_add_dutch_auction_fields.py` | Dutch auction support | ALTER |
| `0018_shadow_pilot_tables.py` | Shadow/pilot mode tables | CREATE |
| `0019_core_governance_models.py` | Governance decision record tables | CREATE |

---

## Model Files Changed

### ChainBridge Core Models (`ChainBridge/api/models/`)
- `canonical.py` — Canonical data types
- `chaindocs.py` — Document models
- `chainiq.py` — ChainIQ scoring models
- `chainpay.py` — Payment models
- `chainstake.py` — Staking models
- `decision_record.py` — OCC decision records
- `esg_evidence.py` — ESG evidence tracking
- `exception.py` — Exception handling models
- `finance.py` — Financial primitives
- `legal.py` — Legal/contract models
- `party.py` — Party/entity models
- `party_relationship.py` — Relationship mappings
- `playbook.py` — Playbook definitions
- `settlement_policy.py` — Settlement policies
- `shadow_pilot.py` — Shadow mode models

### ChainIQ Service Models (`ChainBridge/chainiq-service/`)
- `app/models/features.py` — ML feature definitions
- `app/models/scoring.py` — Risk scoring models
- `app/risk/db_models.py` — Risk database models
- `migrations/001_shadow_mode_tables.sql` — SQL migration

### ChainPay Service Models (`ChainBridge/chainpay-service/app/`)
- `models.py` — Core payment models
- `models_analytics.py` — Analytics models
- `models_audit.py` — Audit models
- `models_context_ledger.py` — Context ledger
- `models_settlement.py` — Settlement models
- `governance/models.py` — Governance models

---

## Breaking Changes

**None.** All migrations are additive:
- New tables created with `CREATE TABLE IF NOT EXISTS`
- New columns added with `ALTER TABLE ADD COLUMN`
- New indexes created without blocking

---

## Rollback Procedure

```bash
# Rollback to previous state
cd ChainBridge
alembic downgrade -1  # Single step back

# Or rollback to specific revision
alembic downgrade 0018  # Back to shadow_pilot_tables
```

---

## Testing

- All pytest tests pass locally (`pytest -q`)
- No schema conflicts detected
- Alembic history is linear (no branch conflicts)

---

## Approval

- **Prepared by:** ATLAS (GID-11)
- **Authorized by:** BENSON CTO (GID-00)
- **Governance:** ALEX Pre-Check compliance
