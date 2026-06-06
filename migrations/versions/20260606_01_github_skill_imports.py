"""add github skill imports

Revision ID: 20260606_01
Revises: 20260530_01
Create Date: 2026-06-06 20:00:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260606_01"
down_revision = "20260530_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE skills
        ADD COLUMN IF NOT EXISTS source_type VARCHAR(32) NOT NULL DEFAULT 'user',
        ADD COLUMN IF NOT EXISTS source_url TEXT NULL,
        ADD COLUMN IF NOT EXISTS source_name VARCHAR(255) NULL,
        ADD COLUMN IF NOT EXISTS original_author VARCHAR(255) NULL,
        ADD COLUMN IF NOT EXISTS license VARCHAR(100) NULL,
        ADD COLUMN IF NOT EXISTS is_verified_source BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS last_source_synced_at TIMESTAMP NULL
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_github_sources (
          id UUID PRIMARY KEY,
          skill_id UUID NULL REFERENCES skills(id) ON DELETE SET NULL,
          repo_full_name VARCHAR(255) NOT NULL UNIQUE,
          owner_login VARCHAR(255) NOT NULL,
          repo_name VARCHAR(255) NOT NULL,
          github_url TEXT NOT NULL,
          clone_url TEXT NULL,
          default_branch VARCHAR(100) NULL,
          repo_description TEXT NULL,
          homepage_url TEXT NULL,
          license_key VARCHAR(100) NULL,
          license_name VARCHAR(255) NULL,
          original_author VARCHAR(255) NULL,
          source_version VARCHAR(100) NULL,
          stars_count INTEGER NOT NULL DEFAULT 0,
          forks_count INTEGER NOT NULL DEFAULT 0,
          watchers_count INTEGER NOT NULL DEFAULT 0,
          open_issues_count INTEGER NOT NULL DEFAULT 0,
          is_archived BOOLEAN NOT NULL DEFAULT FALSE,
          is_private BOOLEAN NOT NULL DEFAULT FALSE,
          skill_md_path VARCHAR(255) NULL,
          skill_md_sha VARCHAR(100) NULL,
          readme_path VARCHAR(255) NULL,
          readme_sha VARCHAR(100) NULL,
          license_path VARCHAR(255) NULL,
          license_sha VARCHAR(100) NULL,
          last_commit_sha VARCHAR(100) NULL,
          github_created_at TIMESTAMP NULL,
          github_updated_at TIMESTAMP NULL,
          github_pushed_at TIMESTAMP NULL,
          last_synced_at TIMESTAMP NULL,
          created_at TIMESTAMP NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS github_skill_import_batches (
          id UUID PRIMARY KEY,
          mode VARCHAR(50) NOT NULL,
          submit_review BOOLEAN NOT NULL DEFAULT FALSE,
          auto_publish BOOLEAN NOT NULL DEFAULT FALSE,
          default_category VARCHAR(100) NULL,
          default_skill_type VARCHAR(100) NULL,
          default_difficulty VARCHAR(50) NULL,
          total_count INTEGER NOT NULL DEFAULT 0,
          success_count INTEGER NOT NULL DEFAULT 0,
          failed_count INTEGER NOT NULL DEFAULT 0,
          duplicate_count INTEGER NOT NULL DEFAULT 0,
          created_by UUID NULL,
          created_at TIMESTAMP NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS github_skill_imports (
          id UUID PRIMARY KEY,
          repo_full_name VARCHAR(255) NOT NULL,
          github_url TEXT NOT NULL,
          import_status VARCHAR(50) NOT NULL DEFAULT 'parsed',
          parsed_title VARCHAR(255) NULL,
          parsed_summary TEXT NULL,
          parsed_description TEXT NULL,
          parsed_category VARCHAR(100) NULL,
          parsed_skill_type VARCHAR(100) NULL,
          parsed_difficulty VARCHAR(50) NULL,
          parsed_tags JSONB NULL,
          parsed_license VARCHAR(100) NULL,
          parsed_original_author VARCHAR(255) NULL,
          raw_repo_json JSONB NULL,
          raw_skill_md_frontmatter JSONB NULL,
          raw_skill_md_preview TEXT NULL,
          raw_readme_preview TEXT NULL,
          batch_id UUID NULL REFERENCES github_skill_import_batches(id) ON DELETE SET NULL,
          duplicate_skill_id UUID NULL REFERENCES skills(id) ON DELETE SET NULL,
          error_message TEXT NULL,
          created_by UUID NULL,
          reviewed_by UUID NULL,
          reviewed_at TIMESTAMP NULL,
          created_at TIMESTAMP NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS idx_skills_source_type ON skills(source_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_skills_source_name ON skills(source_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_skill_github_sources_skill_id ON skill_github_sources(skill_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_skill_github_sources_repo_full_name ON skill_github_sources(repo_full_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_github_skill_imports_repo_full_name ON github_skill_imports(repo_full_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_github_skill_imports_status ON github_skill_imports(import_status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_github_skill_imports_batch_id ON github_skill_imports(batch_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_github_skill_imports_status")
    op.execute("DROP INDEX IF EXISTS idx_github_skill_imports_repo_full_name")
    op.execute("DROP INDEX IF EXISTS idx_github_skill_imports_batch_id")
    op.execute("DROP INDEX IF EXISTS idx_skill_github_sources_repo_full_name")
    op.execute("DROP INDEX IF EXISTS idx_skill_github_sources_skill_id")
    op.execute("DROP INDEX IF EXISTS idx_skills_source_name")
    op.execute("DROP INDEX IF EXISTS idx_skills_source_type")
    op.execute("DROP TABLE IF EXISTS github_skill_import_batches")
    op.execute("DROP TABLE IF EXISTS github_skill_imports")
    op.execute("DROP TABLE IF EXISTS skill_github_sources")
    op.execute(
        """
        ALTER TABLE skills
        DROP COLUMN IF EXISTS last_source_synced_at,
        DROP COLUMN IF EXISTS is_verified_source,
        DROP COLUMN IF EXISTS license,
        DROP COLUMN IF EXISTS original_author,
        DROP COLUMN IF EXISTS source_name,
        DROP COLUMN IF EXISTS source_url,
        DROP COLUMN IF EXISTS source_type
        """
    )
