"""add recon fields to payment_intents

Revision ID: 0004_payment_intent_recon_fields
Revises: 0003_payment_intent_pricing_fields
Create Date: 2025-11-20
"""
from alembic import op
import sqlalchemy as sa

revision = '0004_payment_intent_recon_fields'
down_revision = '0003_payment_intent_pricing_fields'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    pi_cols = {col['name'] for col in inspector.get_columns('payment_intents')}
    with op.batch_alter_table('payment_intents') as batch:
        if 'clearing_partner' not in pi_cols:
            batch.add_column(sa.Column('clearing_partner', sa.String(), nullable=True))
        if 'intent_hash' not in pi_cols:
            batch.add_column(sa.Column('intent_hash', sa.String(), nullable=True))
        if 'risk_gate_reason' not in pi_cols:
            batch.add_column(sa.Column('risk_gate_reason', sa.String(), nullable=True))
        if 'compliance_blocks' not in pi_cols:
            batch.add_column(sa.Column('compliance_blocks', sa.JSON(), nullable=True))
        if 'ready_at' not in pi_cols:
            batch.add_column(sa.Column('ready_at', sa.DateTime(), nullable=True))
        if 'calculated_amount' not in pi_cols:
            batch.add_column(sa.Column('calculated_amount', sa.Float(), nullable=True))
        if 'pricing_breakdown' not in pi_cols:
            batch.add_column(sa.Column('pricing_breakdown', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('payment_intents') as batch:
        for col in [
            'pricing_breakdown',
            'calculated_amount',
            'ready_at',
            'compliance_blocks',
            'risk_gate_reason',
            'intent_hash',
            'clearing_partner',
        ]:
            try:
                batch.drop_column(col)
            except Exception:
                pass
