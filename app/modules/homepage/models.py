from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HomepageStats(Base):
    __tablename__ = "homepage_stats"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    skill_favorites: Mapped[int] = mapped_column(Integer, nullable=False, default=10000)
    quality_templates: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    monthly_visits: Mapped[int] = mapped_column(Integer, nullable=False, default=50000)
    beginner_tutorials: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
