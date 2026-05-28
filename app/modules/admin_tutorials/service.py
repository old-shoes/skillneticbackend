from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.admin_tutorials.schemas import (
    AdminLearningPathIn,
    AdminLearningPathOut,
    AdminOperationLogListItemOut,
    AdminOperationLogListOut,
    AdminOperationLogQueryIn,
    AdminPaginationOut,
    AdminPromptBlockOut,
    AdminTutorialCategoryIn,
    AdminTutorialCategoryListOut,
    AdminTutorialCategoryOut,
    AdminTutorialCategoryQueryIn,
    AdminTutorialCategorySortIn,
    AdminTutorialCategoryStatsOut,
    AdminTutorialDetailOut,
    AdminTutorialListItemOut,
    AdminTutorialListOut,
    AdminTutorialQueryIn,
    AdminTutorialSaveIn,
    AdminTutorialTagIn,
    AdminTutorialTagListItemOut,
    AdminTutorialTagOut,
)
from app.modules.tutorial.models import (
    AdminOperationLog,
    LearningPath,
    Tutorial,
    TutorialCategory,
    TutorialPromptBlock,
    TutorialTag,
    TutorialTagRelation,
)


DEFAULT_OPERATOR_NAME = "Local Admin"


class AdminTutorialService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _parse_uuid(self, value: str, field_name: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"invalid {field_name}") from exc

    def _get_category_or_404(self, category_id: str) -> TutorialCategory:
        category = self.db.get(TutorialCategory, self._parse_uuid(category_id, "categoryId"))
        if category is None or category.deleted_at is not None:
            raise HTTPException(status_code=404, detail="tutorial category not found")
        return category

    def _get_learning_path_or_404(self, learning_path_id: str) -> LearningPath:
        learning_path = self.db.get(LearningPath, self._parse_uuid(learning_path_id, "learningPathId"))
        if learning_path is None or learning_path.deleted_at is not None:
            raise HTTPException(status_code=404, detail="learning path not found")
        return learning_path

    def _get_tag_ids(self, tag_ids: List[str]) -> List[UUID]:
        if not tag_ids:
            return []
        uuids = [self._parse_uuid(tag_id, "tagId") for tag_id in tag_ids]
        tags = self.db.scalars(
            select(TutorialTag).where(TutorialTag.id.in_(uuids), TutorialTag.deleted_at.is_(None))
        ).all()
        if len(tags) != len(uuids):
            raise HTTPException(status_code=404, detail="tutorial tag not found")
        return uuids

    def _ensure_unique_slug(self, slug: str, tutorial_id: Optional[UUID] = None) -> None:
        stmt = select(Tutorial).where(Tutorial.slug == slug, Tutorial.deleted_at.is_(None))
        if tutorial_id is not None:
            stmt = stmt.where(Tutorial.id != tutorial_id)
        exists = self.db.scalar(stmt)
        if exists is not None:
            raise HTTPException(status_code=400, detail="slug already exists")

    def _parse_date_boundary(self, value: str, field_name: str, end_of_day: bool = False) -> datetime:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"invalid {field_name}") from exc
        if end_of_day:
            parsed = parsed + timedelta(days=1)
        return parsed.replace(tzinfo=timezone.utc)

    def _tutorial_to_list_item(self, tutorial: Tutorial, category: Optional[TutorialCategory], tags: List[TutorialTag]) -> AdminTutorialListItemOut:
        return AdminTutorialListItemOut(
            id=str(tutorial.id),
            title=tutorial.title,
            slug=tutorial.slug,
            coverImage=tutorial.cover_image,
            category=AdminTutorialCategoryOut(
                id=str(category.id),
                name=category.name,
                slug=category.slug,
                icon=category.icon,
                color=category.color,
                description=category.description,
                group=category.category_group,
                scene=category.scene,
                difficulty=category.difficulty,
                tutorialCount=category.tutorial_count,
                skillCount=category.skill_count,
                isHot=category.is_hot,
                isEnabled=category.is_enabled,
                sortOrder=category.sort_order,
                createdAt=category.created_at,
                updatedAt=category.updated_at,
            )
            if category
            else None,
            tags=[AdminTutorialTagOut(id=str(tag.id), name=tag.name, slug=tag.slug) for tag in tags],
            difficulty=tutorial.difficulty,
            readTimeMinutes=tutorial.read_time_minutes,
            viewCount=tutorial.view_count,
            favoriteCount=tutorial.favorite_count,
            status=tutorial.status,
            isFeatured=tutorial.is_featured,
            isBeginner=tutorial.is_beginner,
            updatedAt=tutorial.updated_at,
            publishedAt=tutorial.published_at,
        )

    def _get_tags_for_tutorial(self, tutorial_id: UUID) -> List[TutorialTag]:
        return self.db.scalars(
            select(TutorialTag)
            .join(TutorialTagRelation, TutorialTagRelation.tag_id == TutorialTag.id)
            .where(TutorialTagRelation.tutorial_id == tutorial_id, TutorialTag.deleted_at.is_(None))
            .order_by(TutorialTag.sort_order.asc(), TutorialTag.created_at.asc())
        ).all()

    def _refresh_counts(self) -> None:
        categories = self.db.scalars(select(TutorialCategory).where(TutorialCategory.deleted_at.is_(None))).all()
        for category in categories:
            category.tutorial_count = int(
                self.db.scalar(
                    select(func.count(Tutorial.id)).where(
                        Tutorial.category_id == category.id,
                        Tutorial.deleted_at.is_(None),
                    )
                )
                or 0
            )

        tags = self.db.scalars(select(TutorialTag).where(TutorialTag.deleted_at.is_(None))).all()
        for tag in tags:
            tag.tutorial_count = int(
                self.db.scalar(
                    select(func.count(TutorialTagRelation.tutorial_id)).where(TutorialTagRelation.tag_id == tag.id)
                )
                or 0
            )

    def _write_log(
        self,
        module: str,
        action: str,
        target_id: Optional[UUID],
        target_title: Optional[str],
        before_data: Optional[dict],
        after_data: Optional[dict],
    ) -> None:
        self.db.add(
            AdminOperationLog(
                operator_name=DEFAULT_OPERATOR_NAME,
                module=module,
                action=action,
                target_id=target_id,
                target_title=target_title,
                before_data=before_data,
                after_data=after_data,
            )
        )

    def get_tutorials(self, query: AdminTutorialQueryIn) -> AdminTutorialListOut:
        stmt = (
            select(Tutorial, TutorialCategory)
            .outerjoin(TutorialCategory, Tutorial.category_id == TutorialCategory.id)
            .where(Tutorial.deleted_at.is_(None))
            .order_by(Tutorial.updated_at.desc(), Tutorial.created_at.desc())
        )

        if query.q:
            keyword = f"%{query.q.strip()}%"
            stmt = stmt.where(or_(Tutorial.title.ilike(keyword), Tutorial.summary.ilike(keyword), Tutorial.slug.ilike(keyword)))
        if query.categoryId:
            stmt = stmt.where(Tutorial.category_id == self._parse_uuid(query.categoryId, "categoryId"))
        if query.status:
            stmt = stmt.where(Tutorial.status == query.status)
        if query.difficulty:
            stmt = stmt.where(Tutorial.difficulty == query.difficulty)
        if query.isFeatured is not None:
            stmt = stmt.where(Tutorial.is_featured.is_(query.isFeatured))
        if query.tagId:
            stmt = stmt.where(
                Tutorial.id.in_(
                    select(TutorialTagRelation.tutorial_id).where(
                        TutorialTagRelation.tag_id == self._parse_uuid(query.tagId, "tagId")
                    )
                )
            )
        if query.publishedFrom:
            stmt = stmt.where(Tutorial.published_at >= self._parse_date_boundary(query.publishedFrom, "publishedFrom"))
        if query.publishedTo:
            stmt = stmt.where(Tutorial.published_at < self._parse_date_boundary(query.publishedTo, "publishedTo", end_of_day=True))

        rows = self.db.execute(stmt).all()
        total = len(rows)
        start = (query.page - 1) * query.pageSize
        end = start + query.pageSize
        paged_rows = rows[start:end]

        items = [
            self._tutorial_to_list_item(tutorial, category, self._get_tags_for_tutorial(tutorial.id))
            for tutorial, category in paged_rows
        ]
        return AdminTutorialListOut(
            list=items,
            pagination=AdminPaginationOut.from_total(query.page, query.pageSize, total),
        )

    def get_tutorial_detail(self, tutorial_id: str) -> AdminTutorialDetailOut:
        tutorial = self.db.get(Tutorial, self._parse_uuid(tutorial_id, "tutorialId"))
        if tutorial is None or tutorial.deleted_at is not None:
            raise HTTPException(status_code=404, detail="tutorial not found")

        prompt_blocks = self.db.scalars(
            select(TutorialPromptBlock)
            .where(TutorialPromptBlock.tutorial_id == tutorial.id, TutorialPromptBlock.deleted_at.is_(None))
            .order_by(TutorialPromptBlock.sort_order.asc(), TutorialPromptBlock.created_at.asc())
        ).all()

        return AdminTutorialDetailOut(
            id=str(tutorial.id),
            title=tutorial.title,
            slug=tutorial.slug,
            summary=tutorial.summary,
            contentMarkdown=tutorial.content_markdown,
            coverImage=tutorial.cover_image,
            coverIcon=tutorial.cover_icon,
            categoryId=str(tutorial.category_id) if tutorial.category_id else "",
            tagIds=[str(tag.id) for tag in self._get_tags_for_tutorial(tutorial.id)],
            difficulty=tutorial.difficulty,
            readTimeMinutes=tutorial.read_time_minutes,
            learningPoints=[str(item) for item in tutorial.learning_points or []],
            suitableFor=[str(item) for item in tutorial.suitable_for or []],
            promptBlocks=[
                AdminPromptBlockOut(
                    id=str(item.id),
                    title=item.title,
                    description=item.description,
                    content=item.content,
                    sortOrder=item.sort_order,
                )
                for item in prompt_blocks
            ],
            seoTitle=tutorial.seo_title,
            seoDescription=tutorial.seo_description,
            status=tutorial.status,
            isFeatured=tutorial.is_featured,
            isBeginner=tutorial.is_beginner,
            publishedAt=tutorial.published_at,
            updatedAt=tutorial.updated_at,
        )

    def _apply_payload_to_tutorial(self, tutorial: Tutorial, payload: AdminTutorialSaveIn) -> None:
        category = self._get_category_or_404(payload.categoryId)
        tag_ids = self._get_tag_ids(payload.tagIds)

        tutorial.title = payload.title
        tutorial.slug = payload.slug
        tutorial.summary = payload.summary
        tutorial.content_markdown = payload.contentMarkdown
        tutorial.cover_image = payload.coverImage
        tutorial.cover_icon = payload.coverIcon
        tutorial.category_id = category.id
        tutorial.difficulty = payload.difficulty
        tutorial.read_time_minutes = payload.readTimeMinutes
        tutorial.learning_points = payload.learningPoints
        tutorial.suitable_for = payload.suitableFor
        tutorial.seo_title = payload.seoTitle
        tutorial.seo_description = payload.seoDescription
        tutorial.is_featured = payload.isFeatured
        tutorial.is_beginner = payload.isBeginner
        tutorial.status = payload.status
        if payload.status == "published" and tutorial.published_at is None:
            tutorial.published_at = datetime.now(timezone.utc)

        self.db.execute(
            TutorialTagRelation.__table__.delete().where(TutorialTagRelation.tutorial_id == tutorial.id)
        )
        for tag_id in tag_ids:
            self.db.add(TutorialTagRelation(tutorial_id=tutorial.id, tag_id=tag_id))

        self.db.execute(
            TutorialPromptBlock.__table__.delete().where(TutorialPromptBlock.tutorial_id == tutorial.id)
        )
        for block in payload.promptBlocks:
            self.db.add(
                TutorialPromptBlock(
                    tutorial_id=tutorial.id,
                    title=block.title,
                    description=block.description,
                    content=block.content,
                    sort_order=block.sortOrder,
                )
            )

    def create_tutorial(self, payload: AdminTutorialSaveIn) -> AdminTutorialDetailOut:
        self._ensure_unique_slug(payload.slug)
        tutorial = Tutorial(
            title=payload.title,
            slug=payload.slug,
            summary=payload.summary,
            content_markdown=payload.contentMarkdown,
            cover_image=payload.coverImage,
            cover_icon=payload.coverIcon,
            difficulty=payload.difficulty,
            read_time_minutes=payload.readTimeMinutes,
            learning_points=payload.learningPoints,
            suitable_for=payload.suitableFor,
            seo_title=payload.seoTitle,
            seo_description=payload.seoDescription,
            is_featured=payload.isFeatured,
            is_beginner=payload.isBeginner,
            status=payload.status,
            published_at=datetime.now(timezone.utc) if payload.status == "published" else None,
        )
        self.db.add(tutorial)
        self.db.flush()
        self._apply_payload_to_tutorial(tutorial, payload)
        self._refresh_counts()
        self._write_log("tutorial", "tutorial_create", tutorial.id, tutorial.title, None, {"slug": tutorial.slug})
        self.db.commit()
        self.db.refresh(tutorial)
        return self.get_tutorial_detail(str(tutorial.id))

    def update_tutorial(self, tutorial_id: str, payload: AdminTutorialSaveIn) -> AdminTutorialDetailOut:
        tutorial = self.db.get(Tutorial, self._parse_uuid(tutorial_id, "tutorialId"))
        if tutorial is None or tutorial.deleted_at is not None:
            raise HTTPException(status_code=404, detail="tutorial not found")

        before = {"title": tutorial.title, "status": tutorial.status, "slug": tutorial.slug}
        self._ensure_unique_slug(payload.slug, tutorial.id)
        self._apply_payload_to_tutorial(tutorial, payload)
        self._refresh_counts()
        self._write_log("tutorial", "tutorial_update", tutorial.id, tutorial.title, before, {"title": tutorial.title, "status": tutorial.status, "slug": tutorial.slug})
        self.db.commit()
        return self.get_tutorial_detail(str(tutorial.id))

    def publish_tutorial(self, tutorial_id: str) -> AdminTutorialDetailOut:
        tutorial = self.db.get(Tutorial, self._parse_uuid(tutorial_id, "tutorialId"))
        if tutorial is None or tutorial.deleted_at is not None:
            raise HTTPException(status_code=404, detail="tutorial not found")
        if not tutorial.title or not tutorial.slug or not tutorial.summary or not tutorial.content_markdown or not tutorial.category_id:
            raise HTTPException(status_code=400, detail="tutorial is missing required fields")
        before = {"status": tutorial.status}
        tutorial.status = "published"
        if tutorial.published_at is None:
            tutorial.published_at = datetime.now(timezone.utc)
        self._write_log("tutorial", "tutorial_publish", tutorial.id, tutorial.title, before, {"status": tutorial.status})
        self.db.commit()
        return self.get_tutorial_detail(str(tutorial.id))

    def offline_tutorial(self, tutorial_id: str) -> AdminTutorialDetailOut:
        tutorial = self.db.get(Tutorial, self._parse_uuid(tutorial_id, "tutorialId"))
        if tutorial is None or tutorial.deleted_at is not None:
            raise HTTPException(status_code=404, detail="tutorial not found")
        before = {"status": tutorial.status}
        tutorial.status = "offline"
        self._write_log("tutorial", "tutorial_offline", tutorial.id, tutorial.title, before, {"status": tutorial.status})
        self.db.commit()
        return self.get_tutorial_detail(str(tutorial.id))

    def delete_tutorial(self, tutorial_id: str) -> None:
        tutorial = self.db.get(Tutorial, self._parse_uuid(tutorial_id, "tutorialId"))
        if tutorial is None or tutorial.deleted_at is not None:
            raise HTTPException(status_code=404, detail="tutorial not found")
        before = {"title": tutorial.title, "status": tutorial.status}
        tutorial.deleted_at = datetime.now(timezone.utc)
        tutorial.status = "offline"
        self._refresh_counts()
        self._write_log("tutorial", "tutorial_delete", tutorial.id, tutorial.title, before, None)
        self.db.commit()

    def list_categories(self) -> List[AdminTutorialCategoryOut]:
        rows = self.db.scalars(
            select(TutorialCategory)
            .where(TutorialCategory.deleted_at.is_(None))
            .order_by(TutorialCategory.sort_order.asc(), TutorialCategory.created_at.asc())
        ).all()
        return [self._map_admin_category(item) for item in rows]

    def _map_admin_category(self, item: TutorialCategory) -> AdminTutorialCategoryOut:
        return AdminTutorialCategoryOut(
            id=str(item.id),
            name=item.name,
            slug=item.slug,
            icon=item.icon,
            color=item.color,
            description=item.description,
            group=item.category_group,
            scene=item.scene,
            difficulty=item.difficulty,
            tutorialCount=item.tutorial_count,
            skillCount=item.skill_count,
            isHot=item.is_hot,
            isEnabled=item.is_enabled,
            sortOrder=item.sort_order,
            createdAt=item.created_at,
            updatedAt=item.updated_at,
        )

    def get_category_list(self, query: AdminTutorialCategoryQueryIn) -> AdminTutorialCategoryListOut:
        rows = self.db.scalars(
            select(TutorialCategory)
            .where(TutorialCategory.deleted_at.is_(None))
            .order_by(TutorialCategory.sort_order.asc(), TutorialCategory.created_at.asc())
        ).all()
        items = [self._map_admin_category(item) for item in rows]

        if query.q:
            keyword = query.q.strip().lower()
            items = [
                item
                for item in items
                if keyword in item.name.lower()
                or keyword in item.slug.lower()
                or keyword in item.description.lower()
            ]

        if query.status == "enabled":
            items = [item for item in items if item.isEnabled]
        elif query.status == "disabled":
            items = [item for item in items if not item.isEnabled]

        total = len(items)
        start = (query.page - 1) * query.pageSize
        end = start + query.pageSize
        return AdminTutorialCategoryListOut(
            list=items[start:end],
            pagination=AdminPaginationOut.from_total(query.page, query.pageSize, total),
        )

    def get_category_stats(self) -> AdminTutorialCategoryStatsOut:
        rows = self.db.scalars(select(TutorialCategory).where(TutorialCategory.deleted_at.is_(None))).all()
        return AdminTutorialCategoryStatsOut(
            totalCategories=len(rows),
            enabledCategories=sum(1 for item in rows if item.is_enabled),
            disabledCategories=sum(1 for item in rows if not item.is_enabled),
            totalTutorials=sum(item.tutorial_count for item in rows),
        )

    def get_category_detail(self, category_id: str) -> AdminTutorialCategoryOut:
        category = self._get_category_or_404(category_id)
        return self._map_admin_category(category)

    def create_category(self, payload: AdminTutorialCategoryIn) -> AdminTutorialCategoryOut:
        exists = self.db.scalar(
            select(TutorialCategory).where(TutorialCategory.slug == payload.slug, TutorialCategory.deleted_at.is_(None))
        )
        if exists is not None:
            raise HTTPException(status_code=400, detail="category slug already exists")
        category = TutorialCategory(
            name=payload.name,
            slug=payload.slug,
            icon=payload.icon,
            color=payload.color,
            description=payload.description,
            category_group=payload.group,
            scene=payload.scene,
            difficulty=payload.difficulty,
            sort_order=payload.sortOrder,
            is_hot=payload.isHot,
            is_enabled=payload.isEnabled,
        )
        self.db.add(category)
        self.db.flush()
        self._write_log(
            "tutorial_category",
            "tutorial_category_create",
            category.id,
            category.name,
            None,
            {"slug": category.slug, "group": category.category_group, "scene": category.scene},
        )
        self.db.commit()
        return self._map_admin_category(category)

    def update_category(self, category_id: str, payload: AdminTutorialCategoryIn) -> AdminTutorialCategoryOut:
        category = self._get_category_or_404(category_id)
        exists = self.db.scalar(
            select(TutorialCategory).where(
                TutorialCategory.slug == payload.slug,
                TutorialCategory.deleted_at.is_(None),
                TutorialCategory.id != category.id,
            )
        )
        if exists is not None:
            raise HTTPException(status_code=400, detail="category slug already exists")
        before = {
            "name": category.name,
            "slug": category.slug,
            "group": category.category_group,
            "scene": category.scene,
            "difficulty": category.difficulty,
            "isHot": category.is_hot,
            "isEnabled": category.is_enabled,
        }
        category.name = payload.name
        category.slug = payload.slug
        category.icon = payload.icon
        category.color = payload.color
        category.description = payload.description
        category.category_group = payload.group
        category.scene = payload.scene
        category.difficulty = payload.difficulty
        category.sort_order = payload.sortOrder
        category.is_hot = payload.isHot
        category.is_enabled = payload.isEnabled
        self._write_log(
            "tutorial_category",
            "tutorial_category_update",
            category.id,
            category.name,
            before,
            {
                "name": category.name,
                "slug": category.slug,
                "group": category.category_group,
                "scene": category.scene,
                "difficulty": category.difficulty,
                "isHot": category.is_hot,
                "isEnabled": category.is_enabled,
            },
        )
        self.db.commit()
        return self._map_admin_category(category)

    def delete_category(self, category_id: str) -> None:
        category = self._get_category_or_404(category_id)
        in_use = int(
            self.db.scalar(
                select(func.count(Tutorial.id)).where(
                    Tutorial.category_id == category.id,
                    Tutorial.deleted_at.is_(None),
                )
            )
            or 0
        )
        if in_use > 0:
            raise HTTPException(status_code=400, detail="category still has tutorials")
        before = {"name": category.name, "slug": category.slug}
        category.deleted_at = datetime.now(timezone.utc)
        self._write_log("tutorial_category", "tutorial_category_delete", category.id, category.name, before, None)
        self.db.commit()

    def enable_category(self, category_id: str) -> AdminTutorialCategoryOut:
        category = self._get_category_or_404(category_id)
        category.is_enabled = True
        self._write_log("tutorial_category", "tutorial_category_enable", category.id, category.name, {"isEnabled": False}, {"isEnabled": True})
        self.db.commit()
        return self._map_admin_category(category)

    def disable_category(self, category_id: str) -> AdminTutorialCategoryOut:
        category = self._get_category_or_404(category_id)
        category.is_enabled = False
        self._write_log("tutorial_category", "tutorial_category_disable", category.id, category.name, {"isEnabled": True}, {"isEnabled": False})
        self.db.commit()
        return self._map_admin_category(category)

    def sort_categories(self, payload: AdminTutorialCategorySortIn) -> List[AdminTutorialCategoryOut]:
        id_map = {
            str(item.id): item
            for item in self.db.scalars(
                select(TutorialCategory).where(TutorialCategory.deleted_at.is_(None))
            ).all()
        }
        for row in payload.items:
            category = id_map.get(row.id)
            if category is None:
                raise HTTPException(status_code=404, detail="tutorial category not found")
            category.sort_order = row.sortOrder
        self._write_log("tutorial_category", "tutorial_category_sort", None, "tutorial_categories", None, {"count": len(payload.items)})
        self.db.commit()
        rows = self.db.scalars(
            select(TutorialCategory)
            .where(TutorialCategory.deleted_at.is_(None))
            .order_by(TutorialCategory.sort_order.asc(), TutorialCategory.created_at.asc())
        ).all()
        return [self._map_admin_category(item) for item in rows]

    def list_tags(self) -> List[AdminTutorialTagListItemOut]:
        rows = self.db.scalars(
            select(TutorialTag)
            .where(TutorialTag.deleted_at.is_(None))
            .order_by(TutorialTag.sort_order.asc(), TutorialTag.created_at.asc())
        ).all()
        return [
            AdminTutorialTagListItemOut(
                id=str(item.id),
                name=item.name,
                slug=item.slug,
                tutorialCount=item.tutorial_count,
                isHot=item.is_hot,
                isEnabled=item.is_enabled,
                sortOrder=item.sort_order,
                createdAt=item.created_at,
                updatedAt=item.updated_at,
            )
            for item in rows
        ]

    def create_tag(self, payload: AdminTutorialTagIn) -> AdminTutorialTagListItemOut:
        exists = self.db.scalar(select(TutorialTag).where(TutorialTag.slug == payload.slug, TutorialTag.deleted_at.is_(None)))
        if exists is not None:
            raise HTTPException(status_code=400, detail="tag slug already exists")
        tag = TutorialTag(
            name=payload.name,
            slug=payload.slug,
            sort_order=payload.sortOrder,
            is_enabled=payload.isEnabled,
            is_hot=payload.isHot,
        )
        self.db.add(tag)
        self.db.flush()
        self._write_log("tutorial_tag", "tutorial_tag_create", tag.id, tag.name, None, {"slug": tag.slug})
        self.db.commit()
        return AdminTutorialTagListItemOut(
            id=str(tag.id),
            name=tag.name,
            slug=tag.slug,
            tutorialCount=tag.tutorial_count,
            isHot=tag.is_hot,
            isEnabled=tag.is_enabled,
            sortOrder=tag.sort_order,
            createdAt=tag.created_at,
            updatedAt=tag.updated_at,
        )

    def update_tag(self, tag_id: str, payload: AdminTutorialTagIn) -> AdminTutorialTagListItemOut:
        tag = self.db.get(TutorialTag, self._parse_uuid(tag_id, "tagId"))
        if tag is None or tag.deleted_at is not None:
            raise HTTPException(status_code=404, detail="tutorial tag not found")
        exists = self.db.scalar(
            select(TutorialTag).where(
                TutorialTag.slug == payload.slug,
                TutorialTag.deleted_at.is_(None),
                TutorialTag.id != tag.id,
            )
        )
        if exists is not None:
            raise HTTPException(status_code=400, detail="tag slug already exists")
        before = {"name": tag.name, "slug": tag.slug}
        tag.name = payload.name
        tag.slug = payload.slug
        tag.sort_order = payload.sortOrder
        tag.is_enabled = payload.isEnabled
        tag.is_hot = payload.isHot
        self._write_log("tutorial_tag", "tutorial_tag_update", tag.id, tag.name, before, {"name": tag.name, "slug": tag.slug})
        self.db.commit()
        return AdminTutorialTagListItemOut(
            id=str(tag.id),
            name=tag.name,
            slug=tag.slug,
            tutorialCount=tag.tutorial_count,
            isHot=tag.is_hot,
            isEnabled=tag.is_enabled,
            sortOrder=tag.sort_order,
            createdAt=tag.created_at,
            updatedAt=tag.updated_at,
        )

    def delete_tag(self, tag_id: str) -> None:
        tag = self.db.get(TutorialTag, self._parse_uuid(tag_id, "tagId"))
        if tag is None or tag.deleted_at is not None:
            raise HTTPException(status_code=404, detail="tutorial tag not found")
        before = {"name": tag.name, "slug": tag.slug}
        tag.deleted_at = datetime.now(timezone.utc)
        self._write_log("tutorial_tag", "tutorial_tag_delete", tag.id, tag.name, before, None)
        self.db.commit()

    def list_learning_paths(self) -> List[AdminLearningPathOut]:
        rows = self.db.scalars(
            select(LearningPath)
            .where(LearningPath.deleted_at.is_(None))
            .order_by(LearningPath.sort_order.asc(), LearningPath.created_at.asc())
        ).all()
        return [
            AdminLearningPathOut(
                id=str(item.id),
                title=item.title,
                slug=item.slug,
                description=item.description,
                icon=item.icon,
                tutorialCount=item.tutorial_count,
                isEnabled=item.is_enabled,
                sortOrder=item.sort_order,
                createdAt=item.created_at,
                updatedAt=item.updated_at,
            )
            for item in rows
        ]

    def create_learning_path(self, payload: AdminLearningPathIn) -> AdminLearningPathOut:
        exists = self.db.scalar(
            select(LearningPath).where(LearningPath.slug == payload.slug, LearningPath.deleted_at.is_(None))
        )
        if exists is not None:
            raise HTTPException(status_code=400, detail="learning path slug already exists")
        learning_path = LearningPath(
            title=payload.title,
            slug=payload.slug,
            description=payload.description,
            icon=payload.icon,
            sort_order=payload.sortOrder,
            is_enabled=payload.isEnabled,
        )
        self.db.add(learning_path)
        self.db.flush()
        self._write_log(
            "learning_path",
            "learning_path_create",
            learning_path.id,
            learning_path.title,
            None,
            {"slug": learning_path.slug},
        )
        self.db.commit()
        return AdminLearningPathOut(
            id=str(learning_path.id),
            title=learning_path.title,
            slug=learning_path.slug,
            description=learning_path.description,
            icon=learning_path.icon,
            tutorialCount=learning_path.tutorial_count,
            isEnabled=learning_path.is_enabled,
            sortOrder=learning_path.sort_order,
            createdAt=learning_path.created_at,
            updatedAt=learning_path.updated_at,
        )

    def update_learning_path(self, learning_path_id: str, payload: AdminLearningPathIn) -> AdminLearningPathOut:
        learning_path = self._get_learning_path_or_404(learning_path_id)
        exists = self.db.scalar(
            select(LearningPath).where(
                LearningPath.slug == payload.slug,
                LearningPath.deleted_at.is_(None),
                LearningPath.id != learning_path.id,
            )
        )
        if exists is not None:
            raise HTTPException(status_code=400, detail="learning path slug already exists")
        before = {"title": learning_path.title, "slug": learning_path.slug}
        learning_path.title = payload.title
        learning_path.slug = payload.slug
        learning_path.description = payload.description
        learning_path.icon = payload.icon
        learning_path.sort_order = payload.sortOrder
        learning_path.is_enabled = payload.isEnabled
        self._write_log(
            "learning_path",
            "learning_path_update",
            learning_path.id,
            learning_path.title,
            before,
            {"title": learning_path.title, "slug": learning_path.slug},
        )
        self.db.commit()
        return AdminLearningPathOut(
            id=str(learning_path.id),
            title=learning_path.title,
            slug=learning_path.slug,
            description=learning_path.description,
            icon=learning_path.icon,
            tutorialCount=learning_path.tutorial_count,
            isEnabled=learning_path.is_enabled,
            sortOrder=learning_path.sort_order,
            createdAt=learning_path.created_at,
            updatedAt=learning_path.updated_at,
        )

    def delete_learning_path(self, learning_path_id: str) -> None:
        learning_path = self._get_learning_path_or_404(learning_path_id)
        before = {"title": learning_path.title, "slug": learning_path.slug}
        learning_path.deleted_at = datetime.now(timezone.utc)
        self._write_log("learning_path", "learning_path_delete", learning_path.id, learning_path.title, before, None)
        self.db.commit()

    def get_operation_logs(self, query: AdminOperationLogQueryIn) -> AdminOperationLogListOut:
        stmt = (
            select(AdminOperationLog)
            .order_by(AdminOperationLog.created_at.desc())
        )
        if query.module:
            stmt = stmt.where(AdminOperationLog.module == query.module)
        if query.action:
            stmt = stmt.where(AdminOperationLog.action == query.action)

        rows = self.db.scalars(stmt).all()
        total = len(rows)
        start = (query.page - 1) * query.pageSize
        end = start + query.pageSize
        items = rows[start:end]
        return AdminOperationLogListOut(
            list=[
                AdminOperationLogListItemOut(
                    id=str(item.id),
                    operatorName=item.operator_name,
                    module=item.module,
                    action=item.action,
                    targetId=str(item.target_id) if item.target_id else None,
                    targetTitle=item.target_title,
                    beforeData=item.before_data,
                    afterData=item.after_data,
                    createdAt=item.created_at,
                )
                for item in items
            ],
            pagination=AdminPaginationOut.from_total(query.page, query.pageSize, total),
        )
