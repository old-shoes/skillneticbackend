from __future__ import annotations

from typing import Dict, List, Optional, Set

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.category.models import Category
from app.modules.homepage.models import HomepageStats
from app.modules.homepage.schemas import (
    CategoryItemOut,
    HomepageOut,
    HomepageSceneCountOut,
    HomepageSkillOut,
    HomepageStatsOut,
    SkillTagOut,
    TutorialItemOut,
)
from app.modules.skill.models import Skill, SkillCategoryRelation, SkillTag, Tag
from app.modules.me.models import UserFavorite
from app.modules.tutorial.models import Tutorial

def _map_category_skill_counts(db: Session, rows: List[Category]) -> Dict[UUID, int]:
    if not rows:
        return {}

    root_ids = [row.id for row in rows]
    child_rows = db.scalars(
        select(Category).where(
            Category.parent_id.in_(root_ids),
            Category.deleted_at.is_(None),
            Category.is_enabled.is_(True),
        )
    ).all()

    member_ids_by_root: Dict[UUID, List[UUID]] = {}
    for row in rows:
        member_ids_by_root[row.id] = [row.id]
    for child in child_rows:
        if child.parent_id is not None and child.parent_id in member_ids_by_root:
            member_ids_by_root[child.parent_id].append(child.id)

    all_member_ids = sorted({member_id for member_ids in member_ids_by_root.values() for member_id in member_ids})
    if not all_member_ids:
        return {row.id: 0 for row in rows}

    count_rows = db.execute(
        select(
            SkillCategoryRelation.category_id,
            func.count(func.distinct(SkillCategoryRelation.skill_id)).label("skill_count"),
        )
        .join(Skill, Skill.id == SkillCategoryRelation.skill_id)
        .where(
            SkillCategoryRelation.category_id.in_(all_member_ids),
            Skill.status == "published",
            Skill.deleted_at.is_(None),
        )
        .group_by(SkillCategoryRelation.category_id)
    ).all()
    direct_counts = {category_id: int(skill_count or 0) for category_id, skill_count in count_rows}

    return {
        row.id: sum(direct_counts.get(member_id, 0) for member_id in member_ids_by_root[row.id])
        for row in rows
    }


def _map_categories(rows: List[Category], counts: Dict[UUID, int]) -> List[CategoryItemOut]:
    return [
        CategoryItemOut(
            id=str(row.id),
            name=row.name,
            slug=row.slug,
            icon=row.icon,
            color=row.color,
            description=row.description,
            skillCount=counts.get(row.id, 0),
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


def _map_scene_counts(db: Session) -> List[HomepageSceneCountOut]:
    rows = db.execute(
        select(
            Tag.slug,
            func.count(func.distinct(Skill.id)).label("skill_count"),
        )
        .join(SkillTag, SkillTag.tag_id == Tag.id)
        .join(Skill, Skill.id == SkillTag.skill_id)
        .where(
            Tag.type == "scene",
            Tag.deleted_at.is_(None),
            Tag.is_enabled.is_(True),
            Skill.status == "published",
            Skill.deleted_at.is_(None),
        )
        .group_by(Tag.slug, Tag.sort_order)
        .order_by(Tag.sort_order.asc(), Tag.slug.asc())
    ).all()
    return [HomepageSceneCountOut(slug=slug, count=int(skill_count or 0)) for slug, skill_count in rows]


def get_homepage_data(db: Session, user_id: Optional[UUID] = None) -> HomepageOut:
    category_rows = db.scalars(
        select(Category)
        .where(
            Category.is_enabled.is_(True),
            Category.deleted_at.is_(None),
            Category.level == 1,
        )
        .order_by(Category.sort_order.asc(), Category.created_at.asc())
        .limit(8)
    ).all()
    category_counts = _map_category_skill_counts(db, category_rows)

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

    if len(featured_rows) < 4:
        featured_ids = {skill.id for skill, _ in featured_rows}
        fallback_stmt = (
            select(Skill, Category)
            .join(Category, Skill.category_id == Category.id, isouter=True)
            .where(Skill.status == "published", Skill.deleted_at.is_(None))
            .order_by(
                Skill.favorite_count.desc(),
                Skill.view_count.desc(),
                Skill.published_at.desc(),
                Skill.created_at.desc(),
            )
            .limit(4 - len(featured_rows))
        )
        if featured_ids:
            fallback_stmt = fallback_stmt.where(Skill.id.not_in(featured_ids))
        fallback_rows = db.execute(fallback_stmt).all()
        featured_rows = [*featured_rows, *fallback_rows]

    if len(featured_rows) < 4:
        featured_ids = {skill.id for skill, _ in featured_rows}
        random_stmt = (
            select(Skill, Category)
            .join(Category, Skill.category_id == Category.id, isouter=True)
            .where(Skill.status == "published", Skill.deleted_at.is_(None))
            .order_by(func.random())
            .limit(4 - len(featured_rows))
        )
        if featured_ids:
            random_stmt = random_stmt.where(Skill.id.not_in(featured_ids))
        random_rows = db.execute(random_stmt).all()
        featured_rows = [*featured_rows, *random_rows]

    latest_rows = db.execute(
        select(Skill, Category)
        .join(Category, Skill.category_id == Category.id, isouter=True)
        .where(Skill.status == "published", Skill.deleted_at.is_(None))
        .order_by(Skill.published_at.desc(), Skill.created_at.desc())
        .limit(8)
    ).all()

    trending_rows = db.execute(
        select(Skill, Category)
        .join(Category, Skill.category_id == Category.id, isouter=True)
        .where(Skill.status == "published", Skill.deleted_at.is_(None))
        .order_by(
            Skill.favorite_count.desc(),
            Skill.view_count.desc(),
            Skill.published_at.desc(),
            Skill.created_at.desc(),
        )
        .limit(5)
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
    trending_skills = _map_skills(db, trending_rows, user_id)
    latest_skills = _map_skills(db, latest_rows, user_id)

    stats = HomepageStatsOut(
        skillFavorites=stats_row.skill_favorites if stats_row else 10000,
        qualityTemplates=stats_row.quality_templates if stats_row else 2000,
        monthlyVisits=stats_row.monthly_visits if stats_row else 50000,
        beginnerTutorials=stats_row.beginner_tutorials if stats_row else 30,
    )

    return HomepageOut(
        categories=_map_categories(category_rows, category_counts),
        featuredSkills=featured_skills,
        trendingSkills=trending_skills,
        latestSkills=latest_skills,
        sceneCounts=_map_scene_counts(db),
        tutorials=_map_tutorials(tutorial_rows),
        stats=stats,
    )
