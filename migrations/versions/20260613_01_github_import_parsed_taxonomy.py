"""add parsed use cases and models for github imports

Revision ID: 20260613_01
Revises: 20260611_01
Create Date: 2026-06-13 10:00:00
"""

from alembic import op


revision = "20260613_01"
down_revision = "20260611_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE github_skill_imports
        ADD COLUMN IF NOT EXISTS parsed_use_cases JSONB,
        ADD COLUMN IF NOT EXISTS parsed_models JSONB
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE github_skill_imports
        DROP COLUMN IF EXISTS parsed_models,
        DROP COLUMN IF EXISTS parsed_use_cases
        """
    )
