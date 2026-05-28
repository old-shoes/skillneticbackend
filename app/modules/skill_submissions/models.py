from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SkillSubmission(Base):
    __tablename__ = "skill_submissions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    submitter_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    slug: Mapped[Optional[str]] = mapped_column(String(140))
    summary: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("categories.id"))
    category_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    category_name: Mapped[Optional[str]] = mapped_column(String(80))
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    skill_type: Mapped[str] = mapped_column(String(30), nullable=False, default="prompt")
    recommended_models: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    difficulty: Mapped[str] = mapped_column(String(30), nullable=False, default="beginner")
    estimated_time: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    cover_image: Mapped[Optional[str]] = mapped_column(String(500))
    target_audience: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    use_cases: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    highlights: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    prompt_role: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    prompt_file_name: Mapped[Optional[str]] = mapped_column(String(255))
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    output_formats: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    creativity: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=0.7)
    precision: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=0.6)
    output_language: Mapped[str] = mapped_column(String(50), nullable=False, default="zh-CN")
    output_length: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    example_inputs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    example_output: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    usage_guide: Mapped[str] = mapped_column(Text, nullable=False, default="")
    faqs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    submit_note: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    quality_score: Mapped[Optional[int]] = mapped_column(Integer)
    review_comment: Mapped[Optional[str]] = mapped_column(Text)
    review_reason_code: Mapped[Optional[str]] = mapped_column(String(80))
    reviewed_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    approved_skill_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("skills.id"))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class SkillSubmissionVariable(Base):
    __tablename__ = "skill_submission_variables"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    submission_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("skill_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    variable_name: Mapped[str] = mapped_column(String(80), nullable=False)
    variable_label: Mapped[str] = mapped_column(String(80), nullable=False)
    placeholder: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SkillSubmissionExample(Base):
    __tablename__ = "skill_submission_examples"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    submission_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("skill_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    example_input: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    example_output: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    usage_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SkillSubmissionReviewLog(Base):
    __tablename__ = "skill_submission_review_logs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    submission_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("skill_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    operator_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    operator_type: Mapped[str] = mapped_column(String(30), nullable=False, default="admin")
    operator_name: Mapped[Optional[str]] = mapped_column(String(80))
    from_status: Mapped[Optional[str]] = mapped_column(String(40))
    to_status: Mapped[Optional[str]] = mapped_column(String(40))
    comment: Mapped[Optional[str]] = mapped_column(Text)
    reason_code: Mapped[Optional[str]] = mapped_column(String(80))
    required_fields: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    before_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    after_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    ip: Mapped[Optional[str]] = mapped_column(String(80))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SkillSubmissionRiskCheck(Base):
    __tablename__ = "skill_submission_risk_checks"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    submission_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("skill_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    check_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    result_message: Mapped[Optional[str]] = mapped_column(String(255))
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
