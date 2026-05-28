from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.modules.category.models import Category
from app.modules.homepage.models import HomepageStats
from app.modules.skill.models import Skill, SkillTag, Tag
from app.modules.tutorial.models import Tutorial


def main() -> None:
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    try:
        db.execute(delete(SkillTag))
        db.execute(delete(Skill))
        db.execute(delete(Tag))
        db.execute(delete(Tutorial))
        db.execute(delete(Category))
        db.execute(delete(HomepageStats))

        categories = [
            Category(name="写作", slug="writing", icon="pen", color="blue", description="文案写作、标题生成、内容润色等", skill_count=2345, sort_order=1),
            Category(name="编程", slug="coding", icon="code", color="green", description="代码生成、调试、解释与优化", skill_count=2128, sort_order=2),
            Category(name="办公", slug="office", icon="briefcase", color="orange", description="文档处理、数据分析、PPT 等效率工具", skill_count=2256, sort_order=3),
            Category(name="设计", slug="design", icon="palette", color="purple", description="图像生成、UI 设计、创意视觉等", skill_count=1789, sort_order=4),
            Category(name="营销", slug="marketing", icon="megaphone", color="rose", description="社媒运营、广告文案、用户增长等", skill_count=1654, sort_order=5),
            Category(name="学习", slug="learning", icon="graduation", color="indigo", description="知识问答、笔记总结、学习规划等", skill_count=1402, sort_order=6),
            Category(name="视频", slug="video", icon="play", color="cyan", description="脚本创作、分镜、剪辑辅助", skill_count=1210, sort_order=7),
            Category(name="自动化", slug="automation", icon="robot", color="emerald", description="工作流编排、Agent、任务串联", skill_count=1098, sort_order=8),
        ]
        db.add_all(categories)
        db.flush()

        category_map = {item.slug: item for item in db.scalars(select(Category)).all()}

        tags = [
            Tag(name="GPT-4o", slug="gpt-4o", type="model", sort_order=1),
            Tag(name="Midjourney", slug="midjourney", type="model", sort_order=2),
            Tag(name="小红书", slug="xiaohongshu", type="scene", sort_order=10),
            Tag(name="办公", slug="office", type="scene", sort_order=11),
            Tag(name="求职", slug="job", type="scene", sort_order=12),
            Tag(name="学术", slug="academic", type="scene", sort_order=13),
            Tag(name="Excel", slug="excel", type="scene", sort_order=14),
            Tag(name="产品", slug="product", type="scene", sort_order=15),
            Tag(name="设计", slug="design", type="scene", sort_order=16),
            Tag(name="邮件", slug="email", type="scene", sort_order=17),
            Tag(name="视频", slug="video", type="scene", sort_order=18),
            Tag(name="编程", slug="coding", type="scene", sort_order=19),
            Tag(name="社媒", slug="social", type="scene", sort_order=20),
            Tag(name="简单", slug="easy", type="difficulty", sort_order=30),
            Tag(name="中等", slug="medium", type="difficulty", sort_order=31),
        ]
        db.add_all(tags)
        db.flush()

        tag_map = {item.slug: item for item in db.scalars(select(Tag)).all()}

        skills = [
            Skill(
                title="小红书爆款标题生成",
                slug="xiaohongshu-title-generator",
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
            Skill(
                title="会议纪要整理助手",
                slug="meeting-notes-assistant",
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
            Skill(
                title="简历优化与岗位匹配",
                slug="resume-match-optimizer",
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
            Skill(
                title="论文大纲生成器",
                slug="paper-outline-generator",
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
            Skill(
                title="Excel 数据分析助手",
                slug="excel-data-helper",
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
            Skill(
                title="产品需求文档生成",
                slug="prd-generator",
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
            Skill(
                title="Midjourney 提示词优化",
                slug="midjourney-prompt-optimizer",
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
            Skill(
                title="邮件润色助手",
                slug="email-polisher",
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
            Skill(
                title="短视频脚本创作",
                slug="short-video-script",
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
            Skill(
                title="代码注释生成",
                slug="code-comment-generator",
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
            Skill(
                title="社媒文案日历生成",
                slug="social-calendar-generator",
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
        ]
        db.add_all(skills)
        db.flush()

        skill_map = {item.slug: item for item in db.scalars(select(Skill)).all()}

        skill_tags = [
            SkillTag(skill_id=skill_map["xiaohongshu-title-generator"].id, tag_id=tag_map["gpt-4o"].id),
            SkillTag(skill_id=skill_map["xiaohongshu-title-generator"].id, tag_id=tag_map["xiaohongshu"].id),
            SkillTag(skill_id=skill_map["xiaohongshu-title-generator"].id, tag_id=tag_map["easy"].id),
            SkillTag(skill_id=skill_map["meeting-notes-assistant"].id, tag_id=tag_map["gpt-4o"].id),
            SkillTag(skill_id=skill_map["meeting-notes-assistant"].id, tag_id=tag_map["office"].id),
            SkillTag(skill_id=skill_map["meeting-notes-assistant"].id, tag_id=tag_map["medium"].id),
            SkillTag(skill_id=skill_map["resume-match-optimizer"].id, tag_id=tag_map["gpt-4o"].id),
            SkillTag(skill_id=skill_map["resume-match-optimizer"].id, tag_id=tag_map["job"].id),
            SkillTag(skill_id=skill_map["resume-match-optimizer"].id, tag_id=tag_map["medium"].id),
            SkillTag(skill_id=skill_map["paper-outline-generator"].id, tag_id=tag_map["gpt-4o"].id),
            SkillTag(skill_id=skill_map["paper-outline-generator"].id, tag_id=tag_map["academic"].id),
            SkillTag(skill_id=skill_map["excel-data-helper"].id, tag_id=tag_map["gpt-4o"].id),
            SkillTag(skill_id=skill_map["excel-data-helper"].id, tag_id=tag_map["excel"].id),
            SkillTag(skill_id=skill_map["prd-generator"].id, tag_id=tag_map["gpt-4o"].id),
            SkillTag(skill_id=skill_map["prd-generator"].id, tag_id=tag_map["product"].id),
            SkillTag(skill_id=skill_map["midjourney-prompt-optimizer"].id, tag_id=tag_map["midjourney"].id),
            SkillTag(skill_id=skill_map["midjourney-prompt-optimizer"].id, tag_id=tag_map["design"].id),
            SkillTag(skill_id=skill_map["email-polisher"].id, tag_id=tag_map["gpt-4o"].id),
            SkillTag(skill_id=skill_map["email-polisher"].id, tag_id=tag_map["email"].id),
            SkillTag(skill_id=skill_map["short-video-script"].id, tag_id=tag_map["gpt-4o"].id),
            SkillTag(skill_id=skill_map["short-video-script"].id, tag_id=tag_map["video"].id),
            SkillTag(skill_id=skill_map["code-comment-generator"].id, tag_id=tag_map["gpt-4o"].id),
            SkillTag(skill_id=skill_map["code-comment-generator"].id, tag_id=tag_map["coding"].id),
            SkillTag(skill_id=skill_map["social-calendar-generator"].id, tag_id=tag_map["gpt-4o"].id),
            SkillTag(skill_id=skill_map["social-calendar-generator"].id, tag_id=tag_map["social"].id),
        ]
        db.add_all(skill_tags)

        tutorials = [
            Tutorial(
                title="零基础学会写 Prompt",
                slug="prompt-basic",
                summary="从提示词基础到进阶技巧，写出更聪明的 Prompt，让 AI 更懂你。",
                chapter_count=5,
                duration_minutes=20,
                is_beginner=True,
                is_featured=True,
                status="published",
                published_at=now - timedelta(days=1),
            ),
            Tutorial(
                title="如何用 AI 提升办公效率",
                slug="ai-office-productivity",
                summary="掌握 AI 在文档、表格、PPT 等场景的高效应用方法。",
                chapter_count=6,
                duration_minutes=25,
                is_beginner=True,
                is_featured=False,
                status="published",
                published_at=now - timedelta(days=2),
            ),
            Tutorial(
                title="从 0 到 1 搭建个人 AI 工作流",
                slug="personal-ai-workflow",
                summary="学习搭建自动化工作流，打造专属 AI 助手。",
                chapter_count=7,
                duration_minutes=35,
                is_beginner=True,
                is_featured=False,
                status="published",
                published_at=now - timedelta(days=3),
            ),
        ]
        db.add_all(tutorials)

        db.add(
            HomepageStats(
                skill_favorites=10000,
                quality_templates=2000,
                monthly_visits=50000,
                beginner_tutorials=30,
                is_active=True,
            )
        )

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
