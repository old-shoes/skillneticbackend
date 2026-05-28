"""add hierarchical skill categories and skill-category relations

Revision ID: 20260526_01
Revises: 20260523_02
Create Date: 2026-05-26 10:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260526_01"
down_revision = "20260523_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("name_en", sa.String(length=80), nullable=True))
    op.add_column("categories", sa.Column("parent_id", sa.UUID(), nullable=True))
    op.add_column(
        "categories",
        sa.Column("level", sa.SmallInteger(), nullable=False, server_default=sa.text("1")),
    )
    op.add_column(
        "categories",
        sa.Column("is_hot", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
    )

    op.create_foreign_key(
        "fk_categories_parent_id_categories",
        "categories",
        "categories",
        ["parent_id"],
        ["id"],
    )
    op.create_check_constraint(
        "chk_categories_level",
        "categories",
        "level IN (1, 2)",
    )
    op.create_check_constraint(
        "chk_categories_parent_level",
        "categories",
        "((level = 1 AND parent_id IS NULL) OR (level = 2 AND parent_id IS NOT NULL))",
    )

    op.create_index("idx_categories_parent_sort", "categories", ["parent_id", "sort_order"], unique=False)
    op.create_index("idx_categories_level_enabled_sort", "categories", ["level", "is_enabled", "sort_order"], unique=False)
    op.create_index("idx_categories_hot_enabled_sort", "categories", ["is_hot", "is_enabled", "sort_order"], unique=False)

    op.create_table(
        "skill_category_rel",
        sa.Column("skill_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("skill_id", "category_id"),
    )
    op.create_index(
        "idx_skill_category_rel_category_skill",
        "skill_category_rel",
        ["category_id", "skill_id"],
        unique=False,
    )
    op.create_index(
        "idx_skill_category_rel_skill_primary",
        "skill_category_rel",
        ["skill_id", "is_primary"],
        unique=False,
    )
    op.create_index(
        "uq_skill_category_rel_primary",
        "skill_category_rel",
        ["skill_id"],
        unique=True,
        postgresql_where=sa.text("is_primary = TRUE"),
    )

    op.execute(
        """
        INSERT INTO skill_category_rel (skill_id, category_id, is_primary)
        SELECT id, category_id, TRUE
        FROM skills
        WHERE category_id IS NOT NULL
        ON CONFLICT (skill_id, category_id) DO NOTHING
        """
    )

    op.alter_column("categories", "level", server_default=None)
    op.alter_column("categories", "is_hot", server_default=None)
    op.alter_column("skill_category_rel", "is_primary", server_default=None)


def downgrade() -> None:
    op.drop_index("uq_skill_category_rel_primary", table_name="skill_category_rel")
    op.drop_index("idx_skill_category_rel_skill_primary", table_name="skill_category_rel")
    op.drop_index("idx_skill_category_rel_category_skill", table_name="skill_category_rel")
    op.drop_table("skill_category_rel")

    op.drop_index("idx_categories_hot_enabled_sort", table_name="categories")
    op.drop_index("idx_categories_level_enabled_sort", table_name="categories")
    op.drop_index("idx_categories_parent_sort", table_name="categories")
    op.drop_constraint("chk_categories_parent_level", "categories", type_="check")
    op.drop_constraint("chk_categories_level", "categories", type_="check")
    op.drop_constraint("fk_categories_parent_id_categories", "categories", type_="foreignkey")
    op.drop_column("categories", "is_hot")
    op.drop_column("categories", "level")
    op.drop_column("categories", "parent_id")
    op.drop_column("categories", "name_en")
