from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserFavorite(Base):
    __tablename__ = "user_favorites"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserPointLog(Base):
    __tablename__ = "user_point_logs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    points_change: Mapped[int] = mapped_column(Integer, nullable=False)
    points_before: Mapped[int] = mapped_column(Integer, nullable=False)
    points_after: Mapped[int] = mapped_column(Integer, nullable=False)
    related_type: Mapped[Optional[str]] = mapped_column(String(80))
    related_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    description: Mapped[Optional[str]] = mapped_column(String(255))
    dedup_key: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserNotification(Base):
    __tablename__ = "user_notifications"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text)
    related_type: Mapped[Optional[str]] = mapped_column(String(80))
    related_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class HelpPost(Base):
    __tablename__ = "help_posts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="published")
    points_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    reply_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
