from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.admin_skill_taxonomy.schemas import (
    AdminPaginationOut,
    AdminSkillCategoryIn,
    AdminSkillCategoryListOut,
    AdminSkillCategoryOut,
    AdminSkillCategoryQueryIn,
    AdminSkillCategoryStatsOut,
    AdminSkillTagIn,
    AdminSkillTagOut,
)
from app.modules.category.models import Category
from app.modules.skill.models import Skill, SkillCategoryRelation, SkillTag, Tag
from app.modules.skill_submissions.models import SkillSubmission
from app.modules.tutorial.models import AdminOperationLog


DEFAULT_OPERATOR_NAME = "Local Admin"


class AdminSkillTaxonomyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _parse_uuid(self, value: str, field_name: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"invalid {field_name}") from exc

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

    def _category_rows(self) -> list[Category]:
        return self.db.scalars(
            select(Category)
            .where(Category.deleted_at.is_(None))
            .order_by(Category.level.asc(), Category.sort_order.asc(), Category.created_at.asc())
        ).all()

    def _category_skill_count_map(self) -> dict[UUID, int]:
        relation_rows = self.db.execute(
            select(SkillCategoryRelation.category_id, func.count(func.distinct(SkillCategoryRelation.skill_id)))
            .join(Skill, Skill.id == SkillCategoryRelation.skill_id)
            .where(Skill.deleted_at.is_(None))
            .group_by(SkillCategoryRelation.category_id)
        ).all()
        counts = {category_id: int(total or 0) for category_id, total in relation_rows}

        direct_rows = self.db.execute(
            select(Skill.category_id, func.count(func.distinct(Skill.id)))
            .where(Skill.deleted_at.is_(None), Skill.category_id.is_not(None))
            .group_by(Skill.category_id)
        ).all()
        for category_id, total in direct_rows:
            if category_id not in counts:
                counts[category_id] = int(total or 0)
        return counts

    def _tag_skill_count_map(self) -> dict[UUID, int]:
        rows = self.db.execute(
            select(SkillTag.tag_id, func.count(func.distinct(SkillTag.skill_id)))
            .join(Skill, Skill.id == SkillTag.skill_id)
            .where(Skill.deleted_at.is_(None))
            .group_by(SkillTag.tag_id)
        ).all()
        return {tag_id: int(total or 0) for tag_id, total in rows}

    def _get_category_or_404(self, category_id: str) -> Category:
        category = self.db.get(Category, self._parse_uuid(category_id, "categoryId"))
        if category is None or category.deleted_at is not None:
            raise HTTPException(status_code=404, detail="skill category not found")
        return category

    def _get_tag_or_404(self, tag_id: str) -> Tag:
        tag = self.db.get(Tag, self._parse_uuid(tag_id, "tagId"))
        if tag is None or tag.deleted_at is not None:
            raise HTTPException(status_code=404, detail="skill tag not found")
        return tag

    def _normalize_parent(self, parent_id: Optional[str], current_id: Optional[UUID] = None) -> tuple[Optional[UUID], int, Optional[Category]]:
        if not parent_id:
            return None, 1, None
        parent = self._get_category_or_404(parent_id)
        if current_id is not None and parent.id == current_id:
            raise HTTPException(status_code=400, detail="parent category cannot be self")
        if int(parent.level or 1) >= 2:
            raise HTTPException(status_code=400, detail="only two category levels are supported")
        return parent.id, int(parent.level or 1) + 1, parent

    def _map_category(
        self,
        category: Category,
        parent_map: dict[UUID, Category],
        skill_counts: dict[UUID, int],
    ) -> AdminSkillCategoryOut:
        parent = parent_map.get(category.parent_id) if category.parent_id else None
        return AdminSkillCategoryOut(
            id=str(category.id),
            name=category.name,
            slug=category.slug,
            nameEn=category.name_en,
            parentId=str(category.parent_id) if category.parent_id else None,
            parentName=parent.name if parent else None,
            level=int(category.level or 1),
            icon=category.icon,
            color=category.color,
            description=category.description,
            skillCount=skill_counts.get(category.id, int(category.skill_count or 0)),
            isEnabled=category.is_enabled,
            isHot=category.is_hot,
            sortOrder=category.sort_order,
            createdAt=category.created_at,
            updatedAt=category.updated_at,
        )

    def get_category_list(self, query: AdminSkillCategoryQueryIn) -> AdminSkillCategoryListOut:
        rows = self._category_rows()
        parent_map = {item.id: item for item in rows}
        skill_counts = self._category_skill_count_map()
        items = [self._map_category(item, parent_map, skill_counts) for item in rows]

        if query.q:
            keyword = query.q.strip().lower()
            items = [
                item
                for item in items
                if keyword in item.name.lower()
                or keyword in item.slug.lower()
                or keyword in (item.nameEn or "").lower()
                or keyword in item.description.lower()
                or keyword in (item.parentName or "").lower()
            ]
        if query.status == "enabled":
            items = [item for item in items if item.isEnabled]
        elif query.status == "disabled":
            items = [item for item in items if not item.isEnabled]

        total = len(items)
        start = (query.page - 1) * query.pageSize
        end = start + query.pageSize
        return AdminSkillCategoryListOut(
            list=items[start:end],
            pagination=AdminPaginationOut.from_total(query.page, query.pageSize, total),
        )

    def get_category_stats(self) -> AdminSkillCategoryStatsOut:
        rows = self._category_rows()
        return AdminSkillCategoryStatsOut(
            totalCategories=len(rows),
            enabledCategories=sum(1 for item in rows if item.is_enabled),
            disabledCategories=sum(1 for item in rows if not item.is_enabled),
            rootCategories=sum(1 for item in rows if int(item.level or 1) == 1),
            childCategories=sum(1 for item in rows if int(item.level or 1) > 1),
        )

    def get_category_detail(self, category_id: str) -> AdminSkillCategoryOut:
        category = self._get_category_or_404(category_id)
        rows = self._category_rows()
        parent_map = {item.id: item for item in rows}
        skill_counts = self._category_skill_count_map()
        return self._map_category(category, parent_map, skill_counts)

    def create_category(self, payload: AdminSkillCategoryIn) -> AdminSkillCategoryOut:
        exists = self.db.scalar(
            select(Category).where(Category.slug == payload.slug, Category.deleted_at.is_(None))
        )
        if exists is not None:
            raise HTTPException(status_code=400, detail="category slug already exists")
        parent_id, level, parent = self._normalize_parent(payload.parentId)
        category = Category(
            name=payload.name.strip(),
            slug=payload.slug.strip(),
            name_en=(payload.nameEn or "").strip() or None,
            parent_id=parent_id,
            level=level,
            icon=payload.icon.strip(),
            color=payload.color.strip(),
            description=payload.description.strip(),
            sort_order=payload.sortOrder,
            is_hot=payload.isHot,
            is_enabled=payload.isEnabled,
        )
        self.db.add(category)
        self.db.flush()
        self._write_log(
            "skill_category",
            "skill_category_create",
            category.id,
            category.name,
            None,
            {
                "slug": category.slug,
                "parentId": str(parent_id) if parent_id else None,
                "parentName": parent.name if parent else None,
                "level": level,
            },
        )
        self.db.commit()
        return self.get_category_detail(str(category.id))

    def update_category(self, category_id: str, payload: AdminSkillCategoryIn) -> AdminSkillCategoryOut:
        category = self._get_category_or_404(category_id)
        exists = self.db.scalar(
            select(Category).where(
                Category.slug == payload.slug,
                Category.deleted_at.is_(None),
                Category.id != category.id,
            )
        )
        if exists is not None:
            raise HTTPException(status_code=400, detail="category slug already exists")
        parent_id, level, parent = self._normalize_parent(payload.parentId, category.id)
        before = {
            "name": category.name,
            "slug": category.slug,
            "nameEn": category.name_en,
            "parentId": str(category.parent_id) if category.parent_id else None,
            "level": int(category.level or 1),
            "isEnabled": category.is_enabled,
        }
        category.name = payload.name.strip()
        category.slug = payload.slug.strip()
        category.name_en = (payload.nameEn or "").strip() or None
        category.parent_id = parent_id
        category.level = level
        category.icon = payload.icon.strip()
        category.color = payload.color.strip()
        category.description = payload.description.strip()
        category.sort_order = payload.sortOrder
        category.is_hot = payload.isHot
        category.is_enabled = payload.isEnabled
        self._write_log(
            "skill_category",
            "skill_category_update",
            category.id,
            category.name,
            before,
            {
                "name": category.name,
                "slug": category.slug,
                "nameEn": category.name_en,
                "parentId": str(parent_id) if parent_id else None,
                "parentName": parent.name if parent else None,
                "level": level,
                "isEnabled": category.is_enabled,
            },
        )
        self.db.commit()
        return self.get_category_detail(str(category.id))

    def delete_category(self, category_id: str) -> None:
        category = self._get_category_or_404(category_id)
        child_exists = self.db.scalar(
            select(Category.id).where(Category.parent_id == category.id, Category.deleted_at.is_(None)).limit(1)
        )
        if child_exists is not None:
            raise HTTPException(status_code=400, detail="category still has child categories")
        skill_in_use = self.db.scalar(
            select(func.count(func.distinct(Skill.id)))
            .where(
                Skill.deleted_at.is_(None),
                or_(
                    Skill.category_id == category.id,
                    Skill.id.in_(
                        select(SkillCategoryRelation.skill_id).where(
                            SkillCategoryRelation.category_id == category.id
                        )
                    ),
                ),
            )
        ) or 0
        if int(skill_in_use) > 0:
            raise HTTPException(status_code=400, detail="category still has skills")
        submission_in_use = self.db.scalar(
            select(func.count(SkillSubmission.id)).where(
                SkillSubmission.deleted_at.is_(None),
                or_(
                    SkillSubmission.category_id == category.id,
                    SkillSubmission.category_ids.contains([str(category.id)]),
                ),
            )
        ) or 0
        if int(submission_in_use) > 0:
            raise HTTPException(status_code=400, detail="category still has skill submissions")
        before = {"name": category.name, "slug": category.slug}
        category.deleted_at = datetime.now(timezone.utc)
        self._write_log("skill_category", "skill_category_delete", category.id, category.name, before, None)
        self.db.commit()

    def enable_category(self, category_id: str) -> AdminSkillCategoryOut:
        category = self._get_category_or_404(category_id)
        category.is_enabled = True
        self._write_log("skill_category", "skill_category_enable", category.id, category.name, {"isEnabled": False}, {"isEnabled": True})
        self.db.commit()
        return self.get_category_detail(category_id)

    def disable_category(self, category_id: str) -> AdminSkillCategoryOut:
        category = self._get_category_or_404(category_id)
        category.is_enabled = False
        self._write_log("skill_category", "skill_category_disable", category.id, category.name, {"isEnabled": True}, {"isEnabled": False})
        self.db.commit()
        return self.get_category_detail(category_id)

    def list_tags(self, tag_type: Optional[str] = None) -> list[AdminSkillTagOut]:
        stmt = select(Tag).where(Tag.deleted_at.is_(None), Tag.type.in_(("scene", "type")))
        if tag_type:
            stmt = stmt.where(Tag.type == tag_type)
        rows = self.db.scalars(
            stmt.order_by(Tag.type.asc(), Tag.sort_order.asc(), Tag.created_at.asc())
        ).all()
        skill_counts = self._tag_skill_count_map()
        return [
            AdminSkillTagOut(
                id=str(item.id),
                name=item.name,
                slug=item.slug,
                type=item.type,
                skillCount=skill_counts.get(item.id, int(item.skill_count or 0)),
                isEnabled=item.is_enabled,
                sortOrder=item.sort_order,
                createdAt=item.created_at,
                updatedAt=item.updated_at,
            )
            for item in rows
        ]

    def create_tag(self, payload: AdminSkillTagIn) -> AdminSkillTagOut:
        exists = self.db.scalar(select(Tag).where(Tag.slug == payload.slug, Tag.deleted_at.is_(None)))
        if exists is not None:
            raise HTTPException(status_code=400, detail="tag slug already exists")
        tag = Tag(
            name=payload.name.strip(),
            slug=payload.slug.strip(),
            type=payload.type,
            sort_order=payload.sortOrder,
            is_enabled=payload.isEnabled,
        )
        self.db.add(tag)
        self.db.flush()
        self._write_log(
            "skill_tag",
            "skill_tag_create",
            tag.id,
            tag.name,
            None,
            {"slug": tag.slug, "type": tag.type},
        )
        self.db.commit()
        return AdminSkillTagOut(
            id=str(tag.id),
            name=tag.name,
            slug=tag.slug,
            type=tag.type,
            skillCount=int(tag.skill_count or 0),
            isEnabled=tag.is_enabled,
            sortOrder=tag.sort_order,
            createdAt=tag.created_at,
            updatedAt=tag.updated_at,
        )

    def update_tag(self, tag_id: str, payload: AdminSkillTagIn) -> AdminSkillTagOut:
        tag = self._get_tag_or_404(tag_id)
        exists = self.db.scalar(
            select(Tag).where(
                Tag.slug == payload.slug,
                Tag.deleted_at.is_(None),
                Tag.id != tag.id,
            )
        )
        if exists is not None:
            raise HTTPException(status_code=400, detail="tag slug already exists")
        before = {"name": tag.name, "slug": tag.slug, "type": tag.type, "isEnabled": tag.is_enabled}
        tag.name = payload.name.strip()
        tag.slug = payload.slug.strip()
        tag.type = payload.type
        tag.sort_order = payload.sortOrder
        tag.is_enabled = payload.isEnabled
        self._write_log(
            "skill_tag",
            "skill_tag_update",
            tag.id,
            tag.name,
            before,
            {"name": tag.name, "slug": tag.slug, "type": tag.type, "isEnabled": tag.is_enabled},
        )
        self.db.commit()
        return AdminSkillTagOut(
            id=str(tag.id),
            name=tag.name,
            slug=tag.slug,
            type=tag.type,
            skillCount=self._tag_skill_count_map().get(tag.id, int(tag.skill_count or 0)),
            isEnabled=tag.is_enabled,
            sortOrder=tag.sort_order,
            createdAt=tag.created_at,
            updatedAt=tag.updated_at,
        )

    def delete_tag(self, tag_id: str) -> None:
        tag = self._get_tag_or_404(tag_id)
        skill_in_use = self.db.scalar(
            select(func.count(func.distinct(SkillTag.skill_id))).where(SkillTag.tag_id == tag.id)
        ) or 0
        if int(skill_in_use) > 0:
            raise HTTPException(status_code=400, detail="tag still has skills")
        before = {"name": tag.name, "slug": tag.slug, "type": tag.type}
        tag.deleted_at = datetime.now(timezone.utc)
        self._write_log("skill_tag", "skill_tag_delete", tag.id, tag.name, before, None)
        self.db.commit()
