from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SkillGithubSource(Base):
    __tablename__ = "skill_github_sources"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    skill_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("skills.id", ondelete="SET NULL"))
    repo_full_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    owner_login: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_name: Mapped[str] = mapped_column(String(255), nullable=False)
    github_url: Mapped[str] = mapped_column(Text, nullable=False)
    clone_url: Mapped[Optional[str]] = mapped_column(Text)
    default_branch: Mapped[Optional[str]] = mapped_column(String(100))
    repo_description: Mapped[Optional[str]] = mapped_column(Text)
    homepage_url: Mapped[Optional[str]] = mapped_column(Text)
    license_key: Mapped[Optional[str]] = mapped_column(String(100))
    license_name: Mapped[Optional[str]] = mapped_column(String(255))
    original_author: Mapped[Optional[str]] = mapped_column(String(255))
    source_version: Mapped[Optional[str]] = mapped_column(String(100))
    stars_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    forks_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    watchers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    open_issues_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    skill_md_path: Mapped[Optional[str]] = mapped_column(String(255))
    skill_md_sha: Mapped[Optional[str]] = mapped_column(String(100))
    readme_path: Mapped[Optional[str]] = mapped_column(String(255))
    readme_sha: Mapped[Optional[str]] = mapped_column(String(100))
    license_path: Mapped[Optional[str]] = mapped_column(String(255))
    license_sha: Mapped[Optional[str]] = mapped_column(String(100))
    last_commit_sha: Mapped[Optional[str]] = mapped_column(String(100))
    github_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    github_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    github_pushed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class GithubSkillImport(Base):
    __tablename__ = "github_skill_imports"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    repo_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    github_url: Mapped[str] = mapped_column(Text, nullable=False)
    import_status: Mapped[str] = mapped_column(String(50), nullable=False, default="parsed")
    parsed_title: Mapped[Optional[str]] = mapped_column(String(255))
    parsed_summary: Mapped[Optional[str]] = mapped_column(Text)
    parsed_description: Mapped[Optional[str]] = mapped_column(Text)
    parsed_category: Mapped[Optional[str]] = mapped_column(String(100))
    parsed_skill_type: Mapped[Optional[str]] = mapped_column(String(100))
    parsed_difficulty: Mapped[Optional[str]] = mapped_column(String(50))
    parsed_tags: Mapped[Optional[list]] = mapped_column(JSONB)
    parsed_use_cases: Mapped[Optional[list]] = mapped_column(JSONB)
    parsed_models: Mapped[Optional[list]] = mapped_column(JSONB)
    parsed_license: Mapped[Optional[str]] = mapped_column(String(100))
    parsed_original_author: Mapped[Optional[str]] = mapped_column(String(255))
    raw_repo_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    raw_skill_md_frontmatter: Mapped[Optional[dict]] = mapped_column(JSONB)
    raw_skill_md_preview: Mapped[Optional[str]] = mapped_column(Text)
    raw_readme_preview: Mapped[Optional[str]] = mapped_column(Text)
    batch_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("github_skill_import_batches.id", ondelete="SET NULL")
    )
    duplicate_skill_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("skills.id", ondelete="SET NULL"))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    reviewed_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class GithubSkillImportBatch(Base):
    __tablename__ = "github_skill_import_batches"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    submit_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_publish: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_category: Mapped[Optional[str]] = mapped_column(String(100))
    default_skill_type: Mapped[Optional[str]] = mapped_column(String(100))
    default_difficulty: Mapped[Optional[str]] = mapped_column(String(50))
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
