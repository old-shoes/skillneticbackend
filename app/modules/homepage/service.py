from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.category.models import Category
from app.modules.homepage.models import HomepageStats
from app.modules.homepage.schemas import (
    CategoryItemOut,
    HomepageActivityOut,
    HomepageContributorOut,
    HomepageOut,
    HomepageSceneCountOut,
    HomepageSkillOut,
    HomepageStatsOut,
    SkillTagOut,
    TutorialItemOut,
)
from app.modules.skill.models import Skill, SkillCategoryRelation, SkillTag, Tag
from app.modules.me.models import UserFavorite
from app.modules.skill_submissions.models import SkillSubmission
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


def _format_ago(value: Optional[datetime]) -> str:
    if value is None:
        return "刚刚"
    current = datetime.now(timezone.utc)
    target = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    seconds = max(0, int((current - target).total_seconds()))
    if seconds < 60:
        return "刚刚"
    if seconds < 3600:
        return f"{max(1, seconds // 60)} 分钟前"
    if seconds < 86400:
        return f"{max(1, seconds // 3600)} 小时前"
    return f"{max(1, seconds // 86400)} 天前"


def _map_latest_activities(db: Session) -> List[HomepageActivityOut]:
    submission_rows = db.execute(
        select(User.nickname, SkillSubmission.title, SkillSubmission.submitted_at)
        .join(User, User.id == SkillSubmission.submitter_id)
        .where(
            SkillSubmission.deleted_at.is_(None),
            SkillSubmission.status.in_(("pending_review", "approved", "needs_revision")),
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
        .order_by(SkillSubmission.submitted_at.desc(), SkillSubmission.created_at.desc())
        .limit(5)
    ).all()

    favorite_rows = db.execute(
        select(User.nickname, Skill.title, UserFavorite.created_at)
        .join(User, User.id == UserFavorite.user_id)
        .join(Skill, Skill.id == UserFavorite.target_id)
        .where(
            UserFavorite.target_type == "skill",
            User.deleted_at.is_(None),
            User.is_active.is_(True),
            Skill.deleted_at.is_(None),
            Skill.status == "published",
        )
        .order_by(UserFavorite.created_at.desc())
        .limit(5)
    ).all()

    items: List[tuple[str, str, str, Optional[datetime]]] = []
    items.extend((nickname, "提交了新的Skill", title, submitted_at) for nickname, title, submitted_at in submission_rows if nickname and title)
    items.extend((nickname, "收藏了 Skill", title, created_at) for nickname, title, created_at in favorite_rows if nickname and title)
    items.sort(key=lambda item: item[3] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    return [
        HomepageActivityOut(
            user=user,
            action=action,
            target=target,
            ago=_format_ago(created_at),
        )
        for user, action, target, created_at in items[:5]
    ]


def _week_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def _map_weekly_contributors(db: Session) -> List[HomepageContributorOut]:
    week_start = _week_start_utc()

    submission_rows = db.execute(
        select(
            SkillSubmission.submitter_id,
            User.nickname,
            func.count(func.distinct(SkillSubmission.approved_skill_id)).label("submission_count"),
        )
        .join(User, User.id == SkillSubmission.submitter_id)
        .where(
            SkillSubmission.deleted_at.is_(None),
            SkillSubmission.submitter_id.is_not(None),
            SkillSubmission.approved_skill_id.is_not(None),
            SkillSubmission.status == "approved",
            SkillSubmission.reviewed_at.is_not(None),
            SkillSubmission.reviewed_at >= week_start,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
        .group_by(SkillSubmission.submitter_id, User.nickname)
    ).all()

    rows_by_user: Dict[UUID, dict[str, object]] = {}
    approved_skill_ids: List[UUID] = []

    for user_id, nickname, submission_count in submission_rows:
        if user_id is None or not nickname:
            continue
        rows_by_user[user_id] = {
            "user": nickname,
            "submissionCount": int(submission_count or 0),
            "favoriteCount": 0,
        }

    approved_skill_rows = db.execute(
        select(
            SkillSubmission.submitter_id,
            SkillSubmission.approved_skill_id,
        )
        .where(
            SkillSubmission.deleted_at.is_(None),
            SkillSubmission.submitter_id.is_not(None),
            SkillSubmission.approved_skill_id.is_not(None),
            SkillSubmission.status == "approved",
            SkillSubmission.reviewed_at.is_not(None),
            SkillSubmission.reviewed_at >= week_start,
        )
    ).all()

    skill_owner_map: Dict[UUID, UUID] = {}
    for user_id, approved_skill_id in approved_skill_rows:
        if user_id is None or approved_skill_id is None:
            continue
        skill_owner_map[approved_skill_id] = user_id
        approved_skill_ids.append(approved_skill_id)

    if approved_skill_ids:
        favorite_rows = db.execute(
            select(
                UserFavorite.target_id,
                func.count(UserFavorite.id).label("favorite_count"),
            )
            .where(
                UserFavorite.target_type == "skill",
                UserFavorite.target_id.in_(approved_skill_ids),
                UserFavorite.created_at >= week_start,
            )
            .group_by(UserFavorite.target_id)
        ).all()

        for skill_id, favorite_count in favorite_rows:
            owner_id = skill_owner_map.get(skill_id)
            if owner_id is None or owner_id not in rows_by_user:
                continue
            rows_by_user[owner_id]["favoriteCount"] = int(rows_by_user[owner_id]["favoriteCount"]) + int(favorite_count or 0)

    contributors = [
        HomepageContributorOut(
            user=str(item["user"]),
            submissionCount=int(item["submissionCount"]),
            favoriteCount=int(item["favoriteCount"]),
            score=int(item["submissionCount"]) * 10 + int(item["favoriteCount"]) * 3,
        )
        for item in rows_by_user.values()
    ]
    contributors.sort(key=lambda item: (item.score, item.favoriteCount, item.submissionCount, item.user), reverse=True)
    return contributors[:5]


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
        latestActivities=_map_latest_activities(db),
        weeklyContributors=_map_weekly_contributors(db),
        sceneCounts=_map_scene_counts(db),
        tutorials=_map_tutorials(tutorial_rows),
        stats=stats,
    )
