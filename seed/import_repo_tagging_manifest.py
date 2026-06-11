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


ROOT_DIR = Path(__file__).resolve().parents[2]
SOURCE_DIRS = (
    "repo_tagging_gorden_ppt",
    "repo_tagging_md",
    "repo_tagging_md_extra_3",
)

CATEGORY_DEFS = {
    "编程开发": {
        "slug": "programming-development",
        "icon": "browse",
        "color": "green",
        "description": "AI 编程、Agent 开发、代码工具与工程工作流。",
    },
    "产品运营": {
        "slug": "product-operations",
        "icon": "prompt",
        "color": "rose",
        "description": "产品、增长、运营与业务协同相关能力。",
    },
    "设计创意": {
        "slug": "design-creative",
        "icon": "browse",
        "color": "purple",
        "description": "设计、创意、界面与视觉生产力工具。",
    },
    "教育学习": {
        "slug": "education-learning",
        "icon": "tutorial",
        "color": "indigo",
        "description": "学习、研究、知识整理与教育辅助。",
    },
    "生活助手": {
        "slug": "life-assistant",
        "icon": "tool",
        "color": "cyan",
        "description": "日常效率、个人助理与生活场景工具。",
    },
    "数据办公": {
        "slug": "data-office",
        "icon": "tool",
        "color": "orange",
        "description": "数据处理、办公自动化与信息整理。",
    },
}

DIFFICULTY_TAG_DEFS = {
    "beginner": ("新手", "beginner"),
    "intermediate": ("进阶", "intermediate"),
    "advanced": ("专业", "advanced"),
}

ICON_BY_SKILL_TYPE = {
    "prompt": "prompt",
    "workflow": "workflow",
    "tutorial": "tutorial",
    "tool_config": "tool",
    "agent": "agent",
}


def slugify(value: str, *, fallback: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", (value or "").strip().lower()).strip("-")
    return slug or fallback


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    match = re.match(r"^---\n.*?\n---\n?", text, flags=re.DOTALL)
    if not match:
        return text
    return text[match.end() :]


def extract_section(markdown: str, heading: str) -> str:
    body = strip_frontmatter(markdown)
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)", flags=re.MULTILINE | re.DOTALL)
    match = pattern.search(body)
    if not match:
        return ""
    return match.group(1).strip()


def normalize_skill_type(type_slug: str, type_name: str) -> str:
    text = f"{type_slug} {type_name}".lower()
    if any(token in text for token in ("workflow", "flow", "harness", "pipeline", "orchestration")):
        return "workflow"
    if any(token in text for token in ("mcp", "cli", "tool", "sdk", "openclaw", "desktop", "web", "browser")):
        return "tool_config"
    if any(token in text for token in ("tutorial", "course", "learn", "education")):
        return "tutorial"
    if any(token in text for token in ("prompt", "skill", "template")):
        return "prompt"
    if any(token in text for token in ("agent", "bot", "assistant", "copilot", "ai")):
        return "agent"
    return "agent"


def build_content(item: dict, markdown_text: str) -> str:
    intro = extract_section(markdown_text, "中文介绍") or item.get("description") or ""
    lines = [
        "## 项目简介",
        "",
        intro.strip(),
        "",
        "## GitHub 信息",
        "",
        f"- 仓库：[{item['repo']}]({item['source_url']})",
        f"- 推荐分类：{item.get('category_name') or '未分类'}",
        f"- 推荐类型：{item.get('type_name') or item.get('type_slug') or '未标注'}",
        f"- 推荐状态：`{item.get('recommend_status') or 'approved'}`",
        f"- 难度：`{item.get('difficulty') or 'intermediate'}`",
        f"- 许可证：`{item.get('license') or 'unknown'}`",
        f"- 中文支持：`{item.get('language') or 'unknown'}`",
    ]

    scene_names = [str(name).strip() for name in item.get("scene_names") or [] if str(name).strip()]
    if scene_names:
        lines.extend(["", "## 适用场景", ""])
        lines.extend([f"- {name}" for name in scene_names])

    tag_slugs = [str(tag).strip() for tag in item.get("tag_slugs") or [] if str(tag).strip()]
    if tag_slugs:
        lines.extend(["", "## 关键词", "", ", ".join(tag_slugs)])

    review_notes = (item.get("review_notes") or "").strip()
    if review_notes:
        lines.extend(["", "## 备注", "", review_notes])

    return "\n".join(lines).strip()


def build_search_keywords(item: dict) -> str:
    parts: list[str] = []
    for key in ("repo", "title", "summary", "category_name", "type_name", "type_slug", "difficulty", "language", "license", "recommend_status"):
        value = str(item.get(key) or "").strip()
        if value:
            parts.append(value)
    parts.extend([str(name).strip() for name in item.get("scene_names") or [] if str(name).strip()])
    parts.extend([str(slug).strip() for slug in item.get("scene_slugs") or [] if str(slug).strip()])
    parts.extend([str(slug).strip() for slug in item.get("tag_slugs") or [] if str(slug).strip()])
    return ", ".join(dict.fromkeys(parts))


def pick_category_icon(normalized_type: str) -> str:
    if normalized_type == "prompt":
        return "prompt"
    if normalized_type == "workflow":
        return "workflow"
    if normalized_type == "tutorial":
        return "tutorial"
    if normalized_type == "tool_config":
        return "tool"
    if normalized_type == "agent":
        return "agent"
    return "browse"


def pick_category_color(category_name: str, normalized_type: str) -> str:
    if "设计" in category_name:
        return "purple"
    if "学习" in category_name or "教育" in category_name:
        return "indigo"
    if "办公" in category_name or "数据" in category_name:
        return "orange"
    if "运营" in category_name or "营销" in category_name or "金融" in category_name:
        return "rose"
    if "生活" in category_name:
        return "cyan"
    if normalized_type == "agent":
        return "emerald"
    return "green"


def build_unique_category_slug(db, raw_value: str, existing_category_id: Optional[object]) -> str:
    base_slug = slugify(raw_value, fallback="category")[:72]
    slug = base_slug
    suffix = 2
    while True:
        existing = db.scalar(select(Category).where(Category.slug == slug))
        if existing is None or existing.id == existing_category_id:
            return slug
        candidate = f"{base_slug}-{suffix}"
        slug = candidate[:80]
        suffix += 1


def ensure_category(db, category_name: str, preferred_slug: str, normalized_type: str) -> Category:
    definition = CATEGORY_DEFS.get(category_name) or {}
    target_slug = preferred_slug or definition.get("slug") or category_name

    category = db.scalar(
        select(Category).where(
            Category.slug == slugify(target_slug, fallback="category"),
            Category.deleted_at.is_(None),
        )
    )
    if category is None:
        category = db.scalar(
            select(Category).where(
                Category.name == category_name,
                Category.deleted_at.is_(None),
            )
        )

    if category is None:
        category = Category(
            name=category_name,
            slug=build_unique_category_slug(db, target_slug, None),
            icon=str(definition.get("icon") or pick_category_icon(normalized_type))[:50],
            color=str(definition.get("color") or pick_category_color(category_name, normalized_type))[:50],
            description=str(definition.get("description") or f"{category_name} 相关 GitHub 仓库能力集合。")[:255],
            skill_count=0,
            is_enabled=True,
            sort_order=0,
        )
        db.add(category)
        db.flush()
        return category

    category.name = category_name
    category.slug = build_unique_category_slug(db, target_slug, category.id)
    category.icon = str(definition.get("icon") or pick_category_icon(normalized_type))[:50]
    category.color = str(definition.get("color") or pick_category_color(category_name, normalized_type))[:50]
    category.description = str(definition.get("description") or f"{category_name} 相关 GitHub 仓库能力集合。")[:255]
    category.is_enabled = True
    db.flush()
    return category


def ensure_tag(db, *, name: str, preferred_slug: str, tag_type: str) -> Tag:
    base_slug = slugify(preferred_slug or name, fallback=tag_type)
    slug = base_slug[:80]
    suffix = 2

    while True:
        tag = db.scalar(select(Tag).where(Tag.slug == slug))
        if tag is None:
            tag = Tag(
                name=name[:50],
                slug=slug,
                type=tag_type,
                skill_count=0,
                is_enabled=True,
                sort_order=0,
            )
            db.add(tag)
            db.flush()
            return tag
        if tag.type == tag_type and tag.deleted_at is None:
            if tag.name != name[:50]:
                tag.name = name[:50]
                db.flush()
            return tag
        candidate = f"{base_slug}-{tag_type}-{suffix}"
        slug = candidate[:80]
        suffix += 1


def build_unique_skill_slug(db, raw_value: str, existing_skill_id: Optional[object]) -> str:
    base_slug = slugify(raw_value, fallback="github-skill")[:150]
    slug = base_slug
    suffix = 2
    while True:
        existing = db.scalar(select(Skill).where(Skill.slug == slug))
        if existing is None or existing.id == existing_skill_id:
            return slug
        candidate = f"{base_slug}-{suffix}"
        slug = candidate[:160]
        suffix += 1


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


def upsert_skill(db, item: dict, markdown_text: str, source_dir: str, now: datetime) -> tuple[Skill, bool]:
    repo_full_name = str(item["repo"]).strip()
    source_url = str(item["source_url"]).strip()
    normalized_type = normalize_skill_type(str(item.get("type_slug") or ""), str(item.get("type_name") or ""))
    category = ensure_category(
        db,
        str(item.get("category_name") or "编程开发").strip(),
        str(item.get("category_slug") or "").strip(),
        normalized_type,
    )
    skill = resolve_skill(db, repo_full_name, source_url)
    created = skill is None

    if skill is None:
        skill = Skill(
            title=str(item.get("title") or repo_full_name.split("/")[-1])[:120],
            slug=build_unique_skill_slug(db, repo_full_name.replace("/", "-"), None),
            summary=str(item.get("summary") or item.get("description") or repo_full_name)[:300],
            content="",
            cover_icon=ICON_BY_SKILL_TYPE[normalized_type],
            category_id=category.id,
            difficulty=str(item.get("difficulty") or "intermediate")[:30],
            type=normalized_type,
            use_case=((item.get("scene_names") or [""])[0] or "")[:120] or None,
            search_keywords="",
            recommended_models=[],
            source_type="github",
            source_url=source_url,
            source_name=repo_full_name,
            original_author=repo_full_name.split("/")[0],
            license=str(item.get("license") or "")[:100] or None,
            is_verified_source=True,
            last_source_synced_at=now,
            status="published",
            published_at=now,
            is_featured=False,
            is_hot=False,
        )
        db.add(skill)
        db.flush()

    skill.title = str(item.get("title") or repo_full_name.split("/")[-1])[:120]
    skill.slug = build_unique_skill_slug(db, repo_full_name.replace("/", "-"), skill.id)
    skill.summary = str(item.get("summary") or item.get("description") or repo_full_name)[:300]
    skill.content = build_content(item, markdown_text)
    skill.cover_icon = ICON_BY_SKILL_TYPE[normalized_type]
    skill.category_id = category.id
    skill.difficulty = str(item.get("difficulty") or "intermediate")[:30]
    skill.type = normalized_type
    skill.use_case = ((item.get("scene_names") or [""])[0] or "")[:120] or None
    skill.search_keywords = build_search_keywords(item)
    skill.source_type = "github"
    skill.source_url = source_url
    skill.source_name = repo_full_name
    skill.original_author = repo_full_name.split("/")[0]
    skill.license = str(item.get("license") or "")[:100] or None
    skill.is_verified_source = True
    skill.last_source_synced_at = now
    skill.status = "published"
    skill.published_at = skill.published_at or now
    db.flush()

    db.execute(delete(SkillCategoryRelation).where(SkillCategoryRelation.skill_id == skill.id))
    db.execute(delete(SkillTag).where(SkillTag.skill_id == skill.id))
    db.flush()

    db.add(SkillCategoryRelation(skill_id=skill.id, category_id=category.id, is_primary=True))

    attached_tag_ids: set[object] = set()
    raw_type_name = str(item.get("type_name") or normalized_type).strip()
    raw_type_slug = str(item.get("type_slug") or normalized_type).strip()
    type_tag_id = ensure_tag(db, name=raw_type_name[:50], preferred_slug=raw_type_slug or raw_type_name, tag_type="type").id
    if type_tag_id not in attached_tag_ids:
        db.add(SkillTag(skill_id=skill.id, tag_id=type_tag_id))
        attached_tag_ids.add(type_tag_id)

    difficulty_key = str(item.get("difficulty") or "intermediate").strip().lower()
    difficulty_name, difficulty_slug = DIFFICULTY_TAG_DEFS.get(difficulty_key, DIFFICULTY_TAG_DEFS["intermediate"])
    difficulty_tag_id = ensure_tag(db, name=difficulty_name, preferred_slug=difficulty_slug, tag_type="difficulty").id
    if difficulty_tag_id not in attached_tag_ids:
        db.add(SkillTag(skill_id=skill.id, tag_id=difficulty_tag_id))
        attached_tag_ids.add(difficulty_tag_id)

    scene_names = [str(name).strip() for name in item.get("scene_names") or [] if str(name).strip()]
    scene_slugs = [str(slug).strip() for slug in item.get("scene_slugs") or []]
    for index, scene_name in enumerate(scene_names):
        preferred_slug = scene_slugs[index] if index < len(scene_slugs) else ""
        tag = ensure_tag(db, name=scene_name[:50], preferred_slug=preferred_slug or scene_name, tag_type="scene")
        if tag.id in attached_tag_ids:
            continue
        db.add(SkillTag(skill_id=skill.id, tag_id=tag.id))
        attached_tag_ids.add(tag.id)

    # The public API only accepts scene/difficulty/type tag variants.
    # Store free-form repo tags under the existing "type" taxonomy to avoid response validation failures.
    for raw_tag in [str(tag).strip() for tag in item.get("tag_slugs") or [] if str(tag).strip()]:
        tag = ensure_tag(db, name=raw_tag[:50], preferred_slug=raw_tag, tag_type="type")
        if tag.id in attached_tag_ids:
            continue
        db.add(SkillTag(skill_id=skill.id, tag_id=tag.id))
        attached_tag_ids.add(tag.id)

    source = db.scalar(select(SkillGithubSource).where(SkillGithubSource.repo_full_name == repo_full_name))
    if source is None:
        source = SkillGithubSource(
            repo_full_name=repo_full_name,
            owner_login=repo_full_name.split("/")[0],
            repo_name=repo_full_name.split("/")[1],
            github_url=source_url,
        )
        db.add(source)
        db.flush()

    source.skill_id = skill.id
    source.owner_login = repo_full_name.split("/")[0]
    source.repo_name = repo_full_name.split("/")[1]
    source.github_url = source_url
    source.clone_url = source_url + ".git"
    source.repo_description = str(item.get("description") or item.get("summary") or "") or None
    source.license_key = str(item.get("license") or "") or None
    source.license_name = str(item.get("license") or "") or None
    source.original_author = repo_full_name.split("/")[0]
    source.skill_md_path = str(Path(source_dir) / str(item.get("md_file") or ""))
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


def load_entries() -> list[tuple[str, dict]]:
    entries: list[tuple[str, dict]] = []
    for source_dir in SOURCE_DIRS:
        manifest_path = ROOT_DIR / source_dir / "tagging_manifest.json"
        items = json.loads(manifest_path.read_text(encoding="utf-8"))
        for item in items:
            entries.append((source_dir, item))
    return entries


def load_repo_markdown(source_dir: str, md_file: str) -> str:
    path = ROOT_DIR / source_dir / md_file
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def main() -> None:
    entries = load_entries()
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    created_count = 0
    updated_count = 0
    category_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()

    try:
        for source_dir, item in entries:
            markdown_text = load_repo_markdown(source_dir, str(item.get("md_file") or ""))
            _, created = upsert_skill(db, item, markdown_text, source_dir, now)
            if created:
                created_count += 1
            else:
                updated_count += 1
            category_counter[str(item.get("category_name") or "未分类")] += 1
            status_counter[str(item.get("recommend_status") or "approved")] += 1
            source_counter[source_dir] += 1

        recalc_counts(db)
        db.commit()

        print(
            json.dumps(
                {
                    "manifest_count": len(entries),
                    "created": created_count,
                    "updated": updated_count,
                    "sources": dict(source_counter),
                    "categories": dict(category_counter),
                    "recommend_statuses": dict(status_counter),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
