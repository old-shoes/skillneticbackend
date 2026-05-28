from typing import Optional

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success
from app.modules.auth.deps import get_session_token
from app.modules.auth.models import User
from app.modules.auth.service import AuthService
from app.modules.homepage.service import get_homepage_data


router = APIRouter()


def get_optional_current_user(
    request: Request,
    authorization: str = Header(default="", alias="Authorization"),
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = get_session_token(request, authorization)
    return AuthService(db).get_current_user_optional(token)


@router.get("/homepage")
def homepage(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> dict:
    data = get_homepage_data(db, current_user.id if current_user else None)
    return success(data.model_dump())
