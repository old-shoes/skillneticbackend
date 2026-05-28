from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TutorialCategory(Base):
    __tablename__ = "tutorial_categories"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    icon: Mapped[str] = mapped_column(String(80), nullable=False)
    color: Mapped[str] = mapped_column(String(50), nullable=False, default="blue")
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    category_group: Mapped[Optional[str]] = mapped_column(String(80))
    scene: Mapped[Optional[str]] = mapped_column(String(80))
    difficulty: Mapped[Optional[str]] = mapped_column(String(30))
    tutorial_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skill_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_hot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    updated_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class TutorialTag(Base):
    __tablename__ = "tutorial_tags"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    tutorial_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_hot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Tutorial(Base):
    __tablename__ = "tutorials"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cover_image: Mapped[Optional[str]] = mapped_column(String(500))
    cover_icon: Mapped[Optional[str]] = mapped_column(String(80))
    category_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tutorial_categories.id"))
    difficulty: Mapped[str] = mapped_column(String(30), nullable=False, default="beginner")
    read_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    favorite_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_beginner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    learning_points: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    suitable_for: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    search_keywords: Mapped[Optional[str]] = mapped_column(Text)
    seo_title: Mapped[Optional[str]] = mapped_column(String(160))
    seo_description: Mapped[Optional[str]] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class TutorialTagRelation(Base):
    __tablename__ = "tutorial_tag_relations"

    tutorial_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tutorials.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tutorial_tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TutorialPromptBlock(Base):
    __tablename__ = "tutorial_prompt_blocks"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tutorial_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tutorials.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class TutorialRelatedItem(Base):
    __tablename__ = "tutorial_related_items"

    tutorial_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tutorials.id", ondelete="CASCADE"),
        primary_key=True,
    )
    related_tutorial_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tutorials.id", ondelete="CASCADE"),
        primary_key=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AdminOperationLog(Base):
    __tablename__ = "admin_operation_logs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    operator_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    operator_name: Mapped[Optional[str]] = mapped_column(String(80))
    module: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    target_title: Mapped[Optional[str]] = mapped_column(String(160))
    before_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    after_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    ip: Mapped[Optional[str]] = mapped_column(String(80))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str] = mapped_column(String(80), nullable=False)
    tutorial_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
