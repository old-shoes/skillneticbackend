from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success
from app.modules.admin_common.deps import get_current_admin
from app.modules.admin_common.permissions import require_permission
from app.modules.admin_common.response import page_response
from app.modules.github_skills.models import SkillGithubSource
from app.modules.skill.models import Skill


router = APIRouter()


@router.get("")
def list_skills(
    q: Optional[str] = None,
    categoryId: Optional[str] = None,
    status: Optional[str] = None,
    isFeatured: Optional[bool] = None,
    isHot: Optional[bool] = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "skill:read")
    where = ["s.deleted_at IS NULL"]
    params: Dict[str, object] = {"limit": pageSize, "offset": (page - 1) * pageSize}
    if q:
        where.append("(s.title ILIKE :q OR s.summary ILIKE :q)")
        params["q"] = f"%{q.strip()}%"
    if categoryId:
        where.append("s.category_id = CAST(:category_id AS uuid)")
        params["category_id"] = categoryId
    if status:
        where.append("s.status = :status")
        params["status"] = status
    if isFeatured is not None:
        where.append("s.is_featured = :is_featured")
        params["is_featured"] = isFeatured
    if isHot is not None:
        where.append("s.is_hot = :is_hot")
        params["is_hot"] = isHot
    where_sql = " AND ".join(where)
    total = db.execute(text(f"SELECT COUNT(*) FROM skills s WHERE {where_sql}"), params).scalar() or 0
    rows = db.execute(
        text(
            f"""
            SELECT
              s.id,
              s.title,
              s.slug,
              s.summary,
              s.cover_icon AS cover_image,
              s.status,
              s.view_count,
              s.favorite_count,
              s.is_featured,
              s.is_hot,
              s.published_at,
              s.updated_at,
              c.name AS category_name
            FROM skills s
            LEFT JOIN categories c ON c.id = s.category_id
            WHERE {where_sql}
            ORDER BY s.updated_at DESC, s.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    return page_response([dict(row) for row in rows], page, pageSize, int(total))


@router.get("/{skill_id}")
def get_skill(
    skill_id: str,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "skill:read")
    row = db.execute(
        text(
            """
            SELECT s.*, c.name AS category_name
            FROM skills s
            LEFT JOIN categories c ON c.id = s.category_id
            WHERE s.id = CAST(:skill_id AS uuid) AND s.deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"skill_id": skill_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Skill 不存在")
    return success(dict(row))


@router.delete("/{skill_id}")
def delete_skill(
    skill_id: str,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "skill:write")
    skill = db.get(Skill, skill_id)
    if skill is None or skill.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Skill 不存在")

    skill.deleted_at = datetime.now(timezone.utc)
    if skill.status == "published":
        skill.status = "deleted"
    db.add(skill)

    sources = db.query(SkillGithubSource).filter(SkillGithubSource.skill_id == skill.id).all()
    for source in sources:
        source.skill_id = None
        db.add(source)

    db.commit()
    return success({"success": True})
