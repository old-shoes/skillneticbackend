"""add multi-category support to skill submissions

Revision ID: 20260527_01
Revises: 20260526_02
Create Date: 2026-05-27 09:30:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260527_01"
down_revision = "20260526_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "skill_submissions",
        sa.Column("category_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.execute(
        """
        UPDATE skill_submissions
        SET category_ids = CASE
          WHEN category_id IS NOT NULL THEN jsonb_build_array(category_id::text)
          ELSE '[]'::jsonb
        END
        """
    )
    op.alter_column("skill_submissions", "category_ids", server_default=None)


def downgrade() -> None:
    op.drop_column("skill_submissions", "category_ids")
