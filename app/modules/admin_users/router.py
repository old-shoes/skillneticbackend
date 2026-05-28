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
def list_users(
    q: Optional[str] = None,
    status: Optional[str] = None,
    githubConnected: Optional[bool] = None,
    minPoints: Optional[int] = None,
    maxPoints: Optional[int] = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "user:read")
    where = ["u.deleted_at IS NULL"]
    params: Dict[str, object] = {"limit": pageSize, "offset": (page - 1) * pageSize}
    if q:
        where.append("(u.email ILIKE :q OR u.nickname ILIKE :q)")
        params["q"] = f"%{q.strip()}%"
    if status == "active":
        where.append("u.is_active = TRUE")
    elif status == "disabled":
        where.append("u.is_active = FALSE")
    if githubConnected is not None:
        where.append("u.github_connected = :github_connected")
        params["github_connected"] = githubConnected
    if minPoints is not None:
        where.append("u.points >= :min_points")
        params["min_points"] = minPoints
    if maxPoints is not None:
        where.append("u.points <= :max_points")
        params["max_points"] = maxPoints
    where_sql = " AND ".join(where)
    total = db.execute(text(f"SELECT COUNT(*) FROM users u WHERE {where_sql}"), params).scalar() or 0
    rows = db.execute(
        text(
            f"""
            SELECT
              u.id,
              u.email,
              u.nickname,
              u.avatar_url,
              u.points,
              u.email_verified,
              u.github_connected,
              u.is_active,
              u.created_at,
              u.last_login_at,
              (SELECT COUNT(*) FROM skill_submissions s WHERE s.submitter_id = u.id AND s.deleted_at IS NULL) AS submission_count,
              (SELECT COUNT(*) FROM user_favorites f WHERE f.user_id = u.id) AS favorite_count,
              (SELECT COUNT(*) FROM help_posts h WHERE h.user_id = u.id AND h.deleted_at IS NULL) AS help_post_count
            FROM users u
            WHERE {where_sql}
            ORDER BY u.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    return page_response([dict(row) for row in rows], page, pageSize, int(total))


@router.get("/{user_id}")
def get_user_detail(
    user_id: str,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "user:read")
    row = db.execute(
        text(
            """
            SELECT
              u.*,
              (SELECT COUNT(*) FROM skill_submissions s WHERE s.submitter_id = u.id AND s.deleted_at IS NULL) AS submission_count,
              (SELECT COUNT(*) FROM user_favorites f WHERE f.user_id = u.id) AS favorite_count,
              (SELECT COUNT(*) FROM help_posts h WHERE h.user_id = u.id AND h.deleted_at IS NULL) AS help_post_count
            FROM users u
            WHERE u.id = CAST(:user_id AS uuid) AND u.deleted_at IS NULL
            LIMIT 1
            """
        ),
        {"user_id": user_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return success(dict(row))


@router.get("/{user_id}/points")
def get_user_points(
    user_id: str,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "point:read")
    total = db.execute(
        text("SELECT COUNT(*) FROM user_point_logs WHERE user_id = CAST(:user_id AS uuid)"),
        {"user_id": user_id},
    ).scalar() or 0
    rows = db.execute(
        text(
            """
            SELECT *
            FROM user_point_logs
            WHERE user_id = CAST(:user_id AS uuid)
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"user_id": user_id, "limit": pageSize, "offset": (page - 1) * pageSize},
    ).mappings().all()
    return page_response([dict(row) for row in rows], page, pageSize, int(total))


@router.get("/{user_id}/skill-submissions")
def get_user_submissions(
    user_id: str,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "user:read")
    total = db.execute(
        text("SELECT COUNT(*) FROM skill_submissions WHERE submitter_id = CAST(:id AS uuid) AND deleted_at IS NULL"),
        {"id": user_id},
    ).scalar() or 0
    rows = db.execute(
        text(
            """
            SELECT id, title, summary, status, submitted_at, updated_at
            FROM skill_submissions
            WHERE submitter_id = CAST(:id AS uuid) AND deleted_at IS NULL
            ORDER BY updated_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"id": user_id, "limit": pageSize, "offset": (page - 1) * pageSize},
    ).mappings().all()
    return page_response([dict(row) for row in rows], page, pageSize, int(total))
