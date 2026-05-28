from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from starlette.responses import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.response import success
from app.modules.auth.deps import get_session_token
from app.modules.auth.schemas import (
    AuthEmailCodeSendIn,
    AuthEmailLoginIn,
    AuthEmailRegisterIn,
    AuthLoginIn,
    AuthPasswordChangeIn,
    AuthPasswordResetIn,
    AuthRegisterIn,
)
from app.modules.auth.service import AuthService, REMEMBER_SESSION_DAYS, SESSION_DAYS, SHORT_SESSION_DAYS


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


@router.post("/auth/register")
def register(payload: AuthRegisterIn, request: Request, db: Session = Depends(get_db)) -> dict:
    data = AuthService(db).register(payload, request)
    response = JSONResponse(success({"user": data.user.model_dump()}))
    _set_session_cookie(response, data.token, max_age=_session_max_age(SESSION_DAYS))
    return response


@router.post("/auth/login")
def login(payload: AuthLoginIn, request: Request, db: Session = Depends(get_db)) -> dict:
    data = AuthService(db).login(payload, request)
    response = JSONResponse(success({"user": data.user.model_dump()}))
    _set_session_cookie(response, data.token, max_age=_session_max_age(SESSION_DAYS))
    return response


@router.post("/auth/email-code/send")
def send_email_code(payload: AuthEmailCodeSendIn, request: Request, db: Session = Depends(get_db)) -> dict:
    data = AuthService(db).send_email_code(payload, request)
    return success(data.model_dump())


@router.post("/auth/register/email")
def register_email(payload: AuthEmailRegisterIn, request: Request, db: Session = Depends(get_db)) -> dict:
    data = AuthService(db).register_email(payload, request)
    response = JSONResponse(success({"user": data.user.model_dump()}))
    _set_session_cookie(response, data.token, max_age=_session_max_age(SESSION_DAYS))
    return response


@router.post("/auth/login/email")
def login_email(payload: AuthEmailLoginIn, request: Request, db: Session = Depends(get_db)) -> dict:
    data = AuthService(db).login_email(payload, request)
    response = JSONResponse(success({"user": data.user.model_dump()}))
    max_age = _session_max_age(REMEMBER_SESSION_DAYS if payload.rememberMe else SHORT_SESSION_DAYS)
    _set_session_cookie(response, data.token, max_age=max_age)
    return response


@router.get("/auth/github/login")
def github_login(
    intent: str = Query(default="login"),
    db: Session = Depends(get_db),
) -> dict:
    data = AuthService(db).github_login_url(intent)
    return success(data.model_dump())


@router.get("/auth/github/callback")
def github_callback(
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_db),
):
    data = AuthService(db).github_callback(code, state, request)
    response = RedirectResponse(url=f"{settings.frontend_base_url.rstrip('/')}/auth/callback", status_code=302)
    _set_session_cookie(response, data.token, max_age=_session_max_age(SESSION_DAYS))
    return response


@router.get("/auth/me")
def me(
    token: str = Depends(get_session_token),
    db: Session = Depends(get_db),
) -> dict:
    data = AuthService(db).me(token)
    return success(data.model_dump())


@router.post("/auth/logout")
def logout(
    request: Request,
    token: str = Depends(get_session_token),
    db: Session = Depends(get_db),
) -> dict:
    data = AuthService(db).logout(token, request)
    response = JSONResponse(success(data.model_dump()))
    _clear_session_cookie(response)
    return response


@router.post("/auth/password/reset")
def reset_password(payload: AuthPasswordResetIn, request: Request, db: Session = Depends(get_db)) -> dict:
    data = AuthService(db).reset_password(payload, request)
    return success(data.model_dump())


@router.post("/account/password/change")
def change_password(
    payload: AuthPasswordChangeIn,
    request: Request,
    token: str = Depends(get_session_token),
    db: Session = Depends(get_db),
) -> dict:
    data = AuthService(db).change_password(token, payload, request)
    response = JSONResponse(success(data.model_dump()))
    _clear_session_cookie(response)
    return response
