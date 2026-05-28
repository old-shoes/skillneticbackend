from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.response import success
from app.modules.auth.deps import get_session_token
from app.modules.auth.service import AuthService
from app.modules.auth.models import User
from app.modules.me.router import require_current_user
from app.modules.skills.schemas import SkillQueryIn
from app.modules.skills.service import SkillService


router = APIRouter()


def get_optional_current_user(
    request: Request,
    authorization: str = Header(default="", alias="Authorization"),
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = get_session_token(request, authorization)
    return AuthService(db).get_current_user_optional(token)


@router.get("/skills")
def get_skills(
    q: str = Query(default=None),
    category: str = Query(default=None),
    scene: str = Query(default=None),
    type: str = Query(default=None),
    sort: str = Query(default="latest"),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=9, ge=1, le=30),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> dict:
    query = SkillQueryIn(
        q=q,
        category=category,
        scene=scene,
        type=type,
        sort=sort,
        page=page,
        pageSize=pageSize,
    )
    data = SkillService(db).get_skill_list(query, current_user.id if current_user else None)
    return success(data.model_dump())


@router.get("/skills/filters")
def get_skill_filters(db: Session = Depends(get_db)) -> dict:
    data = SkillService(db).get_filters()
    return success(data.model_dump())


@router.get("/skills/{slug}")
def get_skill_detail(
    slug: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> dict:
    data = SkillService(db).get_skill_detail(slug, current_user.id if current_user else None)
    if data is None:
        raise HTTPException(status_code=404, detail="skill not found")
    return success(data.model_dump())


@router.post("/skills/{skill_id}/favorite")
def post_skill_favorite(
    skill_id: UUID,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        data = SkillService(db).favorite_skill(user_id=current_user.id, skill_id=skill_id)
    except ValueError as exc:
        detail = str(exc)
        if detail == "skill not found":
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    return success(data.model_dump())


@router.delete("/skills/{skill_id}/favorite")
def delete_skill_favorite(
    skill_id: UUID,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        data = SkillService(db).unfavorite_skill(user_id=current_user.id, skill_id=skill_id)
    except ValueError as exc:
        detail = str(exc)
        if detail == "skill not found":
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    return success(data.model_dump())
