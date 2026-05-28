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


@router.get("/operation-logs")
def list_operation_logs(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    action: Optional[str] = None,
    targetType: Optional[str] = None,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "operation_log:read")
    where = ["1=1"]
    params: Dict[str, object] = {"limit": pageSize, "offset": (page - 1) * pageSize}
    if action:
        where.append("action = :action")
        params["action"] = action
    if targetType:
        where.append("module = :module")
        params["module"] = targetType
    where_sql = " AND ".join(where)
    total = db.execute(
        text(f"SELECT COUNT(*) FROM admin_operation_logs WHERE {where_sql}"),
        params,
    ).scalar() or 0
    rows = db.execute(
        text(
            f"""
            SELECT
              id,
              action,
              module,
              target_id,
              target_title,
              before_data,
              after_data,
              ip,
              user_agent,
              created_at,
              operator_name
            FROM admin_operation_logs
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    items = []
    for row in rows:
        items.append(
            {
                "id": row["id"],
                "action": row["action"],
                "target_type": row["module"],
                "target_id": str(row["target_id"]) if row["target_id"] else None,
                "detail": {
                    "targetTitle": row["target_title"],
                    "beforeData": row["before_data"],
                    "afterData": row["after_data"],
                },
                "ip": row["ip"],
                "user_agent": row["user_agent"],
                "created_at": row["created_at"],
                "admin_username": row["operator_name"],
                "admin_nickname": row["operator_name"],
            }
        )
    return page_response(items, page, pageSize, int(total))
