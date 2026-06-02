"""add skills query indexes

Revision ID: 20260530_01
Revises: 20260529_01
Create Date: 2026-05-30 16:30:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260530_01"
down_revision = "20260529_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_skills_status_published
        ON skills (status, published_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_skills_category_status
        ON skills (category_id, status)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_skills_difficulty_status
        ON skills (difficulty, status)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_skills_type_status
        ON skills (type, status)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_skills_hot_status
        ON skills (is_hot, status, favorite_count DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_skills_featured_status
        ON skills (is_featured, status, published_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tags_type_enabled
        ON tags (type, is_enabled, sort_order)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tags_slug_type
        ON tags (slug, type)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_skill_tags_skill
        ON skill_tags (skill_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_skill_tags_tag
        ON skill_tags (tag_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_skill_tags_tag")
    op.execute("DROP INDEX IF EXISTS idx_skill_tags_skill")
    op.execute("DROP INDEX IF EXISTS idx_tags_slug_type")
    op.execute("DROP INDEX IF EXISTS idx_tags_type_enabled")
    op.execute("DROP INDEX IF EXISTS idx_skills_featured_status")
    op.execute("DROP INDEX IF EXISTS idx_skills_hot_status")
    op.execute("DROP INDEX IF EXISTS idx_skills_type_status")
    op.execute("DROP INDEX IF EXISTS idx_skills_difficulty_status")
    op.execute("DROP INDEX IF EXISTS idx_skills_category_status")
    op.execute("DROP INDEX IF EXISTS idx_skills_status_published")
