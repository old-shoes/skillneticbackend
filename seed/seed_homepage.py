from datetime import datetime, timedelta, timezone
from typing import Dict

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.category.models import Category
from app.modules.homepage.models import HomepageStats
from app.modules.skill.models import Skill, SkillTag, Tag
from app.modules.tutorial.models import Tutorial


def get_or_create_category(db, *, slug: str, **values) -> Category:
    item = db.scalar(select(Category).where(Category.slug == slug))
    if item is None:
        item = Category(slug=slug, **values)
        db.add(item)
        db.flush()
        return item

    for key, value in values.items():
        setattr(item, key, value)
    db.flush()
    return item


def get_or_create_tag(db, *, slug: str, **values) -> Tag:
    item = db.scalar(select(Tag).where(Tag.slug == slug))
    if item is None:
        item = Tag(slug=slug, **values)
        db.add(item)
        db.flush()
        return item

    for key, value in values.items():
        setattr(item, key, value)
    db.flush()
    return item


def get_or_create_skill(db, *, slug: str, **values) -> Skill:
    item = db.scalar(select(Skill).where(Skill.slug == slug))
    if item is None:
        item = Skill(slug=slug, **values)
        db.add(item)
        db.flush()
        return item

    for key, value in values.items():
        setattr(item, key, value)
    db.flush()
    return item


def get_or_create_tutorial(db, *, slug: str, **values) -> Tutorial:
    item = db.scalar(select(Tutorial).where(Tutorial.slug == slug))
    if item is None:
        item = Tutorial(slug=slug, **values)
        db.add(item)
        db.flush()
        return item

    for key, value in values.items():
        setattr(item, key, value)
    db.flush()
    return item


def ensure_skill_tag(db, skill_id, tag_id) -> None:
    exists = db.scalar(
        select(SkillTag.skill_id).where(
            SkillTag.skill_id == skill_id,
            SkillTag.tag_id == tag_id,
        )
    )
    if exists is None:
        db.add(SkillTag(skill_id=skill_id, tag_id=tag_id))


def upsert_homepage_stats(db, **values) -> HomepageStats:
    item = db.scalar(
        select(HomepageStats)
        .where(HomepageStats.is_active.is_(True))
        .order_by(HomepageStats.updated_at.desc(), HomepageStats.created_at.desc())
    )
    if item is None:
        item = HomepageStats(**values)
        db.add(item)
        db.flush()
        return item

    for key, value in values.items():
        setattr(item, key, value)
    db.flush()
    return item


def main() -> None:
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    try:
        categories = [
            ("writing", dict(name="写作", icon="pen", color="blue", description="文案写作、标题生成、内容润色等", skill_count=2345, sort_order=1)),
            ("coding", dict(name="编程", icon="code", color="green", description="代码生成、调试、解释与优化", skill_count=2128, sort_order=2)),
            ("office", dict(name="办公", icon="briefcase", color="orange", description="文档处理、数据分析、PPT 等效率工具", skill_count=2256, sort_order=3)),
            ("design", dict(name="设计", icon="palette", color="purple", description="图像生成、UI 设计、创意视觉等", skill_count=1789, sort_order=4)),
            ("marketing", dict(name="营销", icon="megaphone", color="rose", description="社媒运营、广告文案、用户增长等", skill_count=1654, sort_order=5)),
            ("learning", dict(name="学习", icon="graduation", color="indigo", description="知识问答、笔记总结、学习规划等", skill_count=1402, sort_order=6)),
            ("video", dict(name="视频", icon="play", color="cyan", description="脚本创作、分镜、剪辑辅助", skill_count=1210, sort_order=7)),
            ("automation", dict(name="自动化", icon="robot", color="emerald", description="工作流编排、Agent、任务串联", skill_count=1098, sort_order=8)),
        ]
        category_map: Dict[str, Category] = {
            slug: get_or_create_category(db, slug=slug, **payload) for slug, payload in categories
        }

        tags = [
            ("xiaohongshu", dict(name="小红书", type="scene", sort_order=10)),
            ("office", dict(name="办公", type="scene", sort_order=11)),
            ("job", dict(name="求职", type="scene", sort_order=12)),
            ("academic", dict(name="学术", type="scene", sort_order=13)),
            ("excel", dict(name="Excel", type="scene", sort_order=14)),
            ("product", dict(name="产品", type="scene", sort_order=15)),
            ("design", dict(name="设计", type="scene", sort_order=16)),
            ("email", dict(name="邮件", type="scene", sort_order=17)),
            ("video", dict(name="视频", type="scene", sort_order=18)),
            ("coding", dict(name="编程", type="scene", sort_order=19)),
            ("social", dict(name="社媒", type="scene", sort_order=20)),
            ("gpt-4o", dict(name="GPT-4o", type="model", sort_order=21)),
            ("midjourney", dict(name="Midjourney", type="type", sort_order=22)),
            ("easy", dict(name="简单", type="difficulty", sort_order=30)),
            ("medium", dict(name="中等", type="difficulty", sort_order=31)),
        ]
        tag_map: Dict[str, Tag] = {
            slug: get_or_create_tag(db, slug=slug, **payload) for slug, payload in tags
        }

        skills = [
            (
                "xiaohongshu-title-generator",
                dict(
                    title="小红书爆款标题生成",
                    summary="快速生成高点击率的小红书标题，提升曝光与互动率。",
                    cover_icon="document",
                    category_id=category_map["writing"].id,
                    difficulty="beginner",
                    favorite_count=8600,
                    view_count=23000,
                    is_featured=True,
                    is_hot=True,
                    status="published",
                    published_at=now - timedelta(days=1),
                ),
                ["gpt-4o", "xiaohongshu", "easy"],
            ),
            (
                "meeting-notes-assistant",
                dict(
                    title="会议纪要整理助手",
                    summary="自动整理会议纪要和待办事项，提升协作效率。",
                    cover_icon="group",
                    category_id=category_map["office"].id,
                    difficulty="intermediate",
                    favorite_count=6200,
                    view_count=18400,
                    is_featured=True,
                    is_hot=False,
                    status="published",
                    published_at=now - timedelta(days=2),
                ),
                ["gpt-4o", "office", "medium"],
            ),
            (
                "resume-match-optimizer",
                dict(
                    title="简历优化与岗位匹配",
                    summary="优化简历内容并匹配岗位要求，提升面试命中率。",
                    cover_icon="resume",
                    category_id=category_map["office"].id,
                    difficulty="intermediate",
                    favorite_count=5100,
                    view_count=15100,
                    is_featured=True,
                    is_hot=False,
                    status="published",
                    published_at=now - timedelta(days=3),
                ),
                ["gpt-4o", "job", "medium"],
            ),
            (
                "paper-outline-generator",
                dict(
                    title="论文大纲生成器",
                    summary="根据主题快速生成论文大纲与结构。",
                    cover_icon="document",
                    category_id=category_map["writing"].id,
                    difficulty="beginner",
                    favorite_count=2100,
                    view_count=9200,
                    is_featured=False,
                    is_hot=False,
                    status="published",
                    published_at=now - timedelta(days=4),
                ),
                ["gpt-4o", "academic"],
            ),
            (
                "excel-data-helper",
                dict(
                    title="Excel 数据分析助手",
                    summary="自动分析数据，生成图表与洞察。",
                    cover_icon="chart",
                    category_id=category_map["office"].id,
                    difficulty="beginner",
                    favorite_count=1800,
                    view_count=8400,
                    is_featured=False,
                    is_hot=False,
                    status="published",
                    published_at=now - timedelta(days=5),
                ),
                ["gpt-4o", "excel"],
            ),
            (
                "prd-generator",
                dict(
                    title="产品需求文档生成",
                    summary="一键生成结构完整、清晰的 PRD。",
                    cover_icon="document",
                    category_id=category_map["office"].id,
                    difficulty="beginner",
                    favorite_count=1600,
                    view_count=7800,
                    is_featured=False,
                    is_hot=False,
                    status="published",
                    published_at=now - timedelta(days=6),
                ),
                ["gpt-4o", "product"],
            ),
            (
                "midjourney-prompt-optimizer",
                dict(
                    title="Midjourney 提示词优化",
                    summary="优化提示词，生成更高质量的图像。",
                    cover_icon="cube",
                    category_id=category_map["design"].id,
                    difficulty="intermediate",
                    favorite_count=1500,
                    view_count=7100,
                    is_featured=False,
                    is_hot=True,
                    status="published",
                    published_at=now - timedelta(days=7),
                ),
                ["midjourney", "design"],
            ),
            (
                "email-polisher",
                dict(
                    title="邮件润色助手",
                    summary="让邮件表达更专业、简洁且高效。",
                    cover_icon="email",
                    category_id=category_map["office"].id,
                    difficulty="beginner",
                    favorite_count=1300,
                    view_count=6200,
                    is_featured=False,
                    is_hot=False,
                    status="published",
                    published_at=now - timedelta(days=8),
                ),
                ["gpt-4o", "email"],
            ),
            (
                "short-video-script",
                dict(
                    title="短视频脚本创作",
                    summary="围绕选题快速生成短视频脚本与分镜。",
                    cover_icon="play",
                    category_id=category_map["video"].id,
                    difficulty="intermediate",
                    favorite_count=1200,
                    view_count=6000,
                    is_featured=False,
                    is_hot=False,
                    status="published",
                    published_at=now - timedelta(days=9),
                ),
                ["gpt-4o", "video"],
            ),
            (
                "code-comment-generator",
                dict(
                    title="代码注释生成",
                    summary="自动补充代码注释，帮助理解与维护。",
                    cover_icon="code-block",
                    category_id=category_map["coding"].id,
                    difficulty="intermediate",
                    favorite_count=1100,
                    view_count=5400,
                    is_featured=False,
                    is_hot=False,
                    status="published",
                    published_at=now - timedelta(days=10),
                ),
                ["gpt-4o", "coding"],
            ),
            (
                "social-calendar-generator",
                dict(
                    title="社媒文案日历生成",
                    summary="生成一周社媒文案与发布节奏建议。",
                    cover_icon="calendar",
                    category_id=category_map["marketing"].id,
                    difficulty="beginner",
                    favorite_count=987,
                    view_count=4300,
                    is_featured=False,
                    is_hot=False,
                    status="published",
                    published_at=now - timedelta(days=11),
                ),
                ["gpt-4o", "social"],
            ),
        ]

        for slug, payload, tag_slugs in skills:
            skill = get_or_create_skill(db, slug=slug, **payload)
            for tag_slug in tag_slugs:
                ensure_skill_tag(db, skill.id, tag_map[tag_slug].id)

        tutorials = [
            (
                "prompt-basic",
                dict(
                    title="零基础学会写 Prompt",
                    summary="从提示词基础到进阶技巧，写出更聪明的 Prompt，让 AI 更懂你。",
                    read_time_minutes=20,
                    is_beginner=True,
                    is_featured=True,
                    status="published",
                    published_at=now - timedelta(days=1),
                ),
            ),
            (
                "ai-office-productivity",
                dict(
                    title="如何用 AI 提升办公效率",
                    summary="掌握 AI 在文档、表格、PPT 等场景的高效应用方法。",
                    read_time_minutes=25,
                    is_beginner=True,
                    is_featured=False,
                    status="published",
                    published_at=now - timedelta(days=2),
                ),
            ),
            (
                "personal-ai-workflow",
                dict(
                    title="从 0 到 1 搭建个人 AI 工作流",
                    summary="学习搭建自动化工作流，打造专属 AI 助手。",
                    read_time_minutes=35,
                    is_beginner=True,
                    is_featured=False,
                    status="published",
                    published_at=now - timedelta(days=3),
                ),
            ),
        ]

        for slug, payload in tutorials:
            get_or_create_tutorial(db, slug=slug, **payload)

        upsert_homepage_stats(
            db,
            skill_favorites=10000,
            quality_templates=2000,
            monthly_visits=50000,
            beginner_tutorials=30,
            is_active=True,
        )

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
