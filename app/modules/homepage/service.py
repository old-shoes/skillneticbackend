from typing import Dict, List, Optional, Set

from uuid import UUID

from sqlalchemy import func, select
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


def _map_favorite_counts(db: Session, skill_ids: List[UUID]) -> Dict[UUID, int]:
    if not skill_ids:
        return {}

    rows = db.execute(
        select(
            UserFavorite.target_id,
            func.count(UserFavorite.id),
        )
        .where(
            UserFavorite.target_type == "skill",
            UserFavorite.target_id.in_(skill_ids),
        )
        .group_by(UserFavorite.target_id)
    ).all()
    return {target_id: int(count) for target_id, count in rows}


def _map_tags_by_skill(db: Session, skill_ids: List[UUID]) -> Dict[UUID, List[SkillTagOut]]:
    if not skill_ids:
        return {}

    rows = db.execute(
        select(SkillTag.skill_id, Tag)
        .join(Tag, SkillTag.tag_id == Tag.id)
        .where(
            SkillTag.skill_id.in_(skill_ids),
            Tag.deleted_at.is_(None),
            Tag.is_enabled.is_(True),
        )
        .order_by(Tag.sort_order.asc(), Tag.created_at.asc())
    ).all()

    result: Dict[UUID, List[SkillTagOut]] = {}
    for skill_id, tag in rows:
        result.setdefault(skill_id, []).append(
            SkillTagOut(id=str(tag.id), name=tag.name, type=tag.type)
        )
    return result


def _map_skills(
    db: Session,
    rows: List[tuple[Skill, Optional[Category]]],
    user_id: Optional[UUID] = None,
) -> List[HomepageSkillOut]:
    skill_ids = [skill.id for skill, _ in rows]
    favorite_counts = _map_favorite_counts(db, skill_ids)
    favorited_ids = _map_user_favorites(db, user_id, skill_ids)
    tags_map = _map_tags_by_skill(db, skill_ids)

    result: List[HomepageSkillOut] = []
    for skill, category in rows:
        result.append(
            HomepageSkillOut(
                id=str(skill.id),
                title=skill.title,
                slug=skill.slug,
                summary=skill.summary,
                coverIcon=skill.cover_icon,
                categoryName=category.name if category else "",
                tags=tags_map.get(skill.id, []),
                difficulty=skill.difficulty,
                favoriteCount=favorite_counts.get(skill.id, 0),
                viewCount=skill.view_count,
                isFeatured=skill.is_featured,
                isHot=skill.is_hot,
                isFavorited=skill.id in favorited_ids,
            )
        )
    return result


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
        select(Skill, Category)
        .join(Category, Skill.category_id == Category.id, isouter=True)
        .where(
            Skill.status == "published",
            Skill.deleted_at.is_(None),
            Skill.is_featured.is_(True),
        )
        .order_by(Skill.published_at.desc(), Skill.created_at.desc())
        .limit(3)
    ).all()

    latest_rows = db.execute(
        select(Skill, Category)
        .join(Category, Skill.category_id == Category.id, isouter=True)
        .where(Skill.status == "published", Skill.deleted_at.is_(None))
        .order_by(Skill.published_at.desc(), Skill.created_at.desc())
        .limit(8)
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

    featured_skills = _map_skills(db, featured_rows, user_id)
    latest_skills = _map_skills(db, latest_rows, user_id)

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
