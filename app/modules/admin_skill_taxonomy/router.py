from typing import Iterable, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success
from app.modules.admin_skill_taxonomy.schemas import (
    AdminSkillCategoryIn,
    AdminSkillCategoryQueryIn,
    AdminSkillTagIn,
)
from app.modules.admin_skill_taxonomy.service import AdminSkillTaxonomyService


router = APIRouter()


CATEGORY_VIEW_ROLES = {"super_admin", "content_admin", "editor"}
CATEGORY_MANAGE_ROLES = {"super_admin", "content_admin"}


def require_category_role(allowed_roles: Iterable[str]):
    allowed = set(allowed_roles)

    def dependency(x_admin_role: str = Header(default="content_admin", alias="X-Admin-Role")) -> str:
        role = (x_admin_role or "").strip()
        if role not in CATEGORY_VIEW_ROLES:
            raise HTTPException(status_code=403, detail="forbidden")
        if role not in allowed:
            raise HTTPException(status_code=403, detail="forbidden")
        return role

    return dependency


@router.get("/skill-categories")
def get_admin_skill_categories(
    q: str = Query(default=None),
    status: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    _: str = Depends(require_category_role(CATEGORY_VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    query = AdminSkillCategoryQueryIn(q=q, status=status, page=page, pageSize=pageSize)
    data = AdminSkillTaxonomyService(db).get_category_list(query)
    return success(data.model_dump())


@router.get("/skill-categories/stats")
def get_admin_skill_category_stats(
    _: str = Depends(require_category_role(CATEGORY_VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminSkillTaxonomyService(db).get_category_stats()
    return success(data.model_dump())


@router.get("/skill-categories/{category_id}")
def get_admin_skill_category_detail(
    category_id: str,
    _: str = Depends(require_category_role(CATEGORY_VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminSkillTaxonomyService(db).get_category_detail(category_id)
    return success(data.model_dump())


@router.post("/skill-categories")
def create_admin_skill_category(
    payload: AdminSkillCategoryIn,
    _: str = Depends(require_category_role(CATEGORY_MANAGE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminSkillTaxonomyService(db).create_category(payload)
    return success(data.model_dump())


@router.patch("/skill-categories/{category_id}")
def update_admin_skill_category(
    category_id: str,
    payload: AdminSkillCategoryIn,
    _: str = Depends(require_category_role(CATEGORY_MANAGE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminSkillTaxonomyService(db).update_category(category_id, payload)
    return success(data.model_dump())


@router.delete("/skill-categories/{category_id}")
def delete_admin_skill_category(
    category_id: str,
    _: str = Depends(require_category_role(CATEGORY_MANAGE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    AdminSkillTaxonomyService(db).delete_category(category_id)
    return success({"ok": True})


@router.post("/skill-categories/{category_id}/enable")
def enable_admin_skill_category(
    category_id: str,
    _: str = Depends(require_category_role(CATEGORY_MANAGE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminSkillTaxonomyService(db).enable_category(category_id)
    return success(data.model_dump())


@router.post("/skill-categories/{category_id}/disable")
def disable_admin_skill_category(
    category_id: str,
    _: str = Depends(require_category_role(CATEGORY_MANAGE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminSkillTaxonomyService(db).disable_category(category_id)
    return success(data.model_dump())


@router.get("/skill-tags")
def get_admin_skill_tags(
    type: Optional[str] = Query(default=None),
    _: str = Depends(require_category_role(CATEGORY_VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminSkillTaxonomyService(db).list_tags(type)
    return success([item.model_dump() for item in data])


@router.post("/skill-tags")
def create_admin_skill_tag(
    payload: AdminSkillTagIn,
    _: str = Depends(require_category_role(CATEGORY_MANAGE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminSkillTaxonomyService(db).create_tag(payload)
    return success(data.model_dump())


@router.patch("/skill-tags/{tag_id}")
def update_admin_skill_tag(
    tag_id: str,
    payload: AdminSkillTagIn,
    _: str = Depends(require_category_role(CATEGORY_MANAGE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminSkillTaxonomyService(db).update_tag(tag_id, payload)
    return success(data.model_dump())


@router.delete("/skill-tags/{tag_id}")
def delete_admin_skill_tag(
    tag_id: str,
    _: str = Depends(require_category_role(CATEGORY_MANAGE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    AdminSkillTaxonomyService(db).delete_tag(tag_id)
    return success({"ok": True})
