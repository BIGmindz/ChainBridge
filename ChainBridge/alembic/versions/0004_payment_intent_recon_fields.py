"""add recon fields to payment_intents

Revision ID: 0004_recon_fields
Revises: 0003_pricing_fields
Create Date: 2025-11-20
"""
from alembic import op
import sqlalchemy as sa

revision = '0004_recon_fields'
down_revision = '0003_pricing_fields'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('payment_intents')}
    with op.batch_alter_table('payment_intents') as batch:
        if 'recon_state' not in cols:
            batch.add_column(sa.Column('recon_state', sa.String(), nullable=True))
        if 'recon_score' not in cols:
            batch.add_column(sa.Column('recon_score', sa.Float(), nullable=True))
        if 'recon_policy_id' not in cols:
            batch.add_column(sa.Column('recon_policy_id', sa.String(), nullable=True))
        if 'approved_amount' not in cols:
            batch.add_column(sa.Column('approved_amount', sa.Float(), nullable=True))
        if 'held_amount' not in cols:
            batch.add_column(sa.Column('held_amount', sa.Float(), nullable=True))
    op.create_index('ix_payment_intents_recon_state', 'payment_intents', ['recon_state'], unique=False)


def downgrade():
    with op.batch_alter_table('payment_intents') as batch:
        for col in ['held_amount', 'approved_amount', 'recon_policy_id', 'recon_score', 'recon_state']:
            try:
                batch.drop_column(col)
            except Exception:
                pass
    try:
        op.drop_index('ix_payment_intents_recon_state', table_name='payment_intents')
    except Exception:
        pass
