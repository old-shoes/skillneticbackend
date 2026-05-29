from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from app.core.response import success
from app.modules.admin_auth.schemas import AdminLoginIn
from app.modules.admin_auth.service import ADMIN_SESSION_DAYS, AdminAuthService
from app.modules.admin_common.deps import get_admin_session_token
from app.core.config import settings
from app.core.database import get_db
from sqlalchemy.orm import Session


router = APIRouter()


def _session_max_age(days: int) -> int:
    return days * 24 * 60 * 60


def _set_session_cookie(response: Response, token: str, *, max_age: int) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


@router.post("/login")
def admin_login(payload: AdminLoginIn, db: Session = Depends(get_db)) -> dict:
    data = AdminAuthService(db).login(payload, None)
    response = JSONResponse(success(data.model_dump()))
    _set_session_cookie(response, data.accessToken, max_age=_session_max_age(ADMIN_SESSION_DAYS))
    return response


@router.get("/me")
def admin_me(token: str = Depends(get_admin_session_token), db: Session = Depends(get_db)) -> dict:
    data = AdminAuthService(db).me(token)
    return success(data.model_dump())


@router.get("/seed-credential")
def admin_seed_credential(db: Session = Depends(get_db)) -> dict:
    data = AdminAuthService(db).ensure_default_super_admin()
    return success(data.model_dump())


@router.post("/logout")
def admin_logout(response: Response, token: str = Depends(get_admin_session_token), db: Session = Depends(get_db)) -> dict:
    AdminAuthService(db).logout(token)
    _clear_session_cookie(response)
    return success({})
