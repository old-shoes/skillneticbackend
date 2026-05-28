from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(80), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    bio: Mapped[Optional[str]] = mapped_column(String(300))
    location: Mapped[Optional[str]] = mapped_column(String(80))
    points: Mapped[int] = mapped_column(nullable=False, default=0)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    github_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="Lv1")
    locale: Mapped[str] = mapped_column(String(20), nullable=False, default="zh")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class UserAuthAccount(Base):
    __tablename__ = "user_auth_accounts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_user_id: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    github_username: Mapped[Optional[str]] = mapped_column(String(100))
    github_avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    github_profile_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    bound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    ip: Mapped[Optional[str]] = mapped_column(String(80))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AuthEmailCode(Base):
    __tablename__ = "auth_email_codes"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    scene: Mapped[str] = mapped_column(String(50), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="unused")
    send_ip: Mapped[Optional[str]] = mapped_column(String(80))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AuthLog(Base):
    __tablename__ = "auth_logs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    ip: Mapped[Optional[str]] = mapped_column(String(80))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fail_reason: Mapped[Optional[str]] = mapped_column(String(255))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PasswordResetRecord(Base):
    __tablename__ = "password_reset_records"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    email_code_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("auth_email_codes.id", ondelete="SET NULL"),
    )
    reset_ip: Mapped[Optional[str]] = mapped_column(String(80))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fail_reason: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
