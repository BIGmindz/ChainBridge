"""add settlement indexes and paymentintent constraints

Revision ID: 0002_settlement_indexes
Revises: 0001_baseline
Create Date: 2025-11-20
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_settlement_indexes'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # SettlementEvents columns/indexes
    settlement_cols = {col['name'] for col in inspector.get_columns('settlement_events')}
    with op.batch_alter_table('settlement_events') as batch:
        if 'sequence' not in settlement_cols:
            batch.add_column(sa.Column('sequence', sa.Integer(), nullable=True, server_default='0'))
        if 'metadata' not in settlement_cols:
            batch.add_column(sa.Column('metadata', sa.JSON(), nullable=True))
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('settlement_events')}
    if 'ix_settlement_events_intent_occurred' not in existing_indexes:
        op.create_index('ix_settlement_events_intent_occurred', 'settlement_events', ['payment_intent_id', 'occurred_at'], unique=False)
    if 'ix_settlement_events_intent_sequence' not in existing_indexes:
        op.create_index('ix_settlement_events_intent_sequence', 'settlement_events', ['payment_intent_id', 'sequence'], unique=False)
    if 'ix_settlement_events_type_occurred' not in existing_indexes:
        op.create_index('ix_settlement_events_type_occurred', 'settlement_events', ['event_type', 'occurred_at'], unique=False)

    # PaymentIntents additions
    pi_cols = {col['name'] for col in inspector.get_columns('payment_intents')}
    with op.batch_alter_table('payment_intents') as batch:
        if 'latest_risk_snapshot_id' not in pi_cols:
            batch.add_column(sa.Column('latest_risk_snapshot_id', sa.Integer(), nullable=True))
    pi_indexes = {idx['name'] for idx in inspector.get_indexes('payment_intents')}
    if 'ix_payment_intents_shipment_latest_risk' not in pi_indexes:
        op.create_index('ix_payment_intents_shipment_latest_risk', 'payment_intents', ['shipment_id', 'latest_risk_snapshot_id'], unique=False)

    # Active intent uniqueness on SQLite via partial index
    if 'uq_payment_intents_active' not in pi_indexes:
        op.create_index(
            'uq_payment_intents_active',
            'payment_intents',
            ['shipment_id', 'status'],
            unique=True,
            sqlite_where=sa.text("status IN ('PENDING','AUTHORIZED')"),
        )


def downgrade():
    op.drop_index('uq_payment_intents_active', table_name='payment_intents')
    op.drop_index('ix_payment_intents_shipment_latest_risk', table_name='payment_intents')
    with op.batch_alter_table('payment_intents') as batch:
        batch.drop_column('latest_risk_snapshot_id')

    op.drop_index('ix_settlement_events_type_occurred', table_name='settlement_events')
    op.drop_index('ix_settlement_events_intent_sequence', table_name='settlement_events')
    op.drop_index('ix_settlement_events_intent_occurred', table_name='settlement_events')
    with op.batch_alter_table('settlement_events') as batch:
        batch.drop_column('metadata')
        batch.drop_column('sequence')
