from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.modules.skill.models import Skill, SkillTag, Tag


TYPE_TAGS = {
    "prompt": ("提示词", "prompt"),
    "workflow": ("工作流", "workflow"),
    "tutorial": ("教程", "tutorial"),
    "tool_config": ("工具配置", "tool-config"),
    "agent": ("Agent", "agent"),
}

SCENE_TAGS = {
    "xiaohongshu": ("小红书", "xiaohongshu"),
    "short-video": ("短视频", "short-video"),
    "resume": ("简历", "resume"),
    "ppt": ("PPT", "ppt"),
    "excel": ("Excel", "excel"),
    "seo": ("SEO", "seo"),
    "ecommerce": ("电商", "ecommerce"),
    "social-media": ("社媒", "social-media"),
    "paper": ("论文", "paper"),
    "meeting": ("会议", "meeting"),
    "office": ("办公", "office"),
    "image": ("图片", "image"),
    "video": ("视频", "video"),
    "data": ("数据分析", "data-analysis"),
    "automation": ("自动化", "automation"),
    "development": ("编程开发", "development"),
}

SKILL_TAG_PAIRS: Dict[str, List[str]] = {
    "xiaohongshu-title-generator": ["xiaohongshu", "prompt"],
    "python-code-explainer": ["development", "tool-config"],
    "excel-data-analysis-assistant": ["excel", "workflow"],
    "article-polisher": ["prompt"],
    "midjourney-prompt-generator": ["image", "prompt"],
    "resume-optimizer-master": ["resume", "prompt"],
    "ppt-outline-generator": ["ppt", "workflow"],
    "short-video-script-creator": ["short-video", "prompt"],
    "automation-workflow-design": ["automation", "workflow"],
    "meeting-notes-assistant": ["meeting", "workflow"],
    "prd-generator": ["workflow"],
    "email-polisher": ["prompt"],
    "paper-outline-generator": ["paper", "tutorial"],
    "social-content-calendar-generator": ["social-media", "workflow"],
    "code-comment-generator": ["development", "tool-config"],
    "seo-title-generator": ["seo", "prompt"],
    "ecommerce-detail-copy-generator": ["ecommerce", "prompt"],
    "study-plan-assistant": ["tutorial"],
    "interview-qa-simulator": ["resume", "agent"],
    "ai-weekly-report-generator": ["workflow"],
    "xlsx": ["excel", "workflow"],
    "pdf": ["workflow"],
    "pptx": ["ppt", "workflow"],
    "video-downloader": ["video", "workflow"],
    "webapp-testing": ["development", "workflow"],
    "web-artifacts-builder": ["development", "workflow"],
    "theme-factory": ["image", "prompt"],
    "twitter-algorithm-optimizer": ["social-media", "workflow"],
    "tailored-resume-generator": ["resume", "prompt"],
    "slack-gif-creator": ["image", "workflow"],
    "skill-share": ["workflow"],
    "skill-creator": ["prompt"],
    "raffle-winner-picker": ["workflow"],
    "meeting-insights-analyzer": ["meeting", "workflow"],
    "mcp-builder": ["development", "workflow"],
    "lead-research-assistant": ["workflow"],
    "langsmith-fetch": ["development", "agent"],
    "invoice-organizer": ["office", "workflow"],
    "internal-comms": ["office", "prompt"],
    "image-enhancer": ["image", "prompt"],
}


def ensure_tag(db, *, name: str, slug: str, tag_type: str) -> Tag:
    tag = db.scalar(
        select(Tag).where(
            Tag.slug == slug,
            Tag.type == tag_type,
            Tag.deleted_at.is_(None),
        )
    )
    if tag is not None:
        return tag

    tag = Tag(
        name=name,
        slug=slug,
        type=tag_type,
        is_enabled=True,
        sort_order=0,
        skill_count=0,
    )
    db.add(tag)
    db.flush()
    return tag


def infer_scene_slugs(skill: Skill) -> List[str]:
    explicit = SKILL_TAG_PAIRS.get(skill.slug, [])
    scene_slugs = [item for item in explicit if item in SCENE_TAGS]
    if scene_slugs:
        return scene_slugs

    haystack = " ".join(
        [
            skill.slug or "",
            skill.title or "",
            skill.summary or "",
            skill.search_keywords or "",
            skill.use_case or "",
        ]
    ).lower()

    keywords = {
        "xiaohongshu": ["小红书", "xiaohongshu"],
        "short-video": ["短视频", "video", "抖音"],
        "resume": ["简历", "resume", "interview", "求职"],
        "ppt": ["ppt", "演示", "slides"],
        "excel": ["excel", "表格", "xlsx"],
        "seo": ["seo"],
        "ecommerce": ["电商", "ecommerce"],
        "social-media": ["社媒", "social", "twitter", "slack"],
        "paper": ["论文", "paper", "academic"],
        "meeting": ["会议", "meeting"],
        "office": ["办公", "office", "邮件", "internal"],
        "image": ["图片", "图像", "midjourney", "image", "视觉"],
        "video": ["视频", "video"],
        "data": ["数据", "analysis", "analytics"],
        "automation": ["自动化", "automation", "workflow"],
        "development": ["编程", "代码", "python", "webapp", "mcp", "langsmith", "developer"],
    }

    result: List[str] = []
    for slug, terms in keywords.items():
        if any(term.lower() in haystack for term in terms):
            result.append(slug)
            break
    return result


def collect_tag_defs(skill: Skill) -> List[tuple[str, str, str]]:
    results: List[tuple[str, str, str]] = []

    explicit = SKILL_TAG_PAIRS.get(skill.slug, [])
    for scene_slug in explicit:
        if scene_slug in SCENE_TAGS:
            name, slug = SCENE_TAGS[scene_slug]
            results.append((name, slug, "scene"))

    type_name, type_slug = TYPE_TAGS.get(skill.type or "", ("类型", "type"))
    results.append((type_name, type_slug, "type"))

    if not any(item[2] == "scene" for item in results):
        for scene_slug in infer_scene_slugs(skill):
            if scene_slug in SCENE_TAGS:
                name, slug = SCENE_TAGS[scene_slug]
                results.append((name, slug, "scene"))

    deduped: List[tuple[str, str, str]] = []
    seen = set()
    for item in results:
        key = (item[1], item[2])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def main() -> None:
    db = SessionLocal()
    try:
        skills: Sequence[Skill] = db.scalars(
            select(Skill).where(
                Skill.deleted_at.is_(None),
                Skill.status == "published",
            )
        ).all()

        db.execute(
            delete(SkillTag).where(
                SkillTag.skill_id.in_([skill.id for skill in skills])
            )
        )
        db.flush()

        inserted = 0
        touched_skills = 0
        for skill in skills:
            tag_defs = collect_tag_defs(skill)
            if not tag_defs:
                continue
            touched_skills += 1
            for name, slug, tag_type in tag_defs:
                tag = ensure_tag(db, name=name, slug=slug, tag_type=tag_type)
                db.add(SkillTag(skill_id=skill.id, tag_id=tag.id))
                inserted += 1

        db.commit()
        print(f"backfilled_skill_tags skills={touched_skills} links={inserted}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
