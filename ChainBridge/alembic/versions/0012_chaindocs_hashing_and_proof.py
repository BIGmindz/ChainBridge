"""Add hashing fields to documents and payment intents."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0012_chaindocs_hashing_and_proof"
down_revision = "0011_stake_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("sha256_hex", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("storage_backend", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("storage_ref", sa.String(), nullable=True))
    op.add_column("payment_intents", sa.Column("proof_hash", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("payment_intents", "proof_hash")
    op.drop_column("documents", "storage_ref")
    op.drop_column("documents", "storage_backend")
    op.drop_column("documents", "sha256_hex")
