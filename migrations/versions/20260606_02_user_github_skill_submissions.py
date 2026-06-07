"""add user github skill submission fields

Revision ID: 20260606_02
Revises: 20260606_01
Create Date: 2026-06-06 18:00:00
"""

from alembic import op


revision = "20260606_02"
down_revision = "20260606_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE skill_submissions
        ADD COLUMN IF NOT EXISTS submission_type VARCHAR(50) NOT NULL DEFAULT 'manual',
        ADD COLUMN IF NOT EXISTS source_type VARCHAR(32) NOT NULL DEFAULT 'user',
        ADD COLUMN IF NOT EXISTS github_url TEXT NULL,
        ADD COLUMN IF NOT EXISTS repo_full_name VARCHAR(255) NULL,
        ADD COLUMN IF NOT EXISTS source_name VARCHAR(255) NULL,
        ADD COLUMN IF NOT EXISTS original_author VARCHAR(255) NULL,
        ADD COLUMN IF NOT EXISTS license VARCHAR(100) NULL,
        ADD COLUMN IF NOT EXISTS attachment_urls JSONB NOT NULL DEFAULT '[]'::jsonb
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_skill_submissions_source_type ON skill_submissions(source_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_skill_submissions_github_url ON skill_submissions(github_url)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_skill_submissions_repo_full_name ON skill_submissions(repo_full_name)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_skill_submissions_repo_full_name")
    op.execute("DROP INDEX IF EXISTS idx_skill_submissions_github_url")
    op.execute("DROP INDEX IF EXISTS idx_skill_submissions_source_type")
    op.execute(
        """
        ALTER TABLE skill_submissions
        DROP COLUMN IF EXISTS attachment_urls,
        DROP COLUMN IF EXISTS license,
        DROP COLUMN IF EXISTS original_author,
        DROP COLUMN IF EXISTS source_name,
        DROP COLUMN IF EXISTS repo_full_name,
        DROP COLUMN IF EXISTS github_url,
        DROP COLUMN IF EXISTS source_type,
        DROP COLUMN IF EXISTS submission_type
        """
    )
