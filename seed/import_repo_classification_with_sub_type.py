from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import delete, func, select

from app.core.database import SessionLocal
from app.modules.category.models import Category
from app.modules.github_skills.models import SkillGithubSource
from app.modules.skill.models import Skill, SkillCategoryRelation, SkillTag, Tag


ROOT_DIR = Path(__file__).resolve().parents[3]
SOURCE_FILE = ROOT_DIR / "repo_classification_with_sub_type" / "repo_classification_with_sub_type.json"

DOMAIN_DEFS = {
    "编程开发": {
        "slug": "coding",
        "icon": "browse",
        "color": "green",
        "description": "AI 编程、Agent 开发、自动化与工程工作流。",
    },
    "数据办公": {
        "slug": "data-office",
        "icon": "tool",
        "color": "orange",
        "description": "办公协作、数据处理、知识整理与企业工作台能力。",
    },
    "投资金融": {
        "slug": "finance-investing",
        "icon": "prompt",
        "color": "rose",
        "description": "投研分析、交易研究与金融辅助能力。",
    },
    "产品运营": {
        "slug": "product-operations",
        "icon": "prompt",
        "color": "rose",
        "description": "产品规划、PRD、项目管理与市场研究能力。",
    },
    "安全工具": {
        "slug": "security-tools",
        "icon": "agent",
        "color": "emerald",
        "description": "Agent 安全、沙箱运行、漏洞检测与防护能力。",
    },
    "教育学习": {
        "slug": "education-learning",
        "icon": "tutorial",
        "color": "indigo",
        "description": "学习研究、知识问答、论文写作与教育辅助能力。",
    },
    "生活助手": {
        "slug": "life-assistant",
        "icon": "tool",
        "color": "cyan",
        "description": "求职、个人助理、角色模拟与生活效率能力。",
    },
    "设计创意": {
        "slug": "design-creative",
        "icon": "browse",
        "color": "purple",
        "description": "设计系统、UI/UX 与创意生产力能力。",
    },
}

RESOURCE_TYPE_TO_SKILL_TYPE = {
    "Prompt": "prompt",
    "Skill": "tool_config",
    "Workflow": "workflow",
    "Agent 运行平台": "agent",
    "开发者框架": "tutorial",
}

SKILL_TYPE_TO_COVER_ICON = {
    "prompt": "prompt",
    "tool_config": "tool",
    "workflow": "workflow",
    "agent": "agent",
    "tutorial": "tutorial",
}

DIFFICULTY_NAME = "进阶"
DIFFICULTY_SLUG = "intermediate"


def slugify(value: str, *, fallback: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", (value or "").strip().lower()).strip("-")
    return slug or fallback


def build_unique_category_slug(db, raw_value: str, existing_category_id: Optional[object]) -> str:
    base_slug = slugify(raw_value, fallback="category")[:72]
    slug = base_slug
    suffix = 2
    while True:
        existing = db.scalar(select(Category).where(Category.slug == slug))
        if existing is None or existing.id == existing_category_id:
            return slug
        slug = f"{base_slug[:76]}-{suffix}"[:80]
        suffix += 1


def build_unique_tag_slug(db, raw_value: str, tag_type: str, existing_tag_id: Optional[object]) -> str:
    base_slug = slugify(raw_value, fallback=tag_type)[:72]
    slug = base_slug
    suffix = 2
    while True:
        existing = db.scalar(select(Tag).where(Tag.slug == slug))
        if existing is None or existing.id == existing_tag_id:
            return slug
        if existing.type == tag_type and existing.deleted_at is None:
            return slug
        slug = f"{base_slug[:68]}-{suffix}"[:80]
        suffix += 1


def build_unique_skill_slug(db, raw_value: str, existing_skill_id: Optional[object]) -> str:
    base_slug = slugify(raw_value, fallback="github-skill")[:150]
    slug = base_slug
    suffix = 2
    while True:
        existing = db.scalar(select(Skill).where(Skill.slug == slug))
        if existing is None or existing.id == existing_skill_id:
            return slug
        slug = f"{base_slug[:156]}-{suffix}"[:160]
        suffix += 1


def ensure_category(db, domain_name: str) -> Category:
    definition = DOMAIN_DEFS.get(domain_name, {})
    preferred_slug = definition.get("slug") or domain_name

    category = db.scalar(
        select(Category).where(
            Category.slug == slugify(preferred_slug, fallback="category"),
            Category.deleted_at.is_(None),
        )
    )
    if category is None:
        category = db.scalar(
            select(Category).where(
                Category.name == domain_name,
                Category.deleted_at.is_(None),
            )
        )

    if category is None:
        category = Category(
            name=domain_name[:50],
            slug=build_unique_category_slug(db, preferred_slug, None),
            icon=str(definition.get("icon") or "browse")[:50],
            color=str(definition.get("color") or "green")[:50],
            description=str(definition.get("description") or f"{domain_name} 相关 GitHub 资源。")[:255],
            skill_count=0,
            is_enabled=True,
            sort_order=0,
        )
        db.add(category)
        db.flush()
        return category

    category.name = domain_name[:50]
    category.slug = build_unique_category_slug(db, preferred_slug, category.id)
    category.icon = str(definition.get("icon") or category.icon or "browse")[:50]
    category.color = str(definition.get("color") or category.color or "green")[:50]
    category.description = str(definition.get("description") or category.description or f"{domain_name} 相关 GitHub 资源。")[:255]
    category.is_enabled = True
    db.flush()
    return category


def ensure_tag(db, *, name: str, tag_type: str) -> Tag:
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("tag name is empty")

    slug = slugify(cleaned, fallback=tag_type)[:80]
    tag = db.scalar(
        select(Tag).where(
            Tag.slug == slug,
            Tag.type == tag_type,
            Tag.deleted_at.is_(None),
        )
    )
    if tag is None:
        tag = db.scalar(
            select(Tag).where(
                Tag.name == cleaned[:50],
                Tag.type == tag_type,
                Tag.deleted_at.is_(None),
            )
        )
    if tag is None:
        tag = Tag(
            name=cleaned[:50],
            slug=build_unique_tag_slug(db, cleaned, tag_type, None),
            type=tag_type,
            skill_count=0,
            is_enabled=True,
            sort_order=0,
        )
        db.add(tag)
        db.flush()
        return tag

    tag.name = cleaned[:50]
    tag.slug = build_unique_tag_slug(db, cleaned, tag_type, tag.id)
    tag.is_enabled = True
    db.flush()
    return tag


def resolve_skill(db, repo_full_name: str, source_url: str) -> Optional[Skill]:
    source = db.scalar(select(SkillGithubSource).where(SkillGithubSource.repo_full_name == repo_full_name))
    if source is not None and source.skill_id is not None:
        return db.get(Skill, source.skill_id)

    return db.scalar(
        select(Skill).where(
            Skill.deleted_at.is_(None),
            (Skill.source_name == repo_full_name) | (Skill.source_url == source_url),
        )
    )


def build_summary(repo_name: str, resource_type: str, domain: str, scenes: list[str]) -> str:
    scene_text = "、".join([item for item in scenes if item][:3])
    summary = f"{repo_name} 属于 {domain} 类 {resource_type} 资源"
    if scene_text:
        summary += f"，适用于 {scene_text}"
    return summary[:300]


def build_content(repo_full_name: str, resource_type: str, sub_type: str, domain: str, scenes: list[str], runtimes: list[str]) -> str:
    lines = [
        "## 资源信息",
        "",
        f"- 仓库：[{repo_full_name}](https://github.com/{repo_full_name})",
        f"- 主类型：{resource_type}",
        f"- 子类型：{sub_type or '未填写'}",
        f"- 领域分类：{domain}",
        f"- 使用场景：{'、'.join(scenes) if scenes else '未填写'}",
        f"- 适用工具：{'、'.join(runtimes) if runtimes else '未填写'}",
    ]
    return "\n".join(lines)


def build_search_keywords(repo_full_name: str, resource_type: str, sub_type: str, domain: str, scenes: list[str], runtimes: list[str]) -> str:
    parts = [repo_full_name, resource_type, sub_type, domain, *scenes, *runtimes]
    return ", ".join(dict.fromkeys([item.strip() for item in parts if item and item.strip()]))


def attach_tag(db, skill_id, tag_id) -> None:
    exists = db.scalar(select(SkillTag).where(SkillTag.skill_id == skill_id, SkillTag.tag_id == tag_id))
    if exists is None:
        db.add(SkillTag(skill_id=skill_id, tag_id=tag_id))


def upsert_skill(db, item: dict, now: datetime) -> tuple[Skill, bool]:
    repo_full_name = str(item.get("repo") or "").strip()
    if not repo_full_name or "/" not in repo_full_name:
        raise ValueError(f"invalid repo: {repo_full_name}")

    repo_name = repo_full_name.split("/")[-1]
    source_url = f"https://github.com/{repo_full_name}"
    resource_type = str(item.get("resource_type") or "Skill").strip() or "Skill"
    resource_sub_type = str(item.get("resource_sub_type") or "").strip()
    domain = str(item.get("domain") or "编程开发").strip() or "编程开发"
    scenes = [str(scene).strip() for scene in (item.get("use_scenes") or []) if str(scene).strip()]
    runtimes = [str(runtime).strip() for runtime in (item.get("runtimes") or []) if str(runtime).strip()]

    skill_type = RESOURCE_TYPE_TO_SKILL_TYPE.get(resource_type, "tool_config")
    category = ensure_category(db, domain)
    skill = resolve_skill(db, repo_full_name, source_url)
    created = skill is None

    if skill is None:
        skill = Skill(
            title=repo_name[:120],
            slug=build_unique_skill_slug(db, repo_full_name.replace("/", "-"), None),
            summary=build_summary(repo_name, resource_type, domain, scenes),
            content="",
            cover_icon=SKILL_TYPE_TO_COVER_ICON.get(skill_type, "tool"),
            category_id=category.id,
            difficulty="intermediate",
            type=skill_type,
            use_case=(scenes[0][:120] if scenes else None),
            search_keywords="",
            recommended_models=runtimes,
            source_type="github",
            source_url=source_url,
            source_name=repo_full_name,
            original_author=repo_full_name.split("/")[0],
            is_verified_source=True,
            last_source_synced_at=now,
            status="published",
            published_at=now,
        )
        db.add(skill)
        db.flush()

    skill.title = repo_name[:120]
    skill.slug = build_unique_skill_slug(db, repo_full_name.replace("/", "-"), skill.id)
    skill.summary = build_summary(repo_name, resource_type, domain, scenes)
    skill.content = build_content(repo_full_name, resource_type, resource_sub_type, domain, scenes, runtimes)
    skill.cover_icon = SKILL_TYPE_TO_COVER_ICON.get(skill_type, "tool")
    skill.category_id = category.id
    skill.difficulty = "intermediate"
    skill.type = skill_type
    skill.use_case = scenes[0][:120] if scenes else None
    skill.search_keywords = build_search_keywords(repo_full_name, resource_type, resource_sub_type, domain, scenes, runtimes)
    skill.recommended_models = runtimes
    skill.source_type = "github"
    skill.source_url = source_url
    skill.source_name = repo_full_name
    skill.original_author = repo_full_name.split("/")[0]
    skill.is_verified_source = True
    skill.last_source_synced_at = now
    skill.status = "published"
    skill.published_at = skill.published_at or now
    db.flush()

    db.execute(delete(SkillCategoryRelation).where(SkillCategoryRelation.skill_id == skill.id))
    db.execute(delete(SkillTag).where(SkillTag.skill_id == skill.id))
    db.flush()

    db.add(SkillCategoryRelation(skill_id=skill.id, category_id=category.id, is_primary=True))

    main_type_tag = ensure_tag(db, name=resource_type, tag_type="type")
    attach_tag(db, skill.id, main_type_tag.id)

    if resource_sub_type:
        sub_type_tag = ensure_tag(db, name=resource_sub_type, tag_type="type")
        attach_tag(db, skill.id, sub_type_tag.id)

    difficulty_tag = ensure_tag(db, name=DIFFICULTY_NAME, tag_type="difficulty")
    attach_tag(db, skill.id, difficulty_tag.id)

    for scene in scenes:
        scene_tag = ensure_tag(db, name=scene, tag_type="scene")
        attach_tag(db, skill.id, scene_tag.id)

    source = db.scalar(select(SkillGithubSource).where(SkillGithubSource.repo_full_name == repo_full_name))
    if source is None:
        source = SkillGithubSource(
            repo_full_name=repo_full_name,
            owner_login=repo_full_name.split("/")[0],
            repo_name=repo_name,
            github_url=source_url,
        )
        db.add(source)
        db.flush()

    source.skill_id = skill.id
    source.owner_login = repo_full_name.split("/")[0]
    source.repo_name = repo_name
    source.github_url = source_url
    source.clone_url = source_url + ".git"
    source.repo_description = skill.summary
    source.original_author = skill.original_author
    source.last_synced_at = now
    db.flush()

    return skill, created


def recalc_counts(db) -> None:
    category_counts = {
        category_id: count
        for category_id, count in db.execute(
            select(SkillCategoryRelation.category_id, func.count(SkillCategoryRelation.skill_id))
            .join(Skill, Skill.id == SkillCategoryRelation.skill_id)
            .where(
                Skill.deleted_at.is_(None),
                Skill.status == "published",
            )
            .group_by(SkillCategoryRelation.category_id)
        ).all()
    }
    for category in db.scalars(select(Category).where(Category.deleted_at.is_(None))).all():
        category.skill_count = int(category_counts.get(category.id, 0))

    tag_counts = {
        tag_id: count
        for tag_id, count in db.execute(
            select(SkillTag.tag_id, func.count(SkillTag.skill_id))
            .join(Skill, Skill.id == SkillTag.skill_id)
            .where(
                Skill.deleted_at.is_(None),
                Skill.status == "published",
            )
            .group_by(SkillTag.tag_id)
        ).all()
    }
    for tag in db.scalars(select(Tag).where(Tag.deleted_at.is_(None))).all():
        tag.skill_count = int(tag_counts.get(tag.id, 0))


def load_entries() -> list[dict]:
    return json.loads(SOURCE_FILE.read_text(encoding="utf-8"))


def main() -> None:
    entries = load_entries()
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    created_count = 0
    updated_count = 0
    domain_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()

    try:
        for item in entries:
            _, created = upsert_skill(db, item, now)
            if created:
                created_count += 1
            else:
                updated_count += 1
            domain_counter[str(item.get("domain") or "未分类")] += 1
            type_counter[str(item.get("resource_type") or "未知")] += 1

        recalc_counts(db)
        db.commit()

        print(
            json.dumps(
                {
                    "source_file": str(SOURCE_FILE),
                    "entry_count": len(entries),
                    "created": created_count,
                    "updated": updated_count,
                    "domains": dict(domain_counter),
                    "resource_types": dict(type_counter),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
