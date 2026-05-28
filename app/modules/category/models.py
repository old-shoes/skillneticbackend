from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name_en: Mapped[Optional[str]] = mapped_column(String(80))
    parent_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("categories.id"))
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    icon: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(50), nullable=False, default="blue")
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    skill_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_hot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
