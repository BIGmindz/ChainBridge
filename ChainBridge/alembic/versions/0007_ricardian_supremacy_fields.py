"""Add digital supremacy fields to ricardian instruments."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_ricardian_supremacy_fields"
down_revision = "0006_inventory_stakes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ricardian_instruments",
        sa.Column(
            "supremacy_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "ricardian_instruments",
        sa.Column("traditional_arbitration_uri", sa.String(), nullable=True),
    )
    op.add_column(
        "ricardian_instruments",
        sa.Column(
            "material_adverse_override",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.alter_column("ricardian_instruments", "ricardian_version", server_default="v1.1")


def downgrade() -> None:
    op.alter_column("ricardian_instruments", "ricardian_version", server_default="Ricardian_v1")
    op.drop_column("ricardian_instruments", "material_adverse_override")
    op.drop_column("ricardian_instruments", "traditional_arbitration_uri")
    op.drop_column("ricardian_instruments", "supremacy_enabled")
