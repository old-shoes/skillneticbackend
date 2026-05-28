from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from app.modules.auth.models import User, UserAuthAccount, UserSession
from app.modules.me.engagement import PointService
from app.modules.skill_submissions.models import SkillSubmission
from app.modules.skill_submissions.schemas import PaginationOut, SkillSubmissionListItemOut, SubmissionCategoryOut

from .schemas import (
    MeActionOut,
    MeFavoriteItemOut,
    MeFavoriteListOut,
    MeNotificationListOut,
    MeNotificationOut,
    MeOverviewOut,
    MePointLogListOut,
    MePointLogOut,
    MePointSummaryOut,
    MeProfileUpdateIn,
    MeProfileUserOut,
    MeSecurityOut,
    MeStatsOut,
)


POINT_RULES = {
    "earn": [
        {"label": "每日登录", "points": 1},
        {"label": "Skill 审核通过", "points": 30},
    ],
    "consume": [
        {"label": "发布求助帖", "points": -5},
    ],
}


class MeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.inspector = inspect(db.get_bind())

    def _has_table(self, table_name: str) -> bool:
        try:
            return bool(self.inspector.has_table(table_name))
        except Exception:
            return False

    def _table_columns(self, table_name: str) -> set[str]:
        if not self._has_table(table_name):
            return set()
        try:
            return {str(column["name"]) for column in self.inspector.get_columns(table_name)}
        except Exception:
            return set()

    def _get_user(self, user_id: UUID) -> User:
        user = self.db.get(User, user_id)
        if user is None or user.deleted_at is not None or not user.is_active:
            raise HTTPException(status_code=404, detail="user not found")
        return user

    def _get_optional_user_fields(self, user_id: UUID) -> Dict[str, Any]:
        columns = self._table_columns("users")
        optional_columns = [
            column
            for column in ("bio", "location", "points", "email_verified", "last_login_at", "last_login_ip")
            if column in columns
        ]
        if not optional_columns:
            return {}

        stmt = text(
            f"SELECT {', '.join(optional_columns)} FROM users WHERE id = :user_id"
        )
        row = self.db.execute(stmt, {"user_id": user_id}).mappings().first()
        return dict(row or {})

    def _is_email_verified(self, user: User, extras: Dict[str, Any]) -> bool:
        if "email_verified" in extras:
            return bool(extras["email_verified"])
        account = self.db.scalar(
            select(UserAuthAccount).where(
                UserAuthAccount.user_id == user.id,
                UserAuthAccount.provider == "email",
                UserAuthAccount.is_verified.is_(True),
            )
        )
        return account is not None

    def _is_github_connected(self, user: User) -> bool:
        if user.github_connected:
            return True
        account = self.db.scalar(
            select(UserAuthAccount).where(
                UserAuthAccount.user_id == user.id,
                UserAuthAccount.provider == "github",
            )
        )
        return account is not None

    def _current_points(self, extras: Dict[str, Any]) -> int:
        return int(extras.get("points") or 0)

    def _profile_user_out(self, user: User) -> MeProfileUserOut:
        extras = self._get_optional_user_fields(user.id)
        return MeProfileUserOut(
            id=str(user.id),
            email=user.email,
            nickname=user.nickname,
            avatarUrl=user.avatar_url,
            bio=extras.get("bio"),
            location=extras.get("location"),
            emailVerified=self._is_email_verified(user, extras),
            githubConnected=self._is_github_connected(user),
            points=self._current_points(extras),
            level=user.level,
            locale=user.locale,
            joinedAt=user.created_at,
        )

    def _submission_category(self, submission: SkillSubmission) -> Optional[SubmissionCategoryOut]:
        if not submission.category_id or not submission.category_name:
            return None
        return SubmissionCategoryOut(
            id=str(submission.category_id),
            name=submission.category_name,
            slug="",
        )

    def _submission_item_out(self, submission: SkillSubmission) -> SkillSubmissionListItemOut:
        return SkillSubmissionListItemOut(
            id=str(submission.id),
            title=submission.title,
            summary=submission.summary,
            coverImage=submission.cover_image,
            tags=submission.tags or [],
            status=submission.status,
            difficulty=submission.difficulty,
            category=self._submission_category(submission),
            submittedAt=submission.submitted_at,
            updatedAt=submission.updated_at,
        )

    def _count_rows(self, sql: str, user_id: UUID, table_name: str) -> int:
        if not self._has_table(table_name):
            return 0
        return int(self.db.execute(text(sql), {"user_id": user_id}).scalar() or 0)

    def daily_check_in(self, user_id: UUID) -> MeActionOut:
        user = self._get_user(user_id)
        point_service = PointService(self.db)
        point_service.update_last_login(user_id=user.id, ip=None)
        point_service.award_daily_login_points(user.id)
        self.db.commit()
        return MeActionOut(success=True)

    def ensure_daily_check_in(self, user_id: UUID) -> None:
        user = self._get_user(user_id)
        point_service = PointService(self.db)
        point_service.update_last_login(user_id=user.id, ip=None)
        point_service.award_daily_login_points(user.id)
        self.db.commit()

    def _stats_out(self, user_id: UUID) -> MeStatsOut:
        submission_count = int(
            self.db.scalar(
                select(func.count()).select_from(
                    select(SkillSubmission.id)
                    .where(
                        SkillSubmission.submitter_id == user_id,
                        SkillSubmission.deleted_at.is_(None),
                    )
                    .subquery()
                )
            )
            or 0
        )
        pending_review_count = int(
            self.db.scalar(
                select(func.count()).select_from(
                    select(SkillSubmission.id)
                    .where(
                        SkillSubmission.submitter_id == user_id,
                        SkillSubmission.status == "pending_review",
                        SkillSubmission.deleted_at.is_(None),
                    )
                    .subquery()
                )
            )
            or 0
        )
        favorite_count = self._count_rows(
            "SELECT COUNT(*) FROM user_favorites WHERE user_id = :user_id AND target_type = 'skill'",
            user_id,
            "user_favorites",
        )
        help_post_count = self._count_rows(
            "SELECT COUNT(*) FROM help_posts WHERE user_id = :user_id AND deleted_at IS NULL",
            user_id,
            "help_posts",
        )
        return MeStatsOut(
            favoriteCount=favorite_count,
            submissionCount=submission_count,
            pendingReviewCount=pending_review_count,
            helpPostCount=help_post_count,
        )

    def _point_summary_out(self, current_points: int) -> MePointSummaryOut:
        return MePointSummaryOut(currentPoints=current_points, rules=POINT_RULES)

    def _recent_notifications(self, user_id: UUID, limit: int = 5) -> List[MeNotificationOut]:
        if not self._has_table("user_notifications"):
            return []
        rows = self.db.execute(
            text(
                """
                SELECT id, type, title, content, related_type, related_id, is_read, created_at
                FROM user_notifications
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"user_id": user_id, "limit": limit},
        ).mappings().all()
        return [
            MeNotificationOut(
                id=str(row["id"]),
                type=str(row["type"]),
                title=str(row["title"]),
                content=row["content"],
                relatedType=row["related_type"],
                relatedId=str(row["related_id"]) if row["related_id"] else None,
                isRead=bool(row["is_read"]),
                createdAt=row["created_at"],
            )
            for row in rows
        ]

    def _latest_login(self, user: User, extras: Dict[str, Any]) -> tuple[Optional[datetime], Optional[str]]:
        last_login_at = extras.get("last_login_at")
        last_login_ip = extras.get("last_login_ip")
        if last_login_at or last_login_ip:
            return last_login_at, last_login_ip

        session = self.db.scalar(
            select(UserSession)
            .where(UserSession.user_id == user.id)
            .order_by(UserSession.created_at.desc())
        )
        if session is None:
            return None, None
        return session.created_at, session.ip

    def get_overview(self, user_id: UUID) -> MeOverviewOut:
        self.ensure_daily_check_in(user_id)
        user = self._get_user(user_id)
        user_out = self._profile_user_out(user)
        recent_submissions = self.db.scalars(
            select(SkillSubmission)
            .where(
                SkillSubmission.submitter_id == user_id,
                SkillSubmission.deleted_at.is_(None),
            )
            .order_by(SkillSubmission.updated_at.desc(), SkillSubmission.created_at.desc())
            .limit(4)
        ).all()
        return MeOverviewOut(
            user=user_out,
            stats=self._stats_out(user_id),
            pointSummary=self._point_summary_out(user_out.points),
            recentNotifications=self._recent_notifications(user_id, limit=3),
            recentSubmissions=[self._submission_item_out(item) for item in recent_submissions],
        )

    def get_profile(self, user_id: UUID) -> MeProfileUserOut:
        self.ensure_daily_check_in(user_id)
        return self._profile_user_out(self._get_user(user_id))

    def update_profile(self, user_id: UUID, payload: MeProfileUpdateIn) -> MeProfileUserOut:
        user = self._get_user(user_id)
        if payload.nickname is not None:
            user.nickname = payload.nickname.strip()
        if payload.avatarUrl is not None:
            user.avatar_url = payload.avatarUrl.strip() or None
        if payload.locale is not None:
            user.locale = payload.locale.strip() or user.locale

        extra_columns = self._table_columns("users")
        raw_updates: Dict[str, Any] = {}
        if payload.bio is not None and "bio" in extra_columns:
            raw_updates["bio"] = payload.bio.strip() or None
        if payload.location is not None and "location" in extra_columns:
            raw_updates["location"] = payload.location.strip() or None

        self.db.add(user)
        if raw_updates:
            assignments = ", ".join(f"{key} = :{key}" for key in raw_updates.keys())
            if "updated_at" in extra_columns:
                assignments = f"{assignments}, updated_at = NOW()"
            self.db.execute(
                text(f"UPDATE users SET {assignments} WHERE id = :user_id"),
                {"user_id": user_id, **raw_updates},
            )

        self.db.commit()
        self.db.refresh(user)
        return self._profile_user_out(user)

    def list_skill_submissions(self, user_id: UUID, status: Optional[str], page: int, page_size: int):
        self.ensure_daily_check_in(user_id)
        stmt = (
            select(SkillSubmission)
            .where(
                SkillSubmission.submitter_id == user_id,
                SkillSubmission.deleted_at.is_(None),
            )
            .order_by(SkillSubmission.updated_at.desc(), SkillSubmission.created_at.desc())
        )
        if status:
            stmt = stmt.where(SkillSubmission.status == status)
        rows = self.db.scalars(stmt).all()
        total = len(rows)
        start = (page - 1) * page_size
        end = start + page_size
        items = [self._submission_item_out(item) for item in rows[start:end]]
        return {
            "list": items,
            "pagination": PaginationOut.from_total(page, page_size, total),
        }

    def list_favorites(self, user_id: UUID, page: int, page_size: int) -> MeFavoriteListOut:
        self.ensure_daily_check_in(user_id)
        if not self._has_table("user_favorites"):
            return MeFavoriteListOut(list=[], pagination=PaginationOut.from_total(page, page_size, 0))

        total = int(
            self.db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM user_favorites
                    WHERE user_id = :user_id AND target_type = 'skill'
                    """
                ),
                {"user_id": user_id},
            ).scalar()
            or 0
        )
        rows = self.db.execute(
            text(
                """
                SELECT
                  uf.target_id,
                  uf.created_at,
                  COALESCE(s.title, 'Skill') AS title,
                  COALESCE(s.summary, '') AS summary,
                  s.slug,
                  c.name AS category_name
                FROM user_favorites uf
                LEFT JOIN skills s ON s.id = uf.target_id AND s.deleted_at IS NULL
                LEFT JOIN categories c ON c.id = s.category_id
                WHERE uf.user_id = :user_id
                  AND uf.target_type = 'skill'
                ORDER BY uf.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {
                "user_id": user_id,
                "limit": page_size,
                "offset": (page - 1) * page_size,
            },
        ).mappings().all()
        items = [
            MeFavoriteItemOut(
                targetId=str(row["target_id"]),
                title=str(row["title"]),
                summary=str(row["summary"]),
                slug=row["slug"],
                categoryName=row["category_name"],
                favoritedAt=row["created_at"],
            )
            for row in rows
        ]
        return MeFavoriteListOut(list=items, pagination=PaginationOut.from_total(page, page_size, total))

    def get_point_summary(self, user_id: UUID) -> MePointSummaryOut:
        self.ensure_daily_check_in(user_id)
        user = self._get_user(user_id)
        extras = self._get_optional_user_fields(user.id)
        return self._point_summary_out(self._current_points(extras))

    def list_point_logs(
        self,
        user_id: UUID,
        page: int,
        page_size: int,
        event_type: Optional[str],
    ) -> MePointLogListOut:
        self.ensure_daily_check_in(user_id)
        if not self._has_table("user_point_logs"):
            return MePointLogListOut(list=[], pagination=PaginationOut.from_total(page, page_size, 0))

        query_filter = " AND event_type = :event_type" if event_type else ""
        params: Dict[str, Any] = {
            "user_id": user_id,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        if event_type:
            params["event_type"] = event_type

        total = int(
            self.db.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM user_point_logs
                    WHERE user_id = :user_id{query_filter}
                    """
                ),
                params,
            ).scalar()
            or 0
        )
        rows = self.db.execute(
            text(
                f"""
                SELECT
                  id,
                  event_type,
                  points_change,
                  points_before,
                  points_after,
                  description,
                  related_type,
                  related_id,
                  created_at
                FROM user_point_logs
                WHERE user_id = :user_id{query_filter}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        items = [
            MePointLogOut(
                id=str(row["id"]),
                eventType=str(row["event_type"]),
                pointsChange=int(row["points_change"]),
                pointsBefore=int(row["points_before"]),
                pointsAfter=int(row["points_after"]),
                description=row["description"],
                relatedType=row["related_type"],
                relatedId=str(row["related_id"]) if row["related_id"] else None,
                createdAt=row["created_at"],
            )
            for row in rows
        ]
        return MePointLogListOut(list=items, pagination=PaginationOut.from_total(page, page_size, total))

    def list_notifications(
        self,
        user_id: UUID,
        page: int,
        page_size: int,
        is_read: Optional[bool],
        notification_type: Optional[str],
    ) -> MeNotificationListOut:
        self.ensure_daily_check_in(user_id)
        if not self._has_table("user_notifications"):
            return MeNotificationListOut(list=[], pagination=PaginationOut.from_total(page, page_size, 0))

        conditions = ["user_id = :user_id"]
        params: Dict[str, Any] = {
            "user_id": user_id,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        if is_read is not None:
            conditions.append("is_read = :is_read")
            params["is_read"] = is_read
        if notification_type:
            conditions.append("type = :notification_type")
            params["notification_type"] = notification_type

        where_clause = " AND ".join(conditions)
        total = int(
            self.db.execute(
                text(f"SELECT COUNT(*) FROM user_notifications WHERE {where_clause}"),
                params,
            ).scalar()
            or 0
        )
        rows = self.db.execute(
            text(
                f"""
                SELECT id, type, title, content, related_type, related_id, is_read, created_at
                FROM user_notifications
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        items = [
            MeNotificationOut(
                id=str(row["id"]),
                type=str(row["type"]),
                title=str(row["title"]),
                content=row["content"],
                relatedType=row["related_type"],
                relatedId=str(row["related_id"]) if row["related_id"] else None,
                isRead=bool(row["is_read"]),
                createdAt=row["created_at"],
            )
            for row in rows
        ]
        return MeNotificationListOut(list=items, pagination=PaginationOut.from_total(page, page_size, total))

    def read_notification(self, user_id: UUID, notification_id: str) -> MeActionOut:
        if not self._has_table("user_notifications"):
            return MeActionOut()
        self.db.execute(
            text(
                """
                UPDATE user_notifications
                SET is_read = TRUE, read_at = NOW()
                WHERE id = :notification_id AND user_id = :user_id
                """
            ),
            {"notification_id": notification_id, "user_id": user_id},
        )
        self.db.commit()
        return MeActionOut()

    def read_all_notifications(self, user_id: UUID) -> MeActionOut:
        if not self._has_table("user_notifications"):
            return MeActionOut()
        self.db.execute(
            text(
                """
                UPDATE user_notifications
                SET is_read = TRUE, read_at = NOW()
                WHERE user_id = :user_id AND is_read = FALSE
                """
            ),
            {"user_id": user_id},
        )
        self.db.commit()
        return MeActionOut()

    def get_security(self, user_id: UUID) -> MeSecurityOut:
        self.ensure_daily_check_in(user_id)
        user = self._get_user(user_id)
        extras = self._get_optional_user_fields(user.id)
        last_login_at, last_login_ip = self._latest_login(user, extras)
        return MeSecurityOut(
            emailVerified=self._is_email_verified(user, extras),
            githubConnected=self._is_github_connected(user),
            hasPassword=bool(user.password_hash),
            lastLoginAt=last_login_at,
            lastLoginIp=last_login_ip,
        )
