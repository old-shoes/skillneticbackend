"""add newsletter subscribers table

Revision ID: 20260611_01
Revises: 20260606_02
Create Date: 2026-06-11 13:35:00
"""

from alembic import op


revision = "20260611_01"
down_revision = "20260606_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS newsletter_subscribers (
            id UUID PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            locale VARCHAR(20) NOT NULL DEFAULT 'zh',
            source VARCHAR(50) NOT NULL DEFAULT 'footer',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            unsubscribed_at TIMESTAMPTZ NULL
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_newsletter_subscribers_status ON newsletter_subscribers(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_newsletter_subscribers_created_at ON newsletter_subscribers(created_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_newsletter_subscribers_created_at")
    op.execute("DROP INDEX IF EXISTS idx_newsletter_subscribers_status")
    op.execute("DROP TABLE IF EXISTS newsletter_subscribers")
