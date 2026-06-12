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
BUNDLE_DIR = ROOT_DIR / "repo_import_bundle_production"
SOURCE_FILE = BUNDLE_DIR / "repo_import_bundle_production.json"

RESOURCE_TYPE_TO_SKILL_TYPE = {
    "prompt": "prompt",
    "skill": "tool_config",
    "workflow": "workflow",
    "platform": "agent",
}

SKILL_TYPE_TO_COVER_ICON = {
    "prompt": "prompt",
    "tool_config": "tool",
    "workflow": "workflow",
    "agent": "agent",
    "tutorial": "tutorial",
}

CATEGORY_COLORS = [
    "green",
    "blue",
    "orange",
    "rose",
    "emerald",
    "indigo",
    "cyan",
    "purple",
]

DIFFICULTY_NAME = "进阶"


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


def ensure_category(db, *, name: str, sort_order: int) -> tuple[Category, bool]:
    cleaned = (name or "").strip() or "未分类"
    category = db.scalar(
        select(Category).where(
            Category.name == cleaned[:50],
            Category.deleted_at.is_(None),
        )
    )
    if category is None:
        slug = slugify(cleaned, fallback=f"category-{sort_order}")
        category = db.scalar(
            select(Category).where(
                Category.slug == slug,
                Category.deleted_at.is_(None),
            )
        )

    if category is None:
        category = Category(
            name=cleaned[:50],
            slug=build_unique_category_slug(db, cleaned, None),
            level=1,
            icon="browse",
            color=CATEGORY_COLORS[sort_order % len(CATEGORY_COLORS)],
            description=f"{cleaned} 相关 GitHub 资源"[:255],
            skill_count=0,
            is_enabled=True,
            sort_order=sort_order,
        )
        db.add(category)
        db.flush()
        return category, True

    category.name = cleaned[:50]
    category.slug = build_unique_category_slug(db, cleaned, category.id)
    category.level = 1
    category.icon = category.icon or "browse"
    category.color = category.color or CATEGORY_COLORS[sort_order % len(CATEGORY_COLORS)]
    category.description = (category.description or f"{cleaned} 相关 GitHub 资源")[:255]
    category.is_enabled = True
    if not category.sort_order:
        category.sort_order = sort_order
    db.flush()
    return category, False


def ensure_tag(db, *, name: str, tag_type: str, sort_order: int) -> tuple[Tag, bool]:
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
            sort_order=sort_order,
        )
        db.add(tag)
        db.flush()
        return tag, True

    tag.name = cleaned[:50]
    tag.slug = build_unique_tag_slug(db, cleaned, tag_type, tag.id)
    tag.is_enabled = True
    if not tag.sort_order:
        tag.sort_order = sort_order
    db.flush()
    return tag, False


def attach_tag(db, skill_id, tag_id) -> None:
    exists = db.scalar(select(SkillTag).where(SkillTag.skill_id == skill_id, SkillTag.tag_id == tag_id))
    if exists is None:
        db.add(SkillTag(skill_id=skill_id, tag_id=tag_id))


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


def build_summary(repo_name: str, resource_type_name: str, domains: list[str], scenes: list[str]) -> str:
    domain_text = "、".join(domains[:2]) if domains else "未分类"
    scene_text = "、".join(scenes[:3]) if scenes else "未标注场景"
    return f"{repo_name} 是 {resource_type_name} 资源，领域覆盖 {domain_text}，适用于 {scene_text}"[:300]


def build_content(
    *,
    repo_full_name: str,
    github_url: str,
    resource_type_name: str,
    verified: bool,
    note: str,
    domains: list[str],
    scenes: list[str],
    tools: list[str],
) -> str:
    lines = [
        "## 资源信息",
        "",
        f"- 仓库：[{repo_full_name}]({github_url})",
        f"- 资源类型：{resource_type_name}",
        f"- 是否验证：{'是' if verified else '否'}",
        f"- 领域分类：{'、'.join(domains) if domains else '未填写'}",
        f"- 使用场景：{'、'.join(scenes) if scenes else '未填写'}",
        f"- 适用工具：{'、'.join(tools) if tools else '未填写'}",
    ]
    if note:
        lines.extend(["", f"- 备注：{note}"])
    return "\n".join(lines)


def build_search_keywords(
    repo_full_name: str,
    resource_type_name: str,
    domains: list[str],
    scenes: list[str],
    tools: list[str],
) -> str:
    parts = [repo_full_name, resource_type_name, *domains, *scenes, *tools]
    return ", ".join(dict.fromkeys([item.strip() for item in parts if item and item.strip()]))


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


def load_bundle() -> dict:
    return json.loads(SOURCE_FILE.read_text(encoding="utf-8"))


def main() -> None:
    payload = load_bundle()
    now = datetime.now(timezone.utc)
    db = SessionLocal()

    resource_type_map = {
        int(item["resource_type_id"]): item
        for item in payload.get("resource_types", [])
    }
    domain_tag_map = {
        int(item["tag_id"]): item
        for item in payload.get("domain_tags", [])
    }
    scene_tag_map = {
        int(item["tag_id"]): item
        for item in payload.get("scene_tags", [])
    }
    tool_tag_map = {
        int(item["tag_id"]): item
        for item in payload.get("tool_tags", [])
    }

    repo_domain_links: dict[int, list[int]] = {}
    repo_scene_links: dict[int, list[int]] = {}
    repo_tool_links: dict[int, list[int]] = {}

    for row in payload.get("repo_domain_tags", []):
        repo_domain_links.setdefault(int(row["repo_id"]), []).append(int(row["tag_id"]))
    for row in payload.get("repo_scene_tags", []):
        repo_scene_links.setdefault(int(row["repo_id"]), []).append(int(row["tag_id"]))
    for row in payload.get("repo_tool_tags", []):
        repo_tool_links.setdefault(int(row["repo_id"]), []).append(int(row["tag_id"]))

    created_skills = 0
    updated_skills = 0
    created_categories = 0
    created_tags = Counter()
    repo_counter = Counter()

    try:
        difficulty_tag, difficulty_created = ensure_tag(db, name=DIFFICULTY_NAME, tag_type="difficulty", sort_order=0)
        if difficulty_created:
            created_tags["difficulty"] += 1

        for repo_row in payload.get("repositories", []):
            repo_id = int(repo_row["repo_id"])
            repo_full_name = str(repo_row["repo_full_name"]).strip()
            github_url = str(repo_row["github_url"]).strip()
            repo_name = repo_full_name.split("/")[-1]
            note = str(repo_row.get("note") or "").strip()
            is_verified = bool(int(repo_row.get("is_verified") or 0))

            resource_type_row = resource_type_map[int(repo_row["resource_type_id"])]
            resource_type_code = str(resource_type_row["code"]).strip().lower()
            resource_type_name = str(resource_type_row["name"]).strip()
            skill_type = RESOURCE_TYPE_TO_SKILL_TYPE.get(resource_type_code, "tool_config")

            domain_rows = [
                domain_tag_map[tag_id]
                for tag_id in repo_domain_links.get(repo_id, [])
                if tag_id in domain_tag_map
            ]
            scene_rows = [
                scene_tag_map[tag_id]
                for tag_id in repo_scene_links.get(repo_id, [])
                if tag_id in scene_tag_map
            ]
            tool_rows = [
                tool_tag_map[tag_id]
                for tag_id in repo_tool_links.get(repo_id, [])
                if tag_id in tool_tag_map
            ]

            domain_names = [str(item["tag_name"]).strip() for item in domain_rows if str(item["tag_name"]).strip()]
            scene_names = [str(item["tag_name"]).strip() for item in scene_rows if str(item["tag_name"]).strip()]
            tool_names = [str(item["tag_name"]).strip() for item in tool_rows if str(item["tag_name"]).strip()]

            primary_domain_name = domain_names[0] if domain_names else "未分类"
            primary_category, category_created = ensure_category(
                db,
                name=primary_domain_name,
                sort_order=int(domain_rows[0]["sort_order"]) if domain_rows else 0,
            )
            if category_created:
                created_categories += 1

            skill = resolve_skill(db, repo_full_name, github_url)
            created = skill is None

            if skill is None:
                skill = Skill(
                    title=repo_name[:120],
                    slug=build_unique_skill_slug(db, repo_full_name.replace("/", "-"), None),
                    summary=build_summary(repo_name, resource_type_name, domain_names, scene_names),
                    content="",
                    cover_icon=SKILL_TYPE_TO_COVER_ICON.get(skill_type, "tool"),
                    category_id=primary_category.id,
                    difficulty="intermediate",
                    type=skill_type,
                    use_case=(scene_names[0][:120] if scene_names else None),
                    search_keywords="",
                    recommended_models=tool_names,
                    source_type="github",
                    source_url=github_url,
                    source_name=repo_full_name,
                    original_author=repo_full_name.split("/")[0],
                    is_verified_source=is_verified,
                    last_source_synced_at=now,
                    status="published",
                    published_at=now,
                )
                db.add(skill)
                db.flush()

            skill.title = repo_name[:120]
            skill.slug = build_unique_skill_slug(db, repo_full_name.replace("/", "-"), skill.id)
            skill.summary = build_summary(repo_name, resource_type_name, domain_names, scene_names)
            skill.content = build_content(
                repo_full_name=repo_full_name,
                github_url=github_url,
                resource_type_name=resource_type_name,
                verified=is_verified,
                note=note,
                domains=domain_names,
                scenes=scene_names,
                tools=tool_names,
            )
            skill.cover_icon = SKILL_TYPE_TO_COVER_ICON.get(skill_type, "tool")
            skill.category_id = primary_category.id
            skill.difficulty = "intermediate"
            skill.type = skill_type
            skill.use_case = scene_names[0][:120] if scene_names else None
            skill.search_keywords = build_search_keywords(repo_full_name, resource_type_name, domain_names, scene_names, tool_names)
            skill.recommended_models = tool_names
            skill.source_type = "github"
            skill.source_url = github_url
            skill.source_name = repo_full_name
            skill.original_author = repo_full_name.split("/")[0]
            skill.is_verified_source = is_verified
            skill.last_source_synced_at = now
            skill.status = "published"
            skill.published_at = skill.published_at or now
            db.flush()

            db.execute(delete(SkillCategoryRelation).where(SkillCategoryRelation.skill_id == skill.id))
            db.execute(delete(SkillTag).where(SkillTag.skill_id == skill.id))
            db.flush()

            for domain_row in domain_rows:
                category, category_created = ensure_category(
                    db,
                    name=str(domain_row["tag_name"]).strip(),
                    sort_order=int(domain_row.get("sort_order") or 0),
                )
                if category_created:
                    created_categories += 1
                db.add(
                    SkillCategoryRelation(
                        skill_id=skill.id,
                        category_id=category.id,
                        is_primary=(category.name == primary_domain_name),
                    )
                )

            type_tag, type_created = ensure_tag(
                db,
                name=resource_type_name,
                tag_type="type",
                sort_order=int(resource_type_row.get("sort_order") or 0),
            )
            if type_created:
                created_tags["type"] += 1
            attach_tag(db, skill.id, type_tag.id)
            attach_tag(db, skill.id, difficulty_tag.id)

            for scene_row in scene_rows:
                scene_tag, scene_created = ensure_tag(
                    db,
                    name=str(scene_row["tag_name"]).strip(),
                    tag_type="scene",
                    sort_order=int(scene_row.get("sort_order") or 0),
                )
                if scene_created:
                    created_tags["scene"] += 1
                attach_tag(db, skill.id, scene_tag.id)

            for tool_row in tool_rows:
                tool_tag, tool_created = ensure_tag(
                    db,
                    name=str(tool_row["tag_name"]).strip(),
                    tag_type="tool",
                    sort_order=int(tool_row.get("sort_order") or 0),
                )
                if tool_created:
                    created_tags["tool"] += 1
                attach_tag(db, skill.id, tool_tag.id)

            source = db.scalar(select(SkillGithubSource).where(SkillGithubSource.repo_full_name == repo_full_name))
            if source is None:
                source = SkillGithubSource(
                    repo_full_name=repo_full_name,
                    owner_login=repo_full_name.split("/")[0],
                    repo_name=repo_name,
                    github_url=github_url,
                )
                db.add(source)
                db.flush()

            source.skill_id = skill.id
            source.owner_login = repo_full_name.split("/")[0]
            source.repo_name = repo_name
            source.github_url = github_url
            source.clone_url = github_url + ".git"
            source.repo_description = skill.summary
            source.original_author = skill.original_author
            source.last_synced_at = now
            db.flush()

            if created:
                created_skills += 1
            else:
                updated_skills += 1
            repo_counter[resource_type_name] += 1

        recalc_counts(db)
        db.commit()

        print(
            json.dumps(
                {
                    "source_file": str(SOURCE_FILE),
                    "repo_count": len(payload.get("repositories", [])),
                    "created_skills": created_skills,
                    "updated_skills": updated_skills,
                    "created_categories": created_categories,
                    "created_tags": dict(created_tags),
                    "resource_types": dict(repo_counter),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
