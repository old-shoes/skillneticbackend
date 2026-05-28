from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


class PointService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.inspector = inspect(db.get_bind())

    def _has_table(self, table_name: str) -> bool:
        try:
            return bool(self.inspector.has_table(table_name))
        except Exception:
            return False

    def _users_columns(self) -> set[str]:
        try:
            return {str(column["name"]) for column in self.inspector.get_columns("users")}
        except Exception:
            return set()

    def _today_string(self) -> str:
        return datetime.now(SHANGHAI_TZ).strftime("%Y-%m-%d")

    def update_last_login(self, user_id: UUID, ip: Optional[str]) -> None:
        columns = self._users_columns()
        assignments = []
        params = {"user_id": user_id}
        if "last_login_at" in columns:
            assignments.append("last_login_at = NOW()")
        if "last_login_ip" in columns:
            assignments.append("last_login_ip = :last_login_ip")
            params["last_login_ip"] = ip
        if "updated_at" in columns:
            assignments.append("updated_at = NOW()")
        if not assignments:
            return
        self.db.execute(
            text(f"UPDATE users SET {', '.join(assignments)} WHERE id = :user_id"),
            params,
        )

    def award_points(
        self,
        *,
        user_id: UUID,
        event_type: str,
        points: int,
        dedup_key: str,
        description: str,
        related_type: Optional[str] = None,
        related_id: Optional[UUID] = None,
    ) -> dict:
        if not self._has_table("user_point_logs"):
            return {"awarded": False, "reason": "point_logs_table_missing"}

        existed = self.db.execute(
            text(
                """
                SELECT id
                FROM user_point_logs
                WHERE dedup_key = :dedup_key
                LIMIT 1
                """
            ),
            {"dedup_key": dedup_key},
        ).first()
        if existed:
            return {"awarded": False, "reason": "already_awarded"}

        try:
            with self.db.begin_nested():
                row = self.db.execute(
                    text(
                        """
                        SELECT points
                        FROM users
                        WHERE id = :user_id
                        FOR UPDATE
                        """
                    ),
                    {"user_id": user_id},
                ).mappings().first()
                if row is None:
                    return {"awarded": False, "reason": "user_not_found"}

                points_before = int(row["points"] or 0)
                points_after = points_before + points
                self.db.execute(
                    text(
                        """
                        UPDATE users
                        SET points = :points_after,
                            updated_at = NOW()
                        WHERE id = :user_id
                        """
                    ),
                    {
                        "user_id": user_id,
                        "points_after": points_after,
                    },
                )
                self.db.execute(
                    text(
                        """
                        INSERT INTO user_point_logs (
                          user_id,
                          event_type,
                          points_change,
                          points_before,
                          points_after,
                          related_type,
                          related_id,
                          description,
                          dedup_key
                        )
                        VALUES (
                          :user_id,
                          :event_type,
                          :points_change,
                          :points_before,
                          :points_after,
                          :related_type,
                          :related_id,
                          :description,
                          :dedup_key
                        )
                        """
                    ),
                    {
                        "user_id": user_id,
                        "event_type": event_type,
                        "points_change": points,
                        "points_before": points_before,
                        "points_after": points_after,
                        "related_type": related_type,
                        "related_id": related_id,
                        "description": description,
                        "dedup_key": dedup_key,
                    },
                )
        except IntegrityError:
            return {"awarded": False, "reason": "already_awarded"}

        return {
            "awarded": True,
            "pointsChange": points,
            "pointsAfter": points_after,
        }

    def award_daily_login_points(self, user_id: UUID) -> dict:
        return self.award_points(
            user_id=user_id,
            event_type="daily_login",
            points=1,
            dedup_key=f"daily_login:{user_id}:{self._today_string()}",
            description="每日登录",
        )

    def award_skill_approved_points(self, user_id: UUID, submission_id: UUID) -> dict:
        return self.award_points(
            user_id=user_id,
            event_type="skill_approved",
            points=30,
            dedup_key=f"skill_approved:{user_id}:{submission_id}",
            description="Skill 审核通过",
            related_type="skill_submission",
            related_id=submission_id,
        )


class NotificationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.inspector = inspect(db.get_bind())

    def _has_table(self, table_name: str) -> bool:
        try:
            return bool(self.inspector.has_table(table_name))
        except Exception:
            return False

    def create_notification(
        self,
        *,
        user_id: UUID,
        type: str,
        title: str,
        content: Optional[str] = None,
        related_type: Optional[str] = None,
        related_id: Optional[UUID] = None,
    ) -> None:
        if not self._has_table("user_notifications"):
            return
        self.db.execute(
            text(
                """
                INSERT INTO user_notifications (
                  user_id,
                  type,
                  title,
                  content,
                  related_type,
                  related_id,
                  is_read
                )
                VALUES (
                  :user_id,
                  :type,
                  :title,
                  :content,
                  :related_type,
                  :related_id,
                  FALSE
                )
                """
            ),
            {
                "user_id": user_id,
                "type": type,
                "title": title,
                "content": content,
                "related_type": related_type,
                "related_id": related_id,
            },
        )
