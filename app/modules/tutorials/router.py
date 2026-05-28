from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success
from app.modules.tutorials.schemas import TutorialHelpfulIn, TutorialQueryIn
from app.modules.tutorials.service import TutorialService


router = APIRouter()


@router.get("/tutorials")
def get_tutorials(
    locale: str = Query(default="zh"),
    q: str = Query(default=None),
    category: str = Query(default=None),
    tag: str = Query(default=None),
    sort: str = Query(default="latest"),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=6, ge=1, le=30),
    db: Session = Depends(get_db),
) -> dict:
    query = TutorialQueryIn(
        locale=locale,
        q=q,
        category=category,
        tag=tag,
        sort=sort,
        page=page,
        pageSize=pageSize,
    )
    data = TutorialService(db).get_tutorial_list(query)
    return success(data.model_dump())


@router.get("/tutorials/filters")
def get_tutorial_filters(locale: str = Query(default="zh"), db: Session = Depends(get_db)) -> dict:
    data = TutorialService(db).get_filters(locale)
    return success(data.model_dump())


@router.get("/tutorials/learning-paths")
def get_learning_paths(locale: str = Query(default="zh"), db: Session = Depends(get_db)) -> dict:
    data = TutorialService(db).get_learning_paths(locale)
    return success([item.model_dump() for item in data])


@router.get("/tutorials/weekly-hot")
def get_weekly_hot(locale: str = Query(default="zh"), db: Session = Depends(get_db)) -> dict:
    data = TutorialService(db).get_weekly_hot(locale)
    return success([item.model_dump() for item in data])


@router.get("/tutorials/{slug}")
def get_tutorial_detail(slug: str, locale: str = Query(default="zh"), db: Session = Depends(get_db)) -> dict:
    data = TutorialService(db).get_tutorial_detail(slug, locale)
    if data is None:
        raise HTTPException(status_code=404, detail="tutorial not found")
    return success(data.model_dump())


@router.post("/tutorials/{tutorial_id}/view")
def post_tutorial_view(tutorial_id: UUID, db: Session = Depends(get_db)) -> dict:
    ok = TutorialService(db).increment_view_count(tutorial_id)
    if not ok:
        raise HTTPException(status_code=404, detail="tutorial not found")
    return success({"ok": True})


@router.post("/tutorials/{tutorial_id}/favorite")
def post_tutorial_favorite(tutorial_id: UUID, db: Session = Depends(get_db)) -> dict:
    ok = TutorialService(db).increment_favorite_count(tutorial_id)
    if not ok:
        raise HTTPException(status_code=404, detail="tutorial not found")
    return success({"ok": True})


@router.post("/tutorials/{tutorial_id}/like")
def post_tutorial_like(tutorial_id: UUID, db: Session = Depends(get_db)) -> dict:
    ok = TutorialService(db).increment_like_count(tutorial_id)
    if not ok:
        raise HTTPException(status_code=404, detail="tutorial not found")
    return success({"ok": True})


@router.post("/tutorials/{tutorial_id}/helpful")
def post_tutorial_helpful(tutorial_id: UUID, payload: TutorialHelpfulIn, db: Session = Depends(get_db)) -> dict:
    ok = TutorialService(db).record_helpful_vote(tutorial_id, payload)
    if not ok:
        raise HTTPException(status_code=404, detail="tutorial not found")
    return success({"ok": True})
