from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.admin_common.deps import get_current_admin
from app.modules.admin_common.permissions import require_permission
from app.modules.admin_common.response import page_response


router = APIRouter()


@router.get("/notifications")
def list_notifications(
    q: Optional[str] = None,
    type: Optional[str] = None,
    isRead: Optional[bool] = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "notification:read")
    where = ["1=1"]
    params: Dict[str, object] = {"limit": pageSize, "offset": (page - 1) * pageSize}
    if type:
        where.append("n.type = :type")
        params["type"] = type
    if isRead is not None:
        where.append("n.is_read = :is_read")
        params["is_read"] = isRead
    if q:
        where.append("(n.title ILIKE :q OR n.content ILIKE :q OR u.email ILIKE :q OR u.nickname ILIKE :q)")
        params["q"] = f"%{q.strip()}%"
    where_sql = " AND ".join(where)
    total = db.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM user_notifications n
            LEFT JOIN users u ON u.id = n.user_id
            WHERE {where_sql}
            """
        ),
        params,
    ).scalar() or 0
    rows = db.execute(
        text(
            f"""
            SELECT
              n.*,
              u.email AS user_email,
              u.nickname AS user_nickname
            FROM user_notifications n
            LEFT JOIN users u ON u.id = n.user_id
            WHERE {where_sql}
            ORDER BY n.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    return page_response([dict(row) for row in rows], page, pageSize, int(total))
