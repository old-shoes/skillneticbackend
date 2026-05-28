from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success

from .schemas import CategoryListQueryIn
from .service import CategoryService


router = APIRouter()


@router.get("/categories/overview")
def get_categories_overview(
    locale: str = Query(default="zh"),
    db: Session = Depends(get_db),
) -> dict:
    data = CategoryService(db).get_overview(locale)
    return success(data.model_dump())


@router.get("/categories")
def get_categories(
    locale: str = Query(default="zh"),
    q: str = Query(default=None),
    group: str = Query(default="all"),
    scene: str = Query(default=None),
    sort: str = Query(default="default"),
    db: Session = Depends(get_db),
) -> dict:
    query = CategoryListQueryIn(
        locale=locale,
        q=q,
        group=group,
        scene=scene,
        sort=sort,
    )
    data = CategoryService(db).get_categories(query)
    return success(data.model_dump())
