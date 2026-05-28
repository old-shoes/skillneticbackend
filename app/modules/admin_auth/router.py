from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.response import success
from app.modules.admin_common.deps import get_current_admin


router = APIRouter()


@router.post("/login")
def admin_login() -> dict:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="admin login is not enabled yet; use X-Admin-Role for local admin access",
    )


@router.get("/me")
def admin_me(admin: dict = Depends(get_current_admin)) -> dict:
    return success(
        {
            "id": admin.get("id"),
            "username": admin.get("username"),
            "nickname": admin.get("nickname"),
            "role": admin.get("role"),
            "permissions": admin.get("permissions", []),
        }
    )


@router.post("/logout")
def admin_logout(response: Response) -> dict:
    response.delete_cookie("admin_session")
    return success({})
