from typing import Dict, List, Optional, Sequence, Set, Tuple
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.category.models import Category
from app.modules.skill.models import Skill, SkillCategoryRelation, SkillTag, Tag
from app.modules.me.models import UserFavorite
from app.modules.skill_submissions.models import SkillSubmission
from app.modules.skills.schemas import (
    CategoryOut,
    CategoryTreeOut,
    FilterOptionOut,
    PaginationOut,
    SkillDetailOut,
    SkillFavoriteOut,
    SkillFiltersOut,
    SkillListItemOut,
    SkillListOut,
    SkillQueryIn,
    TagOut,
)


TYPE_OPTIONS = [
    FilterOptionOut(label="提示词", value="prompt", count=0),
    FilterOptionOut(label="工作流", value="workflow", count=0),
    FilterOptionOut(label="教程", value="tutorial", count=0),
    FilterOptionOut(label="工具配置", value="tool_config", count=0),
    FilterOptionOut(label="Agent", value="agent", count=0),
]


class SkillService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _base_skill_query(self) -> Select:
        return (
            select(Skill.id)
            .join(Category, Skill.category_id == Category.id)
            .where(
                Skill.status == "published",
                Skill.deleted_at.is_(None),
                Category.deleted_at.is_(None),
                Category.is_enabled.is_(True),
            )
        )

    def _category_ids_by_slug(self, slug: str) -> List[UUID]:
        category = self.db.scalar(
            select(Category).where(
                Category.slug == slug,
                Category.deleted_at.is_(None),
                Category.is_enabled.is_(True),
            )
        )
        if category is None:
            return []
        if category.level == 2:
            return [category.id]
        child_ids = self.db.scalars(
            select(Category.id).where(
                Category.parent_id == category.id,
                Category.deleted_at.is_(None),
                Category.is_enabled.is_(True),
            )
        ).all()
        return list(child_ids) or [category.id]

    def _category_out(self, category: Optional[Category]) -> CategoryOut:
        return CategoryOut(
            id=str(category.id) if category else "",
            name=category.name if category else "",
            slug=category.slug if category else "",
            icon=category.icon if category else "",
            color=category.color if category else "blue",
            parentId=str(category.parent_id) if category and category.parent_id else None,
            level=int(category.level) if category and category.level else 1,
        )

    def _skill_category_maps(self, skill_ids: Sequence[UUID]) -> Tuple[Dict[UUID, List[CategoryOut]], Dict[UUID, CategoryOut]]:
        if not skill_ids:
            return {}, {}

        rows = self.db.execute(
            select(SkillCategoryRelation.skill_id, SkillCategoryRelation.is_primary, Category)
            .join(Category, SkillCategoryRelation.category_id == Category.id)
            .where(
                SkillCategoryRelation.skill_id.in_(list(skill_ids)),
                Category.deleted_at.is_(None),
                Category.is_enabled.is_(True),
            )
            .order_by(
                SkillCategoryRelation.is_primary.desc(),
                Category.level.asc(),
                Category.sort_order.asc(),
                Category.created_at.asc(),
            )
        ).all()

        categories_map: Dict[UUID, List[CategoryOut]] = {}
        primary_map: Dict[UUID, CategoryOut] = {}
        for skill_id, is_primary, category in rows:
            category_out = self._category_out(category)
            categories_map.setdefault(skill_id, []).append(category_out)
            if is_primary and skill_id not in primary_map:
                primary_map[skill_id] = category_out
        return categories_map, primary_map

    def _category_tree(self) -> List[CategoryTreeOut]:
        rows = self.db.scalars(
            select(Category)
            .where(Category.deleted_at.is_(None), Category.is_enabled.is_(True))
            .order_by(Category.level.asc(), Category.sort_order.asc(), Category.created_at.asc())
        ).all()

        nodes: Dict[UUID, CategoryTreeOut] = {}
        roots: List[CategoryTreeOut] = []
        for row in rows:
            nodes[row.id] = CategoryTreeOut(
                id=str(row.id),
                name=row.name,
                slug=row.slug,
                icon=row.icon,
                color=row.color,
                parentId=str(row.parent_id) if row.parent_id else None,
                level=int(row.level or 1),
                children=[],
            )

        for row in rows:
            node = nodes[row.id]
            if row.parent_id and row.parent_id in nodes:
                nodes[row.parent_id].children.append(node)
            else:
                roots.append(node)

        return roots

    def _selectable_categories(self) -> List[Category]:
        rows = self.db.scalars(
            select(Category)
            .where(Category.deleted_at.is_(None), Category.is_enabled.is_(True))
            .order_by(Category.level.asc(), Category.sort_order.asc(), Category.created_at.asc())
        ).all()
        parent_ids = {item.parent_id for item in rows if item.parent_id is not None}
        return [item for item in rows if item.id not in parent_ids]

    def _flat_filter_categories(self) -> List[Category]:
        return self.db.scalars(
            select(Category)
            .where(
                Category.deleted_at.is_(None),
                Category.is_enabled.is_(True),
                Category.level == 1,
            )
            .order_by(Category.sort_order.asc(), Category.created_at.asc())
        ).all()

    def _apply_filters(self, stmt: Select, query: SkillQueryIn) -> Select:
        if query.q:
            keyword = f"%{query.q.strip()}%"
            stmt = stmt.where(
                or_(
                    Skill.title.ilike(keyword),
                    Skill.summary.ilike(keyword),
                    Skill.search_keywords.ilike(keyword),
                )
            )

        if query.category:
            category_ids = self._category_ids_by_slug(query.category)
            if not category_ids:
                stmt = stmt.where(Skill.id.in_([]))
            else:
                stmt = stmt.where(
                    Skill.id.in_(
                        select(SkillCategoryRelation.skill_id).where(
                            SkillCategoryRelation.category_id.in_(category_ids)
                        )
                    )
                )

        if query.type:
            stmt = stmt.where(Skill.type == query.type)

        if query.scene:
            stmt = stmt.where(
                Skill.id.in_(
                    select(SkillTag.skill_id)
                    .join(Tag, SkillTag.tag_id == Tag.id)
                    .where(Tag.type == "scene", Tag.slug == query.scene)
                )
            )

        return stmt

    def _apply_sort(self, stmt: Select, sort: str) -> Select:
        if sort == "popular":
            return stmt.order_by(Skill.is_hot.desc(), Skill.favorite_count.desc(), Skill.view_count.desc(), Skill.published_at.desc())
        if sort == "favorites":
            return stmt.order_by(Skill.favorite_count.desc(), Skill.published_at.desc())
        if sort == "views":
            return stmt.order_by(Skill.view_count.desc(), Skill.published_at.desc())
        return stmt.order_by(Skill.published_at.desc(), Skill.created_at.desc())

    def _map_tags_by_skill(self, skill_ids: Sequence[UUID]) -> Dict[UUID, List[TagOut]]:
        if not skill_ids:
            return {}

        rows = self.db.execute(
            select(SkillTag.skill_id, Tag)
            .join(Tag, SkillTag.tag_id == Tag.id)
            .where(
                SkillTag.skill_id.in_(list(skill_ids)),
                Tag.deleted_at.is_(None),
                Tag.is_enabled.is_(True),
                Tag.type != "difficulty",
            )
            .order_by(Tag.sort_order.asc(), Tag.created_at.asc())
        ).all()

        result: Dict[UUID, List[TagOut]] = {}
        for skill_id, tag in rows:
            result.setdefault(skill_id, []).append(
                TagOut(id=str(tag.id), name=tag.name, slug=tag.slug, type=tag.type)
            )
        return result

    def _map_user_favorites(self, user_id: Optional[UUID], skill_ids: Sequence[UUID]) -> Set[UUID]:
        if user_id is None or not skill_ids:
            return set()
        rows = self.db.scalars(
            select(UserFavorite.target_id).where(
                UserFavorite.user_id == user_id,
                UserFavorite.target_type == "skill",
                UserFavorite.target_id.in_(list(skill_ids)),
            )
        ).all()
        return set(rows)

    def _map_skill_authors(self, skill_ids: Sequence[UUID]) -> Dict[UUID, str]:
        if not skill_ids:
            return {}

        rows = self.db.execute(
            select(SkillSubmission.approved_skill_id, User.nickname)
            .join(User, User.id == SkillSubmission.submitter_id)
            .where(
                SkillSubmission.approved_skill_id.in_(list(skill_ids)),
                SkillSubmission.deleted_at.is_(None),
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
            .order_by(SkillSubmission.created_at.desc())
        ).all()

        result: Dict[UUID, str] = {}
        for approved_skill_id, nickname in rows:
            if approved_skill_id is None or not nickname or approved_skill_id in result:
                continue
            result[approved_skill_id] = nickname
        return result

    def favorite_skill(self, *, user_id: UUID, skill_id: UUID) -> SkillFavoriteOut:
        user = self.db.get(User, user_id)
        if user is None or user.deleted_at is not None or not user.is_active:
            raise ValueError("user not found")

        skill = self.db.get(Skill, skill_id)
        if skill is None or skill.deleted_at is not None or skill.status != "published":
            raise ValueError("skill not found")

        favorite = self.db.scalar(
            select(UserFavorite).where(
                UserFavorite.user_id == user_id,
                UserFavorite.target_type == "skill",
                UserFavorite.target_id == skill_id,
            )
        )
        if favorite is None:
            self.db.add(
                UserFavorite(
                    user_id=user_id,
                    target_type="skill",
                    target_id=skill_id,
                )
            )
            skill.favorite_count = int(skill.favorite_count or 0) + 1
            self.db.add(skill)
            self.db.commit()
            self.db.refresh(skill)
            return SkillFavoriteOut(favorited=True, favoriteCount=int(skill.favorite_count or 0))

        return SkillFavoriteOut(favorited=True, favoriteCount=int(skill.favorite_count or 0))

    def unfavorite_skill(self, *, user_id: UUID, skill_id: UUID) -> SkillFavoriteOut:
        user = self.db.get(User, user_id)
        if user is None or user.deleted_at is not None or not user.is_active:
            raise ValueError("user not found")

        skill = self.db.get(Skill, skill_id)
        if skill is None or skill.deleted_at is not None or skill.status != "published":
            raise ValueError("skill not found")

        favorite = self.db.scalar(
            select(UserFavorite).where(
                UserFavorite.user_id == user_id,
                UserFavorite.target_type == "skill",
                UserFavorite.target_id == skill_id,
            )
        )
        if favorite is not None:
            self.db.delete(favorite)
            skill.favorite_count = max(0, int(skill.favorite_count or 0) - 1)
            self.db.add(skill)
            self.db.commit()
            self.db.refresh(skill)
            return SkillFavoriteOut(favorited=False, favoriteCount=int(skill.favorite_count or 0))

        return SkillFavoriteOut(favorited=False, favoriteCount=int(skill.favorite_count or 0))

    def get_skill_list(self, query: SkillQueryIn, user_id: Optional[UUID] = None) -> SkillListOut:
        filtered_ids_stmt = self._apply_filters(self._base_skill_query(), query)
        total = self.db.scalar(select(func.count()).select_from(filtered_ids_stmt.subquery())) or 0

        page = query.page
        page_size = query.pageSize
        paged_ids = self.db.scalars(
            self._apply_sort(
                select(Skill.id)
                .join(Category, Skill.category_id == Category.id)
                .where(Skill.id.in_(filtered_ids_stmt)),
                query.sort,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        if not paged_ids:
            return SkillListOut(list=[], pagination=PaginationOut.from_total(page, page_size, total))

        rows = self.db.execute(
            select(Skill, Category)
            .join(Category, Skill.category_id == Category.id)
            .where(Skill.id.in_(paged_ids))
        ).all()

        row_map: Dict[UUID, Tuple[Skill, Category]] = {skill.id: (skill, category) for skill, category in rows}
        tags_map = self._map_tags_by_skill(paged_ids)
        category_map, primary_category_map = self._skill_category_maps(paged_ids)
        favorited_ids = self._map_user_favorites(user_id, paged_ids)
        author_map = self._map_skill_authors(paged_ids)

        items: List[SkillListItemOut] = []
        for skill_id in paged_ids:
            pair = row_map.get(skill_id)
            if pair is None:
                continue

            skill, category = pair
            fallback_category = self._category_out(category)
            primary_category = primary_category_map.get(skill.id, fallback_category)
            categories = category_map.get(skill.id, [primary_category])
            items.append(
                SkillListItemOut(
                    id=str(skill.id),
                    title=skill.title,
                    slug=skill.slug,
                    summary=skill.summary,
                    authorName=author_map.get(skill.id),
                    coverIcon=skill.cover_icon,
                    category=primary_category,
                    primaryCategory=primary_category,
                    categories=categories,
                    tags=tags_map.get(skill.id, []),
                    difficulty=skill.difficulty,
                    type=skill.type,
                    recommendedModels=skill.recommended_models or [],
                    favoriteCount=int(skill.favorite_count or 0),
                    viewCount=skill.view_count,
                    publishedAt=skill.published_at or skill.created_at,
                    isFeatured=skill.is_featured,
                    isHot=skill.is_hot,
                    sourceType=skill.source_type,
                    sourceUrl=skill.source_url,
                    sourceName=skill.source_name,
                    originalAuthor=skill.original_author,
                    license=skill.license,
                    isFavorited=skill.id in favorited_ids,
                )
            )

        return SkillListOut(list=items, pagination=PaginationOut.from_total(page, page_size, total))

    def get_skill_detail(
        self,
        slug: str,
        user_id: Optional[UUID] = None,
        *,
        increment_view: bool = False,
    ) -> Optional[SkillDetailOut]:
        row = self.db.execute(
            select(Skill, Category)
            .join(Category, Skill.category_id == Category.id, isouter=True)
            .where(
                Skill.slug == slug,
                Skill.status == "published",
                Skill.deleted_at.is_(None),
            )
            .limit(1)
        ).first()
        if row is None:
            return None

        skill, category = row
        if increment_view:
            skill.view_count = int(skill.view_count or 0) + 1
            self.db.add(skill)
            self.db.commit()
            self.db.refresh(skill)
        tags_map = self._map_tags_by_skill([skill.id])
        category_map, primary_category_map = self._skill_category_maps([skill.id])
        favorited_ids = self._map_user_favorites(user_id, [skill.id])
        author_map = self._map_skill_authors([skill.id])
        fallback_category = self._category_out(category)
        primary_category = primary_category_map.get(skill.id, fallback_category)
        categories = category_map.get(skill.id, [primary_category])

        return SkillDetailOut(
            id=str(skill.id),
            title=skill.title,
            slug=skill.slug,
            summary=skill.summary,
            contentMarkdown=skill.content or "",
            authorName=author_map.get(skill.id),
            coverIcon=skill.cover_icon,
            category=primary_category,
            primaryCategory=primary_category,
            categories=categories,
            tags=tags_map.get(skill.id, []),
            difficulty=skill.difficulty,
            type=skill.type,
            useCase=skill.use_case,
            recommendedModels=skill.recommended_models or [],
            favoriteCount=int(skill.favorite_count or 0),
            viewCount=skill.view_count,
            publishedAt=skill.published_at or skill.created_at,
            updatedAt=skill.updated_at,
            isFeatured=skill.is_featured,
            isHot=skill.is_hot,
            sourceType=skill.source_type,
            sourceUrl=skill.source_url,
            sourceName=skill.source_name,
            originalAuthor=skill.original_author,
            license=skill.license,
            isFavorited=skill.id in favorited_ids,
        )

    def _get_tag_filters(self, tag_type: str) -> List[FilterOptionOut]:
        rows = self.db.scalars(
            select(Tag)
            .where(Tag.type == tag_type, Tag.deleted_at.is_(None), Tag.is_enabled.is_(True))
            .order_by(Tag.sort_order.asc(), Tag.created_at.asc())
        ).all()
        return [FilterOptionOut(label=row.name, value=row.slug, count=row.skill_count) for row in rows]

    def get_filters(self) -> SkillFiltersOut:
        categories = self._flat_filter_categories()

        return SkillFiltersOut(
            categories=[
                FilterOptionOut(label=row.name, value=row.slug, count=row.skill_count)
                for row in categories
            ],
            categoryTree=self._category_tree(),
            scenes=self._get_tag_filters("scene"),
            types=TYPE_OPTIONS,
        )
