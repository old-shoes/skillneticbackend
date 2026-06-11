from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.orm import Session

from app.modules.me.engagement import NotificationService, PointService
from app.modules.auth.models import User
from app.modules.category.models import Category
from app.modules.github_skills.models import SkillGithubSource
from app.modules.github_skills.schemas import GithubSkillParseOut
from app.modules.github_skills.service import GithubSkillService
from app.modules.skill.models import Skill, SkillCategoryRelation, SkillTag
from app.modules.skill.models import Tag
from app.modules.skill_submissions.models import (
    SkillSubmission,
    SkillSubmissionExample,
    SkillSubmissionReviewLog,
    SkillSubmissionRiskCheck,
    SkillSubmissionVariable,
)
from app.modules.skill_submissions.schemas import (
    AdminSkillSubmissionDetailOut,
    AdminSkillSubmissionListItemOut,
    AdminSkillSubmissionListOut,
    AdminSkillSubmissionQueryIn,
    AdminSkillSubmissionStatsOut,
    PaginationOut,
    SkillSubmissionApproveIn,
    SkillSubmissionDraftCreateIn,
    SkillSubmissionDraftIn,
    SkillSubmissionDraftOut,
    SkillSubmissionListItemOut,
    SkillSubmissionListOut,
    SkillSubmissionMetaOut,
    SkillSubmissionQueryIn,
    SkillSubmissionRejectIn,
    SkillSubmissionRequestRevisionIn,
    SkillSubmissionReviewDraftIn,
    SkillSubmissionStatus,
    SkillSubmissionSubmitIn,
    UserGithubSkillSubmitIn,
    UserSkillSubmitResultOut,
    SkillReviewLogOut,
    SkillRiskCheckOut,
    SkillPromptVariableOut,
    SubmitterOut,
    SubmissionCategoryOut,
    SubmissionCategoryTreeOut,
)

DEFAULT_ADMIN_ID = UUID("22222222-2222-2222-2222-222222222222")
DEFAULT_ADMIN_NAME = "Local Admin"
SUBMISSION_COVER_OPTIONS = [
    "/icons/tutorials/cover-chatgpt-prompt.svg",
    "/icons/tutorials/cover-midjourney-guide.svg",
    "/icons/tutorials/cover-workflow-guide.svg",
    "/icons/tutorials/cover-excel-ai.svg",
    "/icons/tutorials/cover-xiaohongshu-writing.svg",
    "/icons/tutorials/cover-python-ai.svg",
]
USE_CASE_OPTIONS = [
    {"label": "内容创作", "value": "content_creation"},
    {"label": "社交媒体运营", "value": "social_media"},
    {"label": "营销推广", "value": "marketing"},
    {"label": "电商转化", "value": "ecommerce"},
    {"label": "办公提效", "value": "productivity"},
    {"label": "学习辅导", "value": "learning"},
    {"label": "数据分析", "value": "data_analysis"},
    {"label": "编程开发", "value": "development"},
]
USE_CASE_VALUE_SET = {item["value"] for item in USE_CASE_OPTIONS}
USE_CASE_LABEL_MAP = {item["label"]: item["value"] for item in USE_CASE_OPTIONS}
SUBMISSION_COVER_SET = set(SUBMISSION_COVER_OPTIONS)
SKILL_TYPE_OPTIONS = [
    {"label": "提示词", "value": "prompt"},
    {"label": "工作流", "value": "workflow"},
    {"label": "教程", "value": "tutorial"},
    {"label": "工具配置", "value": "tool_config"},
    {"label": "Agent", "value": "agent"},
]
SKILL_TYPE_VALUE_SET = {item["value"] for item in SKILL_TYPE_OPTIONS}


class SkillSubmissionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _acquire_github_submission_lock(self, key: str) -> None:
        normalized = (key or "").strip().lower()
        if not normalized:
            return
        # Serialize writes for the same GitHub repo so duplicate submissions
        # cannot slip through concurrent duplicate checks.
        self.db.execute(
            text("select pg_advisory_xact_lock(hashtext(:key))"),
            {"key": normalized},
        )

    def _parse_uuid(self, value: str, field_name: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"invalid {field_name}") from exc

    def _parse_date(self, value: str, field_name: str, end_of_day: bool = False) -> datetime:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"invalid {field_name}") from exc
        if end_of_day:
            parsed = parsed + timedelta(days=1)
        return parsed.replace(tzinfo=timezone.utc)

    def _get_category(self, category_id: Optional[str]) -> Optional[Category]:
        if not category_id:
            return None
        category = self.db.get(Category, self._parse_uuid(category_id, "categoryId"))
        if category is None or category.deleted_at is not None:
            raise HTTPException(status_code=404, detail="category not found")
        return category

    def _category_filter_ids(self, category_id: str) -> List[UUID]:
        category = self._get_category(category_id)
        if category is None:
            return []
        if category.level == 2:
            return [category.id]
        child_ids = self.db.scalars(
            select(Category.id).where(
                Category.parent_id == category.id,
                Category.deleted_at.is_(None),
                Category.is_enabled.is_(True),
            )
        ).all()
        return list(child_ids) or [category.id]

    def _normalize_category_ids(self, category_ids: Optional[List[str]], category_id: Optional[str]) -> List[Category]:
        raw_values = category_ids if category_ids is not None else ([category_id] if category_id else [])
        normalized_ids: List[str] = []
        seen = set()
        for raw in raw_values:
            value = (raw or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized_ids.append(value)

        categories: List[Category] = []
        for item in normalized_ids:
            category = self._get_category(item)
            if category is None:
                continue
            categories.append(category)
        return categories

    def _category_out(self, category: Category) -> SubmissionCategoryOut:
        return SubmissionCategoryOut(
            id=str(category.id),
            name=category.name,
            slug=category.slug,
            parentId=str(category.parent_id) if category.parent_id else None,
            level=int(category.level or 1),
        )

    def _category_tree(self) -> List[SubmissionCategoryTreeOut]:
        rows = self.db.scalars(
            select(Category)
            .where(Category.deleted_at.is_(None), Category.is_enabled.is_(True))
            .order_by(Category.level.asc(), Category.sort_order.asc(), Category.created_at.asc())
        ).all()

        nodes = {
            item.id: SubmissionCategoryTreeOut(
                id=str(item.id),
                name=item.name,
                slug=item.slug,
                parentId=str(item.parent_id) if item.parent_id else None,
                level=int(item.level or 1),
                children=[],
            )
            for item in rows
        }
        roots: List[SubmissionCategoryTreeOut] = []
        for item in rows:
            node = nodes[item.id]
            if item.parent_id and item.parent_id in nodes:
                nodes[item.parent_id].children.append(node)
            else:
                roots.append(node)
        return roots

    def _selectable_categories(self) -> List[Category]:
        rows = self.db.scalars(
            select(Category)
            .where(Category.deleted_at.is_(None), Category.is_enabled.is_(True))
            .order_by(Category.level.asc(), Category.sort_order.asc(), Category.created_at.asc())
        ).all()
        parent_ids = {item.parent_id for item in rows if item.parent_id is not None}
        return [item for item in rows if item.id not in parent_ids]

    def _flat_meta_categories(self) -> List[Category]:
        return self.db.scalars(
            select(Category)
            .where(
                Category.deleted_at.is_(None),
                Category.is_enabled.is_(True),
                Category.level == 1,
            )
            .order_by(Category.sort_order.asc(), Category.created_at.asc())
        ).all()

    def _sync_skill_categories(self, skill: Skill, category_ids: List[UUID]) -> None:
        self.db.execute(delete(SkillCategoryRelation).where(SkillCategoryRelation.skill_id == skill.id))
        if not category_ids:
            return
        for index, category_id in enumerate(category_ids):
            self.db.add(
                SkillCategoryRelation(
                    skill_id=skill.id,
                    category_id=category_id,
                    is_primary=index == 0,
                )
            )

    def _normalize_use_cases(self, values: Optional[List[str]]) -> List[str]:
        if values is None:
            return []
        normalized: List[str] = []
        seen = set()
        for raw in values:
            item = (raw or "").strip()
            if not item:
                continue
            value = USE_CASE_LABEL_MAP.get(item, item)
            if value not in USE_CASE_VALUE_SET:
                raise HTTPException(status_code=400, detail=f"invalid useCases value: {item}")
            if value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized

    def _normalize_cover_image(self, value: Optional[str]) -> Optional[str]:
        normalized = (value or "").strip()
        if not normalized:
            return None
        if normalized not in SUBMISSION_COVER_SET:
            raise HTTPException(status_code=400, detail="invalid coverImage value")
        return normalized

    def _model_options(self) -> List[dict]:
        return []

    def _normalize_skill_type(self, value: Optional[str]) -> Optional[str]:
        normalized = (value or "").strip()
        if not normalized:
            return None
        if normalized not in SKILL_TYPE_VALUE_SET:
            raise HTTPException(status_code=400, detail="invalid skillType value")
        return normalized

    def _normalize_recommended_models(self, values: Optional[List[str]]) -> List[str]:
        if values is None:
            return []
        valid_values = {item["value"] for item in self._model_options()}
        normalized: List[str] = []
        seen = set()
        for raw in values:
            item = (raw or "").strip()
            if not item or item in seen:
                continue
            if item not in valid_values:
                raise HTTPException(status_code=400, detail=f"invalid recommendedModels value: {item}")
            seen.add(item)
            normalized.append(item)
        return normalized

    def get_meta(self) -> SkillSubmissionMetaOut:
        categories = self._flat_meta_categories()
        return SkillSubmissionMetaOut(
            categories=[
                self._category_out(item)
                for item in categories
            ],
            categoryTree=self._category_tree(),
            promptRoles=[
                "内容创作助手",
                "营销文案专家",
                "小红书运营",
                "品牌种草专家",
                "文案校对大师",
                "自定义角色",
            ],
            useCaseOptions=USE_CASE_OPTIONS,
            modelOptions=[],
            skillTypeOptions=SKILL_TYPE_OPTIONS,
            outputFormats=[
                {"label": "标题", "value": "title"},
                {"label": "正文", "value": "body"},
                {"label": "标签", "value": "tags"},
                {"label": "互动引导", "value": "interaction"},
                {"label": "分段输出", "value": "section"},
            ],
            difficulties=[
                {"label": "新手", "value": "beginner"},
                {"label": "进阶", "value": "intermediate"},
                {"label": "专业", "value": "advanced"},
            ],
            revisionFieldOptions=[
                {"label": "标题", "value": "title"},
                {"label": "简介", "value": "summary"},
                {"label": "详细介绍", "value": "description"},
                {"label": "分类", "value": "categoryId"},
                {"label": "标签", "value": "tags"},
                {"label": "Skill 类型", "value": "skillType"},
                {"label": "预计使用时长", "value": "estimatedTime"},
                {"label": "适用场景", "value": "useCases"},
                {"label": "封面", "value": "coverImage"},
                {"label": "Prompt 角色", "value": "promptRole"},
                {"label": "Prompt 模板", "value": "systemPrompt"},
            ],
            rejectReasonOptions=[
                {"label": "内容质量不足", "value": "low_quality"},
                {"label": "涉嫌抄袭", "value": "copyright_risk"},
                {"label": "违规内容", "value": "policy_violation"},
                {"label": "分类不符", "value": "category_mismatch"},
                {"label": "无实际价值", "value": "no_value"},
                {"label": "其他", "value": "other"},
            ],
        )

    def _get_submission(self, submission_id: str) -> SkillSubmission:
        submission = self.db.get(SkillSubmission, self._parse_uuid(submission_id, "submissionId"))
        if submission is None or submission.deleted_at is not None:
            raise HTTPException(status_code=404, detail="skill submission not found")
        return submission

    def _get_own_submission(self, submission_id: str, submitter_id: UUID) -> SkillSubmission:
        submission = self._get_submission(submission_id)
        if submission.submitter_id != submitter_id:
            raise HTTPException(status_code=403, detail="forbidden")
        return submission

    def _get_submitter_out(self, submitter_id: UUID) -> SubmitterOut:
        user = self.db.get(User, submitter_id)
        if user is None:
            return SubmitterOut(id=str(submitter_id), nickname="Unknown User", avatarUrl=None, level="Lv1")
        return SubmitterOut(
            id=str(user.id),
            nickname=user.nickname,
            avatarUrl=user.avatar_url,
            level=user.level,
        )

    def _get_submitter_user(self, submitter_id: UUID) -> Optional[User]:
        return self.db.get(User, submitter_id)

    def _slugify(self, text: str) -> str:
        base = "".join(char.lower() if char.isalnum() else "-" for char in text.strip())
        while "--" in base:
            base = base.replace("--", "-")
        return base.strip("-")[:140] or "skill-submission"

    def _build_unique_skill_slug(self, base_slug: str) -> str:
        slug = base_slug[:140] or "skill-submission"
        current = slug
        index = 2
        while self.db.scalar(select(Skill).where(Skill.slug == current, Skill.deleted_at.is_(None))) is not None:
            suffix = f"-{index}"
            current = f"{slug[: max(1, 140 - len(suffix))]}{suffix}"
            index += 1
        return current

    def _ensure_skill_tags(
        self,
        skill_id: UUID,
        names: List[str],
        tag_type: str,
        attached_tag_ids: Optional[set[UUID]] = None,
    ) -> set[UUID]:
        if attached_tag_ids is None:
            attached_tag_ids = {
                item[0]
                for item in self.db.execute(
                    select(SkillTag.tag_id).where(SkillTag.skill_id == skill_id)
                ).all()
            }
        for name in names:
            cleaned = (name or "").strip()
            if not cleaned:
                continue
            slug = self._slugify(cleaned)[:80] or cleaned[:80]
            tag = self.db.scalar(
                select(Tag).where(
                    Tag.slug == slug,
                    Tag.deleted_at.is_(None),
                )
            )
            if tag is None:
                tag = Tag(name=cleaned[:50], slug=slug, type=tag_type, is_enabled=True)
                self.db.add(tag)
                self.db.flush()
            if tag.id not in attached_tag_ids:
                self.db.add(SkillTag(skill_id=skill_id, tag_id=tag.id))
                attached_tag_ids.add(tag.id)
        return attached_tag_ids

    def _sync_submission_skill_tags(self, submission: SkillSubmission, skill: Skill) -> None:
        self.db.execute(delete(SkillTag).where(SkillTag.skill_id == skill.id))
        attached_tag_ids: set[UUID] = set()
        attached_tag_ids = self._ensure_skill_tags(skill.id, list(submission.tags or []), "type", attached_tag_ids)
        scene_names = [
            next((item["label"] for item in USE_CASE_OPTIONS if item["value"] == use_case), use_case)
            for use_case in (submission.use_cases or [])
            if str(use_case).strip()
        ]
        self._ensure_skill_tags(skill.id, scene_names, "scene", attached_tag_ids)

    def _submission_to_category(self, submission: SkillSubmission) -> Optional[SubmissionCategoryOut]:
        if not submission.category_id or not submission.category_name:
            return None
        category = self.db.get(Category, submission.category_id)
        if category is not None:
            return self._category_out(category)
        return SubmissionCategoryOut(
            id=str(submission.category_id),
            name=submission.category_name,
            slug="",
            parentId=None,
            level=2,
        )

    def _get_variables(self, submission_id: UUID) -> List[SkillPromptVariableOut]:
        rows = self.db.scalars(
            select(SkillSubmissionVariable)
            .where(SkillSubmissionVariable.submission_id == submission_id)
            .order_by(SkillSubmissionVariable.sort_order.asc(), SkillSubmissionVariable.created_at.asc())
        ).all()
        return [
            SkillPromptVariableOut(
                id=str(item.id),
                name=item.variable_name,
                label=item.variable_label,
                placeholder=item.placeholder,
                required=item.is_required,
                description=item.description,
                sortOrder=item.sort_order,
            )
            for item in rows
        ]

    def _get_logs(self, submission_id: UUID) -> List[SkillReviewLogOut]:
        rows = self.db.scalars(
            select(SkillSubmissionReviewLog)
            .where(SkillSubmissionReviewLog.submission_id == submission_id)
            .order_by(SkillSubmissionReviewLog.created_at.desc())
        ).all()
        return [
            SkillReviewLogOut(
                id=str(item.id),
                action=item.action,
                operatorType=item.operator_type,
                operatorName=item.operator_name,
                fromStatus=item.from_status,
                toStatus=item.to_status,
                comment=item.comment,
                reasonCode=item.reason_code,
                requiredFields=list(item.required_fields or []),
                createdAt=item.created_at,
            )
            for item in rows
        ]

    def _get_risk_checks(self, submission_id: UUID) -> List[SkillRiskCheckOut]:
        rows = self.db.scalars(
            select(SkillSubmissionRiskCheck)
            .where(SkillSubmissionRiskCheck.submission_id == submission_id)
            .order_by(SkillSubmissionRiskCheck.created_at.asc())
        ).all()
        return [
            SkillRiskCheckOut(
                id=str(item.id),
                checkType=item.check_type,
                status=item.status,
                resultMessage=item.result_message,
                detail=item.detail or {},
                checkedAt=item.checked_at,
                createdAt=item.created_at,
            )
            for item in rows
        ]

    def _draft_out(self, submission: SkillSubmission) -> SkillSubmissionDraftOut:
        category_ids = [str(item).strip() for item in (submission.category_ids or []) if str(item).strip()]
        return SkillSubmissionDraftOut(
            id=str(submission.id),
            title=submission.title,
            slug=submission.slug,
            summary=submission.summary,
            description=submission.description,
            submissionType=submission.submission_type,
            sourceType=submission.source_type,
            githubUrl=submission.github_url,
            repoFullName=submission.repo_full_name,
            sourceName=submission.source_name,
            originalAuthor=submission.original_author,
            license=submission.license,
            categoryId=str(submission.category_id) if submission.category_id else "",
            categoryIds=category_ids,
            categoryName=submission.category_name,
            tags=list(submission.tags or []),
            skillType=submission.skill_type,
            recommendedModels=list(submission.recommended_models or []),
            difficulty=submission.difficulty,
            estimatedTime=submission.estimated_time,
            coverImage=submission.cover_image,
            useCases=list(submission.use_cases or []),
            promptRole=submission.prompt_role,
            promptFileName=submission.prompt_file_name,
            systemPrompt=submission.system_prompt,
            promptVariables=self._get_variables(submission.id),
            outputFormats=list(submission.output_formats or []),
            creativity=float(submission.creativity),
            precision=float(submission.precision),
            outputLanguage=submission.output_language,
            outputLength=submission.output_length,
            exampleInputs=list(submission.example_inputs or []),
            exampleOutput=submission.example_output or {},
            usageGuide=submission.usage_guide,
            attachmentUrls=list(submission.attachment_urls or []),
            faqs=list(submission.faqs or []),
            submitNote=submission.submit_note,
            status=submission.status,
            qualityScore=submission.quality_score,
            reviewComment=submission.review_comment,
            reviewReasonCode=submission.review_reason_code,
            submittedAt=submission.submitted_at,
            reviewedAt=submission.reviewed_at,
            createdAt=submission.created_at,
            updatedAt=submission.updated_at,
        )

    def _detail_out(self, submission: SkillSubmission) -> AdminSkillSubmissionDetailOut:
        draft = self._draft_out(submission)
        return AdminSkillSubmissionDetailOut(
            **draft.model_dump(),
            category=self._submission_to_category(submission),
            submitter=self._get_submitter_out(submission.submitter_id),
            reviewLogs=self._get_logs(submission.id),
            riskChecks=self._get_risk_checks(submission.id),
        )

    def _ensure_review_checks(self, submission: SkillSubmission) -> None:
        existing = self.db.scalars(
            select(SkillSubmissionRiskCheck).where(SkillSubmissionRiskCheck.submission_id == submission.id)
        ).all()
        if existing:
            return
        for check_type, status, message in [
            ("external_link", "normal", "未发现异常外链"),
            ("sensitive_words", "normal", "未发现敏感词"),
            ("image_compliance", "pending", "封面图暂未接入自动检测"),
            ("copyright_risk", "warning", "建议人工确认是否与已有 Skill 重复"),
        ]:
            self.db.add(
                SkillSubmissionRiskCheck(
                    submission_id=submission.id,
                    check_type=check_type,
                    status=status,
                    result_message=message,
                    detail={},
                    checked_at=datetime.now(timezone.utc) if status != "pending" else None,
                )
            )

    def _write_log(
        self,
        submission: SkillSubmission,
        action: str,
        operator_type: str,
        operator_name: str,
        from_status: Optional[SkillSubmissionStatus],
        to_status: Optional[SkillSubmissionStatus],
        comment: Optional[str] = None,
        reason_code: Optional[str] = None,
        required_fields: Optional[Iterable[str]] = None,
    ) -> None:
        self.db.add(
            SkillSubmissionReviewLog(
                submission_id=submission.id,
                action=action,
                operator_id=DEFAULT_ADMIN_ID if operator_type == "admin" else submission.submitter_id,
                operator_type=operator_type,
                operator_name=operator_name,
                from_status=from_status,
                to_status=to_status,
                comment=comment,
                reason_code=reason_code,
                required_fields=list(required_fields or []),
                before_data=None,
                after_data=None,
            )
        )

    def _replace_variables(self, submission_id: UUID, variables: list) -> None:
        self.db.execute(delete(SkillSubmissionVariable).where(SkillSubmissionVariable.submission_id == submission_id))
        for index, variable in enumerate(variables):
            self.db.add(
                SkillSubmissionVariable(
                    submission_id=submission_id,
                    variable_name=variable.name,
                    variable_label=variable.label,
                    placeholder=variable.placeholder,
                    description=variable.description or "",
                    is_required=variable.required,
                    sort_order=variable.sortOrder if variable.sortOrder is not None else index,
                )
            )

    def _validate_for_submit(self, submission: SkillSubmission) -> None:
        required_errors = []
        title = (submission.title or "").strip()
        summary = (submission.summary or "").strip()
        description = (submission.description or "").strip()
        prompt_role = (submission.prompt_role or "").strip()
        system_prompt = (submission.system_prompt or "").strip()
        tags = [str(item).strip() for item in (submission.tags or []) if str(item).strip()]
        skill_type = (submission.skill_type or "").strip()
        use_cases = [str(item).strip() for item in (submission.use_cases or []) if str(item).strip()]
        is_github_submission = submission.submission_type == "github" or submission.source_type in ("github", "user_github")

        if not title:
            required_errors.append("title")
        elif len(title) < 2 or len(title) > 50:
            required_errors.append("title")

        if not summary:
            required_errors.append("summary")
        elif (not is_github_submission and len(summary) < 10) or len(summary) > (160 if is_github_submission else 80):
            required_errors.append("summary")

        if description and (
            len(description) < 20
            or (not is_github_submission and len(description) > 500)
        ):
            required_errors.append("description")

        if not submission.category_id:
            required_errors.append("categoryId")

        if len(tags) < 1 or len(tags) > 8:
            required_errors.append("tags")

        if skill_type not in SKILL_TYPE_VALUE_SET:
            required_errors.append("skillType")

        if len(use_cases) < 1:
            required_errors.append("useCases")

        if not is_github_submission:
            if not system_prompt:
                required_errors.append("systemPrompt")
            elif len(system_prompt) < 20 or len(system_prompt) > 50000:
                required_errors.append("systemPrompt")

        if not prompt_role:
            required_errors.append("promptRole")

        if required_errors:
            raise HTTPException(
                status_code=400,
                detail=f"missing required fields: {', '.join(required_errors)}",
            )

    def _upsert_skill_from_submission(self, submission: SkillSubmission) -> Skill:
        is_github_submission = submission.submission_type == "github" or submission.source_type in ("github", "user_github")
        skill_content = (submission.description or "").strip() if is_github_submission else ((submission.system_prompt or "").strip() or submission.description)
        submission_category_ids = [
            self._parse_uuid(str(item), "categoryIds")
            for item in (submission.category_ids or [])
            if str(item).strip()
        ]
        skill = None
        if submission.approved_skill_id:
            skill = self.db.get(Skill, submission.approved_skill_id)
        if skill is None and submission.approved_skill_id:
            submission.approved_skill_id = None

        if skill is None:
            base_slug = submission.slug or self._slugify(submission.title)
            skill = Skill(
                title=submission.title,
                slug=self._build_unique_skill_slug(base_slug),
                summary=submission.summary,
                content=skill_content,
                cover_icon=submission.cover_image,
                category_id=submission.category_id,
                difficulty=submission.difficulty,
                type=submission.skill_type or "prompt",
                use_case=(submission.use_cases or [""])[0] if submission.use_cases else None,
                search_keywords=" ".join([submission.title, submission.summary, *(submission.tags or [])]),
                recommended_models=list(submission.recommended_models or []),
                favorite_count=0,
                view_count=0,
                is_featured=False,
                is_hot=False,
                source_type=submission.source_type,
                source_url=submission.github_url if submission.source_type == "user_github" else None,
                source_name=submission.source_name,
                original_author=submission.original_author,
                license=submission.license,
                is_verified_source=submission.source_type == "user_github",
                last_source_synced_at=datetime.now(timezone.utc) if submission.source_type == "user_github" else None,
                status="published",
                published_at=datetime.now(timezone.utc),
            )
            self.db.add(skill)
            self.db.flush()
            self._sync_skill_categories(skill, submission_category_ids or ([submission.category_id] if submission.category_id else []))
            self._sync_submission_skill_tags(submission, skill)
            submission.approved_skill_id = skill.id
        else:
            skill.title = submission.title
            skill.summary = submission.summary
            skill.content = skill_content
            skill.cover_icon = submission.cover_image
            skill.category_id = submission.category_id
            skill.difficulty = submission.difficulty
            skill.type = submission.skill_type or "prompt"
            skill.use_case = (submission.use_cases or [""])[0] if submission.use_cases else None
            skill.search_keywords = " ".join([submission.title, submission.summary, *(submission.tags or [])])
            skill.recommended_models = list(submission.recommended_models or [])
            skill.source_type = submission.source_type
            skill.source_url = submission.github_url if submission.source_type == "user_github" else None
            skill.source_name = submission.source_name
            skill.original_author = submission.original_author
            skill.license = submission.license
            skill.is_verified_source = submission.source_type == "user_github"
            skill.last_source_synced_at = datetime.now(timezone.utc) if submission.source_type == "user_github" else None
            skill.status = "published"
            if skill.published_at is None:
                skill.published_at = datetime.now(timezone.utc)
            self._sync_skill_categories(skill, submission_category_ids or ([submission.category_id] if submission.category_id else []))
            self._sync_submission_skill_tags(submission, skill)
        if submission.source_type == "user_github" and submission.github_url and submission.repo_full_name:
            source = self.db.scalar(select(SkillGithubSource).where(SkillGithubSource.repo_full_name == submission.repo_full_name))
            if source is None:
                source = SkillGithubSource(
                    skill_id=skill.id,
                    repo_full_name=submission.repo_full_name,
                    owner_login=submission.repo_full_name.split("/")[0],
                    repo_name=submission.repo_full_name.split("/")[-1],
                    github_url=submission.github_url,
                )
                self.db.add(source)
            source.skill_id = skill.id
            source.github_url = submission.github_url
            source.original_author = submission.original_author
            source.license_name = submission.license
            source.last_synced_at = datetime.now(timezone.utc)
        return skill

    def create_draft(self, payload: SkillSubmissionDraftCreateIn, submitter_id: UUID) -> SkillSubmissionDraftOut:
        submission = SkillSubmission(
            submitter_id=submitter_id,
            submission_type="manual",
            source_type="user",
            title=payload.title.strip(),
            summary=payload.summary.strip(),
            status="draft",
        )
        self.db.add(submission)
        self.db.flush()
        self._write_log(submission, "submit", "user", self._get_submitter_out(submitter_id).nickname, None, "draft", comment="创建草稿")
        self.db.commit()
        self.db.refresh(submission)
        return self._draft_out(submission)

    def get_submission(self, submission_id: str, submitter_id: UUID) -> SkillSubmissionDraftOut:
        submission = self._get_own_submission(submission_id, submitter_id)
        return self._draft_out(submission)

    def update_submission(self, submission_id: str, payload: SkillSubmissionDraftIn, submitter_id: UUID) -> SkillSubmissionDraftOut:
        submission = self._get_own_submission(submission_id, submitter_id)
        categories = self._normalize_category_ids(payload.categoryIds, payload.categoryId) if (
            payload.categoryIds is not None or payload.categoryId is not None
        ) else None

        if payload.title is not None:
            submission.title = payload.title.strip()
        if payload.slug is not None:
            submission.slug = payload.slug.strip() or None
        if payload.summary is not None:
            submission.summary = payload.summary.strip()
        if payload.description is not None:
            submission.description = payload.description
        if categories is not None:
            primary_category = categories[0] if categories else None
            submission.category_id = primary_category.id if primary_category else None
            submission.category_ids = [str(item.id) for item in categories]
            submission.category_name = primary_category.name if primary_category else None
        if payload.tags is not None:
            submission.tags = [item.strip() for item in payload.tags if item.strip()]
        if payload.skillType is not None:
            submission.skill_type = self._normalize_skill_type(payload.skillType) or "prompt"
        if payload.recommendedModels is not None:
            submission.recommended_models = self._normalize_recommended_models(payload.recommendedModels)
        if payload.difficulty is not None:
            submission.difficulty = payload.difficulty
        if payload.estimatedTime is not None:
            submission.estimated_time = payload.estimatedTime.strip()
        if payload.coverImage is not None:
            submission.cover_image = self._normalize_cover_image(payload.coverImage)
        if payload.useCases is not None:
            submission.use_cases = self._normalize_use_cases(payload.useCases)
        if payload.promptRole is not None:
            submission.prompt_role = payload.promptRole.strip()
        if payload.promptFileName is not None:
            submission.prompt_file_name = payload.promptFileName.strip() or None
        if payload.systemPrompt is not None:
            submission.system_prompt = payload.systemPrompt
        if payload.outputFormats is not None:
            submission.output_formats = list(payload.outputFormats)
        if payload.creativity is not None:
            submission.creativity = payload.creativity
        if payload.precision is not None:
            submission.precision = payload.precision
        if payload.outputLanguage is not None:
            submission.output_language = payload.outputLanguage.strip()
        if payload.outputLength is not None:
            submission.output_length = payload.outputLength.strip()
        if payload.exampleInputs is not None:
            submission.example_inputs = [item.model_dump() for item in payload.exampleInputs]
        if payload.exampleOutput is not None:
            submission.example_output = payload.exampleOutput.model_dump()
        if payload.usageGuide is not None:
            submission.usage_guide = payload.usageGuide
        if payload.attachmentUrls is not None:
            submission.attachment_urls = [item.strip() for item in payload.attachmentUrls if item.strip()]
        if payload.faqs is not None:
            submission.faqs = [item.model_dump() for item in payload.faqs if item.question.strip() or item.answer.strip()]
        if payload.submitNote is not None:
            submission.submit_note = payload.submitNote.strip() or None
        if payload.promptVariables is not None:
            self._replace_variables(submission.id, payload.promptVariables)

        self._write_log(submission, "edit_by_admin", "user", self._get_submitter_out(submitter_id).nickname, submission.status, submission.status, comment="保存草稿")
        self.db.commit()
        self.db.refresh(submission)
        return self._draft_out(submission)

    def submit_submission(self, submission_id: str, payload: SkillSubmissionSubmitIn, submitter_id: UUID) -> SkillSubmissionDraftOut:
        submission = self._get_own_submission(submission_id, submitter_id)
        if submission.status not in {"draft", "needs_revision"}:
            raise HTTPException(status_code=400, detail="submission cannot be submitted in current status")
        self._validate_for_submit(submission)
        from_status = submission.status
        submission.status = "pending_review"
        submission.submit_note = payload.submitNote or submission.submit_note
        submission.submitted_at = datetime.now(timezone.utc)
        self._ensure_review_checks(submission)
        self._write_log(
            submission,
            "resubmit" if from_status == "needs_revision" else "submit",
            "user",
            self._get_submitter_out(submitter_id).nickname,
            from_status,
            "pending_review",
            comment=submission.submit_note,
        )
        if self._get_submitter_user(submission.submitter_id) is not None:
            NotificationService(self.db).create_notification(
                user_id=submission.submitter_id,
                type="skill_pending_review",
                title=f"你的 Skill「{submission.title}」已提交审核",
                content="我们会尽快完成审核，并在状态变化后通知你。",
                related_type="skill_submission",
                related_id=submission.id,
            )
        self.db.commit()
        self.db.refresh(submission)
        return self._draft_out(submission)

    def delete_submission(self, submission_id: str, submitter_id: UUID) -> None:
        submission = self._get_own_submission(submission_id, submitter_id)
        if submission.approved_skill_id or submission.status == "approved":
            raise HTTPException(status_code=400, detail="approved submission cannot be deleted")
        from_status = submission.status
        submission.status = "withdrawn"
        submission.deleted_at = datetime.now(timezone.utc)
        self._write_log(
            submission,
            "edit_by_admin",
            "user",
            self._get_submitter_out(submitter_id).nickname,
            from_status,
            "withdrawn",
            comment="删除提交",
        )
        self.db.commit()

    def list_my_submissions(self, query: SkillSubmissionQueryIn, submitter_id: UUID) -> SkillSubmissionListOut:
        stmt = (
            select(SkillSubmission)
            .where(
                SkillSubmission.submitter_id == submitter_id,
                SkillSubmission.deleted_at.is_(None),
            )
            .order_by(SkillSubmission.updated_at.desc(), SkillSubmission.created_at.desc())
        )
        if query.status:
            stmt = stmt.where(SkillSubmission.status == query.status)
        rows = self.db.scalars(stmt).all()
        total = len(rows)
        start = (query.page - 1) * query.pageSize
        end = start + query.pageSize
        paged = rows[start:end]
        items = [
            SkillSubmissionListItemOut(
                id=str(item.id),
                title=item.title,
                summary=item.summary,
                coverImage=item.cover_image,
                tags=item.tags or [],
                submissionType=item.submission_type,
                sourceType=item.source_type,
                githubUrl=item.github_url,
                repoFullName=item.repo_full_name,
                status=item.status,
                difficulty=item.difficulty,
                category=self._submission_to_category(item),
                submittedAt=item.submitted_at,
                updatedAt=item.updated_at,
            )
            for item in paged
        ]
        return SkillSubmissionListOut(
            list=items,
            pagination=PaginationOut.from_total(query.page, query.pageSize, total),
        )

    def parse_user_github_skill(self, github_url: str) -> GithubSkillParseOut:
        return GithubSkillService(self.db).parse_repo(github_url)

    def submit_user_github_skill(self, payload: UserGithubSkillSubmitIn, submitter_id: UUID) -> UserSkillSubmitResultOut:
        github_service = GithubSkillService(self.db)
        parsed, preview = github_service._build_parse_result(payload.github_url)
        self._acquire_github_submission_lock(parsed.repo_full_name or parsed.github_url)

        duplicate_skill = self.db.scalar(
            select(Skill.id).where(
                Skill.source_url == parsed.github_url,
                Skill.source_type.in_(("github", "user_github")),
                Skill.deleted_at.is_(None),
            )
        )
        if duplicate_skill is not None:
            raise HTTPException(status_code=400, detail="该 GitHub 仓库已被收录或提交")

        duplicate_submission = self.db.scalar(
            select(SkillSubmission.id).where(
                SkillSubmission.github_url == parsed.github_url,
                SkillSubmission.deleted_at.is_(None),
                SkillSubmission.status.in_(("draft", "pending_review", "approved", "needs_revision")),
            )
        )
        if duplicate_submission is not None:
            raise HTTPException(status_code=400, detail="该 GitHub 仓库已被收录或提交")

        category = None
        category_slug = (payload.category or parsed.parsed.category or "").strip()
        if category_slug:
            category = self.db.scalar(
                select(Category).where(
                    Category.slug == category_slug,
                    Category.deleted_at.is_(None),
                    Category.is_enabled.is_(True),
                )
            )

        metadata = preview.skill_md_frontmatter.get("metadata") if isinstance(preview.skill_md_frontmatter, dict) else None
        original_author = metadata.get("author") if isinstance(metadata, dict) else None
        cleaned_tags = [item.strip() for item in payload.tags if item.strip()]
        normalized_use_cases = self._normalize_use_cases(payload.use_cases or parsed.parsed.use_cases or [])
        summary = payload.summary.strip()

        submission = SkillSubmission(
            submitter_id=submitter_id,
            submission_type="github",
            source_type="user_github",
            title=payload.title.strip(),
            slug=self._slugify(payload.title),
            summary=summary[:160],
            description=(payload.description or parsed.parsed.description or "").strip(),
            github_url=parsed.github_url,
            repo_full_name=parsed.repo_full_name,
            source_name=parsed.repo_full_name,
            original_author=original_author,
            license=parsed.license,
            category_id=category.id if category else None,
            category_ids=[str(category.id)] if category else [],
            category_name=category.name if category else None,
            tags=cleaned_tags or list(parsed.parsed.tags or []),
            skill_type=payload.skill_type or parsed.parsed.skill_type or "agent",
            recommended_models=[],
            difficulty=payload.difficulty or parsed.parsed.difficulty or "intermediate",
            estimated_time="",
            cover_image=(payload.cover_url or "").strip() or None,
            target_audience=[],
            use_cases=normalized_use_cases,
            highlights=[],
            prompt_role=(parsed.parsed.prompt_role or payload.title).strip()[:100],
            prompt_file_name="SKILL.md" if parsed.skill_md_found else None,
            system_prompt=(parsed.parsed.system_prompt or preview.skill_md_preview or "").strip(),
            output_formats=[],
            creativity=0.7,
            precision=0.6,
            output_language="zh-CN",
            output_length="",
            example_inputs=[],
            example_output={"rawText": (payload.example_output or "").strip() or None},
            usage_guide=(payload.usage_guide or "").strip(),
            attachment_urls=[item.strip() for item in payload.attachment_urls if item.strip()],
            faqs=[],
            submit_note=None,
            status="pending_review",
            submitted_at=datetime.now(timezone.utc),
        )
        self.db.add(submission)
        self.db.flush()
        self._ensure_review_checks(submission)
        self._write_log(
            submission,
            "submit",
            "user",
            self._get_submitter_out(submitter_id).nickname,
            None,
            "pending_review",
            comment="GitHub Skill 提交审核",
        )
        if self._get_submitter_user(submission.submitter_id) is not None:
            NotificationService(self.db).create_notification(
                user_id=submission.submitter_id,
                type="skill_pending_review",
                title=f"你的 Skill「{submission.title}」已提交审核",
                content="我们会尽快完成审核，并在状态变化后通知你。",
                related_type="skill_submission",
                related_id=submission.id,
            )
        self.db.commit()
        return UserSkillSubmitResultOut(
            skill_id=str(submission.approved_skill_id or submission.id),
            submission_id=str(submission.id),
            status=submission.status,
        )

    def _stats(self) -> AdminSkillSubmissionStatsOut:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        base = select(SkillSubmission).where(SkillSubmission.deleted_at.is_(None))
        total = int(self.db.scalar(select(func.count()).select_from(base.subquery())) or 0)
        return AdminSkillSubmissionStatsOut(
            total=total,
            pending=int(self.db.scalar(select(func.count()).select_from(base.where(SkillSubmission.status == "pending_review").subquery())) or 0),
            todaySubmitted=int(
                self.db.scalar(
                    select(func.count())
                    .select_from(
                        base.where(
                            SkillSubmission.submitted_at.is_not(None),
                            SkillSubmission.submitted_at >= today_start,
                        ).subquery()
                    )
                )
                or 0
            ),
            approved=int(self.db.scalar(select(func.count()).select_from(base.where(SkillSubmission.status == "approved").subquery())) or 0),
            rejected=int(self.db.scalar(select(func.count()).select_from(base.where(SkillSubmission.status == "rejected").subquery())) or 0),
            needsRevision=int(
                self.db.scalar(select(func.count()).select_from(base.where(SkillSubmission.status == "needs_revision").subquery()))
                or 0
            ),
        )

    def list_admin_submissions(self, query: AdminSkillSubmissionQueryIn) -> AdminSkillSubmissionListOut:
        stmt = (
            select(SkillSubmission)
            .where(SkillSubmission.deleted_at.is_(None))
            .order_by(
                SkillSubmission.submitted_at.desc().nullslast(),
                SkillSubmission.updated_at.desc(),
            )
        )
        if query.q:
            keyword = f"%{query.q.strip()}%"
            stmt = stmt.where(
                or_(
                    SkillSubmission.title.ilike(keyword),
                    SkillSubmission.summary.ilike(keyword),
                    SkillSubmission.category_name.ilike(keyword),
                )
            )
        if query.status:
            stmt = stmt.where(SkillSubmission.status == query.status)
        if query.onlyPending:
            stmt = stmt.where(SkillSubmission.status == "pending_review")
        if query.categoryId:
            stmt = stmt.where(SkillSubmission.category_id.in_(self._category_filter_ids(query.categoryId)))
        if query.tag:
            stmt = stmt.where(SkillSubmission.tags.contains([query.tag]))
        if query.source:
            if query.source == "user_submission":
                stmt = stmt.where(SkillSubmission.submitter_id.is_not(None))
            elif query.source == "official_entry":
                stmt = stmt.where(SkillSubmission.submitter_id.is_(None))
            elif query.source == "admin_proxy":
                stmt = stmt.where(SkillSubmission.submitter_id == DEFAULT_ADMIN_ID)
        if query.submittedStart:
            stmt = stmt.where(SkillSubmission.submitted_at >= self._parse_date(query.submittedStart, "submittedStart"))
        if query.submittedEnd:
            stmt = stmt.where(SkillSubmission.submitted_at < self._parse_date(query.submittedEnd, "submittedEnd", end_of_day=True))

        rows = self.db.scalars(stmt).all()
        total = len(rows)
        start = (query.page - 1) * query.pageSize
        end = start + query.pageSize
        paged = rows[start:end]
        items = [
            AdminSkillSubmissionListItemOut(
                id=str(item.id),
                title=item.title,
                summary=item.summary,
                coverImage=item.cover_image,
                category=self._submission_to_category(item),
                tags=list(item.tags or []),
                submitter=self._get_submitter_out(item.submitter_id),
                source="admin_proxy" if item.submitter_id == DEFAULT_ADMIN_ID else "user_submission",
                status=item.status,
                qualityScore=item.quality_score,
                difficulty=item.difficulty,
                submittedAt=item.submitted_at,
                updatedAt=item.updated_at,
            )
            for item in paged
        ]
        return AdminSkillSubmissionListOut(
            stats=self._stats(),
            list=items,
            pagination=PaginationOut.from_total(query.page, query.pageSize, total),
        )

    def get_admin_detail(self, submission_id: str) -> AdminSkillSubmissionDetailOut:
        submission = self._get_submission(submission_id)
        self._ensure_review_checks(submission)
        self.db.commit()
        self.db.refresh(submission)
        return self._detail_out(submission)

    def approve(self, submission_id: str, payload: SkillSubmissionApproveIn) -> AdminSkillSubmissionDetailOut:
        submission = self._get_submission(submission_id)
        if submission.status != "pending_review":
            raise HTTPException(status_code=400, detail="only pending submissions can be approved")
        self._validate_for_submit(submission)
        skill = self._upsert_skill_from_submission(submission)
        skill.is_featured = bool(payload.setFeatured)
        submission.status = "approved"
        submission.review_comment = payload.reviewComment
        submission.review_reason_code = None
        submission.reviewed_by = DEFAULT_ADMIN_ID
        submission.reviewed_at = datetime.now(timezone.utc)
        submission.quality_score = submission.quality_score or 88
        self._write_log(
            submission,
            "approve",
            "admin",
            DEFAULT_ADMIN_NAME,
            "pending_review",
            "approved",
            comment=payload.reviewComment,
        )
        if self._get_submitter_user(submission.submitter_id) is not None:
            PointService(self.db).award_skill_approved_points(submission.submitter_id, submission.id)
            NotificationService(self.db).create_notification(
                user_id=submission.submitter_id,
                type="skill_approved",
                title=f"你的 Skill「{submission.title}」已通过审核",
                content=payload.reviewComment or "现在可以在平台上继续查看和管理这条 Skill。",
                related_type="skill_submission",
                related_id=submission.id,
            )
        self.db.commit()
        self.db.refresh(submission)
        self.db.refresh(skill)
        return self._detail_out(submission)

    def reject(self, submission_id: str, payload: SkillSubmissionRejectIn) -> AdminSkillSubmissionDetailOut:
        submission = self._get_submission(submission_id)
        if submission.status != "pending_review":
            raise HTTPException(status_code=400, detail="only pending submissions can be rejected")
        submission.status = "rejected"
        submission.review_comment = payload.reviewComment
        submission.review_reason_code = payload.reasonCode
        submission.reviewed_by = DEFAULT_ADMIN_ID
        submission.reviewed_at = datetime.now(timezone.utc)
        self._write_log(
            submission,
            "reject",
            "admin",
            DEFAULT_ADMIN_NAME,
            "pending_review",
            "rejected",
            comment=payload.reviewComment,
            reason_code=payload.reasonCode,
        )
        if self._get_submitter_user(submission.submitter_id) is not None:
            NotificationService(self.db).create_notification(
                user_id=submission.submitter_id,
                type="skill_rejected",
                title=f"你的 Skill「{submission.title}」未通过审核",
                content=payload.reviewComment,
                related_type="skill_submission",
                related_id=submission.id,
            )
        self.db.commit()
        self.db.refresh(submission)
        return self._detail_out(submission)

    def request_revision(self, submission_id: str, payload: SkillSubmissionRequestRevisionIn) -> AdminSkillSubmissionDetailOut:
        submission = self._get_submission(submission_id)
        if submission.status != "pending_review":
            raise HTTPException(status_code=400, detail="only pending submissions can request revision")
        submission.status = "needs_revision"
        submission.review_comment = payload.reviewComment
        submission.review_reason_code = None
        submission.reviewed_by = DEFAULT_ADMIN_ID
        submission.reviewed_at = datetime.now(timezone.utc)
        self._write_log(
            submission,
            "request_revision",
            "admin",
            DEFAULT_ADMIN_NAME,
            "pending_review",
            "needs_revision",
            comment=payload.reviewComment,
            required_fields=payload.requiredFields,
        )
        if self._get_submitter_user(submission.submitter_id) is not None:
            NotificationService(self.db).create_notification(
                user_id=submission.submitter_id,
                type="skill_needs_revision",
                title=f"你的 Skill「{submission.title}」需要修改后重新提交",
                content=payload.reviewComment,
                related_type="skill_submission",
                related_id=submission.id,
            )
        self.db.commit()
        self.db.refresh(submission)
        return self._detail_out(submission)

    def save_review_draft(self, submission_id: str, payload: SkillSubmissionReviewDraftIn) -> AdminSkillSubmissionDetailOut:
        submission = self._get_submission(submission_id)
        self._write_log(
            submission,
            "save_review_draft",
            "admin",
            DEFAULT_ADMIN_NAME,
            submission.status,
            submission.status,
            comment=payload.reviewComment,
            required_fields=payload.requiredFields,
        )
        self.db.commit()
        self.db.refresh(submission)
        return self._detail_out(submission)
