"""add prompt file name to skill submissions

Revision ID: 20260522_02
Revises: 20260522_01
Create Date: 2026-05-22 22:10:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260522_02"
down_revision = "20260522_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE skill_submissions
        ADD COLUMN IF NOT EXISTS prompt_file_name VARCHAR(255)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE skill_submissions
        DROP COLUMN IF EXISTS prompt_file_name
        """
    )
