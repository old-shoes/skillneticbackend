from typing import Iterable

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success
from app.modules.admin_tutorials.schemas import (
    AdminLearningPathIn,
    AdminTutorialCategoryQueryIn,
    AdminTutorialCategorySortIn,
    AdminOperationLogQueryIn,
    AdminTutorialCategoryIn,
    AdminTutorialQueryIn,
    AdminTutorialSaveIn,
    AdminTutorialTagIn,
)
from app.modules.admin_tutorials.service import AdminTutorialService


router = APIRouter()


CATEGORY_VIEW_ROLES = {"super_admin", "content_admin", "editor"}
CATEGORY_MANAGE_ROLES = {"super_admin", "content_admin"}


def require_category_role(allowed_roles: Iterable[str]):
    allowed = set(allowed_roles)

    def dependency(x_admin_role: str = Header(default="content_admin", alias="X-Admin-Role")) -> str:
        role = (x_admin_role or "").strip()
        if role not in CATEGORY_VIEW_ROLES:
            raise HTTPException(status_code=403, detail="forbidden")
        if role not in allowed:
            raise HTTPException(status_code=403, detail="forbidden")
        return role

    return dependency


@router.get("/tutorials")
def get_admin_tutorials(
    q: str = Query(default=None),
    categoryId: str = Query(default=None),
    tagId: str = Query(default=None),
    status: str = Query(default=None),
    difficulty: str = Query(default=None),
    isFeatured: bool = Query(default=None),
    publishedFrom: str = Query(default=None),
    publishedTo: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> dict:
    query = AdminTutorialQueryIn(
        q=q,
        categoryId=categoryId,
        tagId=tagId,
        status=status,
        difficulty=difficulty,
        isFeatured=isFeatured,
        publishedFrom=publishedFrom,
        publishedTo=publishedTo,
        page=page,
        pageSize=pageSize,
    )
    data = AdminTutorialService(db).get_tutorials(query)
    return success(data.model_dump())


@router.get("/tutorials/{tutorial_id}")
def get_admin_tutorial_detail(tutorial_id: str, db: Session = Depends(get_db)) -> dict:
    data = AdminTutorialService(db).get_tutorial_detail(tutorial_id)
    return success(data.model_dump())


@router.post("/tutorials")
def create_admin_tutorial(payload: AdminTutorialSaveIn, db: Session = Depends(get_db)) -> dict:
    data = AdminTutorialService(db).create_tutorial(payload)
    return success(data.model_dump())


@router.patch("/tutorials/{tutorial_id}")
def update_admin_tutorial(tutorial_id: str, payload: AdminTutorialSaveIn, db: Session = Depends(get_db)) -> dict:
    data = AdminTutorialService(db).update_tutorial(tutorial_id, payload)
    return success(data.model_dump())


@router.post("/tutorials/{tutorial_id}/publish")
def publish_admin_tutorial(tutorial_id: str, db: Session = Depends(get_db)) -> dict:
    data = AdminTutorialService(db).publish_tutorial(tutorial_id)
    return success(data.model_dump())


@router.post("/tutorials/{tutorial_id}/offline")
def offline_admin_tutorial(tutorial_id: str, db: Session = Depends(get_db)) -> dict:
    data = AdminTutorialService(db).offline_tutorial(tutorial_id)
    return success(data.model_dump())


@router.delete("/tutorials/{tutorial_id}")
def delete_admin_tutorial(tutorial_id: str, db: Session = Depends(get_db)) -> dict:
    AdminTutorialService(db).delete_tutorial(tutorial_id)
    return success({"ok": True})


@router.get("/tutorial-categories")
def get_admin_tutorial_categories(
    q: str = Query(default=None),
    status: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    _: str = Depends(require_category_role(CATEGORY_VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    query = AdminTutorialCategoryQueryIn(q=q, status=status, page=page, pageSize=pageSize)
    data = AdminTutorialService(db).get_category_list(query)
    return success(data.model_dump())


@router.get("/tutorial-categories/stats")
def get_admin_tutorial_category_stats(
    _: str = Depends(require_category_role(CATEGORY_VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminTutorialService(db).get_category_stats()
    return success(data.model_dump())


@router.get("/tutorial-categories/{category_id}")
def get_admin_tutorial_category_detail(
    category_id: str,
    _: str = Depends(require_category_role(CATEGORY_VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminTutorialService(db).get_category_detail(category_id)
    return success(data.model_dump())


@router.post("/tutorial-categories")
def create_admin_tutorial_category(
    payload: AdminTutorialCategoryIn,
    _: str = Depends(require_category_role(CATEGORY_MANAGE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminTutorialService(db).create_category(payload)
    return success(data.model_dump())


@router.patch("/tutorial-categories/{category_id}")
def update_admin_tutorial_category(
    category_id: str,
    payload: AdminTutorialCategoryIn,
    _: str = Depends(require_category_role(CATEGORY_MANAGE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminTutorialService(db).update_category(category_id, payload)
    return success(data.model_dump())


@router.delete("/tutorial-categories/{category_id}")
def delete_admin_tutorial_category(
    category_id: str,
    _: str = Depends(require_category_role(CATEGORY_MANAGE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    AdminTutorialService(db).delete_category(category_id)
    return success({"ok": True})


@router.post("/tutorial-categories/{category_id}/enable")
def enable_admin_tutorial_category(
    category_id: str,
    _: str = Depends(require_category_role(CATEGORY_MANAGE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminTutorialService(db).enable_category(category_id)
    return success(data.model_dump())


@router.post("/tutorial-categories/{category_id}/disable")
def disable_admin_tutorial_category(
    category_id: str,
    _: str = Depends(require_category_role(CATEGORY_MANAGE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminTutorialService(db).disable_category(category_id)
    return success(data.model_dump())


@router.post("/tutorial-categories/sort")
def sort_admin_tutorial_categories(
    payload: AdminTutorialCategorySortIn,
    _: str = Depends(require_category_role(CATEGORY_MANAGE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = AdminTutorialService(db).sort_categories(payload)
    return success([item.model_dump() for item in data])


@router.get("/tutorial-tags")
def get_admin_tutorial_tags(db: Session = Depends(get_db)) -> dict:
    data = AdminTutorialService(db).list_tags()
    return success([item.model_dump() for item in data])


@router.post("/tutorial-tags")
def create_admin_tutorial_tag(payload: AdminTutorialTagIn, db: Session = Depends(get_db)) -> dict:
    data = AdminTutorialService(db).create_tag(payload)
    return success(data.model_dump())


@router.patch("/tutorial-tags/{tag_id}")
def update_admin_tutorial_tag(tag_id: str, payload: AdminTutorialTagIn, db: Session = Depends(get_db)) -> dict:
    data = AdminTutorialService(db).update_tag(tag_id, payload)
    return success(data.model_dump())


@router.delete("/tutorial-tags/{tag_id}")
def delete_admin_tutorial_tag(tag_id: str, db: Session = Depends(get_db)) -> dict:
    AdminTutorialService(db).delete_tag(tag_id)
    return success({"ok": True})


@router.get("/learning-paths")
def get_admin_learning_paths(db: Session = Depends(get_db)) -> dict:
    data = AdminTutorialService(db).list_learning_paths()
    return success([item.model_dump() for item in data])


@router.post("/learning-paths")
def create_admin_learning_path(payload: AdminLearningPathIn, db: Session = Depends(get_db)) -> dict:
    data = AdminTutorialService(db).create_learning_path(payload)
    return success(data.model_dump())


@router.patch("/learning-paths/{learning_path_id}")
def update_admin_learning_path(learning_path_id: str, payload: AdminLearningPathIn, db: Session = Depends(get_db)) -> dict:
    data = AdminTutorialService(db).update_learning_path(learning_path_id, payload)
    return success(data.model_dump())


@router.delete("/learning-paths/{learning_path_id}")
def delete_admin_learning_path(learning_path_id: str, db: Session = Depends(get_db)) -> dict:
    AdminTutorialService(db).delete_learning_path(learning_path_id)
    return success({"ok": True})


@router.get("/tutorial-operation-logs")
def get_admin_tutorial_operation_logs(
    module: str = Query(default=None),
    action: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> dict:
    query = AdminOperationLogQueryIn(module=module, action=action, page=page, pageSize=pageSize)
    data = AdminTutorialService(db).get_operation_logs(query)
    return success(data.model_dump())
