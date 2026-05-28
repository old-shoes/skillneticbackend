from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_name: Mapped[str] = mapped_column(String(80), nullable=False)
    user_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    anonymous_id: Mapped[Optional[str]] = mapped_column(String(100))
    page_url: Mapped[str] = mapped_column(String(500), nullable=False)
    referrer: Mapped[Optional[str]] = mapped_column(String(500))
    target_type: Mapped[Optional[str]] = mapped_column(String(50))
    target_id: Mapped[Optional[str]] = mapped_column(String(100))
    extra: Mapped[Dict] = mapped_column(JSONB, nullable=False, default=dict)
    ip: Mapped[Optional[str]] = mapped_column(String(80))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
