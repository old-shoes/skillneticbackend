"""cleanup generated skill content copy

Revision ID: 20260523_02
Revises: 20260523_01
Create Date: 2026-05-23 11:40:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260523_02"
down_revision = "20260523_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE skills
        SET content = replace(
          content,
          '- 适合 当前这个工作场景',
          '- 适合快速完成当前任务'
        )
        WHERE deleted_at IS NULL
          AND status = 'published'
          AND content LIKE '%- 适合 当前这个工作场景%'
        """
    )


def downgrade() -> None:
    pass
