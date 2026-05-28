from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success
from app.modules.auth.deps import get_session_token
from app.modules.auth.models import User
from app.modules.auth.service import AuthService

from .schemas import MeActionOut, MeProfileUpdateIn
from .service import MeService


router = APIRouter()


def require_current_user(
    token: str = Depends(get_session_token),
    db: Session = Depends(get_db),
) -> User:
    return AuthService(db).get_current_user(token)


@router.post("/me/check-in")
def post_me_check_in(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> dict:
    data = MeService(db).daily_check_in(current_user.id)
    return success(data.model_dump())


@router.get("/me/overview")
def get_me_overview(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> dict:
    data = MeService(db).get_overview(current_user.id)
    return success(data.model_dump())


@router.get("/me/profile")
def get_me_profile(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> dict:
    data = MeService(db).get_profile(current_user.id)
    return success(data.model_dump())


@router.patch("/me/profile")
def patch_me_profile(
    payload: MeProfileUpdateIn,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> dict:
    data = MeService(db).update_profile(current_user.id, payload)
    return success(data.model_dump())


@router.get("/me/skill-submissions")
def get_me_skill_submissions(
    status: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> dict:
    data = MeService(db).list_skill_submissions(current_user.id, status, page, pageSize)
    return success({
        "list": [item.model_dump() for item in data["list"]],
        "pagination": data["pagination"].model_dump(),
    })


@router.get("/me/favorites")
def get_me_favorites(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> dict:
    data = MeService(db).list_favorites(current_user.id, page, pageSize)
    return success(data.model_dump())


@router.get("/me/points/summary")
def get_me_point_summary(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> dict:
    data = MeService(db).get_point_summary(current_user.id)
    return success(data.model_dump())


@router.get("/me/points/logs")
def get_me_point_logs(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=50),
    eventType: str = Query(default=None),
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> dict:
    data = MeService(db).list_point_logs(current_user.id, page, pageSize, eventType)
    return success(data.model_dump())


@router.get("/me/notifications")
def get_me_notifications(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=50),
    isRead: bool = Query(default=None),
    type: str = Query(default=None),
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> dict:
    data = MeService(db).list_notifications(current_user.id, page, pageSize, isRead, type)
    return success(data.model_dump())


@router.post("/me/notifications/read-all")
def post_me_notifications_read_all(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> dict:
    data = MeService(db).read_all_notifications(current_user.id)
    return success(data.model_dump())


@router.post("/me/notifications/{notification_id}/read")
def post_me_notification_read(
    notification_id: str,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> dict:
    data = MeService(db).read_notification(current_user.id, notification_id)
    return success(data.model_dump())


@router.get("/me/security")
def get_me_security(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> dict:
    data = MeService(db).get_security(current_user.id)
    return success(data.model_dump())
