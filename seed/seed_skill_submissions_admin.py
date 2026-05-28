from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.modules.auth.models import User
from app.modules.auth.service import hash_password
from app.modules.category.models import Category
from app.modules.skill_submissions.models import (
    SkillSubmission,
    SkillSubmissionReviewLog,
    SkillSubmissionRiskCheck,
    SkillSubmissionVariable,
)


ADMIN_ID = UUID("22222222-2222-2222-2222-222222222222")
USER_A_ID = UUID("33333333-3333-3333-3333-333333333333")
USER_B_ID = UUID("44444444-4444-4444-4444-444444444444")


def upsert_user(db, user_id: UUID, email: str, nickname: str, level: str) -> None:
    user = db.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            email=email,
            password_hash=hash_password("ai-skill-test-token"),
            nickname=nickname,
            level=level,
            locale="zh",
            is_active=True,
        )
        db.add(user)
        return
    user.email = email
    user.nickname = nickname
    user.level = level
    user.is_active = True


def upsert_category(db, slug: str, name: str, icon: str, color: str, description: str) -> Category:
    category = db.scalar(select(Category).where(Category.slug == slug))
    if category is None:
        category = Category(
            slug=slug,
            name=name,
            icon=icon,
            color=color,
            description=description,
            skill_count=0,
            is_enabled=True,
            sort_order=0,
        )
        db.add(category)
        db.flush()
        return category
    category.name = name
    category.icon = icon
    category.color = color
    category.description = description
    category.is_enabled = True
    return category


def create_logs(db, submission_id: UUID, status: str, review_comment: str | None) -> None:
    db.add(
        SkillSubmissionReviewLog(
            submission_id=submission_id,
            action="submit",
            operator_id=USER_A_ID,
            operator_type="user",
            operator_name="投稿用户 A",
            from_status="draft",
            to_status="pending_review",
            comment="提交审核",
            required_fields=[],
        )
    )
    if status == "approved":
        db.add(
            SkillSubmissionReviewLog(
                submission_id=submission_id,
                action="approve",
                operator_id=ADMIN_ID,
                operator_type="admin",
                operator_name="Local Admin",
                from_status="pending_review",
                to_status="approved",
                comment=review_comment,
                required_fields=[],
            )
        )
    elif status == "rejected":
        db.add(
            SkillSubmissionReviewLog(
                submission_id=submission_id,
                action="reject",
                operator_id=ADMIN_ID,
                operator_type="admin",
                operator_name="Local Admin",
                from_status="pending_review",
                to_status="rejected",
                comment=review_comment,
                reason_code="low_quality",
                required_fields=[],
            )
        )
    elif status == "needs_revision":
        db.add(
            SkillSubmissionReviewLog(
                submission_id=submission_id,
                action="request_revision",
                operator_id=ADMIN_ID,
                operator_type="admin",
                operator_name="Local Admin",
                from_status="pending_review",
                to_status="needs_revision",
                comment=review_comment,
                required_fields=["systemPrompt", "useCases"],
            )
        )


def create_risk_checks(db, submission_id: UUID) -> None:
    checks = [
        ("external_link", "normal", "未发现异常外链"),
        ("sensitive_words", "normal", "未发现敏感词"),
        ("image_compliance", "pending", "封面图暂未接入自动检测"),
        ("copyright_risk", "warning", "建议人工确认是否与已有 Skill 重复"),
    ]
    now = datetime.now(timezone.utc)
    for check_type, status, result_message in checks:
        db.add(
            SkillSubmissionRiskCheck(
                submission_id=submission_id,
                check_type=check_type,
                status=status,
                result_message=result_message,
                detail={},
                checked_at=now if status != "pending" else None,
            )
        )


def create_variables(db, submission_id: UUID) -> None:
    variables = [
        ("topic", "主题", "请输入主题", "用户要处理的主题或任务方向", True, 1),
        ("tone", "语气", "如：专业/活泼/种草", "控制输出内容的语气和风格", False, 2),
    ]
    for name, label, placeholder, description, required, sort_order in variables:
        db.add(
            SkillSubmissionVariable(
                submission_id=submission_id,
                variable_name=name,
                variable_label=label,
                placeholder=placeholder,
                description=description,
                is_required=required,
                sort_order=sort_order,
            )
        )


def main() -> None:
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    try:
        upsert_user(db, ADMIN_ID, "admin-local@aiskill.local", "Local Admin", "Lv9")
        upsert_user(db, USER_A_ID, "creator-a@aiskill.local", "投稿用户 A", "Lv3")
        upsert_user(db, USER_B_ID, "creator-b@aiskill.local", "投稿用户 B", "Lv5")

        writing = upsert_category(db, "writing", "写作", "prompt", "blue", "文案写作、标题生成、内容润色等")
        marketing = upsert_category(db, "marketing", "营销", "prompt", "rose", "社媒运营、广告文案、用户增长等")
        office = upsert_category(db, "office", "办公", "tool", "orange", "文档处理、数据分析、PPT 等效率工具")
        db.flush()

        slugs = [
            "admin-demo-xiaohongshu-copywriter",
            "admin-demo-weekly-report-assistant",
            "admin-demo-email-optimizer",
            "admin-demo-video-hook-generator",
        ]
        existing = db.scalars(select(SkillSubmission).where(SkillSubmission.slug.in_(slugs))).all()
        existing_ids = [item.id for item in existing]
        if existing_ids:
            db.execute(delete(SkillSubmissionVariable).where(SkillSubmissionVariable.submission_id.in_(existing_ids)))
            db.execute(delete(SkillSubmissionReviewLog).where(SkillSubmissionReviewLog.submission_id.in_(existing_ids)))
            db.execute(delete(SkillSubmissionRiskCheck).where(SkillSubmissionRiskCheck.submission_id.in_(existing_ids)))
            db.execute(delete(SkillSubmission).where(SkillSubmission.id.in_(existing_ids)))
            db.flush()

        payloads = [
            {
                "submitter_id": USER_A_ID,
                "title": "小红书种草文案生成器",
                "slug": "admin-demo-xiaohongshu-copywriter",
                "summary": "输入产品卖点和目标人群，输出适合小红书场景的种草文案。",
                "description": "适合社媒运营和内容创作者快速生成小红书风格文案，包含标题、正文和互动引导。",
                "category": marketing,
                "tags": ["小红书", "种草", "内容创作"],
                "difficulty": "beginner",
                "estimated_time": "5 分钟",
                "cover_image": "/icons/tutorials/cover-xiaohongshu-writing.svg",
                "use_cases": ["content_creation", "social_media", "marketing"],
                "prompt_role": "小红书运营",
                "system_prompt": "你是一名资深小红书内容运营，请根据输入的产品卖点、目标人群和使用场景，输出适合发布的小红书标题、正文和结尾互动引导。",
                "status": "pending_review",
                "quality_score": 86,
                "review_comment": None,
                "review_reason_code": None,
                "reviewed_by": None,
                "reviewed_at": None,
                "submitted_at": now - timedelta(hours=2),
                "created_at": now - timedelta(hours=5),
                "updated_at": now - timedelta(hours=2),
            },
            {
                "submitter_id": USER_B_ID,
                "title": "周报总结助手",
                "slug": "admin-demo-weekly-report-assistant",
                "summary": "把一周工作记录整理成结构化周报，适合团队同步和向上汇报。",
                "description": "自动输出本周完成事项、问题风险、下周计划，减少重复写周报的时间。",
                "category": office,
                "tags": ["周报", "办公效率", "总结"],
                "difficulty": "beginner",
                "estimated_time": "8 分钟",
                "cover_image": "/icons/tutorials/cover-excel-ai.svg",
                "use_cases": ["productivity", "learning"],
                "prompt_role": "汇报助手",
                "system_prompt": "你是一名工作汇报整理助手，请把用户的一周碎片记录整理为结构化周报，输出本周完成、问题风险和下周计划。",
                "status": "approved",
                "quality_score": 91,
                "review_comment": "结构清晰，适合直接上线。",
                "review_reason_code": None,
                "reviewed_by": ADMIN_ID,
                "reviewed_at": now - timedelta(days=1, hours=3),
                "submitted_at": now - timedelta(days=2),
                "created_at": now - timedelta(days=3),
                "updated_at": now - timedelta(days=1, hours=3),
            },
            {
                "submitter_id": USER_A_ID,
                "title": "商务邮件优化器",
                "slug": "admin-demo-email-optimizer",
                "summary": "帮助用户把普通邮件润色成更专业、礼貌、清晰的商务表达。",
                "description": "适合销售、运营和管理者优化对外邮件表达，减少沟通成本。",
                "category": writing,
                "tags": ["邮件", "商务沟通", "润色"],
                "difficulty": "intermediate",
                "estimated_time": "6 分钟",
                "cover_image": "/icons/tutorials/cover-chatgpt-prompt.svg",
                "use_cases": ["productivity", "content_creation"],
                "prompt_role": "商务邮件顾问",
                "system_prompt": "你是一名商务邮件写作顾问，请将用户输入的原始邮件优化为更礼貌、更专业且重点清晰的版本。",
                "status": "needs_revision",
                "quality_score": 74,
                "review_comment": "Prompt 模板和适用场景还需要补充得更明确。",
                "review_reason_code": None,
                "reviewed_by": ADMIN_ID,
                "reviewed_at": now - timedelta(hours=10),
                "submitted_at": now - timedelta(days=1, hours=6),
                "created_at": now - timedelta(days=2),
                "updated_at": now - timedelta(hours=10),
            },
            {
                "submitter_id": ADMIN_ID,
                "title": "短视频开头钩子生成器",
                "slug": "admin-demo-video-hook-generator",
                "summary": "生成适合短视频前 3 秒的吸引式开头文案，提高完播率。",
                "description": "适合短视频和直播团队做开头脚本测试，但当前示例内容还不够完整。",
                "category": marketing,
                "tags": ["短视频", "脚本", "营销"],
                "difficulty": "intermediate",
                "estimated_time": "10 分钟",
                "cover_image": "/icons/tutorials/cover-workflow-guide.svg",
                "use_cases": ["marketing", "content_creation"],
                "prompt_role": "短视频策划",
                "system_prompt": "你是一名短视频内容策划，请根据主题和受众输出多个适合前 3 秒的吸引式开头方案。",
                "status": "rejected",
                "quality_score": 58,
                "review_comment": "内容价值不足，和平台现有 Skill 重复度较高。",
                "review_reason_code": "low_quality",
                "reviewed_by": ADMIN_ID,
                "reviewed_at": now - timedelta(days=1),
                "submitted_at": now - timedelta(days=2, hours=5),
                "created_at": now - timedelta(days=4),
                "updated_at": now - timedelta(days=1),
            },
        ]

        for payload in payloads:
            submission = SkillSubmission(
                submitter_id=payload["submitter_id"],
                title=payload["title"],
                slug=payload["slug"],
                summary=payload["summary"],
                description=payload["description"],
                category_id=payload["category"].id,
                category_name=payload["category"].name,
                tags=payload["tags"],
                difficulty=payload["difficulty"],
                estimated_time=payload["estimated_time"],
                cover_image=payload["cover_image"],
                target_audience=["运营", "内容创作者"],
                use_cases=payload["use_cases"],
                highlights=["结构清晰", "可直接复用", "适合中文场景"],
                prompt_role=payload["prompt_role"],
                system_prompt=payload["system_prompt"],
                output_formats=["title", "body", "interaction"],
                creativity=0.75,
                precision=0.68,
                output_language="zh-CN",
                output_length="中等",
                example_inputs=[
                    {"key": "topic", "label": "主题", "value": "AI 办公提效"},
                    {"key": "tone", "label": "语气", "value": "专业但易懂"},
                ],
                example_output={
                    "title": "3 个 AI 办公提效技巧",
                    "body": "先明确场景，再拆分动作，最后给出可执行建议。",
                    "tags": ["AI办公", "效率提升"],
                },
                usage_guide="填写主题和语气后即可得到完整输出，建议结合真实业务场景做二次调整。",
                faqs=[
                    {"question": "适合什么人？", "answer": "适合内容、运营、办公场景的日常使用。"},
                ],
                submit_note="后台演示数据",
                status=payload["status"],
                quality_score=payload["quality_score"],
                review_comment=payload["review_comment"],
                review_reason_code=payload["review_reason_code"],
                reviewed_by=payload["reviewed_by"],
                reviewed_at=payload["reviewed_at"],
                submitted_at=payload["submitted_at"],
                created_at=payload["created_at"],
                updated_at=payload["updated_at"],
            )
            db.add(submission)
            db.flush()
            create_variables(db, submission.id)
            create_logs(db, submission.id, payload["status"], payload["review_comment"])
            create_risk_checks(db, submission.id)

        db.commit()
        print("seed_skill_submissions_admin done", f"submissions={len(payloads)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
