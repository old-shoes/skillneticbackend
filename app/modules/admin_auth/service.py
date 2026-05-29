from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.admin_auth.models import AdminSession, AdminUser
from app.modules.admin_auth.schemas import (
    AdminCurrentUserOut,
    AdminLoginIn,
    AdminLoginOut,
    AdminSeedCredentialOut,
    AdminSessionOut,
)
from app.modules.auth.service import hash_password, hash_token


ADMIN_SESSION_DAYS = 14
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin@123456"
DEFAULT_ADMIN_NICKNAME = "超级管理员"
DEFAULT_ADMIN_ROLE = "super_admin"
ROLE_PERMISSIONS = {
    "super_admin": ["*"],
    "content_admin": [
        "dashboard:read",
        "skill:read",
        "skill_submission:read",
        "skill_submission:review",
        "user:read",
        "point:read",
        "help_post:read",
        "notification:read",
        "operation_log:read",
    ],
    "reviewer": [
        "dashboard:read",
        "skill:read",
        "skill_submission:read",
        "skill_submission:review",
        "help_post:read",
        "operation_log:read",
    ],
    "operator": [
        "dashboard:read",
        "user:read",
        "point:read",
        "help_post:read",
        "notification:read",
        "operation_log:read",
    ],
    "viewer": [
        "dashboard:read",
        "skill:read",
        "skill_submission:read",
        "user:read",
        "point:read",
        "help_post:read",
        "notification:read",
        "operation_log:read",
    ],
}


class AdminAuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _request_ip(self, request: Optional[Request]) -> Optional[str]:
        return request.client.host if request and request.client else None

    def _request_user_agent(self, request: Optional[Request]) -> Optional[str]:
        return request.headers.get("user-agent") if request else None

    def _session_permissions(self, role: str) -> list[str]:
        return list(ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["viewer"]))

    def _session_out(self, admin: AdminUser) -> AdminSessionOut:
        return AdminSessionOut(
            id=str(admin.id),
            username=admin.username,
            nickname=admin.nickname,
            role=admin.role,
            permissions=self._session_permissions(admin.role),
            avatarUrl=admin.avatar_url,
        )

    def _user_out(self, admin: AdminUser, token: str) -> AdminCurrentUserOut:
        return AdminCurrentUserOut(
            userId=str(admin.id),
            username=admin.username,
            realName=admin.nickname,
            avatar=admin.avatar_url or "https://avatar.vercel.sh/skillnetic-admin",
            desc=f"Skillnetic Admin / {admin.role}",
            homePath="/admin/dashboard",
            roles=[admin.role],
            token=token,
        )

    def ensure_default_super_admin(self) -> AdminSeedCredentialOut:
        admin = self.db.scalar(
            select(AdminUser).where(AdminUser.username == DEFAULT_ADMIN_USERNAME, AdminUser.deleted_at.is_(None))
        )
        created = False
        if admin is None:
            admin = AdminUser(
                username=DEFAULT_ADMIN_USERNAME,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                nickname=DEFAULT_ADMIN_NICKNAME,
                role=DEFAULT_ADMIN_ROLE,
                is_active=True,
            )
            self.db.add(admin)
            self.db.commit()
            self.db.refresh(admin)
            created = True
        return AdminSeedCredentialOut(
            username=DEFAULT_ADMIN_USERNAME,
            password=DEFAULT_ADMIN_PASSWORD,
            created=created,
            updatedAt=admin.updated_at,
        )

    def _get_admin_by_token(self, token: str) -> Optional[AdminUser]:
        token_hash = hash_token(token)
        session = self.db.scalar(
            select(AdminSession).where(
                AdminSession.token_hash == token_hash,
                AdminSession.revoked_at.is_(None),
                AdminSession.expires_at > datetime.now(timezone.utc),
            )
        )
        if session is None:
            return None
        admin = self.db.get(AdminUser, session.admin_user_id)
        if admin is None or admin.deleted_at is not None or not admin.is_active:
            return None
        return admin

    def login(self, payload: AdminLoginIn, request: Optional[Request]) -> AdminLoginOut:
        username = payload.username.strip().lower()
        admin = self.db.scalar(
            select(AdminUser).where(AdminUser.username == username, AdminUser.deleted_at.is_(None))
        )
        if admin is None or not admin.is_active or admin.password_hash != hash_password(payload.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="管理员账号或密码错误")
        token = __import__("secrets").token_urlsafe(32)
        self.db.add(
            AdminSession(
                admin_user_id=admin.id,
                token_hash=hash_token(token),
                user_agent=self._request_user_agent(request),
                ip=self._request_ip(request),
                expires_at=datetime.now(timezone.utc) + timedelta(days=ADMIN_SESSION_DAYS),
            )
        )
        admin.last_login_at = datetime.now(timezone.utc)
        admin.last_login_ip = self._request_ip(request)
        self.db.commit()
        return AdminLoginOut(accessToken=token)

    def me(self, token: str) -> AdminSessionOut:
        admin = self._get_admin_by_token(token)
        if admin is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="后台未登录")
        return self._session_out(admin)

    def current_user_info(self, token: str) -> AdminCurrentUserOut:
        admin = self._get_admin_by_token(token)
        if admin is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="后台未登录")
        return self._user_out(admin, token)

    def logout(self, token: str) -> None:
        token_hash = hash_token(token)
        session = self.db.scalar(
            select(AdminSession).where(AdminSession.token_hash == token_hash, AdminSession.revoked_at.is_(None))
        )
        if session is not None:
            session.revoked_at = datetime.now(timezone.utc)
            self.db.commit()

    def access_codes(self, token: str) -> list[str]:
        admin = self._get_admin_by_token(token)
        if admin is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="后台未登录")
        return ["*"] if admin.role == "super_admin" else self._session_permissions(admin.role)
