"""add persistent announcement groups

Revision ID: 20260826_add_bot_groups
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_add_bot_groups"
down_revision = None  # Replace with your latest Alembic revision ID.
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bot_groups",
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.PrimaryKeyConstraint("chat_id"),
    )


def downgrade():
    op.drop_table("bot_groups")
