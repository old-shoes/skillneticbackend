from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.response import success
from app.modules.admin_common.deps import get_current_admin
from app.modules.admin_common.permissions import require_permission
from app.core.database import get_db


router = APIRouter()


@router.get("/overview")
def dashboard_overview(
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "dashboard:read")
    row = db.execute(
        text(
            """
            SELECT
              (SELECT COUNT(*) FROM users WHERE created_at::date = CURRENT_DATE) AS today_registered_users,
              (SELECT COUNT(*) FROM skill_submissions WHERE submitted_at::date = CURRENT_DATE) AS today_skill_submissions,
              (SELECT COUNT(*) FROM skill_submissions WHERE status = 'pending_review') AS pending_skill_submissions,
              (SELECT COUNT(*) FROM skills WHERE status = 'published' AND deleted_at IS NULL) AS published_skills,
              (SELECT COUNT(*) FROM tracking_events WHERE created_at::date = CURRENT_DATE) AS today_page_views,
              (SELECT COUNT(*) FROM user_favorites WHERE created_at::date = CURRENT_DATE) AS today_favorites,
              (SELECT COUNT(*) FROM help_posts WHERE deleted_at IS NULL) AS help_post_count,
              0 AS pending_report_count
            """
        )
    ).mappings().first() or {}
    return success(
        {
            "todayRegisteredUsers": row.get("today_registered_users", 0),
            "todaySkillSubmissions": row.get("today_skill_submissions", 0),
            "pendingSkillSubmissions": row.get("pending_skill_submissions", 0),
            "publishedSkills": row.get("published_skills", 0),
            "todayPageViews": row.get("today_page_views", 0),
            "todayFavorites": row.get("today_favorites", 0),
            "helpPostCount": row.get("help_post_count", 0),
            "pendingReportCount": row.get("pending_report_count", 0),
        }
    )


@router.get("/trends")
def dashboard_trends(
    range: str = "7d",
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "dashboard:read")
    days = 30 if range == "30d" else 7
    rows = db.execute(
        text(
            """
            WITH days AS (
              SELECT generate_series(
                CURRENT_DATE - (:days - 1) * INTERVAL '1 day',
                CURRENT_DATE,
                INTERVAL '1 day'
              )::date AS d
            )
            SELECT
              d.d AS date,
              (SELECT COUNT(*) FROM users u WHERE u.created_at::date = d.d) AS registered_users,
              (SELECT COUNT(*) FROM skill_submissions s WHERE s.submitted_at::date = d.d) AS skill_submissions,
              (SELECT COUNT(*) FROM tracking_events e WHERE e.created_at::date = d.d) AS page_views,
              (SELECT COALESCE(SUM(points_change), 0) FROM user_point_logs p WHERE p.created_at::date = d.d) AS point_changes
            FROM days d
            ORDER BY d.d ASC
            """
        ),
        {"days": days},
    ).mappings().all()
    return success(
        {
            "dates": [str(row["date"]) for row in rows],
            "registeredUsers": [row["registered_users"] for row in rows],
            "skillSubmissions": [row["skill_submissions"] for row in rows],
            "pageViews": [row["page_views"] for row in rows],
            "pointChanges": [row["point_changes"] for row in rows],
        }
    )


@router.get("/todos")
def dashboard_todos(
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "dashboard:read")
    pending_submissions = db.execute(
        text(
            """
            SELECT id, title, submitter_id, submitted_at, status
            FROM skill_submissions
            WHERE status = 'pending_review' AND deleted_at IS NULL
            ORDER BY submitted_at ASC NULLS LAST
            LIMIT 10
            """
        )
    ).mappings().all()
    latest_help_posts = db.execute(
        text(
            """
            SELECT id, title, user_id, status, created_at
            FROM help_posts
            WHERE deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 10
            """
        )
    ).mappings().all()
    return success(
        {
            "pendingSubmissions": [dict(item) for item in pending_submissions],
            "latestHelpPosts": [dict(item) for item in latest_help_posts],
        }
    )
