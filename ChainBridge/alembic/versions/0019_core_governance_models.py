"""Add core governance models (Party, Exception, Playbook, SettlementPolicy, DecisionRecord, EsgEvidence, PartyRelationship)

Revision ID: 0019_core_governance_models
Revises: 0018_shadow_pilot_tables
Create Date: 2025-12-07
"""

import sqlalchemy as sa

from alembic import op

revision = "0019_core_governance_models"
down_revision = "0018_shadow_pilot_tables"
branch_labels = None
depends_on = None


def upgrade():
    # --- parties table ---
    op.create_table(
        "parties",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("legal_name", sa.String(), nullable=True),
        sa.Column("tax_id", sa.String(), nullable=True),
        sa.Column("duns_number", sa.String(), nullable=True),
        sa.Column("country_code", sa.String(3), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.String(), nullable=True),
        sa.Column("contact_phone", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("party_metadata", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parties_tenant_id", "parties", ["tenant_id"])
    op.create_index("ix_parties_type", "parties", ["type"])
    op.create_index("ix_parties_tenant_type", "parties", ["tenant_id", "type"])

    # --- playbooks table (must come before exceptions due to FK) ---
    op.create_table(
        "playbooks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("trigger_condition", sa.JSON(), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("supersedes_id", sa.String(), nullable=True),
        sa.Column("author_user_id", sa.String(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_playbooks_tenant_id", "playbooks", ["tenant_id"])
    op.create_index("ix_playbooks_active", "playbooks", ["active"])
    op.create_index("ix_playbooks_tenant_active", "playbooks", ["tenant_id", "active"])

    # --- exceptions table ---
    op.create_table(
        "exceptions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("shipment_id", sa.String(), nullable=True),
        sa.Column("playbook_id", sa.String(), nullable=True),
        sa.Column("payment_intent_id", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(), nullable=False, server_default="OPEN"),
        sa.Column("owner_user_id", sa.String(), nullable=True),
        sa.Column("escalated_to", sa.String(), nullable=True),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("resolution_type", sa.String(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("source_event_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["playbook_id"], ["playbooks.id"]),
    )
    op.create_index("ix_exceptions_tenant_id", "exceptions", ["tenant_id"])
    op.create_index("ix_exceptions_shipment_id", "exceptions", ["shipment_id"])
    op.create_index("ix_exceptions_status", "exceptions", ["status"])
    op.create_index("ix_exceptions_severity", "exceptions", ["severity"])
    op.create_index("ix_exceptions_tenant_status", "exceptions", ["tenant_id", "status"])
    op.create_index("ix_exceptions_owner", "exceptions", ["owner_user_id"])

    # --- settlement_policies table ---
    op.create_table(
        "settlement_policies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("policy_type", sa.String(), nullable=True),
        sa.Column("curve", sa.JSON(), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("max_exposure", sa.Float(), nullable=True),
        sa.Column("min_transaction", sa.Float(), nullable=True),
        sa.Column("max_transaction", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("rails", sa.JSON(), nullable=True),
        sa.Column("preferred_rail", sa.String(), nullable=True),
        sa.Column("fallback_rails", sa.JSON(), nullable=True),
        sa.Column("settlement_delay_hours", sa.Float(), nullable=True),
        sa.Column("float_reduction_target", sa.Float(), nullable=True),
        sa.Column("effective_from", sa.DateTime(), nullable=False),
        sa.Column("effective_to", sa.DateTime(), nullable=True),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_settlement_policies_tenant_id", "settlement_policies", ["tenant_id"])
    op.create_index("ix_settlement_policies_effective", "settlement_policies", ["effective_from", "effective_to"])
    op.create_index("ix_settlement_policies_tenant_currency", "settlement_policies", ["tenant_id", "currency"])

    # --- decision_records table ---
    op.create_table(
        "decision_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("subtype", sa.String(), nullable=True),
        sa.Column("actor_type", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("actor_name", sa.String(), nullable=True),
        sa.Column("entity_type", sa.String(), nullable=True),
        sa.Column("entity_id", sa.String(), nullable=True),
        sa.Column("policy_id", sa.String(), nullable=True),
        sa.Column("policy_type", sa.String(), nullable=True),
        sa.Column("policy_version", sa.String(), nullable=True),
        sa.Column("inputs_hash", sa.String(), nullable=True),
        sa.Column("inputs_snapshot", sa.JSON(), nullable=True),
        sa.Column("outputs", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("primary_factors", sa.JSON(), nullable=True),
        sa.Column("overrides_decision_id", sa.String(), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_records_tenant_id", "decision_records", ["tenant_id"])
    op.create_index("ix_decision_records_type", "decision_records", ["type"])
    op.create_index("ix_decision_records_actor", "decision_records", ["actor_type", "actor_id"])
    op.create_index("ix_decision_records_created", "decision_records", ["created_at"])
    op.create_index("ix_decision_records_entity", "decision_records", ["entity_type", "entity_id"])

    # --- esg_evidence table ---
    op.create_table(
        "esg_evidence",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("party_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("subcategory", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("document_id", sa.String(), nullable=True),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("verified_by", sa.String(), nullable=True),
        sa.Column("score_impact", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["party_id"], ["parties.id"]),
    )
    op.create_index("ix_esg_evidence_tenant_id", "esg_evidence", ["tenant_id"])
    op.create_index("ix_esg_evidence_party_id", "esg_evidence", ["party_id"])
    op.create_index("ix_esg_evidence_type", "esg_evidence", ["type"])
    op.create_index("ix_esg_evidence_tenant_party", "esg_evidence", ["tenant_id", "party_id"])
    op.create_index("ix_esg_evidence_expires", "esg_evidence", ["expires_at"])

    # --- party_relationships table ---
    op.create_table(
        "party_relationships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("from_party_id", sa.String(), nullable=False),
        sa.Column("to_party_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("tier", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("effective_from", sa.DateTime(), nullable=True),
        sa.Column("effective_to", sa.DateTime(), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("verified", sa.String(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("verified_by", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("source_document_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["from_party_id"], ["parties.id"]),
        sa.ForeignKeyConstraint(["to_party_id"], ["parties.id"]),
    )
    op.create_index("ix_party_relationships_tenant_id", "party_relationships", ["tenant_id"])
    op.create_index("ix_party_relationships_from_party", "party_relationships", ["from_party_id"])
    op.create_index("ix_party_relationships_to_party", "party_relationships", ["to_party_id"])
    op.create_index("ix_party_relationships_type", "party_relationships", ["type"])
    op.create_index("ix_party_relationships_tenant_from", "party_relationships", ["tenant_id", "from_party_id"])
    op.create_index("ix_party_relationships_tenant_to", "party_relationships", ["tenant_id", "to_party_id"])


def downgrade():
    op.drop_table("party_relationships")
    op.drop_table("esg_evidence")
    op.drop_table("decision_records")
    op.drop_table("settlement_policies")
    op.drop_table("exceptions")
    op.drop_table("playbooks")
    op.drop_table("parties")
