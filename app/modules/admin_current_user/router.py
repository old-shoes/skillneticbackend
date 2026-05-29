from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success
from app.modules.admin_auth.service import AdminAuthService
from app.modules.admin_common.deps import get_admin_session_token


router = APIRouter()


@router.get("/user/info")
def get_admin_user_info(
    token: str = Depends(get_admin_session_token),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminAuthService(db).current_user_info(token)
    return success(data.model_dump())


@router.get("/user/codes")
def get_admin_user_codes(
    token: str = Depends(get_admin_session_token),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminAuthService(db).access_codes(token)
    return success(data)
