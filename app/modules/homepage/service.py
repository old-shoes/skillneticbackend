from typing import Dict, List, Optional, Set, Tuple

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.modules.category.models import Category
from app.modules.homepage.models import HomepageStats
from app.modules.homepage.schemas import (
    CategoryItemOut,
    HomepageOut,
    HomepageSkillOut,
    HomepageStatsOut,
    SkillTagOut,
    TutorialItemOut,
)
from app.modules.skill.models import Skill, SkillTag, Tag
from app.modules.me.models import UserFavorite
from app.modules.tutorial.models import Tutorial


def _build_skill_query() -> Select:
    return (
        select(Skill, Category, Tag)
        .join(Category, Skill.category_id == Category.id, isouter=True)
        .join(SkillTag, SkillTag.skill_id == Skill.id, isouter=True)
        .join(Tag, SkillTag.tag_id == Tag.id, isouter=True)
        .where(Skill.status == "published", Skill.deleted_at.is_(None))
    )


def _map_categories(rows: List[Category]) -> List[CategoryItemOut]:
    return [
        CategoryItemOut(
            id=str(row.id),
            name=row.name,
            slug=row.slug,
            icon=row.icon,
            color=row.color,
            description=row.description,
            skillCount=row.skill_count,
        )
        for row in rows
    ]


def _map_user_favorites(db: Session, user_id: Optional[UUID], skill_ids: List[UUID]) -> Set[UUID]:
    if user_id is None or not skill_ids:
        return set()
    rows = db.scalars(
        select(UserFavorite.target_id).where(
            UserFavorite.user_id == user_id,
            UserFavorite.target_type == "skill",
            UserFavorite.target_id.in_(skill_ids),
        )
    ).all()
    return set(rows)


def _map_skills(
    db: Session,
    rows: List[Tuple[Skill, Optional[Category], Optional[Tag]]],
    user_id: Optional[UUID] = None,
) -> List[HomepageSkillOut]:
    skill_map: Dict[str, dict] = {}
    skill_ids: List[UUID] = []

    for skill, category, tag in rows:
        item = skill_map.get(skill.id)
        if item is None:
            skill_ids.append(skill.id)
            item = {
                "id": str(skill.id),
                "title": skill.title,
                "slug": skill.slug,
                "summary": skill.summary,
                "coverIcon": skill.cover_icon,
                "categoryName": category.name if category else "",
                "tags": [],
                "difficulty": skill.difficulty,
                "modelLabels": [],
                "favoriteCount": skill.favorite_count,
                "viewCount": skill.view_count,
                "isFeatured": skill.is_featured,
                "isHot": skill.is_hot,
                "isFavorited": False,
            }
            skill_map[skill.id] = item

        if tag is not None:
            tag_out = SkillTagOut(id=str(tag.id), name=tag.name, type=tag.type)
            if all(existing.id != tag_out.id for existing in item["tags"]):
                item["tags"].append(tag_out)
            if tag.type == "model" and tag.name not in item["modelLabels"]:
                item["modelLabels"].append(tag.name)

    favorited_ids = _map_user_favorites(db, user_id, skill_ids)
    for skill_id in skill_ids:
        skill_map[skill_id]["isFavorited"] = skill_id in favorited_ids

    return [HomepageSkillOut.model_validate(item) for item in skill_map.values()]


def _map_tutorials(rows: List[Tutorial]) -> List[TutorialItemOut]:
    return [
        TutorialItemOut(
            id=str(row.id),
            title=row.title,
            slug=row.slug,
            summary=row.summary,
            coverImage=row.cover_image,
            chapterCount=0,
            durationMinutes=row.read_time_minutes,
        )
        for row in rows
    ]


def get_homepage_data(db: Session, user_id: Optional[UUID] = None) -> HomepageOut:
    category_rows = db.scalars(
        select(Category)
        .where(Category.is_enabled.is_(True), Category.deleted_at.is_(None))
        .order_by(Category.sort_order.asc(), Category.created_at.asc())
        .limit(8)
    ).all()

    featured_rows = db.execute(
        _build_skill_query()
        .where(Skill.is_featured.is_(True))
        .order_by(Skill.published_at.desc(), Skill.created_at.desc())
        .limit(30)
    ).all()

    latest_rows = db.execute(
        _build_skill_query()
        .order_by(Skill.published_at.desc(), Skill.created_at.desc())
        .limit(80)
    ).all()

    tutorial_rows = db.scalars(
        select(Tutorial)
        .where(
            Tutorial.status == "published",
            Tutorial.is_beginner.is_(True),
            Tutorial.deleted_at.is_(None),
        )
        .order_by(Tutorial.is_featured.desc(), Tutorial.published_at.desc(), Tutorial.created_at.desc())
        .limit(3)
    ).all()

    stats_row = db.scalar(
        select(HomepageStats)
        .where(HomepageStats.is_active.is_(True))
        .order_by(HomepageStats.updated_at.desc(), HomepageStats.created_at.desc())
        .limit(1)
    )

    featured_skills = _map_skills(db, featured_rows, user_id)[:3]
    latest_skills = _map_skills(db, latest_rows, user_id)[:8]

    stats = HomepageStatsOut(
        skillFavorites=stats_row.skill_favorites if stats_row else 10000,
        qualityTemplates=stats_row.quality_templates if stats_row else 2000,
        monthlyVisits=stats_row.monthly_visits if stats_row else 50000,
        beginnerTutorials=stats_row.beginner_tutorials if stats_row else 30,
    )

    return HomepageOut(
        categories=_map_categories(category_rows),
        featuredSkills=featured_skills,
        latestSkills=latest_skills,
        tutorials=_map_tutorials(tutorial_rows),
        stats=stats,
    )
