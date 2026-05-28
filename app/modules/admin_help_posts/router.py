from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success
from app.modules.admin_common.deps import get_current_admin
from app.modules.admin_common.permissions import require_permission
from app.modules.admin_common.response import page_response


router = APIRouter()


@router.get("")
def list_help_posts(
    q: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "help_post:read")
    where = ["h.deleted_at IS NULL"]
    params: Dict[str, object] = {"limit": pageSize, "offset": (page - 1) * pageSize}
    if q:
        where.append("(h.title ILIKE :q OR h.content ILIKE :q OR u.email ILIKE :q OR u.nickname ILIKE :q)")
        params["q"] = f"%{q.strip()}%"
    if status:
        where.append("h.status = :status")
        params["status"] = status
    where_sql = " AND ".join(where)
    total = db.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM help_posts h
            LEFT JOIN users u ON u.id = h.user_id
            WHERE {where_sql}
            """
        ),
        params,
    ).scalar() or 0
    rows = db.execute(
        text(
            f"""
            SELECT
              h.id,
              h.title,
              h.status,
              h.points_cost,
              h.reply_count,
              h.view_count,
              h.created_at,
              h.updated_at,
              u.id AS user_id,
              u.nickname AS user_nickname,
              u.email AS user_email
            FROM help_posts h
            LEFT JOIN users u ON u.id = h.user_id
            WHERE {where_sql}
            ORDER BY h.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    return page_response([dict(row) for row in rows], page, pageSize, int(total))


@router.get("/{post_id}")
def get_help_post(
    post_id: str,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "help_post:read")
    row = db.execute(
        text(
            """
            SELECT h.*, u.nickname AS user_nickname, u.email AS user_email
            FROM help_posts h
            LEFT JOIN users u ON u.id = h.user_id
            WHERE h.id = CAST(:id AS uuid) AND h.deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"id": post_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="求助帖不存在")
    return success(dict(row))
