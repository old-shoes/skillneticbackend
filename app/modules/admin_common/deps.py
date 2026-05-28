from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.deps import get_session_token
from app.modules.auth.service import AuthService


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


def _normalize_role(role: Optional[str]) -> Optional[str]:
    value = (role or "").strip()
    return value or None


async def get_current_admin(
    request: Request,
    x_admin_role: str = Header(default="", alias="X-Admin-Role"),
    x_admin_name: str = Header(default="", alias="X-Admin-Name"),
    db: Session = Depends(get_db),
) -> dict:
    role = _normalize_role(x_admin_role)
    if role:
        permissions = ROLE_PERMISSIONS.get(role)
        if permissions is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        display_name = x_admin_name.strip() or "Local Admin"
        return {
            "id": "dev-admin",
            "username": display_name,
            "nickname": display_name,
            "role": role,
            "permissions": permissions,
        }

    token = get_session_token(request)
    if token:
        user = AuthService(db).get_current_user_optional(token)
        if user is not None:
            return {
                "id": str(user.id),
                "username": user.email,
                "nickname": user.nickname,
                "role": "viewer",
                "permissions": ROLE_PERMISSIONS["viewer"],
            }

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="后台未登录")

