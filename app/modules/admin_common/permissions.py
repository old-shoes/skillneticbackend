from __future__ import annotations

from fastapi import HTTPException, status


SUPER_ADMIN = "super_admin"


def has_permission(admin: dict, permission: str) -> bool:
    if not admin:
        return False
    if admin.get("role") == SUPER_ADMIN:
        return True
    permissions = admin.get("permissions") or []
    return "*" in permissions or permission in permissions


def require_permission(admin: dict, permission: str) -> None:
    if not has_permission(admin, permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

